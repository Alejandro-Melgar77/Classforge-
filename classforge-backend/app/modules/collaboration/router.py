import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
from app.modules.collaboration.connection_manager import manager
from app.modules.collaboration.service import verify_ws_token, update_diagram_graph_data

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/diagrams/{diagram_id}")
async def websocket_endpoint(websocket: WebSocket, diagram_id: str, token: str = Query(...)):
    user = await verify_ws_token(diagram_id, token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    await manager.connect(diagram_id, user, websocket)
    user_id = str(user.get("_id", user.get("id")))

    try:
        while True:
            data = await websocket.receive_text()
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
                    broadcast_msg = {
                        "type": "NODE_OPERATION",
                        "op": op,
                        "node_id": node_id,
                        "data": node_data,
                        "user_id": user_id
                    }
                    await manager.broadcast(diagram_id, broadcast_msg, exclude_user_id=user_id)
                    await update_diagram_graph_data(diagram_id, node_id, op, node_data, "node")

            elif msg_type == "EDGE_OPERATION":
                op = message.get("op")
                edge_id = message.get("edge_id")
                edge_data = message.get("data")
                if op and edge_id:
                    broadcast_msg = {
                        "type": "EDGE_OPERATION",
                        "op": op,
                        "edge_id": edge_id,
                        "data": edge_data,
                        "user_id": user_id
                    }
                    await manager.broadcast(diagram_id, broadcast_msg, exclude_user_id=user_id)
                    await update_diagram_graph_data(diagram_id, edge_id, op, edge_data, "edge")

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
