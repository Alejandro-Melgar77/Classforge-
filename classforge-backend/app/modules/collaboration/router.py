import asyncio
import json
import logging
import time
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.authz import can_access_diagram, can_access_project
from app.core.database import get_db
from app.core.tasks import spawn
from app.modules.collaboration.connection_manager import manager
from app.modules.collaboration.service import (
    verify_ws_token,
    verify_project_ws_token,
    update_diagram_graph_data,
)

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_MESSAGE_BYTES = 64 * 1024  # 64 KB
MAX_BURST_PER_SECOND = 60      # 60 msg/s


async def _current_ws_access(db, user_id: str, resource_id: str, is_project: bool) -> bool:
    """Recheck live identity and membership, including revocation after handshake."""
    if db is None:
        return False
    def ref(value):
        return ObjectId(str(value)) if ObjectId.is_valid(str(value)) else value
    user = await db.users.find_one({"_id": ref(user_id), "is_active": True, "is_deleted": False})
    if not user:
        return False
    if is_project:
        project = await db.projects.find_one({"_id": ref(resource_id), "is_deleted": False})
        diagram = None
    else:
        diagram = await db.diagrams.find_one({"_id": ref(resource_id), "is_deleted": False})
        if not diagram:
            return False
        project = await db.projects.find_one({"_id": ref(diagram['project_id']), "is_deleted": False}) if diagram.get('project_id') else None
        if diagram.get('project_id') and not project:
            return False
    team_id = (project or {}).get('team_id') or (diagram or {}).get('team_id')
    team = await db.teams.find_one({"_id": ref(team_id), "is_deleted": False}) if team_id else None
    if team_id and not team:
        return False
    # The team document is authoritative; stale denormalized user.team_ids must
    # not retain access after removal from the team.
    user = {**user, "team_ids": []}
    if project and not can_access_project(user, project, team):
        return False
    if is_project:
        return bool(project)
    return can_access_diagram(user, diagram, team, project)


async def _trigger_diagram_changed_helper(diagram_id: str, user_id: str):
    """Notifies trigger manager of diagram edit events with origin checks."""
    try:
        db = get_db()
        if db is not None:
            obj_id = ObjectId(diagram_id) if ObjectId.is_valid(diagram_id) else diagram_id
            diag = await db["diagrams"].find_one({"_id": obj_id}, {"project_id": 1})
            if diag and diag.get("project_id"):
                origin = "ai" if user_id.startswith("ai:") else "human"
                from app.ai_team.application.triggers import get_triggers
                triggers = get_triggers(db)
                await triggers.on_diagram_changed(str(diag["project_id"]), diagram_id, origin=origin)
    except Exception as err:
        logger.debug(f"[DiagramWS] Failed to trigger diagram_changed: {err}")


