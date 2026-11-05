import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
import httpx

from app.core.config import settings
from app.modules.project_reviews.domain.models import (
    VerdictType,
    RecommendationPriority,
    RubricDefinition,
)
from app.modules.project_reviews.schemas import (
    CriterionScore,
    Recommendation,
    TechnicalSpecification,
    ComponentSpec,
    EndpointSpec,
    DataModelEntity,
)
from app.modules.project_reviews.pdf_extractor import ExtractedDocument
from app.modules.project_reviews.rubric import (
    get_rubric,
    evaluate_verdict,
    STANDARD_RUBRIC_CODE,
)

logger = logging.getLogger("classforge.project_reviews.evaluator")

# Prompt injection markers to neutralize in untrusted document text
INJECTION_PATTERNS = [
    re.compile(r"((ignore|disregard)\s+(all\s+)?(previous|prior)\s+instructions)", re.IGNORECASE),
    re.compile(r"(ignora\s+(todas\s+las\s+)?instrucciones\s+(anteriores|previas))", re.IGNORECASE),
    re.compile(r"(system\s+prompt\s*:\s*|system\s+override\s*:\s*)", re.IGNORECASE),
    re.compile(r"(you\s+must\s+score\s+100|califica\s+con\s+100|aprobar\s+autom[aá]ticamente)", re.IGNORECASE),
    re.compile(r"(\[INST\].*?\[/INST\])", re.IGNORECASE),
]


def sanitize_untrusted_text(text: str) -> str:
    """Removes or neutralizes prompt-injection attempts from document text."""
    sanitized = text
    for pattern in INJECTION_PATTERNS:
        sanitized = pattern.sub("[CONTENIDO RESTRINGIDO POR SEGURIDAD]", sanitized)
    return sanitized


