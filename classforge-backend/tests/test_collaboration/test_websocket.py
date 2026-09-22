import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import asyncio
from app.main import app

# NOTE: This requires DB setup and ws_token setup before tests can run fully.
# The following is a stub illustrating the integration test.

from starlette.websockets import WebSocketDisconnect
from app.modules.collaboration.connection_manager import ConnectionManager

class MockWebSocket:
    async def accept(self): pass
    async def send_json(self, data): pass
    async def receive_text(self): return "{}"

def test_websocket_invalid_token():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/diagrams/60b9c0f99a8b1c4d4c8b4567?token=invalid") as websocket:
            websocket.receive_text()
    assert exc_info.value.code == 4001

@pytest.mark.asyncio
async def test_connection_manager_lifecycle():
    manager = ConnectionManager()
    ws = MockWebSocket()
    diagram_id = "test_diagram"
    user_id = "user1"
    user = {"_id": user_id, "name": "Test User"}
    
    # 1. Connection and presence
    await manager.connect(diagram_id, user, ws)
    users = manager.get_room_users(diagram_id)
    assert len(users) == 1
    assert users[0]["user_id"] == user_id
    assert users[0]["status"] == "online"
    
    # 2. Presence update
    manager.update_presence_status(diagram_id, user_id, "away")
    assert manager.get_room_users(diagram_id)[0]["status"] == "away"
    
    # 3. Chat history management
    for i in range(55):
        manager.add_chat_message(diagram_id, user_id, "Test User", "#000", f"Msg {i}")
    chat = manager.get_chat_history(diagram_id)
    assert len(chat) == 50
    assert chat[-1]["content"] == "Msg 54"
    assert chat[0]["content"] == "Msg 5"
    
    # 4. Locks
    assert manager.acquire_lock(diagram_id, user_id, "node1") == True
    assert manager.acquire_lock(diagram_id, "user2", "node1") == False
    manager.release_lock(diagram_id, user_id, "node1")
    assert manager.acquire_lock(diagram_id, "user2", "node1") == True
    
    # 5. Disconnection
    await manager.disconnect(diagram_id, user_id)
    assert len(manager.get_room_users(diagram_id)) == 0
