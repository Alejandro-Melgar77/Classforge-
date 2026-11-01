from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import WebSocket


class RoomDict(dict):
    """Dictionary supporting transparent key lookup for both prefixed (e.g. 'diagram:123')
    and raw ('123') room identifiers, ensuring backward-compatibility with existing diagram WS tests.
    """
    def _alt_keys(self, key: str):
        yield key
        if ":" in key:
            prefix, rest = key.split(":", 1)
            if prefix == "diagram":
                yield rest
        else:
            yield f"diagram:{key}"

    def __getitem__(self, key: str):
        for k in self._alt_keys(key):
            if super().__contains__(k):
                return super().__getitem__(k)
        raise KeyError(key)

    def __contains__(self, key: object):
        if not isinstance(key, str):
            return super().__contains__(key)
        for k in self._alt_keys(key):
            if super().__contains__(k):
                return True
        return False

    def get(self, key: str, default=None):
        for k in self._alt_keys(key):
            if super().__contains__(k):
                return super().__getitem__(k)
        return default

    def __delitem__(self, key: str):
        for k in self._alt_keys(key):
            if super().__contains__(k):
                return super().__delitem__(k)
        raise KeyError(key)


class ConnectionManager:
    """Manages active WebSocket connections for diagram and project collaboration rooms.
    Supports room keys formatted as 'diagram:<id>' and 'project:<id>'.
    """
    def __init__(self):
        self.rooms: RoomDict = RoomDict()
        self.locks: RoomDict = RoomDict()
        self.chat_history: RoomDict = RoomDict()

    def _resolve_room_key(self, room_id: str) -> str:
        """Normalizes room keys; preserves existing prefixes or registers as is."""
        if ":" in room_id:
            return room_id
        # Check if already present under raw or diagram prefix
        if room_id in self.rooms:
            # Return canonical key if found in underlying dict
            if dict.__contains__(self.rooms, f"diagram:{room_id}"):
                return f"diagram:{room_id}"
            return room_id
        return f"diagram:{room_id}"

    async def connect(self, room_id: str, user: dict, websocket: WebSocket):
        await websocket.accept()
        key = self._resolve_room_key(room_id)
        if key not in self.rooms:
            self.rooms[key] = {}
        if key not in self.locks:
            self.locks[key] = {}
            
        user_id = str(user.get("_id", user.get("id")))
        palette = ["#2D6BE4", "#00C896", "#F5A623", "#E74C3C", "#9B51E0", "#00B4D8", "#F72585", "#7209B7"]
        user_color = user.get("color") or palette[abs(hash(user_id)) % len(palette)]
        self.rooms[key][user_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "user_name": user.get("name", "Usuario"),
            "user_color": user_color,
            "role": user.get("role", "dev"),
            "cursor": None,
            "status": "online"
        }

    async def disconnect(self, room_id: str, user_id: str):
        key = self._resolve_room_key(room_id)
        room_data = self.rooms.get(key)
        if room_data and user_id in room_data:
            del room_data[user_id]
            if not room_data:
                try:
                    del self.rooms[key]
                except KeyError:
                    pass
        
        self.release_all_user_locks(room_id, user_id)

    async def broadcast(self, room_id: str, message: dict, exclude_user_id: Optional[str] = None):
        key = self._resolve_room_key(room_id)
        room_data = self.rooms.get(key)
        if room_data:
            for uid, user_data in list(room_data.items()):
                if exclude_user_id and uid == exclude_user_id:
                    continue
                ws = user_data["websocket"]
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

    def get_room_users(self, room_id: str) -> List[dict]:
        key = self._resolve_room_key(room_id)
        room_data = self.rooms.get(key)
        if not room_data:
            return []
        users = []
        for uid, user_data in room_data.items():
            users.append({
                "user_id": uid,
                "user_name": user_data["user_name"],
                "user_color": user_data["user_color"],
                "role": user_data.get("role", "dev"),
                "cursor": user_data["cursor"],
                "status": user_data.get("status", "online")
            })
        return users

    def is_locked_by_other(self, diagram_id: str, element_id: str, user_id: str) -> bool:
        key = self._resolve_room_key(diagram_id)
        lock_data = self.locks.get(key)
        if not lock_data:
            return False
        owner = lock_data.get(element_id)
        if owner is not None and owner != user_id:
            return True
        return False

    def acquire_lock(self, diagram_id: str, user_id: str, element_id: str) -> bool:
        key = self._resolve_room_key(diagram_id)
        if key not in self.locks:
            self.locks[key] = {}
        
        lock_data = self.locks[key]
        current_owner = lock_data.get(element_id)
        if current_owner is None or current_owner == user_id:
            lock_data[element_id] = user_id
            return True
        return False

    def release_lock(self, diagram_id: str, user_id: str, element_id: str):
        key = self._resolve_room_key(diagram_id)
        lock_data = self.locks.get(key)
        if lock_data and lock_data.get(element_id) == user_id:
            del lock_data[element_id]

    def release_all_user_locks(self, diagram_id: str, user_id: str) -> List[str]:
        released_elements = []
        key = self._resolve_room_key(diagram_id)
        lock_data = self.locks.get(key)
        if lock_data:
            to_remove = [el_id for el_id, uid in lock_data.items() if uid == user_id]
            for el_id in to_remove:
                del lock_data[el_id]
                released_elements.append(el_id)
        return released_elements

    def add_chat_message(self, diagram_id: str, user_id: str, user_name: str, user_color: str, content: str) -> Dict[str, Any]:
        """Record a chat message in the ephemeral diagram chat history."""
        key = self._resolve_room_key(diagram_id)
        if key not in self.chat_history:
            self.chat_history[key] = []
            
        message = {
            "type": "CHAT_MESSAGE",
            "content": content,
            "user_id": user_id,
            "user_name": user_name,
            "user_color": user_color,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.chat_history[key].append(message)
        if len(self.chat_history[key]) > 50:
            self.chat_history[key].pop(0)
            
        return message

    def get_chat_history(self, diagram_id: str) -> List[dict]:
        key = self._resolve_room_key(diagram_id)
        return self.chat_history.get(key, [])

    def update_presence_status(self, room_id: str, user_id: str, status: str) -> bool:
        key = self._resolve_room_key(room_id)
        room_data = self.rooms.get(key)
        if room_data and user_id in room_data:
            room_data[user_id]["status"] = status
            return True
        return False


manager = ConnectionManager()
