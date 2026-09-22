from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class WSMessage(BaseModel):
    type: str

class JoinMessage(WSMessage):
    type: str = "JOIN"
    # Metadata about the user joining might be expected, but we get user_id from token usually.
    # The prompt says: "Handshake containing user metadata."
    user_name: Optional[str] = None
    user_color: Optional[str] = None

class UserJoinedMessage(WSMessage):
    type: str = "USER_JOINED"
    user_id: str
    user_name: Optional[str] = None
    user_color: Optional[str] = None

class UserLeftMessage(WSMessage):
    type: str = "USER_LEFT"
    user_id: str

class RoomStateMessage(WSMessage):
    type: str = "ROOM_STATE"
    users: List[dict]
    # We might want to send current locks here too if needed, but the prompt says "current room state".

class CursorMoveMessage(WSMessage):
    type: str = "CURSOR_MOVE"
    x: float
    y: float

class CursorUpdateMessage(WSMessage):
    type: str = "CURSOR_UPDATE"
    user_id: str
    x: float
    y: float

class NodeOperationMessage(WSMessage):
    type: str = "NODE_OPERATION"
    op: str
    node_id: str
    data: Optional[Dict[str, Any]] = None

class EdgeOperationMessage(WSMessage):
    type: str = "EDGE_OPERATION"
    op: str
    edge_id: str
    data: Optional[Dict[str, Any]] = None

class LockAcquireMessage(WSMessage):
    type: str = "LOCK_ACQUIRE"
    element_id: str

class LockGrantedMessage(WSMessage):
    type: str = "LOCK_GRANTED"
    element_id: str
    user_id: str

class LockRejectedMessage(WSMessage):
    type: str = "LOCK_REJECTED"
    element_id: str

class LockReleaseMessage(WSMessage):
    type: str = "LOCK_RELEASE"
    element_id: str

class LockReleasedMessage(WSMessage):
    type: str = "LOCK_RELEASED"
    element_id: str
    user_id: str

class PingMessage(WSMessage):
    type: str = "PING"

class PongMessage(WSMessage):
    type: str = "PONG"

class ChatMessage(WSMessage):
    type: str = "CHAT_MESSAGE"
    content: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_color: Optional[str] = None
    timestamp: Optional[str] = None

class PresenceStatusMessage(WSMessage):
    type: str = "PRESENCE_STATUS"
    status: str
    user_id: Optional[str] = None
