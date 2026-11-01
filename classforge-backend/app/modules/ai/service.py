from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from app.ai_team.application.prompt_builder import PromptBuilder
from app.ai_team.domain.diagram_model import Attribute, Diagram, Edge, Method, Node
from app.ai_team.domain.lint import lint
from app.core.config import settings
from app.llm import get_fake_provider, get_ollama_provider
from app.llm.registry import resolve_routing_chain
from app.modules.ai.gemini_service import (
    generate_uml_with_gemini,
    parse_gemini_json_to_command,
    sanitize_json_string,
)
from app.modules.ai.heuristic_engine import parse_heuristic
from app.modules.ai.schemas import UMLAttribute, UMLClassCommand, UMLCommandResponse

logger = logging.getLogger(__name__)


def validate_command_with_linter(cmd: UMLCommandResponse) -> bool:
    """
    Validates a generated UMLCommandResponse using the P3 deterministic linter.
    Rejects commands that have critical schema errors or critical linter findings
    (e.g., duplicate class names, invalid multiplicity, circular inheritance).
    """
    if not cmd or not cmd.action:
        return False

    if cmd.action in ("create_class", "generate_system") and not cmd.classes:
        return False

    # Check for duplicate class names directly
    class_names = [c.name.strip().lower() for c in cmd.classes if c.name]
    if len(class_names) != len(set(class_names)):
        logger.warning("[LinterValidation] Clases duplicadas detectadas en el comando UML.")
        return False

    # Build canonical diagram for linter evaluation
    nodes: list[Node] = []
    node_id_map: dict[str, str] = {}
    for idx, c in enumerate(cmd.classes):
        nid = f"node_{idx}_{c.name}"
        node_id_map[c.name.strip().lower()] = nid
        nodes.append(
            Node(
                id=nid,
                type="class",
                name=c.name,
                attributes=[
                    Attribute(name=a.name, type=a.type, visibility=a.visibility or "+")
                    for a in c.attributes
                ],
                methods=[
                    Method(
                        name=m.name,
                        params=m.params or "",
                        return_type=m.return_type or "void",
                        visibility=m.visibility or "+",
                    )
                    for m in c.methods
                ],
            )
        )

    edges: list[Edge] = []
    for idx, r in enumerate(cmd.relations):
        src_id = node_id_map.get(r.source.strip().lower(), r.source)
        tgt_id = node_id_map.get(r.target.strip().lower(), r.target)
        edges.append(
            Edge(
                id=f"edge_{idx}",
                source=src_id,
                target=tgt_id,
                type=r.type,
                source_multiplicity=r.source_multiplicity or r.sourceMultiplicity,
                target_multiplicity=r.target_multiplicity or r.targetMultiplicity,
            )
        )

    diag = Diagram(nodes=nodes, edges=edges)
    findings = lint(diag)

    # Reject if any critical linter finding exists
    for f in findings:
        if f.severity == "critical":
            logger.warning(
                f"[LinterValidation] Comando rechazado por regla crítica del linter '{f.rule}': {f.message_es}"
            )
            return False

    return True


def generate_fallback_entities(prompt: str) -> UMLCommandResponse:
    """Deterministic single class extraction without generating random extra entities."""
    single_match = re.search(
        r'(?:(?:crea|agrega|anade|inserta|genera|nueva?)\w*\s+)?(?:una?\s+)?(?:clase|tabla|entidad|clse)\s+(?:con\s+(?:el\s+)?nombre\s+|llamada\s+|de\s+nombre\s+)?([a-zA-Z0-9_]+)',
        prompt,
        re.IGNORECASE,
    )
    if single_match:
        class_name = single_match.group(1).capitalize()
        attrs_match = re.search(
            r'(?:con\s+atributos?|con\s+campos?|atributos?)\s+(?:de\s+nombres?|llamados?|:)?\s*(.+)',
            prompt,
            re.IGNORECASE,
        )
        attrs = [UMLAttribute(name="id", type="Long", visibility="-")]
        if attrs_match:
            raw = attrs_match.group(1).split(".")[0]
            tokens = re.split(r'[,;\s]+(?:y\s+)?', raw)
            for t in tokens:
                clean_t = re.sub(r'[^a-zA-Z0-9_]', '', t).strip()
                if clean_t and clean_t.lower() not in [
                    'con', 'de', 'y', 'los', 'las', 'que', 'id', 'atributos', 'campos', 'clase', 'tabla'
                ]:
                    attrs.append(UMLAttribute(name=clean_t, type="String", visibility="-"))
        return UMLCommandResponse(
            action="create_class",
            classes=[UMLClassCommand(name=class_name, attributes=attrs)],
            relations=[],
            deleted_elements=[],
            explanation=f"Clase '{class_name}' identificada a partir del texto.",
            source="heuristic",
        )

    return UMLCommandResponse(
        action="unknown",
        classes=[],
        relations=[],
        deleted_elements=[],
        explanation="No se pudo interpretar el comando con certeza. Prueba con: 'crear clase Producto con atributos precio, stock, codigo'",
        source="heuristic",
    )


