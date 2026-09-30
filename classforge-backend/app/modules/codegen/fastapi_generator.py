# -*- coding: utf-8 -*-
import re
from typing import Dict, Any, List
from . import fastapi_templates as templates

PYTHON_RESERVED_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await", "break",
    "class", "continue", "def", "del", "elif", "else", "except", "finally",
    "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"
}

def get_python_type_info(raw_type: str) -> Dict[str, str]:
    cleaned = str(raw_type).lower().strip()
    mapping = {
        "string": {"py": "str", "sa": "String(255)", "default": '""'},
        "str": {"py": "str", "sa": "String(255)", "default": '""'},
        "text": {"py": "str", "sa": "String(1000)", "default": '""'},
        "varchar": {"py": "str", "sa": "String(255)", "default": '""'},
        "int": {"py": "int", "sa": "Integer", "default": "0"},
        "integer": {"py": "int", "sa": "Integer", "default": "0"},
        "long": {"py": "int", "sa": "BigInteger", "default": "0"},
        "bigint": {"py": "int", "sa": "BigInteger", "default": "0"},
        "double": {"py": "float", "sa": "Float", "default": "0.0"},
        "float": {"py": "float", "sa": "Float", "default": "0.0"},
        "decimal": {"py": "float", "sa": "Float", "default": "0.0"},
        "bool": {"py": "bool", "sa": "Boolean", "default": "True"},
        "boolean": {"py": "bool", "sa": "Boolean", "default": "True"},
        "date": {"py": "date", "sa": "Date", "default": "None"},
        "datetime": {"py": "datetime", "sa": "DateTime", "default": "None"},
        "timestamp": {"py": "datetime", "sa": "DateTime", "default": "None"}
    }
    return mapping.get(cleaned, {"py": "str", "sa": "String(255)", "default": '""'})

def sanitize_class_name(raw_name: Any) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '', str(raw_name or ''))
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"Entity{cleaned}"
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned in PYTHON_RESERVED_KEYWORDS:
        cleaned = f"{cleaned}Model"
    return cleaned

