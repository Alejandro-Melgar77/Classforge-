import json
import logging
import re
from typing import Dict, Any, Optional, List
import httpx

from app.core.config import settings
from app.modules.codegen.generator import generate_spring_boot_project

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

def parse_diagram_semantics(graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract semantic UML entities, attributes, methods, and relationships
    from ClassForge X6 canvas graph data.
    """
    cells = graph_data.get("cells", []) if isinstance(graph_data, dict) else []
    classes = []
    relations = []
    
    # Track node labels by id
    node_id_to_name = {}

    for cell in cells:
        shape = cell.get("shape", "")
        data = cell.get("data", {})
        
        # Check if node
        if shape in ("class-node", "interface-node", "uml-class") or "attributes" in data or "methods" in data:
            class_name = data.get("name") or cell.get("name") or cell.get("label") or "Entity"
            # Sanitize name
            class_name = re.sub(r'[^a-zA-Z0-9_]', '', class_name).strip() or "Entity"
            node_id_to_name[cell.get("id")] = class_name
            
            raw_attrs = data.get("attributes", [])
            parsed_attrs = []
            for attr in raw_attrs:
                if isinstance(attr, dict):
                    parsed_attrs.append({
                        "name": attr.get("name", "attr"),
                        "type": attr.get("type", "String"),
                        "visibility": attr.get("visibility", "+"),
                        "nullable": attr.get("isNullable", False)
                    })
                elif isinstance(attr, str):
                    # parse string format e.g. "+ id: Long"
                    clean_str = re.sub(r'^[+\-#~]\s*', '', attr).strip()
                    parts = clean_str.split(":")
                    name = parts[0].strip()
                    type_str = parts[1].strip() if len(parts) > 1 else "String"
                    parsed_attrs.append({
                        "name": name,
                        "type": type_str,
                        "visibility": "+",
                        "nullable": False
                    })

            raw_methods = data.get("methods", [])
            parsed_methods = []
            for m in raw_methods:
                if isinstance(m, dict):
                    parsed_methods.append({
                        "name": m.get("name", "method"),
                        "return_type": m.get("return_type") or m.get("type") or "void",
                        "params": m.get("params", "")
                    })
                elif isinstance(m, str):
                    clean_str = re.sub(r'^[+\-#~]\s*', '', m).strip()
                    parsed_methods.append({
                        "name": clean_str,
                        "return_type": "void",
                        "params": ""
                    })

            classes.append({
                "id": cell.get("id"),
                "name": class_name,
                "is_interface": shape == "interface-node",
                "stereotype": data.get("stereotype", ""),
                "attributes": parsed_attrs,
                "methods": parsed_methods
            })

    # Parse relationships (edges)
    for cell in cells:
        shape = cell.get("shape", "")
        if shape in ("edge", "uml-relation", "relation-edge") or "source" in cell:
            source = cell.get("source")
            target = cell.get("target")
            source_id = source.get("cell") if isinstance(source, dict) else source
            target_id = target.get("cell") if isinstance(target, dict) else target
            
            source_name = node_id_to_name.get(source_id)
            target_name = node_id_to_name.get(target_id)
            
            if source_name and target_name:
                data = cell.get("data", {})
                rel_type = data.get("type") or data.get("relationType") or cell.get("relationType") or "association"
                source_card = data.get("sourceMultiplicity") or cell.get("sourceMultiplicity") or "1"
                target_card = data.get("targetMultiplicity") or cell.get("targetMultiplicity") or "*"
                label = data.get("label") or cell.get("label") or ""
                
                relations.append({
                    "source": source_name,
                    "target": target_name,
                    "type": rel_type.lower(),
                    "source_cardinality": source_card,
                    "target_cardinality": target_card,
                    "label": label
                })

    return {
        "classes": classes,
        "relations": relations
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


def build_system_instruction() -> str:
    return """You are a Principal Software Architect and Lead Spring Boot Engineer.
Your task is to take a UML Class Diagram specification and generate a complete, production-grade Spring Boot 3.3.x / Java 17 backend application following strict Clean Architecture, Clean Code principles, and standard Java / Spring Boot conventions.

CRITICAL REQUIREMENTS:
1. Strict Package Structure: com.classforge.generated
   - config: OpenApiConfig.java (OpenAPI 3 / Swagger), CorsConfig.java (allow http://localhost:4200, http://localhost:4201, 10.0.2.2 for mobile)
   - entities: JPA entities with @Entity, @Table(name = "tbl_..."), @Id @GeneratedValue(IDENTITY), relationships (@ManyToOne, @OneToMany, @OneToOne), audit fields (@CreationTimestamp createdAt, @UpdateTimestamp updatedAt)
   - dto: Dedicated {Entity}RequestDTO with Jakarta Bean Validations (@NotBlank, @Email, @PositiveOrZero, @NotNull, @Size), and {Entity}ResponseDTO
   - mappers: Dedicated {Entity}Mapper (toDTO and toEntity methods, pure SRP)
   - repositories: JpaRepository<{Entity}, Long> with custom derived query methods matching entity semantics
   - services: Interface {Entity}Service and implementation {Entity}ServiceImpl with real business logic (calculations, status validations, existence checks, @Transactional, @Slf4j logging)
   - exceptions: GlobalExceptionHandler (@RestControllerAdvice), ResourceNotFoundException, BadRequestException, and ErrorResponseDTO
   - controllers: REST controllers with @RestController, @RequestMapping("/api/v1/{plural}"), @Valid, returning ResponseEntity<T> with standard HTTP status codes (200, 201, 204)
   - GeneratedApplication.java: Main Spring Boot application
   - resources/application.yml: HikariCP, PostgreSQL / H2 config, Swagger UI path
   - pom.xml: Complete Maven build file with spring-boot-starter-web, spring-boot-starter-data-jpa, spring-boot-starter-validation, postgresql, h2, lombok, springdoc-openapi-starter-webmvc-ui
   - README.md: Quickstart guide with VS Code instructions, Maven commands, and API endpoint documentation

2. Standard Java & Spring Boot Coding Standards (Google Java Style / Spring Framework conventions):
   - Clear, clean, and idiomatic Java 17 code (not overly strict or difficult, but professional and clean).
   - Use standard naming conventions: PascalCase for classes/interfaces, camelCase for methods/fields, UPPER_SNAKE_CASE for constants.
   - Descriptive Javadoc comments on class headers and business service methods.
   - Use @Transactional(readOnly = true) for read operations and @Transactional for state changes.
   - Use Lombok (@Getter, @Setter, @NoArgsConstructor, @AllArgsConstructor, @Builder) for clean boilerplate reduction.
   - Proper HTTP response codes: HttpStatus.CREATED (201) on POST, HttpStatus.NO_CONTENT (204) on DELETE, HttpStatus.OK (200) on GET/PUT.

3. Real Domain Business Logic:
   Do NOT generate empty or dummy methods. If there are relationships like Order - OrderDetail (Venta - DetalleVenta), implement total price calculation, stock checks, and status changes.
   Include realistic seed data initializer (CommandLineRunner) to preload 2-3 sample records per entity.

4. Output Format:
   You MUST return ONLY a valid, parseable JSON object matching this schema:
   {
     "files": {
       "src/main/java/com/classforge/generated/GeneratedApplication.java": "...",
       "src/main/java/com/classforge/generated/config/OpenApiConfig.java": "...",
       "src/main/java/com/classforge/generated/config/CorsConfig.java": "...",
       "src/main/java/com/classforge/generated/entities/User.java": "...",
       "src/main/resources/application.yml": "...",
       "pom.xml": "...",
       "README.md": "..."
     },
     "summary": "Detailed technical explanation of the architecture, business logic implemented, and endpoints available."
   }
Do NOT include markdown backticks around the JSON (no ```json). Output raw valid JSON only.
"""


async def generate_spring_boot_with_gemini(
    graph_data: Dict[str, Any],
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a full Spring Boot 3 Clean Architecture backend using Google Gemini API.
    Uses user-specified API key or fallback to system settings.
    """
    key = api_key or settings.GEMINI_API_KEY
    if not key:
        logger.warning("No Gemini API key provided. Falling back to deterministic generator.")
        fallback_files = generate_spring_boot_project(graph_data)
        return {
            "files": fallback_files,
            "total_files": len(fallback_files),
            "engine_used": "deterministic (no API key configured)",
            "summary": "Generated using ClassForge Deterministic Engine."
        }

    # Model resolution with fallback list
    target_model = model or getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash") or "gemini-3.8-flash"
    candidate_models = [target_model]
    for m in ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.7-flash", "gemini-flash-latest"]:
        if m not in candidate_models:
            candidate_models.append(m)


    semantics = parse_diagram_semantics(graph_data)
    
    # If diagram has no classes, return fallback early
    if not semantics["classes"]:
        logger.warning("No classes found in graph data. Falling back to deterministic generator.")
        fallback_files = generate_spring_boot_project(graph_data)
        return {
            "files": fallback_files,
            "total_files": len(fallback_files),
            "engine_used": "deterministic",
            "summary": "Diagram contains no classes."
        }

    user_prompt = f"""Generate the Spring Boot 3 Clean Architecture project for this UML Diagram:

DIAGRAM CLASSES:
{json.dumps(semantics['classes'], indent=2)}

DIAGRAM RELATIONSHIPS:
{json.dumps(semantics['relations'], indent=2)}

Ensure all packages, DTOs, mappers, entities, repositories, services with business logic, controllers, pom.xml and application.yml are generated in full.
"""

    system_instruction = build_system_instruction()

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": user_prompt}
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {"text": system_instruction}
            ]
        },
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2
        }
    }

    last_error = None
    for cand_model in candidate_models:
        url = f"{GEMINI_API_BASE}/{cand_model}:generateContent?key={key}"
        logger.info(f"Invoking Gemini API ({cand_model}) for Spring Boot 3 generation...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ValueError("Gemini returned empty candidates list")
                    
                    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    
                    # Clean up if markdown block quotes exist
                    cleaned = re.sub(r'^```json\s*', '', text.strip())
                    cleaned = re.sub(r'```$', '', cleaned.strip()).strip()
                    
                    parsed = json.loads(cleaned)
                    files = parsed.get("files", {})
                    summary = parsed.get("summary", "Spring Boot 3 backend generated successfully with Google Gemini.")
                    
                    if not files:
                        raise ValueError("No files dictionary in Gemini response")

                    files = ensure_vscode_and_runner_files(files)
                    logger.info(f"Gemini ({cand_model}) successfully generated {len(files)} files.")
                    return {
                        "files": files,
                        "total_files": len(files),
                        "engine_used": f"Google Gemini ({cand_model})",
                        "summary": summary
                    }
                else:
                    error_data = response.json().get("error", {})
                    err_msg = error_data.get("message", response.text)
                    logger.warning(f"Gemini model {cand_model} failed with HTTP {response.status_code}: {err_msg}")
                    last_error = f"HTTP {response.status_code}: {err_msg}"
                    
                    # If quota 429 or 503, try next candidate model
                    if response.status_code in (429, 503, 404):
                        continue
                    else:
                        break
        except Exception as e:
            logger.error(f"Exception during Gemini generation with {cand_model}: {e}")
            last_error = str(e)

    # If all Gemini attempts failed, fall back to deterministic generator
    logger.warning(f"All Gemini models failed ({last_error}). Falling back to deterministic generator.")
    fallback_files = generate_spring_boot_project(graph_data)
    return {
        "files": fallback_files,
        "total_files": len(fallback_files),
        "engine_used": f"deterministic (fallback due to: {last_error})",
        "summary": f"Generación realizada con motor determinista de contingencia. (Aviso de Gemini: {last_error})"
    }