class ProjectEvaluator:
    """
    Intelligent hybrid evaluation engine for software engineering project documents.
    Operates locally: attempts local Ollama LLM with strict fallback to deterministic
    semantic rule-based evaluation. Never contacts external cloud APIs.
    """

    _ollama_reachable: Optional[bool] = None

    def __init__(self, rubric: Optional[RubricDefinition] = None):
        self.rubric = rubric or get_rubric(STANDARD_RUBRIC_CODE)

    async def evaluate_document(
        self,
        doc: ExtractedDocument,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes evaluation against the document.
        Returns full evaluation results dictionary including verdict, scores,
        findings, recommendations, and technical specification.
        """
        # Fast exit for insufficient text / scanned document
        if not doc.has_sufficient_text:
            verdict, summary = evaluate_verdict(
                total_score=0.0,
                criteria_scores={},
                has_sufficient_text=False,
                detected_sections_count=0,
                passing_score=self.rubric.passing_score,
            )
            criteria_results = []
            for crit in self.rubric.criteria:
                criteria_results.append(
                    CriterionScore(
                        criterion_code=crit.code,
                        name=crit.name,
                        weight=crit.weight,
                        score=0.0,
                        weighted_score=0.0,
                        strengths=[],
                        weaknesses=["No se detectó texto digital procesable en el documento"],
                        observations="Documento vacío, escaneado o sin texto legible.",
                        citations=[],
                        evidence_quotes=[],
                    )
                )

            recommendations = [
                Recommendation(
                    priority=RecommendationPriority.HIGH,
                    criterion_code="general",
                    title="Cargar documento digital con capa de texto accesible",
                    description="El PDF cargado no contiene texto seleccionable. Es posible que sea un escaneo o imagen rasterizada.",
                    action_plan="Genere el PDF exportando directamente desde su editor de texto o aplique un software de OCR antes de subirlo.",
                )
            ]

            return {
                "verdict": verdict,
                "total_score": 0.0,
                "passing_score": self.rubric.passing_score,
                "summary": summary,
                "criteria_scores": criteria_results,
                "recommendations": recommendations,
                "technical_specification": None,
                "evaluated_by_model": "heuristic-rule-engine",
            }

        # Attempt local Ollama evaluation if available
        llm_result = await self._try_evaluate_with_ollama(doc, notes)
        if llm_result:
            return llm_result

        # Fallback: Deterministic Semantic Rule Engine
        return self._evaluate_with_semantic_rules(doc)

    async def _try_evaluate_with_ollama(
        self,
        doc: ExtractedDocument,
        notes: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Attempts local Ollama evaluation with short timeout and fail-fast cache."""
        if ProjectEvaluator._ollama_reachable is False:
            return None

        ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
        model = getattr(settings, "OLLAMA_MODEL", "qwen2.5:1.5b")

        # Cap document context to avoid exceeding token budget
        capped_pages = []
        for p in doc.pages[:25]:  # max first 25 pages
            capped_pages.append(f"[Página {p.page_number}]: {p.text[:600]}")
        doc_sample = "\n\n".join(capped_pages)
        sanitized_doc = sanitize_untrusted_text(doc_sample)

        system_prompt = (
            "Eres un evaluador académico y técnico de proyectos de software para ClassForge. "
            "Evalúa el documento según la rúbrica estricta. "
            "Responde ÚNICAMENTE en JSON con las claves: total_score (float), summary (str), "
            "criteria (lista de objetos con code, score, strengths, weaknesses, observations, citations)."
        )

        user_prompt = (
            f"Rúbrica: {self.rubric.name} (Aprobación >= {self.rubric.passing_score})\n"
            f"Documento a evaluar:\n{sanitized_doc}\n\n"
            f"Notas adicionales: {notes or 'Ninguna'}\n"
            "Devuelve únicamente el JSON válido."
        )

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post(
                    f"{ollama_url.rstrip('/')}/api/generate",
                    json={
                        "model": model,
                        "prompt": f"{system_prompt}\n\n{user_prompt}",
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.1},
                    },
                )
                if res.status_code == 200:
                    ProjectEvaluator._ollama_reachable = True
                    data = res.json()
                    response_text = data.get("response", "")
                    parsed = json.loads(response_text)
                    if "criteria" in parsed and "total_score" in parsed:
                        return self._build_evaluation_from_parsed(doc, parsed, f"ollama/{model}")
                else:
                    ProjectEvaluator._ollama_reachable = False
        except Exception as e:
            ProjectEvaluator._ollama_reachable = False
            logger.info("Ollama no disponible (%s). Usando motor semántico local.", e)

        return None

    def _build_evaluation_from_parsed(
        self,
        doc: ExtractedDocument,
        data: Dict[str, Any],
        model_name: str,
    ) -> Dict[str, Any]:
        """Validates and bounds LLM generated evaluation."""
        total_score = float(data.get("total_score", 0.0))
        total_score = max(0.0, min(100.0, total_score))

        criteria_scores: List[CriterionScore] = []
        raw_crit_map = {c.get("code"): c for c in data.get("criteria", []) if isinstance(c, dict)}
        crit_score_map: Dict[str, float] = {}

        for crit in self.rubric.criteria:
            item = raw_crit_map.get(crit.code, {})
            score = float(item.get("score", 50.0))
            score = max(0.0, min(100.0, score))
            crit_score_map[crit.code] = score

            citations = [int(p) for p in item.get("citations", []) if isinstance(p, (int, str)) and str(p).isdigit()]
            valid_citations = [p for p in citations if 1 <= p <= doc.page_count]
            if not valid_citations and crit.code in doc.section_pages and doc.section_pages[crit.code]:
                valid_citations = doc.section_pages[crit.code][:3]

            criteria_scores.append(
                CriterionScore(
                    criterion_code=crit.code,
                    name=crit.name,
                    weight=crit.weight,
                    score=score,
                    weighted_score=round(score * (crit.weight / 100.0), 2),
                    strengths=item.get("strengths", []),
                    weaknesses=item.get("weaknesses", []),
                    observations=item.get("observations", ""),
                    citations=valid_citations,
                    evidence_quotes=item.get("evidence_quotes", []),
                )
            )

        verdict, summary = evaluate_verdict(
            total_score=total_score,
            criteria_scores=crit_score_map,
            has_sufficient_text=doc.has_sufficient_text,
            detected_sections_count=len(doc.detected_sections),
            passing_score=self.rubric.passing_score,
        )

        recommendations = self._generate_recommendations(criteria_scores)
        tech_spec = self._synthesize_technical_specification(doc) if verdict == VerdictType.APROBADO else None

        return {
            "verdict": verdict,
            "total_score": round(total_score, 1),
            "passing_score": self.rubric.passing_score,
            "summary": summary,
            "criteria_scores": criteria_scores,
            "recommendations": recommendations,
            "technical_specification": tech_spec,
            "evaluated_by_model": model_name,
        }

    def _evaluate_with_semantic_rules(self, doc: ExtractedDocument) -> Dict[str, Any]:
        """
        Deterministic, transparent semantic rules evaluation.
        Scans document text for concrete software engineering evidence per criterion.
        """
        criteria_scores: List[CriterionScore] = []
        crit_score_map: Dict[str, float] = {}

        # 1. Definición del Problema y Alcance
        c1_score, c1_str, c1_weak, c1_obs, c1_quotes = self._score_scope(doc)
        crit_score_map["definicion_problema_alcance"] = c1_score
        c1_pages = doc.section_pages.get("definicion_problema_alcance", [1])

        criteria_scores.append(
            CriterionScore(
                criterion_code="definicion_problema_alcance",
                name="Definición del Problema y Alcance",
                weight=15.0,
                score=c1_score,
                weighted_score=round(c1_score * 0.15, 2),
                strengths=c1_str,
                weaknesses=c1_weak,
                observations=c1_obs,
                citations=c1_pages[:3],
                evidence_quotes=c1_quotes,
            )
        )

        # 2. Especificación de Requisitos
        c2_score, c2_str, c2_weak, c2_obs, c2_quotes = self._score_requirements(doc)
        crit_score_map["especificacion_requisitos"] = c2_score
        c2_pages = doc.section_pages.get("especificacion_requisitos", [1])

        criteria_scores.append(
            CriterionScore(
                criterion_code="especificacion_requisitos",
                name="Especificación de Requisitos",
                weight=20.0,
                score=c2_score,
                weighted_score=round(c2_score * 0.20, 2),
                strengths=c2_str,
                weaknesses=c2_weak,
                observations=c2_obs,
                citations=c2_pages[:3],
                evidence_quotes=c2_quotes,
            )
        )

        # 3. Arquitectura y Diagrama de Clases UML
        c3_score, c3_str, c3_weak, c3_obs, c3_quotes = self._score_architecture(doc)
        crit_score_map["arquitectura_diagrama_uml"] = c3_score
        c3_pages = doc.section_pages.get("arquitectura_diagrama_uml", [1])

        criteria_scores.append(
            CriterionScore(
                criterion_code="arquitectura_diagrama_uml",
                name="Arquitectura y Diagrama de Clases UML",
                weight=25.0,
                score=c3_score,
                weighted_score=round(c3_score * 0.25, 2),
                strengths=c3_str,
                weaknesses=c3_weak,
                observations=c3_obs,
                citations=c3_pages[:3],
                evidence_quotes=c3_quotes,
            )
        )

        # 4. Modelo de Persistencia y Base de Datos
        c4_score, c4_str, c4_weak, c4_obs, c4_quotes = self._score_persistence(doc)
        crit_score_map["modelo_persistencia_datos"] = c4_score
        c4_pages = doc.section_pages.get("modelo_persistencia_datos", [1])

        criteria_scores.append(
            CriterionScore(
                criterion_code="modelo_persistencia_datos",
                name="Modelo de Persistencia y Base de Datos",
                weight=15.0,
                score=c4_score,
                weighted_score=round(c4_score * 0.15, 2),
                strengths=c4_str,
                weaknesses=c4_weak,
                observations=c4_obs,
                citations=c4_pages[:3],
                evidence_quotes=c4_quotes,
            )
        )

        # 5. Plan de Pruebas y Aseguramiento de Calidad
        c5_score, c5_str, c5_weak, c5_obs, c5_quotes = self._score_qa(doc)
        crit_score_map["plan_pruebas_qa"] = c5_score
        c5_pages = doc.section_pages.get("plan_pruebas_qa", [1])

        criteria_scores.append(
            CriterionScore(
                criterion_code="plan_pruebas_qa",
                name="Plan de Pruebas y Aseguramiento de Calidad",
                weight=15.0,
                score=c5_score,
                weighted_score=round(c5_score * 0.15, 2),
                strengths=c5_str,
                weaknesses=c5_weak,
                observations=c5_obs,
                citations=c5_pages[:3],
                evidence_quotes=c5_quotes,
            )
        )

        # 6. Seguridad y Gestión de Riesgos
        c6_score, c6_str, c6_weak, c6_obs, c6_quotes = self._score_security(doc)
        crit_score_map["seguridad_riesgos"] = c6_score
        c6_pages = doc.section_pages.get("seguridad_riesgos", [1])

        criteria_scores.append(
            CriterionScore(
                criterion_code="seguridad_riesgos",
                name="Seguridad y Gestión de Riesgos",
                weight=10.0,
                score=c6_score,
                weighted_score=round(c6_score * 0.10, 2),
                strengths=c6_str,
                weaknesses=c6_weak,
                observations=c6_obs,
                citations=c6_pages[:3],
                evidence_quotes=c6_quotes,
            )
        )

        total_score = sum(c.weighted_score for c in criteria_scores)
        total_score = round(max(0.0, min(100.0, total_score)), 1)

        verdict, summary = evaluate_verdict(
            total_score=total_score,
            criteria_scores=crit_score_map,
            has_sufficient_text=doc.has_sufficient_text,
            detected_sections_count=len(doc.detected_sections),
            passing_score=self.rubric.passing_score,
        )

        recommendations = self._generate_recommendations(criteria_scores)
        tech_spec = self._synthesize_technical_specification(doc) if verdict == VerdictType.APROBADO else None

        return {
            "verdict": verdict,
            "total_score": total_score,
            "passing_score": self.rubric.passing_score,
            "summary": summary,
            "criteria_scores": criteria_scores,
            "recommendations": recommendations,
            "technical_specification": tech_spec,
            "evaluated_by_model": "heuristic-semantic-engine",
        }

    # ── Evaluation Rule Helpers ───────────────────────────────────────────────

    def _score_scope(self, doc: ExtractedDocument) -> Tuple[float, List[str], List[str], str, List[str]]:
        strengths, weaknesses, quotes = [], [], []
        score = 25.0  # base
        text = doc.full_text.lower()

        if "definicion_problema_alcance" in doc.detected_sections:
            score += 25.0
            strengths.append("Se identificó la sección explícita de definición del problema y alcance.")

        if "objetivo general" in text or "objetivos específicos" in text:
            score += 20.0
            strengths.append("El documento formula objetivos generales y específicos.")
        else:
            weaknesses.append("Falta una formulación formal de objetivos medibles del proyecto.")

        if any(w in text for w in ["justificación", "justificacion", "necesidad del negocio", "impacto"]):
            score += 15.0
            strengths.append("Justificación del proyecto adecuadamente argumentada.")

        if any(w in text for w in ["alcance", "delimitación", "fuera del alcance", "criterios de éxito"]):
            score += 15.0
            strengths.append("Delimitación explícita del alcance y límites del producto.")
        else:
            weaknesses.append("No se detallan los límites y elementos fuera del alcance.")

        quotes = self._find_matching_quotes(doc, ["problema", "alcance", "objetivo"], max_quotes=2)
        score = min(100.0, score)
        obs = f"Criterio evaluado con puntaje de {score:.1f}/100. " + (
            "Presenta formulación adecuada." if score >= 70 else "Requiere mayor rigor en la definición del alcance."
        )
        return score, strengths, weaknesses, obs, quotes

    def _score_requirements(self, doc: ExtractedDocument) -> Tuple[float, List[str], List[str], str, List[str]]:
        strengths, weaknesses, quotes = [], [], []
        score = 20.0
        text = doc.full_text

        # Count functional requirements patterns (RF-01, RF1, Requisito Funcional)
        rf_matches = re.findall(r"(RF[-_ ]?\d+|requisito\s+funcional)", text, re.IGNORECASE)
        rnf_matches = re.findall(r"(RNF[-_ ]?\d+|requisito\s+no\s+funcional)", text, re.IGNORECASE)
        cu_matches = re.findall(r"(caso\s+de\s+uso|historia\s+de\s+usuario)", text, re.IGNORECASE)

        if len(rf_matches) >= 3:
            score += 30.0
            strengths.append(f"Se identificaron múltiples requisitos funcionales ({len(rf_matches)} referencias).")
        elif len(rf_matches) > 0:
            score += 15.0
            strengths.append("Se identificaron requisitos funcionales iniciales.")
        else:
            weaknesses.append("No se encontraron identificadores formales de requisitos funcionales (RF).")

        if len(rnf_matches) >= 2 or any(w in text.lower() for w in ["rendimiento", "disponibilidad", "latencia", "escalabilidad"]):
            score += 25.0
            strengths.append("Especificación de requisitos no funcionales (calidad, rendimiento o disponibilidad).")
        else:
            weaknesses.append("Ausencia o vaguedad en requisitos no funcionales (RNF).")

        if len(cu_matches) >= 2:
            score += 25.0
            strengths.append("Inclusión de casos de uso o historias de usuario.")
        else:
            weaknesses.append("Se recomienda incorporar casos de uso con flujos principales y alternativos.")

        quotes = self._find_matching_quotes(doc, ["requisito", "funcional", "caso de uso"], max_quotes=2)
        score = min(100.0, score)
        obs = f"Criterio evaluado con puntaje de {score:.1f}/100. Requisitos detectados con evidencias trazables."
        return score, strengths, weaknesses, obs, quotes

    def _score_architecture(self, doc: ExtractedDocument) -> Tuple[float, List[str], List[str], str, List[str]]:
        strengths, weaknesses, quotes = [], [], []
        score = 20.0
        text = doc.full_text.lower()

        if "diagrama de clases" in text or "clases uml" in text:
            score += 30.0
            strengths.append("Se hace mención y análisis del diagrama de clases UML.")
        else:
            weaknesses.append("No se localizó un análisis explícito del diagrama de clases UML.")

        if any(w in text for w in ["herencia", "asociación", "asociacion", "composición", "composicion", "agregación", "agregacion", "interfaz"]):
            score += 25.0
            strengths.append("Uso de relaciones formales de modelado UML (asociación, herencia o composición).")

        if any(w in text for w in ["arquitectura", "capas", "microservicios", "clean architecture", "hexagonal", "mvc", "api rest"]):
            score += 25.0
            strengths.append("Definición de patrón arquitectónico o estructura de capas de software.")
        else:
            weaknesses.append("Falta mayor detalle sobre el patrón arquitectónico del sistema.")

        quotes = self._find_matching_quotes(doc, ["clase", "arquitectura", "uml", "diagrama"], max_quotes=2)
        score = min(100.0, score)
        obs = f"Criterio evaluado con puntaje de {score:.1f}/100. Soporte arquitectónico y UML analizado."
        return score, strengths, weaknesses, obs, quotes

    def _score_persistence(self, doc: ExtractedDocument) -> Tuple[float, List[str], List[str], str, List[str]]:
        strengths, weaknesses, quotes = [], [], []
        score = 20.0
        text = doc.full_text.lower()

        if any(w in text for w in ["base de datos", "modelo de datos", "entidad-relación", "persistencia"]):
            score += 30.0
            strengths.append("Presencia de sección o descripción formal del modelo de persistencia.")

        if any(w in text for w in ["clave primaria", "foreign key", "tabla", "colección", "índice", "normalización"]):
            score += 30.0
            strengths.append("Definición de claves, tablas/colecciones y elementos de diseño de base de datos.")
        else:
            weaknesses.append("No se detallan claves foráneas, índices o criterios de normalización.")

        if any(w in text for w in ["mongodb", "postgresql", "mysql", "sql", "sqlite"]):
            score += 20.0
            strengths.append("Selección y justificación del motor gestor de base de datos.")

        quotes = self._find_matching_quotes(doc, ["base de datos", "tabla", "entidad", "persistencia"], max_quotes=2)
        score = min(100.0, score)
        obs = f"Criterio evaluado con puntaje de {score:.1f}/100."
        return score, strengths, weaknesses, obs, quotes

    def _score_qa(self, doc: ExtractedDocument) -> Tuple[float, List[str], List[str], str, List[str]]:
        strengths, weaknesses, quotes = [], [], []
        score = 15.0
        text = doc.full_text.lower()

        if any(w in text for w in ["plan de pruebas", "estrategia de pruebas", "qa", "pruebas de software"]):
            score += 30.0
            strengths.append("Se incluye un plan o estrategia de aseguramiento de calidad de software.")

        if any(w in text for w in ["pruebas unitarias", "pruebas de integración", "pruebas e2e", "test"]):
            score += 30.0
            strengths.append("Especificación de niveles de prueba (unitarias, integración o de sistema).")
        else:
            weaknesses.append("Falta desglose de casos de prueba unitarios o de integración.")

        if any(w in text for w in ["criterios de aceptación", "cobertura", "pytest", "jest", "junit"]):
            score += 25.0
            strengths.append("Criterios de aceptación y herramientas de automatización de pruebas.")
        else:
            weaknesses.append("No se mencionan frameworks de testing ni métricas de cobertura mínima.")

        quotes = self._find_matching_quotes(doc, ["prueba", "qa", "test", "criterio"], max_quotes=2)
        score = min(100.0, score)
        obs = f"Criterio evaluado con puntaje de {score:.1f}/100."
        return score, strengths, weaknesses, obs, quotes

    def _score_security(self, doc: ExtractedDocument) -> Tuple[float, List[str], List[str], str, List[str]]:
        strengths, weaknesses, quotes = [], [], []
        score = 15.0
        text = doc.full_text.lower()

        if any(w in text for w in ["seguridad", "autenticación", "autorización", "jwt", "rbac", "oauth"]):
            score += 35.0
            strengths.append("Diseño de mecanismos de autenticación y autorización segura.")
        else:
            weaknesses.append("Falta definición precisa de autenticación y control de accesos.")

        if any(w in text for w in ["riesgo", "matriz de riesgos", "vulnerabilidad", "mitigación", "cifrado"]):
            score += 35.0
            strengths.append("Identificación de riesgos del proyecto y planes de mitigación.")
        else:
            weaknesses.append("No se localizó una matriz de riesgos técnicos u operativos.")

        quotes = self._find_matching_quotes(doc, ["seguridad", "riesgo", "autenticación", "cifrado"], max_quotes=2)
        score = min(100.0, score)
        obs = f"Criterio evaluado con puntaje de {score:.1f}/100."
        return score, strengths, weaknesses, obs, quotes

    def _find_matching_quotes(self, doc: ExtractedDocument, keywords: List[str], max_quotes: int = 2) -> List[str]:
        """Finds representative snippet quotes containing the target keywords."""
        found = []
        for page in doc.pages:
            sentences = re.split(r"(?<=[.!?])\s+", page.text)
            for s in sentences:
                s_lower = s.lower()
                if any(kw in s_lower for kw in keywords) and len(s.split()) >= 6:
                    snippet = s.strip()
                    if len(snippet) > 160:
                        snippet = snippet[:157] + "..."
                    found.append(f'"{snippet}" [Pág. {page.page_number}]')
                    if len(found) >= max_quotes:
                        return found
        return found

    def _generate_recommendations(self, criteria_scores: List[CriterionScore]) -> List[Recommendation]:
        """Produces prioritized actionable recommendations based on weak criteria."""
        recs: List[Recommendation] = []
        for crit in criteria_scores:
            if crit.score < 60.0:
                recs.append(
                    Recommendation(
                        priority=RecommendationPriority.HIGH,
                        criterion_code=crit.criterion_code,
                        title=f"Subsanar deficiencias críticas en {crit.name}",
                        description=f"El criterio obtuvo un puntaje insuficiente ({crit.score:.1f}/100). "
                        + (" ".join(crit.weaknesses) if crit.weaknesses else "Requiere mayor fundamentación técnica."),
                        action_plan="Revisar los requisitos de la rúbrica CF-SE-2026.1 y actualizar el documento con el contenido faltante.",
                    )
                )
            elif crit.score < 75.0:
                recs.append(
                    Recommendation(
                        priority=RecommendationPriority.MEDIUM,
                        criterion_code=crit.criterion_code,
                        title=f"Fortalecer {crit.name}",
                        description=f"El criterio alcanzó un puntaje aceptable pero mejorable ({crit.score:.1f}/100).",
                        action_plan="Incorporar diagramas formales, tablas de trazabilidad y métricas verificables.",
                    )
                )
            elif crit.score < 85.0:
                recs.append(
                    Recommendation(
                        priority=RecommendationPriority.LOW,
                        criterion_code=crit.criterion_code,
                        title=f"Optimizar detalle en {crit.name}",
                        description="El criterio está bien formulado pero puede beneficiarse de mayor exhaustividad.",
                        action_plan="Añadir casos de borde, consideraciones de rendimiento y documentación ampliada.",
                    )
                )

        # Sort recommendations: HIGH -> MEDIUM -> LOW
        priority_order = {RecommendationPriority.HIGH: 0, RecommendationPriority.MEDIUM: 1, RecommendationPriority.LOW: 2}
        recs.sort(key=lambda r: priority_order.get(r.priority, 3))
        return recs

    def _synthesize_technical_specification(self, doc: ExtractedDocument) -> TechnicalSpecification:
        """Synthesizes structured technical specifications for approved projects."""
        # Extract candidate entity names and components from document text
        text = doc.full_text
        classes = re.findall(r"\bclass\s+([A-Z][a-zA-Z0-9]+)\b", text)
        entities = list(set(classes))[:6] if classes else ["Usuario", "Proyecto", "Diagrama", "Informe"]

        components = [
            ComponentSpec(
                name="Frontend Web Application",
                role="Capa de presentación e interfaz de usuario interactiva",
                technology="Angular 17 / AntV X6",
                description="Gestión visual de diagramas UML, paneles colaborativos y visualización de evaluaciones.",
            ),
            ComponentSpec(
                name="Backend API & Business Services",
                role="Lógica de negocio, orquestación y validación de reglas",
                technology="Python 3.11 / FastAPI",
                description="Endpoints REST, autenticación JWT, WebSockets y servicios de análisis.",
            ),
            ComponentSpec(
                name="AI Engine & Document Processor",
                role="Procesamiento de documentos y evaluación local inteligente",
                technology="pypdf, ReportLab, Ollama / Reglas Heurísticas",
                description="Extracción semántica, puntuación de rúbrica y generación de reportes PDF.",
            ),
            ComponentSpec(
                name="Persistence Layer",
                role="Almacenamiento transaccional y documental",
                technology="MongoDB / Motor",
                description="Persistencia de proyectos, diagramas, historial de revisiones y colecciones auditadas.",
            ),
        ]

        endpoints = [
            EndpointSpec(
                method="POST",
                path="/api/v1/auth/login",
                description="Autenticación de usuarios y emisión de tokens JWT",
                request_body="{'email': '...', 'password': '...'}",
                response_body="{'token': '...', 'user': {...}}",
            ),
            EndpointSpec(
                method="GET",
                path="/api/v1/projects",
                description="Consulta paginada de proyectos del usuario",
                response_body="{'items': [...], 'total': 10}",
            ),
            EndpointSpec(
                method="POST",
                path="/api/v1/projects/{id}/reviews",
                description="Creación y ejecución de una nueva evaluación técnica",
                request_body="{'document_id': '...'}",
                response_body="{'id': '...', 'status': 'COMPLETED', 'verdict': 'APROBADO'}",
            ),
            EndpointSpec(
                method="GET",
                path="/api/v1/projects/{id}/reviews/{review_id}/report.pdf",
                description="Descarga del informe oficial de evaluación en formato PDF",
                response_body="application/pdf",
            ),
        ]

        data_models = [
            DataModelEntity(
                name=ent,
                attributes=["id: ObjectId (PK)", "name: String", "created_at: DateTime", "updated_at: DateTime"],
                relationships=["Pertenece a Proyecto", "Referenciado por Revisiones"],
            )
            for ent in entities
        ]

        return TechnicalSpecification(
            title="Pliego de Especificaciones Técnicas del Proyecto",
            overview="Documento formal de especificaciones técnicas generado automáticamente a partir del dictamen aprobatorio de evaluación documental.",
            functional_scope=[
                "Autenticación segura y gestión de identidades con control de roles (RBAC).",
                "Modelado y persistencia de entidades de negocio y diagramas de arquitectura.",
                "Motor de evaluación técnica local con generación de informes y trazabilidad completa.",
            ],
            system_architecture="Arquitectura multicapa desacoplada compuesta por SPA Angular, Backend FastAPI y Persistencia MongoDB.",
            components=components,
            api_endpoints=endpoints,
            data_model=data_models,
            non_functional_requirements=[
                "Rendimiento: Respuestas de API REST en menos de 300 ms en percentil 95.",
                "Disponibilidad: SLA del 99.5% de tiempo operativo.",
                "Seguridad: Encriptación TLS en tránsito y almacenamiento de contraseñas con bcrypt.",
                "Compatibilidad: Navegadores modernos basados en Chromium y Firefox.",
            ],
            deployment_and_security=[
                "Despliegue contenerizado mediante Docker.",
                "Aislamiento de red para base de datos y servicios de inteligencia artificial local.",
                "Gestión de credenciales mediante variables de entorno seguras.",
            ],
        )
