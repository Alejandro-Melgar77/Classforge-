from typing import Dict, Any, List, Optional
from bson import ObjectId
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
from app.modules.diagrams.repository import DiagramRepository
from app.modules.diagrams.schemas import CreateDiagram, UpdateDiagram, SaveGraph

def can_access_diagram(user: Dict[str, Any], diagram: Dict[str, Any], team: Optional[Dict[str, Any]]) -> bool:
    role = user.get("role")
    user_id = str(user["_id"])
    if role == "admin":
        return True
    
    # Creator always has access
    if str(diagram.get("created_by")) == user_id:
        return True

    # If user is assigned as a member/participant to this diagram
    diagram_members = [str(m) for m in diagram.get("member_ids", [])]
    if user_id in diagram_members:
        return True
    
    # If user is the Scrum Master of the diagram's assigned team
    if role == "scrum_master" and team:
        if str(team.get("scrum_master_id")) == user_id:
            return True
            
    return False

class DiagramService:
    def __init__(self, db):
        self.repository = DiagramRepository(db)
        self.db = db

    async def _get_team(self, team_id: Optional[Any]) -> Optional[Dict[str, Any]]:
        if not team_id:
            return None
        if isinstance(team_id, str):
            if not ObjectId.is_valid(team_id):
                return None
            team_id = ObjectId(team_id)
        return await self.db["teams"].find_one({"_id": team_id})

    async def _enrich_team_names(self, diagrams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        team_ids = {d["team_id"] for d in diagrams if d.get("team_id")}
        if not team_ids:
            return diagrams
        valid_team_ids = [tid if isinstance(tid, ObjectId) else ObjectId(str(tid)) for tid in team_ids if ObjectId.is_valid(str(tid))]
        if valid_team_ids:
            teams = await self.db["teams"].find({"_id": {"$in": valid_team_ids}}).to_list(length=None)
            team_map = {str(t["_id"]): t.get("name") for t in teams}
            for d in diagrams:
                tid_str = str(d.get("team_id")) if d.get("team_id") else None
                if tid_str and tid_str in team_map:
                    d["team_name"] = team_map[tid_str]
        return diagrams

    async def create_diagram(self, data: CreateDiagram, user: Dict[str, Any]) -> Dict[str, Any]:
        doc = data.model_dump()
        user_id = ObjectId(user["_id"])
        doc["created_by"] = user_id

        # Safely resolve member_ids
        raw_members = doc.get("member_ids", []) or []
        doc["member_ids"] = [ObjectId(m) for m in raw_members if ObjectId.is_valid(str(m))]

        # Safely resolve project_id
        proj_id_val = doc.get("project_id")
        if proj_id_val and ObjectId.is_valid(str(proj_id_val)):
            doc["project_id"] = ObjectId(str(proj_id_val))
        else:
            # Find an existing project owned by or accessible to user, or auto-create one
            proj = await self.db["projects"].find_one({"owner_id": user_id, "is_deleted": {"$ne": True}})
            if not proj:
                proj = await self.db["projects"].find_one({"is_deleted": {"$ne": True}})
            if not proj:
                new_proj = {
                    "name": "Proyecto Principal",
                    "description": "Proyecto generado automáticamente",
                    "type": "personal",
                    "status": "in_progress",
                    "owner_id": user_id,
                    "created_by": user_id,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "is_deleted": False
                }
                res = await self.db["projects"].insert_one(new_proj)
                doc["project_id"] = res.inserted_id
            else:
                doc["project_id"] = proj["_id"]

        # Safely resolve team_id
        team_id_val = doc.get("team_id")
        if team_id_val and ObjectId.is_valid(str(team_id_val)):
            doc["team_id"] = ObjectId(str(team_id_val))
        else:
            doc["team_id"] = None
        
        diagram = await self.repository.create(doc)

        # Enrich team_name if any
        if diagram.get("team_id"):
            team = await self._get_team(diagram["team_id"])
            if team:
                diagram["team_name"] = team.get("name")
        
        # Audit log
        await self.db["audit_logs"].insert_one({
            "action": "CREATE_DIAGRAM",
            "user_id": user_id,
            "diagram_id": diagram["_id"],
            "timestamp": datetime.now(timezone.utc)
        })
        
        return diagram

    async def list_diagrams(self, user: Dict[str, Any], project_id: Optional[str] = None, team_id: Optional[str] = None, status: Optional[str] = None, page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
        query = {}
        if project_id and ObjectId.is_valid(project_id):
            query["project_id"] = ObjectId(project_id)
        if team_id and ObjectId.is_valid(team_id):
            query["team_id"] = ObjectId(team_id)
        if status:
            query["status"] = status
            
        role = user.get("role")
        user_id = ObjectId(user["_id"])
        if role == "admin":
            # Admin sees all non-deleted diagrams
            pass
        elif role == "scrum_master":
            # Scrum master sees diagrams of teams they lead, diagrams they created, or diagrams where they are assigned as participant
            teams = await self.db["teams"].find({"scrum_master_id": user_id}).to_list(length=None)
            team_ids = [t["_id"] for t in teams]
            conditions = [{"created_by": user_id}, {"member_ids": user_id}]
            if team_ids:
                conditions.append({"team_id": {"$in": team_ids}})
            query["$or"] = conditions
        elif role == "dev":
            # Dev sees diagrams where they have been explicitly assigned as a participant, or created by them
            query["$or"] = [
                {"member_ids": user_id},
                {"created_by": user_id}
            ]
        else:
            query["created_by"] = user_id
                
        skip = (page - 1) * limit
        diagrams = await self.repository.list_diagrams(query, skip, limit)
        return await self._enrich_team_names(diagrams)

    async def get_diagram(self, diagram_id: str, user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        diagram = await self.repository.get_by_id(diagram_id)
        if not diagram:
            return None
            
        team = await self._get_team(diagram.get("team_id"))
        if not can_access_diagram(user, diagram, team):
            raise PermissionError("Access denied")
            
        if team:
            diagram["team_name"] = team.get("name")
        return diagram

    async def update_diagram(self, diagram_id: str, data: UpdateDiagram, user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        diagram = await self.get_diagram(diagram_id, user)  # Checks access
        if not diagram:
            return None
        
        role = user.get("role")
        user_id = str(user["_id"])
        is_creator = str(diagram.get("created_by")) == user_id
        team = await self._get_team(diagram.get("team_id"))
        is_sm = team and str(team.get("scrum_master_id")) == user_id

        # Only Admin, Scrum Master of the team, or Diagram Creator can update metadata
        if role != "admin" and not is_sm and not is_creator:
            raise PermissionError("Only Admin or Scrum Master can modify diagram details")
            
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        
        # Convert member_ids if present
        if "member_ids" in update_data and isinstance(update_data["member_ids"], list):
            update_data["member_ids"] = [ObjectId(m) for m in update_data["member_ids"] if ObjectId.is_valid(str(m))]
            
        # Convert team_id if present
        if "team_id" in update_data:
            if update_data["team_id"] and ObjectId.is_valid(str(update_data["team_id"])):
                update_data["team_id"] = ObjectId(str(update_data["team_id"]))
            else:
                update_data["team_id"] = None
                
        updated = await self.repository.update(diagram_id, update_data)
        if updated and updated.get("team_id"):
            t = await self._get_team(updated["team_id"])
            if t:
                updated["team_name"] = t.get("name")
        return updated

    async def get_diagram_participants(self, diagram_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        diagram = await self.get_diagram(diagram_id, user)
        if not diagram:
            raise ValueError("Diagram not found")
        
        team_id = diagram.get("team_id")
        team = await self._get_team(str(team_id)) if team_id else None
        
        assigned_raw = diagram.get("member_ids", [])
        assigned_ids = [str(m) for m in assigned_raw]
        
        available_members = []
        
        if team:
            # Get members of this team
            team_member_ids = team.get("member_ids", [])
            all_uids = [ObjectId(uid) for uid in team_member_ids if ObjectId.is_valid(str(uid))]
            if all_uids:
                users = await self.db["users"].find({"_id": {"$in": all_uids}, "is_active": True}).to_list(length=None)
                for u in users:
                    uid_str = str(u["_id"])
                    name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get("username", "Usuario")
                    available_members.append({
                        "id": uid_str,
                        "name": name,
                        "email": u.get("email", ""),
                        "role": u.get("role", "dev"),
                        "is_assigned": uid_str in assigned_ids
                    })
        else:
            # If no team assigned yet, list active dev / scrum_master users
            users = await self.db["users"].find({"role": {"$in": ["dev", "scrum_master"]}, "is_active": True}).to_list(length=50)
            for u in users:
                uid_str = str(u["_id"])
                name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get("username", "Usuario")
                available_members.append({
                    "id": uid_str,
                    "name": name,
                    "email": u.get("email", ""),
                    "role": u.get("role", "dev"),
                    "is_assigned": uid_str in assigned_ids
                })

        return {
            "diagram_id": diagram_id,
            "team_id": str(team_id) if team_id else None,
            "team_name": team.get("name") if team else None,
            "assigned_member_ids": assigned_ids,
            "available_members": available_members
        }

    async def update_diagram_participants(self, diagram_id: str, member_ids: List[str], user: Dict[str, Any]) -> Dict[str, Any]:
        diagram = await self.get_diagram(diagram_id, user)
        if not diagram:
            raise ValueError("Diagram not found")
        
        role = user.get("role")
        user_id = str(user["_id"])
        is_creator = str(diagram.get("created_by")) == user_id
        team = await self._get_team(diagram.get("team_id"))
        is_sm = team and str(team.get("scrum_master_id")) == user_id
        
        if role != "admin" and not is_sm and not is_creator:
            raise PermissionError("Only Admin or Scrum Master can manage participants")
            
        obj_ids = [ObjectId(m) for m in member_ids if ObjectId.is_valid(m)]
        await self.repository.update(diagram_id, {"member_ids": obj_ids})
        return await self.get_diagram_participants(diagram_id, user)

    async def delete_diagram(self, diagram_id: str, user: Dict[str, Any]) -> bool:
        if user.get("role") != "admin":
            raise PermissionError("Only admins can delete diagrams")
            
        diagram = await self.repository.get_by_id(diagram_id)
        if not diagram:
            return False
            
        success = await self.repository.soft_delete(diagram_id)
        if success:
            await self.db["audit_logs"].insert_one({
                "action": "DELETE_DIAGRAM",
                "user_id": ObjectId(user["_id"]),
                "diagram_id": ObjectId(diagram_id),
                "timestamp": datetime.now(timezone.utc)
            })
        return success

    async def save_graph(self, diagram_id: str, data: SaveGraph, user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        diagram = await self.get_diagram(diagram_id, user)
        if not diagram:
            return None
            
        updated_diagram = await self.repository.save_graph(diagram_id, data.graph_data, str(user["_id"]), data.comment)
        
        await self.db["audit_logs"].insert_one({
            "action": "SAVE_GRAPH",
            "user_id": ObjectId(user["_id"]),
            "diagram_id": ObjectId(diagram_id),
            "timestamp": datetime.now(timezone.utc)
        })
        
        return updated_diagram

    async def generate_xmi(self, diagram: Dict[str, Any]) -> str:  # async: router awaits this
        # Convert graph_data to XMI 2.1 XML string
        graph_data = diagram.get("graph_data", {})
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        # Setup XML namespaces
        ET.register_namespace('xmi', 'http://www.omg.org/spec/XMI/20131001')
        ET.register_namespace('uml', 'http://www.eclipse.org/uml2/5.0.0/UML')
        
        xmi_root = ET.Element('{http://www.omg.org/spec/XMI/20131001}XMI', {
            '{http://www.omg.org/spec/XMI/20131001}version': '2.1'
        })
        
        doc_elem = ET.SubElement(xmi_root, '{http://www.omg.org/spec/XMI/20131001}Documentation', {
            'exporter': 'ClassForge',
            'exporterVersion': '1.0'
        })

        model = ET.SubElement(xmi_root, '{http://www.eclipse.org/uml2/5.0.0/UML}Model', {
            '{http://www.omg.org/spec/XMI/20131001}id': 'Model1',
            'name': diagram.get("name", "Untitled")
        })
        
        node_type_map = {
            'class': 'uml:Class',
            'interface': 'uml:Interface',
            'abstract': 'uml:Class',
            'enum': 'uml:Enumeration'
        }
        
        vis_map = {
            '+': 'public',
            '-': 'private',
            '#': 'protected',
            '~': 'package'
        }
        
        node_elements = {}
        
        for node in nodes:
            ntype = node.get("type", "class")
            if ntype in ["note", "package"]: continue
            
            xmi_type = node_type_map.get(ntype, 'uml:Class')
            elem = ET.SubElement(model, 'packagedElement', {
                '{http://www.omg.org/spec/XMI/20131001}type': xmi_type,
                '{http://www.omg.org/spec/XMI/20131001}id': node["id"],
                'name': node.get("data", {}).get("name", "Unnamed")
            })
            node_elements[node["id"]] = elem
            
            if ntype == 'abstract':
                elem.set('isAbstract', 'true')
                
            data = node.get("data", {})
            for attr in data.get("attributes", []):
                attr_elem = ET.SubElement(elem, 'ownedAttribute', {
                    '{http://www.omg.org/spec/XMI/20131001}type': 'uml:Property',
                    '{http://www.omg.org/spec/XMI/20131001}id': f"{node['id']}_attr_{attr['name']}",
                    'name': attr.get("name", ""),
                    'visibility': vis_map.get(attr.get("visibility", "+"), "public")
                })
                type_elem = ET.SubElement(attr_elem, 'type', {
                    '{http://www.omg.org/spec/XMI/20131001}type': 'uml:PrimitiveType',
                    'href': f"pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#{attr.get('type', 'String')}"
                })
                
            for method in data.get("methods", []):
                method_elem = ET.SubElement(elem, 'ownedOperation', {
                    '{http://www.omg.org/spec/XMI/20131001}type': 'uml:Operation',
                    '{http://www.omg.org/spec/XMI/20131001}id': f"{node['id']}_op_{method['name']}",
                    'name': method.get("name", ""),
                    'visibility': vis_map.get(method.get("visibility", "+"), "public")
                })
                ret_type = method.get("return_type") or method.get("returnType")
                if ret_type:
                    ET.SubElement(method_elem, 'ownedParameter', {
                        '{http://www.omg.org/spec/XMI/20131001}type': 'uml:Parameter',
                        '{http://www.omg.org/spec/XMI/20131001}id': f"{node['id']}_op_{method['name']}_return",
                        'direction': 'return',
                        'type': ret_type
                    })
                for param in method.get("parameters", []):
                    ET.SubElement(method_elem, 'ownedParameter', {
                        '{http://www.omg.org/spec/XMI/20131001}type': 'uml:Parameter',
                        '{http://www.omg.org/spec/XMI/20131001}id': f"{node['id']}_op_{method['name']}_param_{param['name']}",
                        'name': param.get("name", ""),
                        'type': param.get("type", "String")
                    })
                
        # Edges
        for edge in edges:
            etype = edge.get("type", "association")
            source_id = edge.get("source")
            target_id = edge.get("target")
            
            if etype == 'inheritance' and source_id in node_elements:
                ET.SubElement(node_elements[source_id], 'generalization', {
                    '{http://www.omg.org/spec/XMI/20131001}type': 'uml:Generalization',
                    '{http://www.omg.org/spec/XMI/20131001}id': edge["id"],
                    'general': target_id
                })
            elif etype == 'realization' and source_id in node_elements:
                ET.SubElement(node_elements[source_id], 'interfaceRealization', {
                    '{http://www.omg.org/spec/XMI/20131001}type': 'uml:InterfaceRealization',
                    '{http://www.omg.org/spec/XMI/20131001}id': edge["id"],
                    'supplier': target_id,
                    'client': source_id,
                    'contract': target_id
                })
            elif etype in ['association', 'aggregation', 'composition']:
                assoc_elem = ET.SubElement(model, 'packagedElement', {
                    '{http://www.omg.org/spec/XMI/20131001}type': 'uml:Association',
                    '{http://www.omg.org/spec/XMI/20131001}id': edge["id"]
                })
                ET.SubElement(assoc_elem, 'memberEnd', {'{http://www.omg.org/spec/XMI/20131001}idref': f"{edge['id']}_src"})
                ET.SubElement(assoc_elem, 'memberEnd', {'{http://www.omg.org/spec/XMI/20131001}idref': f"{edge['id']}_tgt"})
                
                agg_kind = 'none'
                if etype == 'aggregation': agg_kind = 'shared'
                elif etype == 'composition': agg_kind = 'composite'
                
                src_end = ET.SubElement(assoc_elem, 'ownedEnd', {
                    '{http://www.omg.org/spec/XMI/20131001}type': 'uml:Property',
                    '{http://www.omg.org/spec/XMI/20131001}id': f"{edge['id']}_src",
                    'type': source_id,
                    'association': edge["id"]
                })
                if edge.get("source_multiplicity"):
                    ET.SubElement(src_end, 'lowerValue', {'{http://www.omg.org/spec/XMI/20131001}type': 'uml:LiteralString', 'value': edge.get("source_multiplicity")})
                    ET.SubElement(src_end, 'upperValue', {'{http://www.omg.org/spec/XMI/20131001}type': 'uml:LiteralString', 'value': edge.get("source_multiplicity")})
                    
                tgt_end = ET.SubElement(assoc_elem, 'ownedEnd', {
                    '{http://www.omg.org/spec/XMI/20131001}type': 'uml:Property',
                    '{http://www.omg.org/spec/XMI/20131001}id': f"{edge['id']}_tgt",
                    'type': target_id,
                    'association': edge["id"],
                    'aggregation': agg_kind
                })
                if edge.get("target_multiplicity"):
                    ET.SubElement(tgt_end, 'lowerValue', {'{http://www.omg.org/spec/XMI/20131001}type': 'uml:LiteralString', 'value': edge.get("target_multiplicity")})
                    ET.SubElement(tgt_end, 'upperValue', {'{http://www.omg.org/spec/XMI/20131001}type': 'uml:LiteralString', 'value': edge.get("target_multiplicity")})
                    
            elif etype == 'dependency':
                ET.SubElement(model, 'packagedElement', {
                    '{http://www.omg.org/spec/XMI/20131001}type': 'uml:Dependency',
                    '{http://www.omg.org/spec/XMI/20131001}id': edge["id"],
                    'client': source_id,
                    'supplier': target_id
                })

        extension = ET.SubElement(xmi_root, '{http://www.omg.org/spec/XMI/20131001}Extension', {'extender': 'ClassForge'})
        elements = ET.SubElement(extension, 'elements')
        for node in nodes:
            pos = node.get("position", {"x": 0, "y": 0})
            size = node.get("size", {"width": 200, "height": 120})
            ET.SubElement(elements, 'element', {
                '{http://www.omg.org/spec/XMI/20131001}idref': node["id"],
                'x': str(pos.get("x", 0)),
                'y': str(pos.get("y", 0)),
                'width': str(size.get("width", 200)),
                'height': str(size.get("height", 120))
            })
            
        xml_str = ET.tostring(xmi_root, encoding='utf-8', method='xml').decode('utf-8')
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

    def parse_xmi(self, xmi_content: str) -> Dict[str, Any]:
        try:
            root = ET.fromstring(xmi_content)
        except ET.ParseError:
            root = ET.Element('empty')
            
        # Clean namespaces to ease parsing
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
            new_attrib = {}
            for k, v in elem.attrib.items():
                if '}' in k:
                    new_attrib[k.split('}', 1)[1]] = v
                else:
                    new_attrib[k] = v
            elem.attrib = new_attrib
            
        graph_data = {
            "nodes": [],
            "edges": [],
            "viewport": {"x": 0, "y": 0, "zoom": 1.0}
        }
        
        vis_map_rev = {
            'public': '+',
            'private': '-',
            'protected': '#',
            'package': '~'
        }
        
        positions = {}
        for ext in root.findall('.//Extension'):
            if ext.get('extender') in ['ClassForge', 'Enterprise Architect']:
                for el in ext.findall('.//element'):
                    idref = el.get('idref')
                    if idref:
                        positions[idref] = {
                            "x": float(el.get('x', 0)),
                            "y": float(el.get('y', 0)),
                            "width": float(el.get('width', 200)),
                            "height": float(el.get('height', 120))
                        }
        
        col, row = 0, 0
        
        for pe in root.findall('.//packagedElement'):
            xmi_type = pe.get('type', '')
            
            if xmi_type in ['Class', 'Interface', 'Enumeration', 'uml:Class', 'uml:Interface', 'uml:Enumeration']:
                node_type = 'class'
                if xmi_type in ['Interface', 'uml:Interface']: node_type = 'interface'
                elif xmi_type in ['Enumeration', 'uml:Enumeration']: node_type = 'enum'
                elif pe.get('isAbstract') == 'true': node_type = 'abstract'
                
                node_id = pe.get('id')
                if not node_id: continue
                
                pos_data = positions.get(node_id, {})
                pos = {"x": pos_data.get("x", col * 250), "y": pos_data.get("y", row * 200)}
                size = {"width": pos_data.get("width", 200), "height": pos_data.get("height", 120)}
                
                if node_id not in positions:
                    col += 1
                    if col > 3:
                        col = 0
                        row += 1

                attrs = []
                for attr in pe.findall('./ownedAttribute'):
                    attr_type = 'String'
                    type_elem = attr.find('./type')
                    if type_elem is not None:
                        href = type_elem.get('href')
                        if href and '#' in href:
                            attr_type = href.split('#')[-1]
                    
                    attrs.append({
                        "name": attr.get('name', ''),
                        "type": attr_type,
                        "visibility": vis_map_rev.get(attr.get('visibility'), '+')
                    })
                    
                methods = []
                for op in pe.findall('./ownedOperation'):
                    ret_type = ''
                    params = []
                    for param in op.findall('./ownedParameter'):
                        if param.get('direction') == 'return':
                            ret_type = param.get('type', 'void')
                        else:
                            params.append({
                                "name": param.get('name', ''),
                                "type": param.get('type', 'String')
                            })
                            
                    methods.append({
                        "name": op.get('name', ''),
                        "return_type": ret_type,
                        "parameters": params,
                        "visibility": vis_map_rev.get(op.get('visibility'), '+')
                    })
                
                node = {
                    "id": node_id,
                    "type": node_type,
                    "position": pos,
                    "size": size,
                    "data": {
                        "name": pe.get('name', ''),
                        "stereotype": None,
                        "attributes": attrs,
                        "methods": methods,
                        "notes": None
                    }
                }
                graph_data["nodes"].append(node)
                
                # Nested generalizations
                for gen in pe.findall('./generalization'):
                    graph_data["edges"].append({
                        "id": gen.get('id', f"gen_{node_id}"),
                        "type": "inheritance",
                        "source": node_id,
                        "target": gen.get('general', '')
                    })
                # Nested interface realizations
                for real in pe.findall('./interfaceRealization'):
                    graph_data["edges"].append({
                        "id": real.get('id', f"real_{node_id}"),
                        "type": "realization",
                        "source": node_id,
                        "target": real.get('supplier', '')
                    })
                    
            elif xmi_type in ['Association', 'Dependency', 'uml:Association', 'uml:Dependency']:
                edge_id = pe.get('id')
                if not edge_id: continue
                
                if xmi_type in ['Dependency', 'uml:Dependency']:
                    graph_data["edges"].append({
                        "id": edge_id,
                        "type": "dependency",
                        "source": pe.get('client', ''),
                        "target": pe.get('supplier', ''),
                    })
                else:
                    src, tgt = None, None
                    agg = 'none'
                    src_mult, tgt_mult = None, None
                    
                    ends = pe.findall('.//ownedEnd')
                    if len(ends) >= 2:
                        src = ends[0].get('type')
                        tgt = ends[1].get('type')
                        agg = ends[1].get('aggregation', 'none')
                        
                        lv = ends[0].find('./lowerValue')
                        uv = ends[0].find('./upperValue')
                        if lv is not None and uv is not None:
                            src_mult = f"{lv.get('value', '1')}..{uv.get('value', '1')}" if lv.get('value') != uv.get('value') else lv.get('value')
                        
                        lv2 = ends[1].find('./lowerValue')
                        uv2 = ends[1].find('./upperValue')
                        if lv2 is not None and uv2 is not None:
                            tgt_mult = f"{lv2.get('value', '1')}..{uv2.get('value', '1')}" if lv2.get('value') != uv2.get('value') else lv2.get('value')
                    
                    etype = 'association'
                    if agg == 'shared': etype = 'aggregation'
                    elif agg == 'composite': etype = 'composition'
                    
                    if src and tgt:
                        graph_data["edges"].append({
                            "id": edge_id,
                            "type": etype,
                            "source": src,
                            "target": tgt,
                            "source_multiplicity": src_mult,
                            "target_multiplicity": tgt_mult
                        })
                        
        graph_data["edges"] = [e for e in graph_data["edges"] if e.get("source") and e.get("target")]
                
        return graph_data

    async def generate_ws_token(self, diagram_id: str, user_id: str) -> Dict[str, Any]:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        token = await self.repository.create_ws_token(diagram_id, user_id, expires_at)
        return {"token": token, "expires_at": expires_at}

