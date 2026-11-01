import asyncio
import json
import logging
import time
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.authz import can_access_project
from app.core.database import get_db
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


async def _trigger_diagram_changed_helper(diagram_id: str, user_id: str):
    """Notifies trigger manager of diagram edit events with origin checks."""
    try:
        db = get_db()
        if db is not None:
            obj_id = ObjectId(diagram_id) if ObjectId.is_valid(diagram_id) else diagram_id
            diag = await db["diagrams"].find_one({"_id": obj_id}, {"project_id": 1})
            if diag and diag.get("project_id"):
                origin = "ai" if user_id.startswith("ai:") else "human"
                from app.ai_team.application.triggers import TriggersManager
                triggers = TriggersManager(db)
                await triggers.on_diagram_changed(str(diag["project_id"]), diagram_id, origin=origin)
    except Exception as err:
        logger.debug(f"[DiagramWS] Failed to trigger diagram_changed: {err}")


@router.websocket("/diagrams/{diagram_id}")
async def websocket_endpoint(websocket: WebSocket, diagram_id: str, token: str = Query(...)):
    user = await verify_ws_token(diagram_id, token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    await manager.connect(diagram_id, user, websocket)
    user_id = str(user.get("_id", user.get("id")))
    message_timestamps = []

    try:
        while True:
            data = await websocket.receive_text()

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
                if op and node_id:
                    # Check if locked by another user
                    if manager.is_locked_by_other(diagram_id, node_id, user_id):
                        await websocket.send_json({
                            "type": "OP_REJECTED",
                            "element_id": node_id,
                            "reason": "locked"
                        })
                        continue

                    broadcast_msg = {
                        "type": "NODE_OPERATION",
                        "op": op,
                        "node_id": node_id,
                        "data": node_data,
                        "user_id": user_id
                    }
                    await manager.broadcast(diagram_id, broadcast_msg, exclude_user_id=user_id)
                    await update_diagram_graph_data(diagram_id, node_id, op, node_data, "node")
                    asyncio.create_task(_trigger_diagram_changed_helper(diagram_id, user_id))

            elif msg_type == "EDGE_OPERATION":
                op = message.get("op")
                edge_id = message.get("edge_id")
                edge_data = message.get("data")
                if op and edge_id:
                    # Check if locked by another user
                    if manager.is_locked_by_other(diagram_id, edge_id, user_id):
                        await websocket.send_json({
                            "type": "OP_REJECTED",
                            "element_id": edge_id,
                            "reason": "locked"
                        })
                        continue

                    broadcast_msg = {
                        "type": "EDGE_OPERATION",
                        "op": op,
                        "edge_id": edge_id,
                        "data": edge_data,
                        "user_id": user_id
                    }
                    await manager.broadcast(diagram_id, broadcast_msg, exclude_user_id=user_id)
                    await update_diagram_graph_data(diagram_id, edge_id, op, edge_data, "edge")
                    asyncio.create_task(_trigger_diagram_changed_helper(diagram_id, user_id))

            elif msg_type == "LOCK_ACQUIRE":
                element_id = message.get("element_id")
                if element_id:
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

            elif msg_type == "LOCK_RELEASE":
                element_id = message.get("element_id")
                if element_id:
                    manager.release_lock(diagram_id, user_id, element_id)
                    await manager.broadcast(diagram_id, {
                        "type": "LOCK_RELEASED",
                        "element_id": element_id,
                        "user_id": user_id
                    })

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

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        released = manager.release_all_user_locks(diagram_id, user_id)
        for el_id in released:
            await manager.broadcast(diagram_id, {
                "type": "LOCK_RELEASED",
                "element_id": el_id,
                "user_id": user_id
            }, exclude_user_id=user_id)
            
        await manager.disconnect(diagram_id, user_id)
        
        await manager.broadcast(diagram_id, {
            "type": "USER_LEFT",
            "user_id": user_id
        })


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
            project = await db.projects.find_one({"_id": pid_obj})
            if not project:
                await websocket.close(code=4003, reason="Project not found")
                return

            team = None
            if project.get("team_id"):
                tid_obj = ObjectId(project["team_id"]) if ObjectId.is_valid(project["team_id"]) else project["team_id"]
                team = await db.teams.find_one({"_id": tid_obj})

            if not can_access_project(user, project, team):
                await websocket.close(code=4003, reason="Forbidden")
                return
        except Exception as e:
            logger.error(f"[ProjectWS] Error verifying authorization: {e}")
            await websocket.close(code=4003, reason="Forbidden")
            return

    room_key = f"project:{project_id}"
    await manager.connect(room_key, user, websocket)
    user_id = str(user.get("_id", user.get("id")))
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

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[ProjectWS] WebSocket error: {e}")
    finally:
        await manager.disconnect(room_key, user_id)
        remaining_members = manager.get_room_users(room_key)
        await manager.broadcast(
            room_key,
            {
                "type": "PRESENCE",
                "members": remaining_members,
            },
        )