@router.websocket("/diagrams/{diagram_id}")
async def websocket_endpoint(websocket: WebSocket, diagram_id: str, token: str = Query(...)):
    user = await verify_ws_token(diagram_id, token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Re-validate resource access: a short-lived token must not outlive a
    # permission change (the token alone used to be the only gate).
    db = get_db()
    if db is not None:
        try:
            oid = ObjectId(diagram_id) if ObjectId.is_valid(diagram_id) else diagram_id
            diagram = await db["diagrams"].find_one({"_id": oid, "is_deleted": False})
            if not diagram:
                await websocket.close(code=4003, reason="Diagram not found")
                return

            team = None
            if diagram.get("team_id"):
                team_oid = ObjectId(str(diagram["team_id"]))
                team = await db["teams"].find_one({"_id": team_oid, "is_deleted": False})

            project = None
            if diagram.get("project_id"):
                project_oid = ObjectId(str(diagram["project_id"]))
                project = await db["projects"].find_one({"_id": project_oid, "is_deleted": False})
                if project and not team and project.get("team_id"):
                    team = await db["teams"].find_one({"_id": ObjectId(str(project["team_id"])), "is_deleted": False})

            if not can_access_diagram(user, diagram, team, project):
                await websocket.close(code=4003, reason="Forbidden")
                return
        except Exception as exc:
            logger.error(f"[DiagramWS] Error verifying authorization: {exc}")
            await websocket.close(code=4003, reason="Forbidden")
            return

    user_id = str(user.get("_id", user.get("id")))
    if get_db() is not None and not await _current_ws_access(get_db(), user_id, diagram_id, False):
        await websocket.close(code=4003, reason="Forbidden")
        return
    await manager.connect(diagram_id, user, websocket,
                          authorize=lambda: _current_ws_access(get_db(), user_id, diagram_id, False))
    message_timestamps = []

    try:
        while True:
            data = await websocket.receive_text()
            if not await _current_ws_access(get_db(), user_id, diagram_id, False):
                await websocket.close(code=4003, reason="Authorization revoked")
                break

            # 1. Message size check (64 KB)
            if len(data.encode("utf-8")) > MAX_MESSAGE_BYTES:
                logger.warning(f"Connection from user {user_id} exceeded max message size (64KB). Closing.")
                await websocket.close(code=4008, reason="Message size exceeds 64KB limit")
                break

            # 2. Message burst rate check (60 msg/s)
            now_ts = time.monotonic()
            message_timestamps = [t for t in message_timestamps if now_ts - t < 1.0]
            if len(message_timestamps) >= MAX_BURST_PER_SECOND:
                logger.warning(f"Connection from user {user_id} exceeded message burst rate (60 msg/s). Closing.")
                await websocket.close(code=4008, reason="Message rate limit exceeded")
                break
            message_timestamps.append(now_ts)

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue

            if not isinstance(message, dict):
                await websocket.send_json({"type": "OP_REJECTED", "reason": "invalid_message"})
                continue

            msg_type = message.get("type")
            if not msg_type:
                continue

            if msg_type == "JOIN":
                user_info = manager.rooms.get(diagram_id, {}).get(user_id, {})
                join_msg = {
                    "type": "USER_JOINED",
                    "user_id": user_id,
                    "user_name": user_info.get("user_name", "Usuario"),
                    "user_color": user_info.get("user_color", "#2D6BE4"),
                    "role": user_info.get("role", "dev"),
                    "status": "online"
                }
                await manager.broadcast(diagram_id, join_msg, exclude_user_id=user_id)
                
                users = manager.get_room_users(diagram_id)
                chat_history = manager.get_chat_history(diagram_id)
                room_state = {
                    "type": "ROOM_STATE",
                    "users": users,
                    "locks": manager.get_locks(diagram_id),
                    "chat_history": chat_history
                }
                await websocket.send_json(room_state)

            elif msg_type == "CURSOR_MOVE":
                if "x" in message and "y" in message and diagram_id in manager.rooms and user_id in manager.rooms[diagram_id]:
                    manager.rooms[diagram_id][user_id]["cursor"] = {"x": message["x"], "y": message["y"]}
                    cursor_msg = {
                        "type": "CURSOR_UPDATE",
                        "user_id": user_id,
                        "x": message["x"],
                        "y": message["y"],
                        "user_name": manager.rooms[diagram_id][user_id].get("user_name", "Usuario"),
                        "user_color": manager.rooms[diagram_id][user_id].get("user_color", "#2D6BE4")
                    }
                    await manager.broadcast(diagram_id, cursor_msg, exclude_user_id=user_id)

            elif msg_type == "NODE_OPERATION":
                op = message.get("op")
                node_id = message.get("node_id")
                node_data = message.get("data")
                op_id = message.get("op_id") or message.get("operation_id")

                if user.get("role") in ("viewer", "guest", "readonly") or user.get("read_only") is True:
                    await websocket.send_json({"type": "OP_REJECTED", "element_id": node_id, "reason": "read_only"})
                    if op_id:
                        await websocket.send_json({
                            "type": "NACK",
                            "op_id": op_id,
                            "diagram_id": diagram_id,
                            "element_id": node_id,
                            "error_code": "READ_ONLY",
                            "message": "Operación rechazada: permiso de sólo lectura"
                        })
                    continue
                if op not in ("add", "move", "update", "delete") or not isinstance(node_id, str) or not node_id or (op != "delete" and (not isinstance(node_data, dict) or not node_data)):
                    await websocket.send_json({"type": "OP_REJECTED", "element_id": node_id, "reason": "invalid_operation"})
                    if op_id:
                        await websocket.send_json({
                            "type": "NACK",
                            "op_id": op_id,
                            "diagram_id": diagram_id,
                            "element_id": node_id,
                            "error_code": "INVALID_OPERATION",
                            "message": "Operación inválida"
                        })
                    continue
                if op and node_id:
                    # Idempotency check: if op_id was already committed, return existing ACK
                    if op_id and db is not None:
                        try:
                            from app.modules.collaboration.outbox import DiagramOutboxRepository
                            outbox_repo = DiagramOutboxRepository(db)
                            existing_ev = await outbox_repo.col.find_one({"diagram_id": str(diagram_id), "operation_id": op_id})
                            if existing_ev:
                                await websocket.send_json({
                                    "type": "ACK",
                                    "op_id": op_id,
                                    "diagram_id": diagram_id,
                                    "revision": existing_ev.get("revision", 1),
                                    "event_id": existing_ev.get("event_id"),
                                    "status": "success",
                                    "duplicate": True
                                })
                                continue
                        except Exception as e_dup:
                            logger.debug(f"[DiagramWS] Deduplication check warning: {e_dup}")

                    # Check if locked by another user
                    if manager.is_locked_by_other(diagram_id, node_id, user_id):
                        await websocket.send_json({
                            "type": "OP_REJECTED",
                            "element_id": node_id,
                            "reason": "locked"
                        })
                        if op_id:
                            await websocket.send_json({
                                "type": "NACK",
                                "op_id": op_id,
                                "diagram_id": diagram_id,
                                "element_id": node_id,
                                "error_code": "LOCKED",
                                "message": "El nodo está bloqueado por otro usuario"
                            })
                        continue

                    # Persist before broadcasting: if the write fails the other
                    # clients must not apply a change that was never stored.
                    new_rev = 1
                    try:
                        res_rev = await update_diagram_graph_data(diagram_id, node_id, op, node_data, "node")
                        if isinstance(res_rev, int):
                            new_rev = res_rev
                    except Exception as exc:
                        logger.error(f"[DiagramWS] Failed to persist NODE_OPERATION: {exc}")
                        await websocket.send_json({
                            "type": "OP_REJECTED",
                            "element_id": node_id,
                            "reason": "persist_failed"
                        })
                        if op_id:
                            await websocket.send_json({
                                "type": "NACK",
                                "op_id": op_id,
                                "diagram_id": diagram_id,
                                "element_id": node_id,
                                "error_code": "PERSIST_FAILED",
                                "message": "Error al persistir la operación"
                            })
                        continue

                    # Record durable event in outbox
                    event_id = None
                    if db is not None:
                        try:
                            from app.modules.collaboration.outbox import DiagramOutboxRepository
                            outbox_repo = DiagramOutboxRepository(db)
                            ev_doc = await outbox_repo.record_event(
                                diagram_id=str(diagram_id),
                                project_id=diagram.get("project_id") if isinstance(diagram, dict) else None,
                                revision=new_rev,
                                previous_revision=max(1, new_rev - 1),
                                actor_id=user_id,
                                operations=[{"type": op, "node_id": node_id, "data": node_data}],
                                operation_id=op_id,
                                origin_connection_id=str(id(websocket)),
                            )
                            event_id = ev_doc.get("event_id")
                            await outbox_repo.mark_dispatched(event_id)
                        except Exception as e_out:
                            logger.warning(f"[DiagramWS] Outbox record error: {e_out}")

                    # Explicit ACK on success
                    if op_id:
                        await websocket.send_json({
                            "type": "ACK",
                            "op_id": op_id,
                            "diagram_id": diagram_id,
                            "revision": new_rev,
                            "event_id": event_id,
                            "status": "success"
                        })

                    broadcast_msg = {
                        "type": "NODE_OPERATION",
                        "op": op,
                        "node_id": node_id,
                        "data": node_data,
                        "user_id": user_id,
                        "revision": new_rev,
                        "event_id": event_id,
                    }
                    await manager.broadcast(diagram_id, broadcast_msg, exclude_websocket=websocket)
                    spawn(_trigger_diagram_changed_helper(diagram_id, user_id))

            elif msg_type == "EDGE_OPERATION":
                op = message.get("op")
                edge_id = message.get("edge_id")
                edge_data = message.get("data")
                op_id = message.get("op_id") or message.get("operation_id")

                if user.get("role") in ("viewer", "guest", "readonly") or user.get("read_only") is True:
                    await websocket.send_json({"type": "OP_REJECTED", "element_id": edge_id, "reason": "read_only"})
                    if op_id:
                        await websocket.send_json({
                            "type": "NACK",
                            "op_id": op_id,
                            "diagram_id": diagram_id,
                            "element_id": edge_id,
                            "error_code": "READ_ONLY",
                            "message": "Operación rechazada: permiso de sólo lectura"
                        })
                    continue
                if op not in ("add", "update", "delete") or not isinstance(edge_id, str) or not edge_id or (op != "delete" and (not isinstance(edge_data, dict) or not edge_data)):
                    await websocket.send_json({"type": "OP_REJECTED", "element_id": edge_id, "reason": "invalid_operation"})
                    if op_id:
                        await websocket.send_json({
                            "type": "NACK",
                            "op_id": op_id,
                            "diagram_id": diagram_id,
                            "element_id": edge_id,
                            "error_code": "INVALID_OPERATION",
                            "message": "Operación inválida"
                        })
                    continue
                if op and edge_id:
                    # Idempotency check
                    if op_id and db is not None:
                        try:
                            from app.modules.collaboration.outbox import DiagramOutboxRepository
                            outbox_repo = DiagramOutboxRepository(db)
                            existing_ev = await outbox_repo.col.find_one({"diagram_id": str(diagram_id), "operation_id": op_id})
                            if existing_ev:
                                await websocket.send_json({
                                    "type": "ACK",
                                    "op_id": op_id,
                                    "diagram_id": diagram_id,
                                    "revision": existing_ev.get("revision", 1),
                                    "event_id": existing_ev.get("event_id"),
                                    "status": "success",
                                    "duplicate": True
                                })
                                continue
                        except Exception as e_dup:
                            logger.debug(f"[DiagramWS] Deduplication check warning: {e_dup}")

                    # Check if locked by another user
                    if manager.is_locked_by_other(diagram_id, edge_id, user_id):
                        await websocket.send_json({
                            "type": "OP_REJECTED",
                            "element_id": edge_id,
                            "reason": "locked"
                        })
                        if op_id:
                            await websocket.send_json({
                                "type": "NACK",
                                "op_id": op_id,
                                "diagram_id": diagram_id,
                                "element_id": edge_id,
                                "error_code": "LOCKED",
                                "message": "La relación está bloqueada por otro usuario"
                            })
                        continue

                    new_rev = 1
                    try:
                        res_rev = await update_diagram_graph_data(diagram_id, edge_id, op, edge_data, "edge")
                        if isinstance(res_rev, int):
                            new_rev = res_rev
                    except Exception as exc:
                        logger.error(f"[DiagramWS] Failed to persist EDGE_OPERATION: {exc}")
                        await websocket.send_json({
                            "type": "OP_REJECTED",
                            "element_id": edge_id,
                            "reason": "persist_failed"
                        })
                        if op_id:
                            await websocket.send_json({
                                "type": "NACK",
                                "op_id": op_id,
                                "diagram_id": diagram_id,
                                "element_id": edge_id,
                                "error_code": "PERSIST_FAILED",
                                "message": "Error al persistir la operación"
                            })
                        continue

                    event_id = None
                    if db is not None:
                        try:
                            from app.modules.collaboration.outbox import DiagramOutboxRepository
                            outbox_repo = DiagramOutboxRepository(db)
                            ev_doc = await outbox_repo.record_event(
                                diagram_id=str(diagram_id),
                                project_id=diagram.get("project_id") if isinstance(diagram, dict) else None,
                                revision=new_rev,
                                previous_revision=max(1, new_rev - 1),
                                actor_id=user_id,
                                operations=[{"type": op, "edge_id": edge_id, "data": edge_data}],
                                operation_id=op_id,
                                origin_connection_id=str(id(websocket)),
                            )
                            event_id = ev_doc.get("event_id")
                            await outbox_repo.mark_dispatched(event_id)
                        except Exception as e_out:
                            logger.warning(f"[DiagramWS] Outbox record error: {e_out}")

                    if op_id:
                        await websocket.send_json({
                            "type": "ACK",
                            "op_id": op_id,
                            "diagram_id": diagram_id,
                            "revision": new_rev,
                            "event_id": event_id,
                            "status": "success"
                        })

                    broadcast_msg = {
                        "type": "EDGE_OPERATION",
                        "op": op,
                        "edge_id": edge_id,
                        "data": edge_data,
                        "user_id": user_id,
                        "revision": new_rev,
                        "event_id": event_id,
                    }
                    await manager.broadcast(diagram_id, broadcast_msg, exclude_websocket=websocket)
                    spawn(_trigger_diagram_changed_helper(diagram_id, user_id))

            elif msg_type == "LOCK_ACQUIRE":
                element_id = message.get("element_id")
                if isinstance(element_id, str) and 0 < len(element_id) <= 256:
                    success = manager.acquire_lock(diagram_id, user_id, element_id)
                    if success:
                        await manager.broadcast(diagram_id, {
                            "type": "LOCK_GRANTED",
                            "element_id": element_id,
                            "user_id": user_id
                        })
                    else:
                        await websocket.send_json({
                            "type": "LOCK_REJECTED",
                            "element_id": element_id
                        })
                else:
                    await websocket.send_json({"type": "OP_REJECTED", "reason": "invalid_operation"})

            elif msg_type == "LOCK_RELEASE":
                element_id = message.get("element_id")
                if isinstance(element_id, str) and element_id and manager.release_lock(diagram_id, user_id, element_id):
                    await manager.broadcast(diagram_id, {
                        "type": "LOCK_RELEASED",
                        "element_id": element_id,
                        "user_id": user_id
                    })
                else:
                    await websocket.send_json({"type": "OP_REJECTED", "element_id": element_id, "reason": "lock_not_owned"})

            elif msg_type == "PING":
                await websocket.send_json({"type": "PONG"})

            elif msg_type == "CHAT_MESSAGE":
                content = message.get("content")
                if content and diagram_id in manager.rooms and user_id in manager.rooms[diagram_id]:
                    user_data = manager.rooms[diagram_id][user_id]
                    chat_msg = manager.add_chat_message(
                        diagram_id, 
                        user_id, 
                        user_data.get("user_name", "Usuario"), 
                        user_data.get("user_color", "#2D6BE4"), 
                        content
                    )
                    await manager.broadcast(diagram_id, chat_msg)

            elif msg_type == "PRESENCE_STATUS":
                status = message.get("status")
                if status in ["online", "away", "busy"]:
                    manager.update_presence_status(diagram_id, user_id, status)
                    await manager.broadcast(diagram_id, {
                        "type": "USER_PRESENCE_UPDATED",
                        "user_id": user_id,
                        "status": status
                    })

            elif msg_type == "SYNC_REQUEST":
                known_rev = int(message.get("known_revision", 0) or 0)
                if db is not None:
                    try:
                        from app.modules.collaboration.outbox import DiagramOutboxRepository
                        outbox_repo = DiagramOutboxRepository(db)
                        oid = ObjectId(diagram_id) if ObjectId.is_valid(diagram_id) else diagram_id
                        diag_doc = await db["diagrams"].find_one({"_id": oid, "is_deleted": False})
                        current_rev = int(diag_doc.get("version", 1) or 1) if diag_doc else 1

                        if known_rev >= current_rev:
                            await websocket.send_json({
                                "type": "SYNC_RESPONSE",
                                "status": "up_to_date",
                                "revision": current_rev,
                            })
                        else:
                            missing_events = await outbox_repo.get_events_since(diagram_id, known_rev, limit=100)
                            is_contiguous = False
                            if missing_events:
                                expected = known_rev + 1
                                is_contiguous = True
                                for ev in missing_events:
                                    if ev.get("revision") != expected:
                                        is_contiguous = False
                                        break
                                    expected += 1
                                if expected - 1 < current_rev:
                                    is_contiguous = False

                            if is_contiguous and missing_events:
                                clean_events = []
                                for ev in missing_events:
                                    clean_events.append({
                                        "event_id": ev["event_id"],
                                        "event_type": ev.get("event_type", "diagram.operation.committed"),
                                        "revision": ev["revision"],
                                        "previous_revision": ev.get("previous_revision"),
                                        "operations": ev.get("operations", []),
                                        "graph_data": ev.get("graph_data"),
                                        "created_at": ev["created_at"].isoformat() if hasattr(ev["created_at"], "isoformat") else str(ev["created_at"])
                                    })
                                await websocket.send_json({
                                    "type": "SYNC_RESPONSE",
                                    "status": "incremental",
                                    "from_revision": known_rev,
                                    "to_revision": current_rev,
                                    "events": clean_events
                                })
                            else:
                                await websocket.send_json({
                                    "type": "SYNC_RESPONSE",
                                    "status": "snapshot",
                                    "revision": current_rev,
                                    "graph_data": diag_doc.get("graph_data", {"nodes": [], "edges": []}) if diag_doc else {"nodes": [], "edges": []}
                                })
                    except Exception as s_err:
                        logger.error(f"[DiagramWS] SYNC_REQUEST error: {s_err}")
                        await websocket.send_json({
                            "type": "SYNC_RESPONSE",
                            "status": "error",
                            "message": str(s_err)
                        })
                else:
                    await websocket.send_json({
                        "type": "SYNC_RESPONSE",
                        "status": "snapshot",
                        "revision": 1,
                        "graph_data": {"nodes": [], "edges": []}
                    })
            else:
                await websocket.send_json({"type": "OP_REJECTED", "reason": "unrecognized_operation"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        owned = [element_id for element_id, owner in manager.get_locks(diagram_id).items() if owner == user_id]
        last_connection = await manager.disconnect(diagram_id, user_id, websocket)
        if last_connection:
            for el_id in owned:
                await manager.broadcast(diagram_id, {
                    "type": "LOCK_RELEASED", "element_id": el_id, "user_id": user_id
                }, exclude_user_id=user_id)
            await manager.broadcast(diagram_id, {"type": "USER_LEFT", "user_id": user_id})


@router.websocket("/projects/{project_id}")
async def project_websocket_endpoint(websocket: WebSocket, project_id: str, token: str = Query(...)):
    """WebSocket endpoint for project-level AI team chat, presence, and real-time state events."""
    user = await verify_project_ws_token(project_id, token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Verify authorization against the project
    db = get_db()
    if db is not None:
        try:
            pid_obj = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
            project = await db.projects.find_one({"_id": pid_obj, "is_deleted": False})
            if not project:
                await websocket.close(code=4003, reason="Project not found")
                return

            team = None
            if project.get("team_id"):
                tid_obj = ObjectId(project["team_id"]) if ObjectId.is_valid(project["team_id"]) else project["team_id"]
                team = await db.teams.find_one({"_id": tid_obj, "is_deleted": False})

            if not can_access_project(user, project, team):
                await websocket.close(code=4003, reason="Forbidden")
                return
        except Exception as e:
            logger.error(f"[ProjectWS] Error verifying authorization: {e}")
            await websocket.close(code=4003, reason="Forbidden")
            return

    room_key = f"project:{project_id}"
    user_id = str(user.get("_id", user.get("id")))
    if get_db() is not None and not await _current_ws_access(get_db(), user_id, project_id, True):
        await websocket.close(code=4003, reason="Forbidden")
        return
    await manager.connect(room_key, user, websocket,
                          authorize=lambda: _current_ws_access(get_db(), user_id, project_id, True))
    message_timestamps = []

    # Broadcast initial PRESENCE to the room
    current_members = manager.get_room_users(room_key)
    presence_msg = {
        "type": "PRESENCE",
        "members": current_members,
    }
    await manager.broadcast(room_key, presence_msg)

    try:
        while True:
            data = await websocket.receive_text()
            if not await _current_ws_access(get_db(), user_id, project_id, True):
                await websocket.close(code=4003, reason="Authorization revoked")
                break

            # 1. Message size check (64 KB)
            if len(data.encode("utf-8")) > MAX_MESSAGE_BYTES:
                logger.warning(f"[ProjectWS] Connection from user {user_id} exceeded max message size. Closing.")
                await websocket.close(code=4008, reason="Message size exceeds 64KB limit")
                break

            # 2. Message burst rate check (60 msg/s)
            now_ts = time.monotonic()
            message_timestamps = [t for t in message_timestamps if now_ts - t < 1.0]
            if len(message_timestamps) >= MAX_BURST_PER_SECOND:
                logger.warning(f"[ProjectWS] Connection from user {user_id} exceeded burst rate. Closing.")
                await websocket.close(code=4008, reason="Message rate limit exceeded")
                break
            message_timestamps.append(now_ts)

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue

            if not isinstance(message, dict):
                await websocket.send_json({"type": "OP_REJECTED", "reason": "invalid_message"})
                continue

            msg_type = message.get("type")
            if not msg_type:
                continue

            if msg_type == "PING":
                await websocket.send_json({"type": "PONG"})

            elif msg_type == "TYPING":
                is_typing = bool(message.get("is_typing", True))
                user_info = manager.rooms.get(room_key, {}).get(user_id, {})
                await manager.broadcast(
                    room_key,
                    {
                        "type": "AI_TYPING",
                        "role": "user",
                        "user_id": user_id,
                        "user_name": user_info.get("user_name", "Usuario"),
                        "state": "start" if is_typing else "stop",
                    },
                    exclude_user_id=user_id,
                )

            else:
                await websocket.send_json({"type": "OP_REJECTED", "reason": "unrecognized_operation"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[ProjectWS] WebSocket error: {e}")
    finally:
        await manager.disconnect(room_key, user_id, websocket)
        remaining_members = manager.get_room_users(room_key)
        await manager.broadcast(
            room_key,
            {
                "type": "PRESENCE",
                "members": remaining_members,
            },
        )