def to_snake_case(name: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def get_plural_name(name: str) -> str:
    lower = name.lower()
    if lower.endswith("s"):
        return lower
    if lower.endswith("y") and len(lower) > 1 and lower[-2] not in "aeiou":
        return lower[:-1] + "ies"
    if lower.endswith("z"):
        return lower[:-1] + "ces"
    if lower.endswith("dad") or lower.endswith("cion") or lower.endswith("sion") or lower.endswith("tad"):
        return lower + "es"
    return lower + "s"

def generate_fastapi_project(graph_data: dict) -> Dict[str, str]:
    """
    Generates a full asynchronous FastAPI backend with Clean Architecture,
    Pydantic v2, SQLAlchemy Async, SQLite/PostgreSQL support, Cloud Bridge & Render deploy readiness.
    """
    files: Dict[str, str] = {}
    
    nodes = graph_data.get("nodes", []) if isinstance(graph_data, dict) else []
    edges = graph_data.get("edges", []) if isinstance(graph_data, dict) else []
    
    classes: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        node_type = (node.get("type") or node.get("shape") or "").lower().replace("uml-", "")
        if node_type in ["class", "abstract", "entity", "classnode"]:
            data = node.get("data", {})
            raw_name = data.get("name") or "Entity"
            clean_name = sanitize_class_name(raw_name)
            
            raw_attrs = data.get("attributes", [])
            parsed_attrs = []
            for attr in raw_attrs:
                if isinstance(attr, dict):
                    aname = attr.get("name", "")
                    atype = attr.get("type", "string")
                elif isinstance(attr, str):
                    cleaned = attr.lstrip("+-#~ ").strip()
                    if ":" in cleaned:
                        parts = cleaned.split(":", 1)
                        aname = parts[0].strip()
                        atype = parts[1].strip()
                    else:
                        aname = cleaned
                        atype = "string"
                else:
                    continue
                aname = re.sub(r'[^a-zA-Z0-9_]', '', str(aname))
                if not aname or aname.lower() in ["id", "_id", "createdat", "updatedat", "created_at", "updated_at"]:
                    continue
                aname = to_snake_case(aname)
                type_info = get_python_type_info(atype)
                parsed_attrs.append({
                    "name": aname,
                    "py_type": type_info["py"],
                    "sa_type": type_info["sa"],
                    "default": type_info["default"]
                })
                
            classes[str(node.get("id"))] = {
                "name": clean_name,
                "snake_name": to_snake_case(clean_name),
                "plural": get_plural_name(to_snake_case(clean_name)),
                "table_name": get_plural_name(to_snake_case(clean_name)),
                "attributes": parsed_attrs
            }
            
    project_name = "ClassForge"
    project_slug = "classforge"
    
    router_imports_list = []
    router_includes_list = []
    endpoints_docs = []
    
    for node_id, cls in classes.items():
        c_name = cls["name"]
        s_name = cls["snake_name"]
        p_name = cls["plural"]
        
        router_imports_list.append(f"from app.routers import {s_name}")
        router_includes_list.append(f"app.include_router({s_name}.router)")
        
        endpoints_docs.append(f"### {c_name} (`/api/v1/{p_name}`)")
        endpoints_docs.append(f"- `GET /api/v1/{p_name}` - Listar todos los {p_name}")
        endpoints_docs.append(f"- `GET /api/v1/{p_name}/{{id}}` - Obtener {c_name} por ID")
        endpoints_docs.append(f"- `POST /api/v1/{p_name}` - Crear nuevo {c_name}")
        endpoints_docs.append(f"- `PUT /api/v1/{p_name}/{{id}}` - Actualizar {c_name}")
        endpoints_docs.append(f"- `DELETE /api/v1/{p_name}/{{id}}` - Eliminar {c_name}\n")
        
        # 1. SQLAlchemy Model
        model_fields = []
        for attr in cls["attributes"]:
            model_fields.append(f"    {attr['name']} = Column({attr['sa_type']}, nullable=True)")
        if not model_fields:
            model_fields.append("    nombre = Column(String(255), nullable=True)")
            
        files[f"app/models/{s_name}.py"] = templates.MODEL_PY.format(
            class_name=c_name,
            table_name=cls["table_name"],
            fields="\n".join(model_fields)
        )
        
        # 2. Pydantic Schemas
        base_fields = []
        update_fields = []
        for attr in cls["attributes"]:
            base_fields.append(f"    {attr['name']}: {attr['py_type']}")
            update_fields.append(f"    {attr['name']}: Optional[{attr['py_type']}] = None")
        if not base_fields:
            base_fields.append("    nombre: Optional[str] = None")
            update_fields.append("    nombre: Optional[str] = None")
            
        files[f"app/schemas/{s_name}.py"] = templates.SCHEMA_PY.format(
            class_name=c_name,
            base_fields="\n".join(base_fields),
            update_fields="\n".join(update_fields)
        )
        
        # 3. Router
        files[f"app/routers/{s_name}.py"] = templates.ROUTER_PY.format(
            class_name=c_name,
            model_file=s_name,
            schema_file=s_name,
            url_path=p_name
        )

    # Core & Infrastructure Files
    files["app/__init__.py"] = ""
    files["app/models/__init__.py"] = ""
    files["app/schemas/__init__.py"] = ""
    files["app/routers/__init__.py"] = ""
    
    files["app/config.py"] = templates.CONFIG_PY.format(project_name=project_name)
    files["app/database.py"] = templates.DATABASE_PY
    files["app/routers/cloud_sync.py"] = templates.CLOUD_SYNC_ROUTER_PY
    
    files["app/main.py"] = templates.MAIN_PY.format(
        project_name=project_name,
        router_imports="\n".join(router_imports_list),
        router_includes="\n".join(router_includes_list)
    )
    
    files["requirements.txt"] = templates.REQUIREMENTS_TXT
    files["Dockerfile"] = templates.DOCKERFILE
    files["render.yaml"] = templates.RENDER_YAML.format(project_slug=project_slug)
    files["run.bat"] = templates.RUN_BAT.format(project_name=project_name)
    files["run.sh"] = templates.RUN_SH.format(project_name=project_name)
    files[".env.example"] = "PORT=8000\nDATABASE_URL=sqlite+aiosqlite:///./app.db\nCLASSFORGE_CLOUD_URL=https://classforge-backend.onrender.com\nCLASSFORGE_API_KEY=\n"
    
    endpoints_str = "\n".join(endpoints_docs) if endpoints_docs else "- *(Sin entidades definidas en el diagrama)*"
    files["README.md"] = templates.FASTAPI_README_MD.format(
        project_name=project_name,
        endpoints_list=endpoints_str
    )
    
    return files
