"""Realtime collaboration regressions (audit A15, A16, M11)."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.database import db_instance
from app.main import app
from app.modules.collaboration.connection_manager import ConnectionManager


class _WS:
    async def accept(self):
        pass

    async def send_json(self, data):
        pass


def test_room_state_includes_locks_and_colour_is_stable():
    manager = ConnectionManager()
    user = {"_id": "u-1", "name": "Uno", "role": "dev"}

    async def scenario():
        await manager.connect("d-1", user, _WS())
        manager.acquire_lock("d-1", "u-1", "node-a")

        async def send(_):
            pass

        assert manager.get_locks("d-1") == {"node-a": "u-1"}
        color_first = manager.get_room_users("d-1")[0]["user_color"]

        # A different process/instance must derive the same colour (M11).
        other = ConnectionManager()
        await other.connect("d-1", user, _WS())
        assert other.get_room_users("d-1")[0]["user_color"] == color_first

        await manager.disconnect("d-1", "u-1")
        # A closed room must not keep locks or chat history around (A15).
        assert manager.get_locks("d-1") == {}
        assert manager.get_chat_history("d-1") == []
        assert manager.rooms.get("d-1") in (None, {})

    asyncio.run(scenario())


def test_chat_history_released_with_room():
    manager = ConnectionManager()

    async def scenario():
        await manager.connect("d-2", {"_id": "u", "name": "U"}, _WS())
        manager.add_chat_message("d-2", "u", "U", "#fff", "hola")
        assert manager.get_chat_history("d-2")
        await manager.disconnect("d-2", "u")
        assert manager.get_chat_history("d-2") == []

    asyncio.run(scenario())


DIAGRAM_ID = ObjectId("507f1f77bcf86cd799439071")
USER_ID = ObjectId("507f1f77bcf86cd799439072")


def _seed(diagram_exists: bool, token: str):
    async def _run():
        db = db_instance.db
        await db["users"].insert_one({
            "_id": USER_ID,
            "name": "U",
            "role": "dev",
            "is_active": True,
            "is_deleted": False,
            "team_ids": [],
        })
        await db["ws_tokens"].insert_one({
            "token": token,
            "diagram_id": DIAGRAM_ID,
            "user_id": USER_ID,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        })
        if diagram_exists:
            now = datetime.now(timezone.utc)
            await db["diagrams"].insert_one({
                "_id": DIAGRAM_ID,
                "name": "D",
                "created_by": USER_ID,
                "member_ids": [],
                "team_id": None,
                "project_id": None,
                "graph_data": {"nodes": [], "edges": []},
                "is_deleted": False,
                "version": 1,
                "created_at": now,
                "updated_at": now,
            })

    asyncio.run(_run())


def test_ws_close_4003_when_diagram_is_missing():
    _seed(diagram_exists=False, token="tok-missing")

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/ws/diagrams/{DIAGRAM_ID}?token=tok-missing") as ws:
            ws.receive_text()

    assert exc.value.code == 4003


def test_room_state_payload_contains_locks_key():
    _seed(diagram_exists=True, token="tok-ok")

    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/ws/diagrams/{DIAGRAM_ID}?token=tok-ok") as ws:
        ws.send_json({"type": "JOIN"})
        state = ws.receive_json()

    assert state["type"] == "ROOM_STATE"
    assert "locks" in state
    assert state["locks"] == {}