async def process_prompt(
    prompt: str,
    diagram_context: Optional[dict] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    preferred_provider: Optional[str] = None,
    local_only: bool = False,
) -> UMLCommandResponse:
    """
    Processes a natural language prompt into a structured UMLCommandResponse
    using purpose-based routing and automatic fallback.
    
    Fallback chain (governed by LLM_ROUTING and preferred_provider):
    1. Local Ollama (if in chain and online, with single JSON repair and P3 linter validation).
    2. Cloud Gemini (if in chain and local_only is False).
    3. Deterministic Heuristic Engine (100% offline).
    """
    chain = resolve_routing_chain(
        purpose="uml_command",
        local_only=local_only,
        preferred_provider=preferred_provider,
    )
    logger.info(f"[AiService] Cadena de enrutamiento para uml_command: {chain}")

    for link in chain:
        # Link 0: Global override or Fake provider (tests / CI)
        if link in ("fake", "global_override"):
            try:
                from app.llm.registry import get_provider
                test_prov = get_provider(purpose="task")
                req = PromptBuilder.build_local_uml_prompt(prompt, diagram_context, model=model)
                res = await test_prov.generate(req)
                raw_dict = res.raw_json or {}
                if not raw_dict and res.text:
                    try:
                        raw_dict = json.loads(sanitize_json_string(res.text))
                    except Exception:
                        raw_dict = {}
                src_val = "local" if preferred_provider in ("local", "ollama") else "gemini"
                cmd = parse_gemini_json_to_command(raw_dict, source=src_val)
                return cmd
            except Exception as e:
                logger.warning(f"[AiService] Error en test/override provider ({e}). Avanzando al siguiente eslabón.")
                continue

        # Link 2: Local Ollama
        if link in ("ollama", "local"):
            try:
                ollama_provider = get_ollama_provider()
                req = PromptBuilder.build_local_uml_prompt(prompt, diagram_context, model=model)
                res = await ollama_provider.generate(req)

                # Check latency threshold
                latency_limit = getattr(settings, "LOCAL_LATENCY_THRESHOLD_S", 15.0) * 1000.0
                if res.latency_ms > latency_limit:
                    logger.warning(
                        f"[AiService] Modelo local tardó {res.latency_ms}ms (> {latency_limit}ms). "
                        "Avanzando al siguiente eslabón de respaldo."
                    )
                    continue

                raw_dict = res.raw_json
                if not raw_dict and res.text:
                    try:
                        raw_dict = json.loads(sanitize_json_string(res.text))
                    except Exception:
                        raw_dict = None

                if raw_dict and isinstance(raw_dict, dict):
                    cmd = parse_gemini_json_to_command(raw_dict, source="local")
                    if validate_command_with_linter(cmd):
                        logger.info(f"[AiService] Respuesta local exitosa ({res.latency_ms}ms).")
                        return cmd
                    else:
                        logger.warning(
                            "[AiService] La salida del modelo local no superó la validación del linter P3. "
                            "Avanzando al siguiente eslabón."
                        )
                        continue
            except Exception as e:
                logger.warning(f"[AiService] Error en llamada a Ollama local ({e}). Avanzando al siguiente eslabón.")
                continue

        # Link 3: Cloud Gemini
        if link == "gemini":
            if local_only or settings.AI_LOCAL_ONLY:
                logger.info("[AiService] Modo local_only activo; omitiendo Gemini.")
                continue
            try:
                gemini_res = await generate_uml_with_gemini(
                    prompt=prompt,
                    diagram_context=diagram_context,
                    api_key=api_key,
                    model=model,
                )
                if gemini_res and (gemini_res.classes or gemini_res.action != "unknown"):
                    if validate_command_with_linter(gemini_res):
                        gemini_res.source = "gemini"
                        return gemini_res
            except Exception as e:
                logger.warning(f"[AiService] Error en Gemini ({e}). Avanzando al siguiente eslabón.")
                continue

        # Link 4: Heuristic Engine
        if link == "heuristic":
            heuristic_res = parse_heuristic(prompt)
            if heuristic_res and heuristic_res.action != "unknown":
                heuristic_res.source = "heuristic"
                return heuristic_res
            fallback = generate_fallback_entities(prompt)
            fallback.source = "heuristic"
            return fallback

    # If all links in chain were exhausted without returning
    heuristic_res = parse_heuristic(prompt)
    if heuristic_res and heuristic_res.action != "unknown":
        heuristic_res.source = "heuristic"
        return heuristic_res
    fallback = generate_fallback_entities(prompt)
    fallback.source = "heuristic"
    return fallback
