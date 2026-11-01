# -*- coding: utf-8 -*-
"""
Spring Boot 3 + Java 17 Production-Grade Code Generator.
Strictly adheres to Clean Architecture, SOLID Principles, and Spring Boot 3 Best Practices.
Supports Enums, Inheritance, 1-N, N-1, and N-N relationships.
"""
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set
from . import templates

JAVA_RESERVED_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class",
    "const", "continue", "default", "do", "double", "else", "enum", "extends", "final",
    "finally", "float", "for", "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private", "protected", "public",
    "return", "short", "static", "strictfp", "super", "switch", "synchronized", "this",
    "throw", "throws", "transient", "try", "void", "volatile", "while", "record", "var",
    "yield", "sealed", "permits", "object", "null", "true", "false"
}

SQL_RESERVED_WORDS = {
    "order", "user", "group", "select", "where", "table", "from", "by", "limit",
    "offset", "primary", "key", "index", "column", "alter", "create", "drop"
}


def transliterate_to_ascii(text: str) -> str:
    """Normalizes and transliterates text to plain ASCII, removing accents and diacritics."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return nfkd.encode("ASCII", "ignore").decode("ASCII")


def get_java_type(ts_type: str, known_enums: Set[str]) -> str:
    cleaned_lower = transliterate_to_ascii(str(ts_type)).lower().strip()

    # Check for known enum
    for enum_name in known_enums:
        if cleaned_lower == enum_name.lower():
            return enum_name

    mapping = {
        "string": "String",
        "str": "String",
        "text": "String",
        "varchar": "String",
        "char": "String",
        "int": "Integer",
        "integer": "Integer",
        "number": "Double",
        "long": "Long",
        "bigint": "Long",
        "double": "Double",
        "float": "Double",
        "decimal": "Double",
        "bool": "Boolean",
        "boolean": "Boolean",
        "date": "LocalDate",
        "datetime": "LocalDateTime",
        "timestamp": "LocalDateTime",
        "time": "LocalTime"
    }
    return mapping.get(cleaned_lower, "String")


def sanitize_class_name(raw_name: Any) -> str:
    ascii_name = transliterate_to_ascii(str(raw_name or ""))
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", ascii_name)
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"Entity{cleaned}"
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned.lower() in JAVA_RESERVED_KEYWORDS:
        cleaned = f"{cleaned}Entity"
    return cleaned


def sanitize_attr_name(raw_name: Any) -> str:
    ascii_name = transliterate_to_ascii(str(raw_name or ""))
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", ascii_name)
    if not cleaned:
        cleaned = "campo"
    parts = [p for p in cleaned.split("_") if p]
    if len(parts) > 1:
        camel = parts[0].lower() + "".join(p.capitalize() for p in parts[1:])
    elif parts:
        camel = parts[0][0].lower() + parts[0][1:]
    else:
        camel = "campo"
    if camel.lower() in JAVA_RESERVED_KEYWORDS or camel.lower() in SQL_RESERVED_WORDS:
        camel = f"val{camel.capitalize()}"
    return camel


def get_plural_name(name: str) -> str:
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


def generate_validation_annotations(attr_name: str, java_type: str, is_enum: bool = False) -> str:
    if is_enum:
        return f'    @NotNull(message = "El campo {attr_name} es obligatorio")'

    annotations = []
    lower_attr = attr_name.lower()

    if java_type == "String":
        if "email" in lower_attr or "correo" in lower_attr:
            annotations.append('    @NotBlank(message = "El correo electrónico es obligatorio")')
            annotations.append('    @Email(message = "El formato del correo electrónico no es válido")')
        elif "phone" in lower_attr or "telefono" in lower_attr or "celular" in lower_attr:
            annotations.append('    @NotBlank(message = "El teléfono es obligatorio")')
        else:
            annotations.append(f'    @NotBlank(message = "El campo {attr_name} no puede estar vacío")')
        annotations.append(f'    @Size(max = 255, message = "El campo {attr_name} no puede exceder 255 caracteres")')
    elif java_type in ["Integer", "Long", "Double"]:
        annotations.append(f'    @NotNull(message = "El campo {attr_name} es obligatorio")')
        if any(k in lower_attr for k in ["price", "precio", "cost", "costo", "monto", "amount", "total", "salary", "salario"]):
            annotations.append(f'    @PositiveOrZero(message = "El valor de {attr_name} debe ser mayor o igual a 0")')
        elif any(k in lower_attr for k in ["age", "edad", "qty", "quantity", "cantidad", "stock"]):
            annotations.append(f'    @Min(value = 0, message = "El valor de {attr_name} no puede ser negativo")')
    elif java_type in ["LocalDate", "LocalDateTime"]:
        annotations.append(f'    @NotNull(message = "La fecha para {attr_name} es obligatoria")')
    else:
        annotations.append(f'    @NotNull(message = "El campo {attr_name} es obligatorio")')

    return "\n".join(annotations)


def generate_spring_boot_project(graph_data: dict, package_name: str = "com.classforge") -> Dict[str, str]:
    files = {}
    base_path = package_name.replace(".", "/")

    # Base Configuration and Infrastructure Files
    files["pom.xml"] = templates.POM_XML.format(package_name=package_name)
    files["src/main/resources/application.yml"] = templates.APPLICATION_YML
    files[f"src/main/java/{base_path}/MainApplication.java"] = templates.MAIN_APPLICATION.format(package_name=package_name)
    files[f"src/main/java/{base_path}/config/OpenApiConfig.java"] = templates.OPENAPI_CONFIG.format(package_name=package_name)
    files[f"src/main/java/{base_path}/config/CorsConfig.java"] = templates.CORS_CONFIG.format(package_name=package_name)
    files[f"src/main/java/{base_path}/config/CloudConfig.java"] = templates.CLOUD_CONFIG.format(package_name=package_name)
    files[f"src/main/java/{base_path}/services/CloudSyncService.java"] = templates.CLOUD_SYNC_SERVICE.format(package_name=package_name)
    files[f"src/main/java/{base_path}/controllers/CloudController.java"] = templates.CLOUD_CONTROLLER.format(package_name=package_name)

    # Global Exception Handling
    files[f"src/main/java/{base_path}/exceptions/ResourceNotFoundException.java"] = templates.RESOURCE_NOT_FOUND_EXCEPTION.format(package_name=package_name)
    files[f"src/main/java/{base_path}/exceptions/BadRequestException.java"] = templates.BAD_REQUEST_EXCEPTION.format(package_name=package_name)
    files[f"src/main/java/{base_path}/exceptions/ErrorResponseDTO.java"] = templates.ERROR_RESPONSE_DTO.format(package_name=package_name)
    files[f"src/main/java/{base_path}/exceptions/GlobalExceptionHandler.java"] = templates.GLOBAL_EXCEPTION_HANDLER.format(package_name=package_name)

    # VS Code Configurations & 1-Click Launchers
    files[".vscode/launch.json"] = templates.VSCODE_LAUNCH_JSON.format(package_name=package_name)
    files[".vscode/settings.json"] = templates.VSCODE_SETTINGS_JSON
    files[".vscode/extensions.json"] = templates.VSCODE_EXTENSIONS_JSON
    files["run.bat"] = templates.RUN_BAT
    files["run.sh"] = templates.RUN_SH
    files["mvnw.cmd"] = templates.MVNW_CMD
    files["mvnw"] = templates.MVNW_SH

    nodes = graph_data.get("nodes", []) if isinstance(graph_data, dict) else []
    edges = graph_data.get("edges", []) if isinstance(graph_data, dict) else []

    # 1. Parse Enums
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

    # Generate enum files
    for enum_name, lits in enums.items():
        formatted_lits = ",\n".join(f"    {lit}" for lit in lits) + ";"
        files[f"src/main/java/{base_path}/entities/enums/{enum_name}.java"] = templates.ENUM_TEMPLATE.format(
            package_name=package_name,
            enum_name=enum_name,
            literals=formatted_lits
        )

    # 2. Index Classes
    classes: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        node_type = (node.get("type") or node.get("shape") or "").lower().replace("uml-", "").replace("-", "")
        if "enum" in node_type:
            continue
        if node_type in ["class", "abstract", "entity", "classnode"] or "class" in node_type or "entity" in node_type:
            data = node.get("data", {})
            raw_name = data.get("name") or "Entity"
            clean_name = sanitize_class_name(raw_name)

            classes[str(node.get("id"))] = {
                "name": clean_name,
                "is_abstract": "abstract" in node_type,
                "attributes": data.get("attributes", []),
                "methods": data.get("methods", []),
                "relations": [],
                "parent_id": None
            }

    # 3. Process Relationships / Edges
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
            source_name = classes[source_id]["name"]
            target_name = classes[target_id]["name"]

            if rel_type in ["inheritance", "realization"]:
                classes[source_id]["parent_id"] = target_id
            elif rel_type in ["manytomany", "nn", "mn"] or (s_mult in ["*", "0..*"] and t_mult in ["*", "0..*"]):
                classes[source_id]["relations"].append({
                    "type": "ManyToMany",
                    "target_id": target_id,
                    "target_name": target_name,
                    "rel_type": rel_type
                })
                classes[target_id]["relations"].append({
                    "type": "ManyToManyMapped",
                    "target_id": source_id,
                    "target_name": source_name,
                    "rel_type": rel_type
                })
            elif rel_type in ["composition", "aggregation", "association"]:
                # Source (Parent/Whole) has OneToMany target items
                classes[source_id]["relations"].append({
                    "type": "OneToMany",
                    "target_id": target_id,
                    "target_name": target_name,
                    "rel_type": rel_type
                })
                # Target (Child/Part) has ManyToOne pointing to parent
                classes[target_id]["relations"].append({
                    "type": "ManyToOne",
                    "target_id": source_id,
                    "target_name": source_name,
                    "rel_type": rel_type
                })

    endpoints_docs = []

    # 4. Generate Layered Architecture per Class
    for cls_id, cls in classes.items():
        name = cls["name"]
        raw_table = get_plural_name(name)
        table_name = f"app_{raw_table}" if raw_table.lower() in SQL_RESERVED_WORDS else raw_table
        url_path = get_plural_name(name)
        endpoints_docs.append(f"- `http://localhost:8080/api/v1/{url_path}` (CRUD para {name})")

        fields = []
        dto_req_fields = []
        dto_res_fields = []
        update_entity_fields = []
        map_to_dto_fields = []
        map_to_entity_fields = []

        # ID and Audit fields
        if not cls["parent_id"]:
            fields.append("    @Id\n    @GeneratedValue(strategy = GenerationType.IDENTITY)\n    private Long id;\n")

        for attr in cls["attributes"]:
            if isinstance(attr, dict):
                raw_attr_name = attr.get("name", "")
                raw_attr_type = attr.get("type", "string")
            elif isinstance(attr, str):
                cleaned = attr.lstrip("+-#~ ").strip()
                if ":" in cleaned:
                    parts = cleaned.split(":", 1)
                    raw_attr_name = parts[0].strip()
                    raw_attr_type = parts[1].strip()
                else:
                    raw_attr_name = cleaned
                    raw_attr_type = "string"
            else:
                continue

            attr_name = sanitize_attr_name(raw_attr_name)
            if not attr_name:
                continue
            if attr_name.lower() in ["id", "_id", "createdat", "updatedat", "created_at", "updated_at"]:
                continue

            attr_type = get_java_type(raw_attr_type, known_enums)
            is_enum_field = attr_type in known_enums
            camel_name = attr_name[0].upper() + attr_name[1:]

            # Entity Field
            column_name = re.sub(r'(?<!^)(?=[A-Z])', '_', attr_name).lower()
            if is_enum_field:
                fields.append(f"    @Enumerated(EnumType.STRING)\n    @Column(name = \"{column_name}\")\n    private {attr_type} {attr_name};\n")
            else:
                fields.append(f"    @Column(name = \"{column_name}\")\n    private {attr_type} {attr_name};\n")

            # DTO Request Field with Validations
            validation_str = generate_validation_annotations(attr_name, attr_type, is_enum=is_enum_field)
            dto_req_fields.append(f"{validation_str}\n    private {attr_type} {attr_name};\n")

            # DTO Response Field
            dto_res_fields.append(f"    private {attr_type} {attr_name};")

            # Mapper fields
            map_to_dto_fields.append(f"        dto.set{camel_name}(entity.get{camel_name}());")
            map_to_entity_fields.append(f"        entity.set{camel_name}(dto.get{camel_name}());")
            update_entity_fields.append(f"        entity.set{camel_name}(dto.get{camel_name}());")

        # Relations
        for rel in cls["relations"]:
            target_name = rel["target_name"]
            field_name = target_name[0].lower() + target_name[1:]
            rel_type = rel["type"]

            if rel_type == "ManyToOne":
                col_name = f"{re.sub(r'(?<!^)(?=[A-Z])', '_', field_name).lower()}_id"
                fields.append(f"    @ManyToOne(fetch = FetchType.LAZY)\n    @JoinColumn(name = \"{col_name}\")\n    @JsonIgnoreProperties(\"{name[0].lower() + name[1:]}s\")\n    private {target_name} {field_name};\n")
                dto_req_fields.append(f"    private Long {field_name}Id;\n")
                dto_res_fields.append(f"    private Long {field_name}Id;")
            elif rel_type == "OneToMany":
                fields.append(f"    @OneToMany(mappedBy = \"{name[0].lower() + name[1:]}\", cascade = CascadeType.ALL, orphanRemoval = true)\n    @JsonIgnoreProperties(\"{name[0].lower() + name[1:]}\")\n    @Builder.Default\n    private List<{target_name}> {field_name}s = new ArrayList<>();\n")
            elif rel_type == "ManyToMany":
                target_col = f"{re.sub(r'(?<!^)(?=[A-Z])', '_', target_name).lower()}_id"
                source_col = f"{re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()}_id"
                join_table = f"{table_name}_{get_plural_name(target_name)}"
                fields.append(f"""    @ManyToMany\n    @JoinTable(\n        name = \"{join_table}\",\n        joinColumns = @JoinColumn(name = \"{source_col}\"),\n        inverseJoinColumns = @JoinColumn(name = \"{target_col}\")\n    )\n    @JsonIgnoreProperties(\"{get_plural_name(name)}\")\n    @Builder.Default\n    private List<{target_name}> {field_name}List = new ArrayList<>();\n""")
            elif rel_type == "ManyToManyMapped":
                fields.append(f"""    @ManyToMany(mappedBy = \"{name[0].lower() + name[1:]}List\")\n    @JsonIgnoreProperties(\"{name[0].lower() + name[1:]}List\")\n    @Builder.Default\n    private List<{target_name}> {field_name}List = new ArrayList<>();\n""")

        # Base Audit Fields in Entity
        if not cls["parent_id"]:
            fields.append("    @CreationTimestamp\n    @Column(name = \"created_at\", updatable = false)\n    private LocalDateTime createdAt;\n")
            fields.append("    @UpdateTimestamp\n    @Column(name = \"updated_at\")\n    private LocalDateTime updatedAt;\n")

        fields_str = "\n".join(fields)
        dto_req_fields_str = "\n".join(dto_req_fields)
        dto_res_fields_str = "\n".join(dto_res_fields)
        update_entity_fields_str = "\n".join(update_entity_fields)
        map_to_dto_fields_str = "\n".join(map_to_dto_fields)
        map_to_entity_fields_str = "\n".join(map_to_entity_fields)

        inheritance_annotation = ""
        extends_clause = ""

        is_parent = any(c["parent_id"] == cls_id for c in classes.values())
        if is_parent:
            inheritance_annotation = "@Inheritance(strategy = InheritanceType.JOINED)"

        if cls["parent_id"] and cls["parent_id"] in classes:
            parent_name = classes[cls["parent_id"]]["name"]
            extends_clause = f"extends {parent_name}"

        # 1. Entity
        files[f"src/main/java/{base_path}/entities/{name}.java"] = templates.ENTITY_TEMPLATE.format(
            package_name=package_name,
            table_name=table_name,
            inheritance_annotation=inheritance_annotation,
            class_name=name,
            extends_clause=extends_clause,
            fields=fields_str
        )

        # 2. Repository
        files[f"src/main/java/{base_path}/repositories/{name}Repository.java"] = templates.REPOSITORY_TEMPLATE.format(
            package_name=package_name,
            class_name=name
        )

        # 3. Request DTO
        files[f"src/main/java/{base_path}/dto/{name}RequestDTO.java"] = templates.DTO_REQUEST_TEMPLATE.format(
            package_name=package_name,
            class_name=name,
            fields=dto_req_fields_str
        )

        # 4. Response DTO
        files[f"src/main/java/{base_path}/dto/{name}ResponseDTO.java"] = templates.DTO_RESPONSE_TEMPLATE.format(
            package_name=package_name,
            class_name=name,
            fields=dto_res_fields_str
        )

        # 5. Dedicated Mapper (SRP)
        files[f"src/main/java/{base_path}/mappers/{name}Mapper.java"] = templates.MAPPER_TEMPLATE.format(
            package_name=package_name,
            class_name=name,
            map_to_entity_fields=map_to_entity_fields_str,
            map_to_dto_fields=map_to_dto_fields_str,
            update_entity_fields=update_entity_fields_str
        )

        # 6. Service Interface
        files[f"src/main/java/{base_path}/services/{name}Service.java"] = templates.SERVICE_INTERFACE_TEMPLATE.format(
            package_name=package_name,
            class_name=name
        )

        # 7. Service Implementation
        files[f"src/main/java/{base_path}/services/impl/{name}ServiceImpl.java"] = templates.SERVICE_IMPL_TEMPLATE.format(
            package_name=package_name,
            class_name=name
        )

        # 8. REST Controller
        files[f"src/main/java/{base_path}/controllers/{name}Controller.java"] = templates.CONTROLLER_TEMPLATE.format(
            package_name=package_name,
            class_name=name,
            url_path=url_path
        )

    # Project README.md
    endpoints_str = "\n".join(endpoints_docs) if endpoints_docs else "- *(Sin entidades definidas en el diagrama)*"
    files["README.md"] = templates.PROJECT_README_MD.format(
        project_name="ClassForge Generated Project",
        base_path=base_path,
        endpoints_list=endpoints_str
    )

    return files
