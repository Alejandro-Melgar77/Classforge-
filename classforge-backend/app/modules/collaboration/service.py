from datetime import datetime, timezone
from bson import ObjectId
from app.core.database import get_db

def _get_db():
    return get_db()

async def verify_ws_token(diagram_id: str, token: str) -> dict:
    """Verifies a WS token and returns the user document if valid."""
    db = _get_db()
    if db is None:
        return None
    ws_token = await db.ws_tokens.find_one({"token": token})
    
    if not ws_token:
        return None
    
    if str(ws_token.get("diagram_id")) != diagram_id:
        return None
        
    expires_at = ws_token.get("expires_at")
    if expires_at:
        now = datetime.now(timezone.utc) if expires_at.tzinfo else datetime.utcnow()
        if expires_at < now:
            return None
        
    user_id = ws_token.get("user_id")
    if not user_id:
        return None
        
    if isinstance(user_id, str):
        try:
            user_id = ObjectId(user_id)
        except:
            pass
            
    user = await db.users.find_one({"_id": user_id})
    return user

async def update_diagram_graph_data(diagram_id: str, element_id: str = None, op: str = None, data: dict = None, element_type: str = "node"):
    """
    Persists updates to graph_data cleanly without structure corruption.
    """
    db = _get_db()
    if db is None:
        return
    try:
        obj_id = ObjectId(diagram_id)
    except:
        return
        
    diagram = await db.diagrams.find_one({"_id": obj_id})
    if not diagram:
        return

    graph_data = diagram.get("graph_data", {"nodes": [], "edges": []})
    if not isinstance(graph_data, dict):
        graph_data = {"nodes": [], "edges": []}
        
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    updated = False
    
    if element_type == "node" and element_id:
        if op == "add":
            if data and not any(n.get("id") == element_id for n in nodes):
                pos = data.get("position", {"x": data.get("x", 100), "y": data.get("y", 100)})
                size = data.get("size", {"width": 220, "height": 140})
                node_type = data.get("type") or data.get("nodeType") or "class"
                node_doc = {
                    "id": element_id,
                    "type": node_type,
                    "position": {"x": pos.get("x", 100), "y": pos.get("y", 100)},
                    "size": {"width": size.get("width", 220), "height": size.get("height", 140)},
                    "data": data.get("data", {
                        "name": "Clase",
                        "stereotype": None,
                        "attributes": [],
                        "methods": [],
                        "notes": None
                    })
                }
                nodes.append(node_doc)
                updated = True
        elif op == "move":
            for i, n in enumerate(nodes):
                if n.get("id") == element_id and data:
                    pos = data.get("position", data)
                    nodes[i]["position"] = {
                        "x": float(pos.get("x", nodes[i].get("position", {}).get("x", 0))),
                        "y": float(pos.get("y", nodes[i].get("position", {}).get("y", 0)))
                    }
                    updated = True
                    break
        elif op == "update":
            for i, n in enumerate(nodes):
                if n.get("id") == element_id and data:
                    if "data" in data:
                        nodes[i]["data"] = data["data"]
                    if "type" in data:
                        nodes[i]["type"] = data["type"]
                    if "nodeType" in data:
                        nodes[i]["type"] = data["nodeType"]
                    if "size" in data:
                        nodes[i]["size"] = data["size"]
                    if "position" in data:
                        nodes[i]["position"] = data["position"]
                    updated = True
                    break
        elif op == "delete":
            nodes = [n for n in nodes if n.get("id") != element_id]
            # Also clean up associated edges
            edges = [e for e in edges if e.get("source") != element_id and e.get("target") != element_id]
            updated = True
            
    elif element_type == "edge" and element_id:
        if op == "add":
            if data and not any(e.get("id") == element_id for e in edges):
                src = data.get("source")
                if isinstance(src, dict): src = src.get("cell", src)
                tgt = data.get("target")
                if isinstance(tgt, dict): tgt = tgt.get("cell", tgt)
                
                edges.append({
                    "id": element_id,
                    "type": data.get("type", "association"),
                    "source": src,
                    "target": tgt,
                    "label": data.get("label"),
                    "source_multiplicity": data.get("source_multiplicity"),
                    "target_multiplicity": data.get("target_multiplicity")
                })
                updated = True
        elif op == "update":
            for i, e in enumerate(edges):
                if e.get("id") == element_id and data:
                    for k in ["type", "source", "target", "label", "source_multiplicity", "target_multiplicity"]:
                        if k in data:
                            val = data[k]
                            if k in ["source", "target"] and isinstance(val, dict):
                                val = val.get("cell", val)
                            edges[i][k] = val
                    updated = True
                    break
        elif op == "delete":
            edges = [e for e in edges if e.get("id") != element_id]
            updated = True

    if updated:
        graph_data["nodes"] = nodes
        graph_data["edges"] = edges
        await db.diagrams.update_one(
            {"_id": obj_id},
            {"$set": {"graph_data": graph_data, "updated_at": datetime.now(timezone.utc)}}
        )
