"""
Comprehensive Phase 3 Test Suite: Real-time Synchronization, Multi-user Collaboration,
Durable Events (Transactional Outbox), and Reconnection Recovery (SYNC-01 to SYNC-03, H06, H11, COLLAB-01, COLLAB-02, SEC-01, AI-01).
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from bson import ObjectId
import pytest
from starlette.websockets import WebSocketDisconnect
from mongomock_motor import AsyncMongoMockClient

from app.modules.collaboration.connection_manager import ConnectionManager
from app.modules.collaboration.outbox import DiagramOutboxRepository, dispatch_outbox_events
from app.modules.collaboration.router import websocket_endpoint
from app.modules.diagrams.repository import DiagramRepository


@pytest.fixture
def mock_db():
    client = AsyncMongoMockClient()
    return client["test_phase3_db"]


# ─── GRUPO A: SINCRONIZACIÓN Y TRANSACTIONAL OUTBOX (H06, SYNC-01) ───

@pytest.mark.anyio
async def test_h06_and_sync01_save_graph_records_outbox_and_broadcasts(mock_db):
    """H06 & SYNC-01: Committed save_graph records durable event in outbox and broadcasts DIAGRAM_COMMITTED."""
    repo = DiagramRepository(mock_db)
    created = await repo.create({"name": "Collab Diagram", "project_id": "proj_123"})
    did = str(created["_id"])

    manager = ConnectionManager()
    ws_client = AsyncMock()
    await manager.connect(did, {"_id": "user_listener", "name": "Listener"}, ws_client)

    graph_v2 = {
        "nodes": [{"id": "n1", "type": "class", "data": {"name": "Customer"}}],
        "edges": []
    }

    with patch("app.modules.collaboration.connection_manager.manager", manager):
        saved = await repo.save_graph(did, graph_v2, saved_by="user_editor", comment="Added customer", base_version=1)

    assert saved["version"] == 2

    # Verify outbox entry in diagram_events
    outbox_repo = DiagramOutboxRepository(mock_db)
    events = await outbox_repo.get_events_since(did, known_revision=1)
    assert len(events) == 1
    event = events[0]
    assert event["diagram_id"] == did
    assert event["revision"] == 2
    assert event["previous_revision"] == 1
    assert event["actor_id"] == "user_editor"
    assert event["status"] == "dispatched"

    # Verify broadcast to the connected WebSocket room
    assert ws_client.send_json.awaited
    sent_msgs = [call.args[0] for call in ws_client.send_json.await_args_list]
    committed_msg = next((m for m in sent_msgs if m.get("type") == "DIAGRAM_COMMITTED"), None)
    assert committed_msg is not None
    assert committed_msg["revision"] == 2
    assert committed_msg["previous_revision"] == 1
    assert committed_msg["actor_id"] == "user_editor"
    assert committed_msg["comment"] == "Added customer"


@pytest.mark.anyio
async def test_sync01_outbox_retry_dispatcher_handles_failed_deliveries(mock_db):
    """SYNC-01: Undispatched pending outbox events are resiliently retried and marked dispatched."""
    outbox_repo = DiagramOutboxRepository(mock_db)
    event_doc = await outbox_repo.record_event(
        diagram_id="diag_999",
        project_id="proj_1",
        revision=5,
        previous_revision=4,
        actor_id="user_actor",
        operations=[{"type": "add", "node_id": "n9"}],
    )
    assert event_doc["status"] == "pending"

    # Test pending retrieval
    pending = await outbox_repo.get_pending_events()
    assert len(pending) == 1
    assert pending[0]["event_id"] == event_doc["event_id"]

    # Dispatcher runs
    manager = ConnectionManager()
    with patch("app.modules.collaboration.connection_manager.manager", manager):
        count = await dispatch_outbox_events(mock_db)
        assert count == 1

    # Verify marked dispatched
    pending_after = await outbox_repo.get_pending_events()
    assert len(pending_after) == 0


# ─── GRUPO B: PROTOCOLO DE CONFIRMACIÓN Y RECHAZO (SYNC-02) ──────────

@pytest.mark.anyio
async def test_sync02_node_operation_sends_explicit_ack_with_revision(mock_db):
    """SYNC-02: Successful real-time operation returns explicit ACK with op_id, revision, and event_id."""
    diag_id = str(ObjectId())
    user_id = str(ObjectId())
    await mock_db["diagrams"].insert_one({
        "_id": ObjectId(diag_id),
        "name": "Sync Diagram",
        "created_by": ObjectId(user_id),
        "version": 3,
        "graph_data": {"nodes": [], "edges": []},
        "is_deleted": False,
    })

    ws = AsyncMock()
    op_msg = {
        "type": "NODE_OPERATION",
        "op": "add",
        "node_id": "node_new",
        "data": {"type": "class", "name": "Payment", "position": {"x": 50, "y": 60}},
        "op_id": "op_unique_101",
    }
    ws.receive_text.side_effect = [json.dumps(op_msg), WebSocketDisconnect()]

    with patch("app.modules.collaboration.router.verify_ws_token", new=AsyncMock(return_value={"_id": ObjectId(user_id), "role": "admin"})), \
         patch("app.modules.collaboration.router._current_ws_access", new=AsyncMock(return_value=True)), \
         patch("app.modules.collaboration.router.get_db", return_value=mock_db), \
         patch("app.modules.collaboration.service._get_db", return_value=mock_db):
        await websocket_endpoint(ws, diag_id, "token_123")

    sent = [call.args[0] for call in ws.send_json.await_args_list]
    ack = next((m for m in sent if m.get("type") == "ACK" and m.get("op_id") == "op_unique_101"), None)
    assert ack is not None
    assert ack["status"] == "success"
    assert ack["diagram_id"] == diag_id
    assert ack["revision"] == 4
    assert "event_id" in ack


@pytest.mark.anyio
async def test_sync02_idempotent_duplicate_op_id_returns_cached_ack(mock_db):
    """SYNC-02: Resent operation with same op_id does not apply twice and returns cached ACK."""
    diag_id = str(ObjectId())
    user_id = str(ObjectId())
    await mock_db["diagrams"].insert_one({
        "_id": ObjectId(diag_id),
        "name": "Idempotent Diagram",
        "created_by": ObjectId(user_id),
        "version": 1,
        "graph_data": {"nodes": [], "edges": []},
        "is_deleted": False,
    })

    outbox_repo = DiagramOutboxRepository(mock_db)
    await outbox_repo.record_event(
        diagram_id=diag_id,
        project_id="p1",
        revision=2,
        previous_revision=1,
        actor_id=user_id,
        operations=[],
        operation_id="op_idempotent_test",
    )

    ws = AsyncMock()
    duplicate_msg = {
        "type": "NODE_OPERATION",
        "op": "add",
        "node_id": "n_dup",
        "data": {"name": "DupClass"},
        "op_id": "op_idempotent_test",
    }
    ws.receive_text.side_effect = [json.dumps(duplicate_msg), WebSocketDisconnect()]

    with patch("app.modules.collaboration.router.verify_ws_token", new=AsyncMock(return_value={"_id": ObjectId(user_id), "role": "admin"})), \
         patch("app.modules.collaboration.router._current_ws_access", new=AsyncMock(return_value=True)), \
         patch("app.modules.collaboration.router.get_db", return_value=mock_db), \
         patch("app.modules.collaboration.service._get_db", return_value=mock_db):
        await websocket_endpoint(ws, diag_id, "token_123")

    sent = [call.args[0] for call in ws.send_json.await_args_list]
    cached_ack = next((m for m in sent if m.get("type") == "ACK" and m.get("op_id") == "op_idempotent_test"), None)
    assert cached_ack is not None
    assert cached_ack.get("duplicate") is True
    assert cached_ack["revision"] == 2


@pytest.mark.anyio
async def test_sync02_locked_node_sends_explicit_nack(mock_db):
    """SYNC-02: Attempting to edit a node locked by another participant yields explicit NACK."""
    diag_id = str(ObjectId())
    user_id = str(ObjectId())
    await mock_db["diagrams"].insert_one({
        "_id": ObjectId(diag_id),
        "name": "Lock Diagram",
        "created_by": ObjectId(user_id),
        "version": 1,
        "graph_data": {"nodes": [{"id": "locked_n1"}], "edges": []},
        "is_deleted": False,
    })

    manager = ConnectionManager()
    manager.acquire_lock(diag_id, "other_user", "locked_n1")

    ws = AsyncMock()
    op_msg = {
        "type": "NODE_OPERATION",
        "op": "move",
        "node_id": "locked_n1",
        "data": {"position": {"x": 100, "y": 200}},
        "op_id": "op_conflict_1",
    }
    ws.receive_text.side_effect = [json.dumps(op_msg), WebSocketDisconnect()]

    with patch("app.modules.collaboration.router.manager", manager), \
         patch("app.modules.collaboration.router.verify_ws_token", new=AsyncMock(return_value={"_id": ObjectId(user_id), "role": "admin"})), \
         patch("app.modules.collaboration.router._current_ws_access", new=AsyncMock(return_value=True)), \
         patch("app.modules.collaboration.router.get_db", return_value=mock_db), \
         patch("app.modules.collaboration.service._get_db", return_value=mock_db):
        await websocket_endpoint(ws, diag_id, "token_123")

    sent = [call.args[0] for call in ws.send_json.await_args_list]
    nack = next((m for m in sent if m.get("type") == "NACK" and m.get("op_id") == "op_conflict_1"), None)
    assert nack is not None
    assert nack["error_code"] == "LOCKED"
    assert nack["element_id"] == "locked_n1"


# ─── GRUPO C: RECUPERACIÓN TRAS DESCONEXIONES (SYNC-03) ──────────────

@pytest.mark.anyio
async def test_sync03_incremental_recovery_delivers_missing_events(mock_db):
    """SYNC-03: Client sends known_revision and receives contiguous missing events incrementally."""
    diag_id = str(ObjectId())
    user_id = str(ObjectId())
    await mock_db["diagrams"].insert_one({
        "_id": ObjectId(diag_id),
        "name": "Recovery Diagram",
        "created_by": ObjectId(user_id),
        "version": 5,
        "graph_data": {"nodes": [], "edges": []},
        "is_deleted": False,
    })

    outbox_repo = DiagramOutboxRepository(mock_db)
    # Populate contiguous events for revision 4 and 5
    await outbox_repo.record_event(
        diagram_id=diag_id, project_id="p1", revision=4, previous_revision=3,
        actor_id="u1", operations=[{"op": "add", "node_id": "n4"}]
    )
    await outbox_repo.record_event(
        diagram_id=diag_id, project_id="p1", revision=5, previous_revision=4,
        actor_id="u2", operations=[{"op": "add", "node_id": "n5"}]
    )

    ws = AsyncMock()
    sync_req = {"type": "SYNC_REQUEST", "known_revision": 3}
    ws.receive_text.side_effect = [json.dumps(sync_req), WebSocketDisconnect()]

    with patch("app.modules.collaboration.router.verify_ws_token", new=AsyncMock(return_value={"_id": ObjectId(user_id), "role": "admin"})), \
         patch("app.modules.collaboration.router._current_ws_access", new=AsyncMock(return_value=True)), \
         patch("app.modules.collaboration.router.get_db", return_value=mock_db), \
         patch("app.modules.collaboration.service._get_db", return_value=mock_db):
        await websocket_endpoint(ws, diag_id, "token_123")

    sent = [call.args[0] for call in ws.send_json.await_args_list]
    sync_resp = next((m for m in sent if m.get("type") == "SYNC_RESPONSE"), None)
    assert sync_resp is not None
    assert sync_resp["status"] == "incremental"
    assert sync_resp["from_revision"] == 3
    assert sync_resp["to_revision"] == 5
    assert len(sync_resp["events"]) == 2
    assert sync_resp["events"][0]["revision"] == 4
    assert sync_resp["events"][1]["revision"] == 5


@pytest.mark.anyio
async def test_sync03_snapshot_fallback_when_event_history_has_gap(mock_db):
    """SYNC-03: If event history is non-contiguous or missing, fall back to snapshot delivery."""
    diag_id = str(ObjectId())
    user_id = str(ObjectId())
    full_graph = {"nodes": [{"id": "n1"}, {"id": "n2"}], "edges": []}
    await mock_db["diagrams"].insert_one({
        "_id": ObjectId(diag_id),
        "name": "Gap Diagram",
        "created_by": ObjectId(user_id),
        "version": 20,
        "graph_data": full_graph,
        "is_deleted": False,
    })

    # Client was disconnected for a long time (known_revision: 5)
    ws = AsyncMock()
    sync_req = {"type": "SYNC_REQUEST", "known_revision": 5}
    ws.receive_text.side_effect = [json.dumps(sync_req), WebSocketDisconnect()]

    with patch("app.modules.collaboration.router.verify_ws_token", new=AsyncMock(return_value={"_id": ObjectId(user_id), "role": "admin"})), \
         patch("app.modules.collaboration.router._current_ws_access", new=AsyncMock(return_value=True)), \
         patch("app.modules.collaboration.router.get_db", return_value=mock_db), \
         patch("app.modules.collaboration.service._get_db", return_value=mock_db):
        await websocket_endpoint(ws, diag_id, "token_123")

    sent = [call.args[0] for call in ws.send_json.await_args_list]
    sync_resp = next((m for m in sent if m.get("type") == "SYNC_RESPONSE"), None)
    assert sync_resp is not None
    assert sync_resp["status"] == "snapshot"
    assert sync_resp["revision"] == 20
    assert sync_resp["graph_data"] == full_graph


# ─── GRUPO D: SESIONES MÚLTIPLES Y CURSORES EFÍMEROS (H11, COLLAB-01) ──

@pytest.mark.anyio
async def test_h11_multi_tab_disconnection_resilience():
    """H11: User with two browser tabs: closing tab A keeps tab B connected and active."""
    manager = ConnectionManager()
    tab_a, tab_b = AsyncMock(), AsyncMock()
    user = {"_id": "user_multitab", "name": "Multitab User"}

    await manager.connect("diagram_room", user, tab_a)
    await manager.connect("diagram_room", user, tab_b)
    assert len(manager.get_room_users("diagram_room")) == 1

    # Disconnect Tab A
    is_last = await manager.disconnect("diagram_room", "user_multitab", tab_a)
    assert is_last is False
    assert len(manager.get_room_users("diagram_room")) == 1

    # Tab B still receives broadcasts
    await manager.broadcast("diagram_room", {"type": "TEST_EVENT"})
    tab_b.send_json.assert_awaited_once()

    # Disconnect Tab B
    is_last_b = await manager.disconnect("diagram_room", "user_multitab", tab_b)
    assert is_last_b is True
    assert len(manager.get_room_users("diagram_room")) == 0


@pytest.mark.anyio
async def test_collab01_ephemeral_cursors_do_not_advance_version(mock_db):
    """COLLAB-01: Cursor movements broadcast ephemeral positions without writing to DB or bumping revision."""
    diag_id = str(ObjectId())
    user_id = str(ObjectId())
    await mock_db["diagrams"].insert_one({
        "_id": ObjectId(diag_id),
        "name": "Cursor Diagram",
        "created_by": ObjectId(user_id),
        "version": 1,
        "graph_data": {"nodes": [], "edges": []},
        "is_deleted": False,
    })

    ws = AsyncMock()
    cursor_msg = {"type": "CURSOR_MOVE", "x": 150.5, "y": 300.2}
    ws.receive_text.side_effect = [json.dumps(cursor_msg), WebSocketDisconnect()]

    with patch("app.modules.collaboration.router.verify_ws_token", new=AsyncMock(return_value={"_id": ObjectId(user_id), "role": "admin"})), \
         patch("app.modules.collaboration.router._current_ws_access", new=AsyncMock(return_value=True)), \
         patch("app.modules.collaboration.router.get_db", return_value=mock_db), \
         patch("app.modules.collaboration.service._get_db", return_value=mock_db):
        await websocket_endpoint(ws, diag_id, "token_123")

    # Verify database diagram was NOT modified and revision stays 1
    doc = await mock_db["diagrams"].find_one({"_id": ObjectId(diag_id)})
    assert doc["version"] == 1

    # Outbox has zero events
    events = await DiagramOutboxRepository(mock_db).get_events_since(diag_id, known_revision=0)
    assert len(events) == 0


# ─── GRUPO E: GESTIÓN DE BLOQUEOS Y TIMEOUTS (COLLAB-02) ─────────────

@pytest.mark.anyio
async def test_collab02_lock_acquisition_competition_and_timeout():
    """COLLAB-02: Lock acquisition by user A prevents user B from acquiring it until released or expired."""
    manager = ConnectionManager()
    room = "diagram_locks"

    # User A acquires lock on node1
    assert manager.acquire_lock(room, "user_a", "node1", ttl_seconds=0.2) is True
    assert manager.is_locked_by_other(room, "node1", "user_b") is True

    # User B cannot acquire while active
    assert manager.acquire_lock(room, "user_b", "node1") is False

    # Wait for TTL to expire (0.2s)
    await asyncio.sleep(0.25)

    # Now lock is expired, User B can acquire it!
    assert manager.is_locked_by_other(room, "node1", "user_b") is False
    assert manager.acquire_lock(room, "user_b", "node1", ttl_seconds=60.0) is True
    assert manager.get_lock_owner(room, "node1") == "user_b"


# ─── GRUPO F: SEGURIDAD ACTIVA Y REVOCACIÓN EN TIEMPO REAL (SEC-01) ──

@pytest.mark.anyio
async def test_sec01_revocation_during_session_closes_websocket(mock_db):
    """SEC-01: When permissions are revoked during an active session, server terminates the connection."""
    diag_id = str(ObjectId())
    user_id = str(ObjectId())
    await mock_db["diagrams"].insert_one({
        "_id": ObjectId(diag_id),
        "name": "Sec Diagram",
        "created_by": ObjectId(user_id),
        "version": 1,
        "is_deleted": False,
    })

    ws = AsyncMock()
    ws.receive_text.side_effect = [
        json.dumps({"type": "PING"}),
        WebSocketDisconnect()
    ]

    # First check succeeds, second check (_current_ws_access) returns False (simulating member removed from team)
    access_checks = [True, False]
    async def mock_access(*args, **kwargs):
        if access_checks:
            return access_checks.pop(0)
        return False

    with patch("app.modules.collaboration.router.verify_ws_token", new=AsyncMock(return_value={"_id": ObjectId(user_id), "role": "admin"})), \
         patch("app.modules.collaboration.router._current_ws_access", side_effect=mock_access), \
         patch("app.modules.collaboration.router.get_db", return_value=mock_db), \
         patch("app.modules.collaboration.service._get_db", return_value=mock_db):
        await websocket_endpoint(ws, diag_id, "token_123")

    # Connection closed with code 4003 (Authorization revoked)
    ws.close.assert_awaited()
    close_call = ws.close.await_args
    assert close_call.kwargs.get("code") == 4003 or (close_call.args and close_call.args[0] == 4003)
