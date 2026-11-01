# -*- coding: utf-8 -*-
"""
Generador de backend FastAPI Asíncrono con Clean Architecture, Pydantic v2,
SQLAlchemy Async, soporte para Enums, Herencia y Relaciones (1-N, N-N).
"""
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set
from . import fastapi_templates as templates

PYTHON_RESERVED_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await", "break",
    "class", "continue", "def", "del", "elif", "else", "except", "finally",
    "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
    # Built-in collisions and SQLAlchemy attributes
    "type", "id", "schema", "metadata", "list", "dict", "set", "str", "int", "float"
}

SQL_RESERVED_WORDS = {
    "order", "user", "group", "select", "where", "table", "from", "by", "limit",
    "offset", "primary", "key", "index", "column", "alter", "create", "drop"
}


def transliterate_to_ascii(text: str) -> str:
    """Normaliza y translitera texto a ASCII plano, eliminando tildes y diacríticos."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return nfkd.encode("ASCII", "ignore").decode("ASCII")


def sanitize_class_name(raw_name: Any) -> str:
    """Convierte un nombre crudo a PascalCase seguro para Python/SQLAlchemy."""
    ascii_name = transliterate_to_ascii(str(raw_name or ""))
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", ascii_name)
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"Entity{cleaned}"
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned in PYTHON_RESERVED_KEYWORDS or cleaned.lower() in PYTHON_RESERVED_KEYWORDS:
        cleaned = f"{cleaned}Model"
    return cleaned


def to_snake_case(name: str) -> str:
    """Convierte cadenas PascalCase o camelCase a snake_case."""
    ascii_name = transliterate_to_ascii(name)
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", ascii_name)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    return re.sub(r"[^a-z0-9_]", "_", snake).strip("_")


def sanitize_attr_name(raw_name: Any) -> str:
    """Sanitiza nombres de atributos evitando palabras reservadas de Python."""
    ascii_name = transliterate_to_ascii(str(raw_name or ""))
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", ascii_name)
    if not cleaned:
        cleaned = "campo"
    snake = to_snake_case(cleaned)
    if not snake or not snake[0].isalpha():
        snake = f"col_{snake}"
    if snake in PYTHON_RESERVED_KEYWORDS or snake in ["id", "_id"]:
        snake = f"field_{snake}"
    return snake


def get_plural_name(name: str) -> str:
    """Genera el plural en español/inglés para endpoints y tablas."""
    lower = name.lower()
    if lower.endswith("s"):
        return lower
    if lower.endswith("y") and len(lower) > 1 and lower[-2] not in "aeiou":
        return lower[:-1] + "ies"
    if lower.endswith("z"):
        return lower[:-1] + "ces"
    if lower.endswith(("dad", "cion", "sion", "tad", "dor", "nal")):
        return lower + "es"
    return lower + "s"


def get_python_type_info(raw_type: str, known_enums: Set[str]) -> Dict[str, str]:
    """Mapea tipos UML a tipos Pydantic y columnas SQLAlchemy."""
    cleaned = transliterate_to_ascii(str(raw_type)).lower().strip()

    # Check for known enum match
    for enum_name in known_enums:
        if cleaned == enum_name.lower():
            return {
                "py": enum_name,
                "sa": f"SAEnum({enum_name})",
                "default": "None",
                "is_enum": True,
                "enum_class": enum_name,
            }

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
        "timestamp": {"py": "datetime", "sa": "DateTime", "default": "None"},
    }
    info = mapping.get(cleaned, {"py": "str", "sa": "String(255)", "default": '""'})
    info["is_enum"] = False
    return info


def generate_fastapi_project(graph_data: dict) -> Dict[str, str]:
    """
    Genera un proyecto completo FastAPI Asíncrono con Clean Architecture,
    Pydantic v2, SQLAlchemy Async, soporte para Enums, Herencia y Relaciones (1-N, N-N).
    """
    files: Dict[str, str] = {}

    nodes = graph_data.get("nodes", []) if isinstance(graph_data, dict) else []
    edges = graph_data.get("edges", []) if isinstance(graph_data, dict) else []

    # 1. Parse Enums first
    enums: Dict[str, List[str]] = {}
    for node in nodes:
        node_type = (node.get("type") or node.get("shape") or "").lower().replace("uml-", "").replace("-", "")
        if "enum" in node_type:
            data = node.get("data", {})
            raw_name = data.get("name") or "Status"
            enum_name = sanitize_class_name(raw_name)
            raw_attrs = data.get("attributes", [])
            literals = []
            for attr in raw_attrs:
                lit_name = attr.get("name") if isinstance(attr, dict) else str(attr).split(":")[0]
                clean_lit = transliterate_to_ascii(lit_name).upper().strip()
                clean_lit = re.sub(r"[^A-Z0-9_]", "_", clean_lit).strip("_")
                if clean_lit:
                    if clean_lit[0].isdigit():
                        clean_lit = f"VAL_{clean_lit}"
                    literals.append(clean_lit)
            if not literals:
                literals = ["ACTIVE", "INACTIVE"]
            enums[enum_name] = literals

    known_enums = set(enums.keys())

    # 2. Parse Classes
    classes: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        node_type = (node.get("type") or node.get("shape") or "").lower().replace("uml-", "").replace("-", "")
        if "enum" in node_type:
            continue
        if node_type in ["class", "abstract", "entity", "classnode"] or "class" in node_type or "entity" in node_type:
            data = node.get("data", {})
            raw_name = data.get("name") or "Entity"
            clean_name = sanitize_class_name(raw_name)
            s_name = to_snake_case(clean_name)
            plural = get_plural_name(s_name)
            tbl_name = f"app_{plural}" if s_name in SQL_RESERVED_WORDS else plural

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

                safe_aname = sanitize_attr_name(aname)
                type_info = get_python_type_info(atype, known_enums)
                parsed_attrs.append({
                    "name": safe_aname,
                    "py_type": type_info["py"],
                    "sa_type": type_info["sa"],
                    "default": type_info["default"],
                    "is_enum": type_info.get("is_enum", False),
                    "enum_class": type_info.get("enum_class"),
                })

            classes[str(node.get("id"))] = {
                "name": clean_name,
                "snake_name": s_name,
                "plural": plural,
                "table_name": tbl_name,
                "is_abstract": "abstract" in node_type,
                "attributes": parsed_attrs,
                "parent_id": None,
                "relations": [],
            }

    # 3. Process Edges / Relationships
    for edge in edges:
        source_val = edge.get("source")
        target_val = edge.get("target")
        source_id = str(source_val if isinstance(source_val, str) else (source_val.get("cell") if isinstance(source_val, dict) else str(source_val or "")))
        target_id = str(target_val if isinstance(target_val, str) else (target_val.get("cell") if isinstance(target_val, dict) else str(target_val or "")))
        rel_type = (edge.get("type") or edge.get("shape") or "").lower().replace("uml-", "").replace("-", "")

        edge_data = edge.get("data", {}) if isinstance(edge.get("data"), dict) else {}
        s_mult = str(edge_data.get("sourceMultiplicity") or "")
        t_mult = str(edge_data.get("targetMultiplicity") or "")

        if source_id in classes and target_id in classes:
            source_cls = classes[source_id]
            target_cls = classes[target_id]

            if rel_type in ["inheritance", "realization"]:
                classes[source_id]["parent_id"] = target_id
            elif rel_type in ["manytomany", "nn", "mn"] or (s_mult in ["*", "0..*"] and t_mult in ["*", "0..*"]):
                # Many to Many
                source_cls["relations"].append({
                    "type": "ManyToMany",
                    "target_id": target_id,
                    "target_name": target_cls["name"],
                    "target_snake": target_cls["snake_name"],
                    "target_plural": target_cls["plural"],
                    "target_table": target_cls["table_name"],
                })
                target_cls["relations"].append({
                    "type": "ManyToManyMapped",
                    "target_id": source_id,
                    "target_name": source_cls["name"],
                    "target_snake": source_cls["snake_name"],
                    "target_plural": source_cls["plural"],
                    "target_table": source_cls["table_name"],
                })
            else:
                # OneToMany (Source) -> ManyToOne (Target)
                source_cls["relations"].append({
                    "type": "OneToMany",
                    "target_id": target_id,
                    "target_name": target_cls["name"],
                    "target_snake": target_cls["snake_name"],
                    "target_plural": target_cls["plural"],
                    "target_table": target_cls["table_name"],
                })
                target_cls["relations"].append({
                    "type": "ManyToOne",
                    "target_id": source_id,
                    "target_name": source_cls["name"],
                    "target_snake": source_cls["snake_name"],
                    "target_plural": source_cls["plural"],
                    "target_table": source_cls["table_name"],
                })

    # 4. Generate Enums file if needed
    if enums:
        enum_blocks = []
        for ename, lits in enums.items():
            lines = [f"class {ename}(str, Enum):"]
            for lit in lits:
                lines.append(f'    {lit} = "{lit}"')
            enum_blocks.append("\n".join(lines))
        files["app/models/enums.py"] = templates.ENUMS_PY.format(
            enums_content="\n\n".join(enum_blocks)
        )

    project_name = "ClassForge"
    project_slug = "classforge"
    router_imports_list = []
    router_includes_list = []
    endpoints_docs = []

    # 5. Generate Models, Schemas, Routers
    for node_id, cls in classes.items():
        c_name = cls["name"]
        s_name = cls["snake_name"]
        p_name = cls["plural"]
        parent_id = cls.get("parent_id")
        parent_cls = classes.get(parent_id) if parent_id else None

        router_imports_list.append(f"from app.routers import {s_name}")
        router_includes_list.append(f"app.include_router({s_name}.router)")

        endpoints_docs.append(f"### {c_name} (`/api/v1/{p_name}`)")
        endpoints_docs.append(f"- `GET /api/v1/{p_name}` - Listar todos los {p_name}")
        endpoints_docs.append(f"- `GET /api/v1/{p_name}/{{id}}` - Obtener {c_name} por ID")
        endpoints_docs.append(f"- `POST /api/v1/{p_name}` - Crear nuevo {c_name}")
        endpoints_docs.append(f"- `PUT /api/v1/{p_name}/{{id}}` - Actualizar {c_name}")
        endpoints_docs.append(f"- `DELETE /api/v1/{p_name}/{{id}}` - Eliminar {c_name}\n")

        # Extra imports for model
        extra_imports = []
        enum_used = {attr["enum_class"] for attr in cls["attributes"] if attr.get("is_enum")}
        if enum_used:
            extra_imports.append(f"from app.models.enums import {', '.join(sorted(enum_used))}")

        association_tables = []
        relationship_fields = []
        base_class = "Base"
        mapper_args = ""
        id_field = "    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)"
        audit_fields = """    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)\n    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)"""

        # Handle Inheritance
        is_parent = any(c.get("parent_id") == node_id for c in classes.values())
        if is_parent:
            mapper_args = f"""    type = Column(String(50))\n    __mapper_args__ = {{\n        "polymorphic_on": type,\n        "polymorphic_identity": "{s_name}",\n    }}"""

        if parent_cls:
            extra_imports.append(f"from app.models.{parent_cls['snake_name']} import {parent_cls['name']}")
            base_class = parent_cls["name"]
            id_field = f'    id = Column(BigInteger, ForeignKey("{parent_cls["table_name"]}.id"), primary_key=True)'
            mapper_args = f"""    __mapper_args__ = {{\n        "polymorphic_identity": "{s_name}",\n    }}"""
            audit_fields = ""  # Inherited from parent

        # Handle Relationships in Model
        for rel in cls["relations"]:
            t_name = rel["target_name"]
            t_snake = rel["target_snake"]
            t_plural = rel["target_plural"]
            t_table = rel["target_table"]

            if rel["type"] == "ManyToOne":
                fk_name = f"{t_snake}_id"
                relationship_fields.append(f'    {fk_name} = Column(BigInteger, ForeignKey("{t_table}.id"), nullable=True)')
                relationship_fields.append(f'    {t_snake} = relationship("{t_name}", back_populates="{cls["plural"]}", foreign_keys=[{fk_name}])')
            elif rel["type"] == "OneToMany":
                relationship_fields.append(f'    {t_plural} = relationship("{t_name}", back_populates="{s_name}", cascade="all, delete-orphan")')
            elif rel["type"] == "ManyToMany":
                assoc_table_name = f"assoc_{s_name}_{t_snake}"
                assoc_def = f"""{assoc_table_name} = Table(
    "{assoc_table_name}",
    Base.metadata,
    Column("{s_name}_id", BigInteger, ForeignKey("{cls['table_name']}.id"), primary_key=True),
    Column("{t_snake}_id", BigInteger, ForeignKey("{t_table}.id"), primary_key=True)
)"""
                association_tables.append(assoc_def)
                relationship_fields.append(f'    {t_plural} = relationship("{t_name}", secondary={assoc_table_name}, back_populates="{cls["plural"]}")')
            elif rel["type"] == "ManyToManyMapped":
                assoc_table_name = f"assoc_{t_snake}_{s_name}"
                relationship_fields.append(f'    {t_plural} = relationship("{t_name}", secondary="{assoc_table_name}", back_populates="{cls["plural"]}")')

        # Model Fields
        model_fields = []
        for attr in cls["attributes"]:
            model_fields.append(f"    {attr['name']} = Column({attr['sa_type']}, nullable=True)")
        if not model_fields and not parent_cls:
            model_fields.append("    nombre = Column(String(255), nullable=True)")

        files[f"app/models/{s_name}.py"] = templates.MODEL_PY.format(
            class_name=c_name,
            table_name=cls["table_name"],
            base_class=base_class,
            extra_imports="\n".join(extra_imports),
            association_tables="\n".join(association_tables),
            mapper_args=mapper_args,
            id_field=id_field,
            fields="\n".join(model_fields),
            relationship_fields="\n".join(relationship_fields),
            audit_fields=audit_fields
        )

        # 2. Pydantic Schemas
        schema_extra_imports = []
        if enum_used:
            schema_extra_imports.append(f"from app.models.enums import {', '.join(sorted(enum_used))}")

        base_fields = []
        update_fields = []
        for attr in cls["attributes"]:
            base_fields.append(f"    {attr['name']}: Optional[{attr['py_type']}] = None")
            update_fields.append(f"    {attr['name']}: Optional[{attr['py_type']}] = None")

        # Include Foreign Keys in DTOs
        for rel in cls["relations"]:
            if rel["type"] == "ManyToOne":
                base_fields.append(f"    {rel['target_snake']}_id: Optional[int] = None")
                update_fields.append(f"    {rel['target_snake']}_id: Optional[int] = None")

        if not base_fields:
            base_fields.append("    nombre: Optional[str] = None")
            update_fields.append("    nombre: Optional[str] = None")

        base_create_class = f"{c_name}Base"
        base_response_class = f"{c_name}Base"

        if parent_cls:
            schema_extra_imports.append(f"from app.schemas.{parent_cls['snake_name']} import {parent_cls['name']}Base, {parent_cls['name']}Response")
            files[f"app/schemas/{s_name}.py"] = f"""# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
{chr(10).join(schema_extra_imports)}

class {c_name}Base({parent_cls['name']}Base):
{chr(10).join(base_fields)}

class {c_name}Create({c_name}Base):
    pass

class {c_name}Update(BaseModel):
{chr(10).join(update_fields)}

class {c_name}Response({c_name}Base):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
"""
        else:
            files[f"app/schemas/{s_name}.py"] = templates.SCHEMA_PY.format(
                class_name=c_name,
                extra_imports="\n".join(schema_extra_imports),
                base_fields="\n".join(base_fields),
                base_create_class=base_create_class,
                update_fields="\n".join(update_fields),
                base_response_class=base_response_class
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
