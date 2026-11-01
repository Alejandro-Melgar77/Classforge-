# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import SecretStr

from app.llm import LlmMessage, LlmRequest, get_provider
from app.modules.codegen.fastapi_generator import generate_fastapi_project
from app.modules.codegen.generator import generate_spring_boot_project

logger = logging.getLogger("classforge.codegen.gemini")


def parse_diagram_semantics(graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts high-level semantics from AntV X6 graph data:
    classes, attributes with types, methods, relations with multiplicities.
    """
    nodes = list(graph_data.get("nodes", [])) if isinstance(graph_data, dict) else []
    edges = list(graph_data.get("edges", [])) if isinstance(graph_data, dict) else []

    if not nodes and not edges and isinstance(graph_data, dict) and "cells" in graph_data:
        cells = graph_data.get("cells", [])
        for cell in cells:
            shape = (cell.get("shape") or cell.get("type") or "").lower()
            if "edge" in shape or cell.get("source") or cell.get("target"):
                edges.append(cell)
            else:
                nodes.append(cell)

    classes = []
    class_id_map = {}

    for node in nodes:
        node_type = (node.get("type") or node.get("shape") or "").lower().replace("uml-", "").replace("-", "")
        if node_type in ["class", "abstract", "entity", "classnode"] or "class" in node_type or "entity" in node_type:
            data = node.get("data", {})
            raw_name = data.get("name") or "Entity"
            clean_name = re.sub(r"[^a-zA-Z0-9_]", "", str(raw_name))
            if clean_name:
                clean_name = clean_name[0].upper() + clean_name[1:]

            node_id = str(node.get("id"))
            class_id_map[node_id] = clean_name

            classes.append(
                {
                    "id": node_id,
                    "name": clean_name,
                    "is_abstract": "abstract" in node_type,
                    "attributes": data.get("attributes", []),
                    "methods": data.get("methods", []),
                }
            )

    relations = []
    for edge in edges:
        source_val = edge.get("source")
        target_val = edge.get("target")
        source_id = str(source_val if isinstance(source_val, str) else (source_val.get("cell") if isinstance(source_val, dict) else str(source_val or "")))
        target_id = str(target_val if isinstance(target_val, str) else (target_val.get("cell") if isinstance(target_val, dict) else str(target_val or "")))

        source_name = class_id_map.get(source_id)
        target_name = class_id_map.get(target_id)

        if source_name and target_name:
            edge_data = edge.get("data", {})
            edge_type = (edge_data.get("type") or edge.get("shape") or "association").lower()
            relations.append(
                {
                    "source": source_name,
                    "target": target_name,
                    "type": edge_type,
                    "source_multiplicity": edge_data.get("sourceMultiplicity", "1"),
                    "target_multiplicity": edge_data.get("targetMultiplicity", "*"),
                    "label": edge_data.get("label", ""),
                }
            )

    return {
        "classes": classes,
        "relations": relations,
        "total_classes": len(classes),
        "total_relations": len(relations),
    }


def ensure_vscode_and_runner_files(files: Dict[str, str], package_name: str = "com.classforge.generated") -> Dict[str, str]:
    """
    Ensures that essential VS Code developer configurations and 1-click execution
    scripts (run.bat, run.sh, mvnw.cmd, mvnw) are always present in the generated project.
    """
    from app.modules.codegen import templates

    if ".vscode/launch.json" not in files:
        files[".vscode/launch.json"] = templates.VSCODE_LAUNCH_JSON.format(package_name=package_name)
    if ".vscode/settings.json" not in files:
        files[".vscode/settings.json"] = templates.VSCODE_SETTINGS_JSON
    if ".vscode/extensions.json" not in files:
        files[".vscode/extensions.json"] = templates.VSCODE_EXTENSIONS_JSON
    if "run.bat" not in files:
        files["run.bat"] = templates.RUN_BAT
    if "run.sh" not in files:
        files["run.sh"] = templates.RUN_SH
    if "mvnw.cmd" not in files:
        files["mvnw.cmd"] = templates.MVNW_CMD
    if "mvnw" not in files:
        files["mvnw"] = templates.MVNW_SH
    return files


def build_spring_boot_instruction() -> str:
    return """You are a Principal Software Architect and Lead Spring Boot Engineer.
Your task is to take a UML Class Diagram specification and generate a complete, production-grade Spring Boot 3.3.x / Java 17 backend application following strict Clean Architecture, Clean Code principles, and standard Java / Spring Boot conventions.

CRITICAL REQUIREMENTS:
1. Strict Package Structure: com.classforge.generated
   - config: OpenApiConfig.java, CorsConfig.java, CloudConfig.java
   - entities: JPA entities with @Entity, @Table, @Id @GeneratedValue(IDENTITY), relationships (@ManyToOne, @OneToMany, @OneToOne)
   - dto: Dedicated {Entity}RequestDTO and {Entity}ResponseDTO
   - mappers: Dedicated {Entity}Mapper
   - repositories: JpaRepository<{Entity}, Long> with custom derived query methods
   - services: Interface {Entity}Service and implementation {Entity}ServiceImpl
   - exceptions: GlobalExceptionHandler, ResourceNotFoundException, BadRequestException
   - controllers: REST controllers with @RestController, @RequestMapping("/api/v1/{plural}"), @Valid
   - MainApplication.java: Main Spring Boot application
   - resources/application.yml: HikariCP, PostgreSQL / H2 config
   - pom.xml: Complete Maven build file
   - README.md: Quickstart guide

2. Standard Java & Spring Boot Conventions.
3. Output Format:
   Return ONLY a valid JSON object matching this schema:
   {
     "files": {
       "src/main/java/com/classforge/generated/MainApplication.java": "...",
       "pom.xml": "...",
       "README.md": "..."
     },
     "summary": "Detailed technical explanation of the architecture."
   }
"""


def build_fastapi_instruction() -> str:
    return """You are a Principal Software Architect and Lead Python Engineer.
Your task is to take a UML Class Diagram specification and generate a complete, production-grade FastAPI (Python 3.11+) backend application following strict Clean Architecture, Pydantic v2, SQLAlchemy 2.0 Async, and Render Deployment readiness.

CRITICAL REQUIREMENTS:
1. Strict Modular Structure:
   - app/main.py: FastAPI initialization, CORS middleware, lifespan event, router registrations, Swagger UI
   - app/config.py: Pydantic BaseSettings with DATABASE_URL, CLASSFORGE_CLOUD_URL, CORS
   - app/database.py: Async engine (create_async_engine), sessionmaker, and Base declarative
   - app/models/{entity}.py: SQLAlchemy Models
   - app/schemas/{entity}.py: Pydantic v2 models
   - app/routers/{entity}.py: Async APIRouter with CRUD operations
   - requirements.txt: fastapi, uvicorn, pydantic, sqlalchemy, aiosqlite, asyncpg, httpx, python-dotenv
   - Dockerfile: Multi-stage slim python 3.11 container
   - render.yaml: Render Blueprint configuration
   - run.bat / run.sh: 1-click execution scripts
   - README.md: Complete documentation

2. Output Format:
   Return ONLY a valid JSON object matching this schema:
   {
     "files": {
       "app/main.py": "...",
       "requirements.txt": "...",
       "render.yaml": "...",
       "README.md": "..."
     },
     "summary": "Detailed technical explanation of the FastAPI architecture."
   }
"""


CODEGEN_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "files": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
        "summary": {"type": "string"},
    },
    "required": ["files"],
}


async def generate_backend_with_gemini(
    graph_data: Dict[str, Any],
    target_backend: str = "spring_boot",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generates a full backend (Spring Boot 3 or FastAPI) using LLM Provider (Gemini / Fake).
    Falls back gracefully to the deterministic generator on connection or quota errors.
    """
    is_fastapi = target_backend == "fastapi"
    semantics = parse_diagram_semantics(graph_data)

    if not semantics["classes"]:
        logger.warning("No classes found in graph data. Falling back to deterministic generator.")
        fallback_files = generate_fastapi_project(graph_data) if is_fastapi else generate_spring_boot_project(graph_data)
        return {
            "files": fallback_files,
            "total_files": len(fallback_files),
            "engine_used": "deterministic",
            "summary": "Diagram contains no classes.",
        }

    backend_label = "FastAPI (Python 3.11+)" if is_fastapi else "Spring Boot 3.3.x (Java 17)"
    user_prompt = f"""Generate the {backend_label} Clean Architecture project for this UML Diagram:

DIAGRAM CLASSES:
{json.dumps(semantics['classes'], indent=2)}

DIAGRAM RELATIONSHIPS:
{json.dumps(semantics['relations'], indent=2)}

Ensure all entities, schemas, routers/controllers, services, configuration, and build scripts are generated in full.
"""

    system_instruction = build_fastapi_instruction() if is_fastapi else build_spring_boot_instruction()
    provider = get_provider(purpose="codegen")

    req = LlmRequest(
        system=system_instruction,
        messages=[LlmMessage(role="user", text=user_prompt)],
        temperature=0.2,
        purpose="codegen",
        json_schema=CODEGEN_JSON_SCHEMA,
        api_key=SecretStr(api_key) if api_key else None,
        model=model,
    )

    try:
        res = await provider.generate(req)
        if res.raw_json and isinstance(res.raw_json, dict):
            parsed = res.raw_json
        else:
            cleaned = re.sub(r"^```(?:json)?\s*", "", res.text.strip())
            cleaned = re.sub(r"```$", "", cleaned.strip()).strip()
            parsed = json.loads(cleaned)

        files = parsed.get("files", {})
        summary = parsed.get("summary", f"{backend_label} backend generated successfully with {res.model}.")

        if not files:
            raise ValueError("No files dictionary in LLM response")

        if not is_fastapi:
            files = ensure_vscode_and_runner_files(files)

        logger.info(f"LLM ({res.model}) successfully generated {len(files)} files.")
        return {
            "files": files,
            "total_files": len(files),
            "engine_used": f"Google Gemini ({res.model})",
            "summary": summary,
        }

    except Exception as exc:
        logger.warning(f"LLM backend generation failed ({exc}). Falling back to deterministic generator.")
        fallback_files = generate_fastapi_project(graph_data) if is_fastapi else generate_spring_boot_project(graph_data)
        return {
            "files": fallback_files,
            "total_files": len(fallback_files),
            "engine_used": f"deterministic (fallback due to: {exc})",
            "summary": f"Generación realizada con motor determinista de contingencia. (Aviso: {exc})",
        }


# Backwards compatibility wrapper
async def generate_spring_boot_with_gemini(
    graph_data: Dict[str, Any],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    return await generate_backend_with_gemini(
        graph_data=graph_data,
        target_backend="spring_boot",
        api_key=api_key,
        model=model,
    )
