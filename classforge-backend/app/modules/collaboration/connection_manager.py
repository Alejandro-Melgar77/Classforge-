from typing import Dict, List, Optional
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Dict[str, dict]] = {}
        self.locks: Dict[str, Dict[str, str]] = {}
        self.chat_history: Dict[str, List[dict]] = {}

    async def connect(self, diagram_id: str, user: dict, websocket: WebSocket):
        await websocket.accept()
        if diagram_id not in self.rooms:
            self.rooms[diagram_id] = {}
        if diagram_id not in self.locks:
            self.locks[diagram_id] = {}
            
        user_id = str(user.get("_id", user.get("id")))
        palette = ["#2D6BE4", "#00C896", "#F5A623", "#E74C3C", "#9B51E0", "#00B4D8", "#F72585", "#7209B7"]
        user_color = user.get("color") or palette[abs(hash(user_id)) % len(palette)]
        self.rooms[diagram_id][user_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "user_name": user.get("name", "Usuario"),
            "user_color": user_color,
            "role": user.get("role", "dev"),
            "cursor": None,
            "status": "online"
        }

    async def disconnect(self, diagram_id: str, user_id: str):
        if diagram_id in self.rooms and user_id in self.rooms[diagram_id]:
            del self.rooms[diagram_id][user_id]
            if not self.rooms[diagram_id]:
                del self.rooms[diagram_id]
        
        self.release_all_user_locks(diagram_id, user_id)

    async def broadcast(self, diagram_id: str, message: dict, exclude_user_id: Optional[str] = None):
        if diagram_id in self.rooms:
            for uid, user_data in list(self.rooms[diagram_id].items()):
                if exclude_user_id and uid == exclude_user_id:
                    continue
                ws = user_data["websocket"]
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

    def get_room_users(self, diagram_id: str) -> List[dict]:
        if diagram_id not in self.rooms:
            return []
        users = []
        for uid, user_data in self.rooms[diagram_id].items():
            users.append({
                "user_id": uid,
                "user_name": user_data["user_name"],
                "user_color": user_data["user_color"],
                "role": user_data.get("role", "dev"),
                "cursor": user_data["cursor"],
                "status": user_data.get("status", "online")
            })
        return users

    def acquire_lock(self, diagram_id: str, user_id: str, element_id: str) -> bool:
        if diagram_id not in self.locks:
            self.locks[diagram_id] = {}
        
        current_owner = self.locks[diagram_id].get(element_id)
        if current_owner is None or current_owner == user_id:
            self.locks[diagram_id][element_id] = user_id
            return True
        return False

    def release_lock(self, diagram_id: str, user_id: str, element_id: str):
        if diagram_id in self.locks:
            if self.locks[diagram_id].get(element_id) == user_id:
                del self.locks[diagram_id][element_id]

    def release_all_user_locks(self, diagram_id: str, user_id: str) -> List[str]:
        released_elements = []
        if diagram_id in self.locks:
            to_remove = [el_id for el_id, uid in self.locks[diagram_id].items() if uid == user_id]
            for el_id in to_remove:
                del self.locks[diagram_id][el_id]
                released_elements.append(el_id)
        return released_elements

    def add_chat_message(self, diagram_id: str, user_id: str, user_name: str, user_color: str, content: str) -> dict:
        import datetime
        if diagram_id not in self.chat_history:
            self.chat_history[diagram_id] = []
            
        message = {
            "type": "CHAT_MESSAGE",
            "content": content,
            "user_id": user_id,
            "user_name": user_name,
            "user_color": user_color,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
        self.chat_history[diagram_id].append(message)
        if len(self.chat_history[diagram_id]) > 50:
            self.chat_history[diagram_id].pop(0)
            
        return message

    def get_chat_history(self, diagram_id: str) -> List[dict]:
        return self.chat_history.get(diagram_id, [])

    def update_presence_status(self, diagram_id: str, user_id: str, status: str) -> bool:
        if diagram_id in self.rooms and user_id in self.rooms[diagram_id]:
            self.rooms[diagram_id][user_id]["status"] = status
            return True
        return False

manager = ConnectionManager()
