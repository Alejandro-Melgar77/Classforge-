import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from bson import ObjectId
from app.core.database import get_db

def _get_db():
    return get_db()

async def generate_project_ws_token(project_id: str, user_id: str) -> Dict[str, Any]:
    """Generates a single-use token for authenticating a project WebSocket connection."""
    db = _get_db()
    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    await db.ws_tokens.insert_one({
        "token": token,
        "project_id": ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id,
        "user_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id,
        "expires_at": expires_at,
    })
    return {"token": token, "expires_at": expires_at}

async def verify_project_ws_token(project_id: str, token: str) -> Optional[Dict[str, Any]]:
    """Verifies and consumes a single-use project WS token, returning the user document if valid."""
    db = _get_db()
    if db is None:
        return None
    ws_token = await db.ws_tokens.find_one_and_delete({"token": token})
    if not ws_token:
        return None

    if str(ws_token.get("project_id")) != str(project_id):
        return None

    expires_at = ws_token.get("expires_at")
    if expires_at:
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            return None

    user_id = ws_token.get("user_id")
    if not user_id:
        return None

    if isinstance(user_id, str):
        try:
            user_id = ObjectId(user_id)
        except Exception:
            pass

    user = await db.users.find_one({"_id": user_id, "is_deleted": False, "is_active": True})
    return user

async def verify_ws_token(diagram_id: str, token: str) -> Optional[Dict[str, Any]]:
    """Verifies a single-use WS token and returns the user document if valid, consuming the token."""
    db = _get_db()
    if db is None:
        return None
    ws_token = await db.ws_tokens.find_one_and_delete({"token": token})
    
    if not ws_token:
        return None
    
    if str(ws_token.get("diagram_id")) != diagram_id:
        return None
        
    expires_at = ws_token.get("expires_at")
    if expires_at:
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            return None
        
    user_id = ws_token.get("user_id")
    if not user_id:
        return None
        
    if isinstance(user_id, str):
        try:
            user_id = ObjectId(user_id)
        except Exception:
            pass
            
    user = await db.users.find_one({"_id": user_id, "is_deleted": False})
    return user

async def update_diagram_graph_data(
    diagram_id: str,
    element_id: str = None,
    op: str = None,
    data: dict = None,
    element_type: str = "node"
):
    """
    Persists updates to graph_data atomically without read-modify-write.
    Uses $push, $pull, and $set with arrayFilters (with atomic positional fallback).
    """
    db = _get_db()
    if db is None or not element_id or not op:
        return
    try:
        obj_id = ObjectId(diagram_id) if not isinstance(diagram_id, ObjectId) else diagram_id
    except Exception:
        return

    now = datetime.now(timezone.utc)

    if element_type == "node":
        if op == "add":
            if data:
                pos = data.get("position", {"x": data.get("x", 100), "y": data.get("y", 100)})
                size = data.get("size", {"width": 220, "height": 140})
                node_type = data.get("type") or data.get("nodeType") or "class"
                node_doc = {
                    "id": element_id,
                    "type": node_type,
                    "position": {"x": float(pos.get("x", 100)), "y": float(pos.get("y", 100))},
                    "size": {"width": float(size.get("width", 220)), "height": float(size.get("height", 140))},
                    "data": data.get("data", {
                        "name": "Clase",
                        "stereotype": None,
                        "attributes": [],
                        "methods": [],
                        "notes": None
                    })
                }
                await db.diagrams.update_one(
                    {"_id": obj_id, "graph_data.nodes.id": {"$ne": element_id}},
                    {"$push": {"graph_data.nodes": node_doc}, "$set": {"updated_at": now}}
                )
        elif op == "move":
            if data:
                pos = data.get("position", data)
                new_pos = {
                    "x": float(pos.get("x", 0)),
                    "y": float(pos.get("y", 0))
                }
                try:
                    await db.diagrams.update_one(
                        {"_id": obj_id},
                        {"$set": {"graph_data.nodes.$[elem].position": new_pos, "updated_at": now}},
                        array_filters=[{"elem.id": element_id}]
                    )
                except NotImplementedError:
                    await db.diagrams.update_one(
                        {"_id": obj_id, "graph_data.nodes.id": element_id},
                        {"$set": {"graph_data.nodes.$.position": new_pos, "updated_at": now}}
                    )
        elif op == "update":
            if data:
                set_fields = {"updated_at": now}
                if "data" in data:
                    set_fields["graph_data.nodes.$[elem].data"] = data["data"]
                if "type" in data or "nodeType" in data:
                    set_fields["graph_data.nodes.$[elem].type"] = data.get("type") or data.get("nodeType")
                if "size" in data:
                    set_fields["graph_data.nodes.$[elem].size"] = data["size"]
                if "position" in data:
                    pos = data["position"]
                    set_fields["graph_data.nodes.$[elem].position"] = {
                        "x": float(pos.get("x", 0)),
                        "y": float(pos.get("y", 0))
                    }
                try:
                    await db.diagrams.update_one(
                        {"_id": obj_id},
                        {"$set": set_fields},
                        array_filters=[{"elem.id": element_id}]
                    )
                except NotImplementedError:
                    pos_set_fields = {k.replace("$[elem]", "$"): v for k, v in set_fields.items()}
                    await db.diagrams.update_one(
                        {"_id": obj_id, "graph_data.nodes.id": element_id},
                        {"$set": pos_set_fields}
                    )
        elif op == "delete":
            try:
                await db.diagrams.update_one(
                    {"_id": obj_id},
                    {
                        "$pull": {
                            "graph_data.nodes": {"id": element_id},
                            "graph_data.edges": {"$or": [{"source": element_id}, {"target": element_id}]}
                        },
                        "$set": {"updated_at": now}
                    }
                )
            except Exception:
                await db.diagrams.update_one(
                    {"_id": obj_id},
                    {"$pull": {"graph_data.nodes": {"id": element_id}}, "$set": {"updated_at": now}}
                )
                await db.diagrams.update_one(
                    {"_id": obj_id},
                    {"$pull": {"graph_data.edges": {"source": element_id}}, "$set": {"updated_at": now}}
                )
                await db.diagrams.update_one(
                    {"_id": obj_id},
                    {"$pull": {"graph_data.edges": {"target": element_id}}, "$set": {"updated_at": now}}
                )

    elif element_type == "edge":
        if op == "add":
            if data:
                src = data.get("source")
                if isinstance(src, dict): src = src.get("cell", src)
                tgt = data.get("target")
                if isinstance(tgt, dict): tgt = tgt.get("cell", tgt)

                edge_doc = {
                    "id": element_id,
                    "type": data.get("type", "association"),
                    "source": src,
                    "target": tgt,
                    "label": data.get("label"),
                    "source_multiplicity": data.get("source_multiplicity"),
                    "target_multiplicity": data.get("target_multiplicity")
                }
                await db.diagrams.update_one(
                    {"_id": obj_id, "graph_data.edges.id": {"$ne": element_id}},
                    {"$push": {"graph_data.edges": edge_doc}, "$set": {"updated_at": now}}
                )
        elif op == "update":
            if data:
                set_fields = {"updated_at": now}
                for k in ["type", "source", "target", "label", "source_multiplicity", "target_multiplicity"]:
                    if k in data:
                        val = data[k]
                        if k in ["source", "target"] and isinstance(val, dict):
                            val = val.get("cell", val)
                        set_fields[f"graph_data.edges.$[elem].{k}"] = val
                try:
                    await db.diagrams.update_one(
                        {"_id": obj_id},
                        {"$set": set_fields},
                        array_filters=[{"elem.id": element_id}]
                    )
                except NotImplementedError:
                    pos_set_fields = {k.replace("$[elem]", "$"): v for k, v in set_fields.items()}
                    await db.diagrams.update_one(
                        {"_id": obj_id, "graph_data.edges.id": element_id},
                        {"$set": pos_set_fields}
                    )
        elif op == "delete":
            await db.diagrams.update_one(
                {"_id": obj_id},
                {"$pull": {"graph_data.edges": {"id": element_id}}, "$set": {"updated_at": now}}
            )
