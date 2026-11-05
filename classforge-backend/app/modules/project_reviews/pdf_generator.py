import io
from datetime import datetime
from typing import List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

from app.modules.project_reviews.domain.models import VerdictType, RecommendationPriority
from app.modules.project_reviews.schemas import (
    ProjectReviewResponse,
    TechnicalSpecification,
)


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and render total page count ('Página X de Y')
    along with running header and footer.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "ClassForge 2.0 — Sistema Inteligente de Evaluación de Software")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Running footer
        page_str = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(558, 36, page_str)
        self.drawString(54, 36, "Documento emitido por ClassForge Local AI Evaluator — Confidencial")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)

        self.restoreState()


def get_custom_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=12,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubSectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceBefore=6,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#1E293B"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmallBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#0F172A"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="FindingQuote",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#334155"),
            leftIndent=10,
        )
    )
    return styles


def generate_review_report_pdf(review: ProjectReviewResponse, project_name: str) -> bytes:
    """Generates an official project evaluation report in PDF format."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = get_custom_styles()
    story = []

    # Title & Subtitle
    story.append(Paragraph("Dictamen de Evaluación Técnica de Proyecto", styles["ReportTitle"]))
    story.append(Paragraph(f"ClassForge 2.0 • Proyecto: <b>{project_name}</b>", styles["ReportSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=12))

    # Metadata & Verdict Summary Card
    verdict_text = review.verdict.value if review.verdict else "PENDIENTE"
    score_text = f"{review.total_score:.1f} / 100" if review.total_score is not None else "N/A"

    if review.verdict == VerdictType.APROBADO:
        v_bg = colors.HexColor("#DCFCE7")
        v_fg = colors.HexColor("#15803D")
    elif review.verdict == VerdictType.RECHAZADO:
        v_bg = colors.HexColor("#FEE2E2")
        v_fg = colors.HexColor("#B91C1C")
    else:
        v_bg = colors.HexColor("#FEF3C7")
        v_fg = colors.HexColor("#B45309")

    date_str = review.created_at.strftime("%Y-%m-%d %H:%M UTC") if review.created_at else "N/A"

    meta_data = [
        [
            Paragraph("<b>Revisión N°:</b>", styles["BodySmallBold"]),
            Paragraph(str(review.review_number), styles["BodySmall"]),
            Paragraph("<b>Dictamen Final:</b>", styles["BodySmallBold"]),
            Paragraph(f"<font color='{v_fg.hexval()}'><b>{verdict_text}</b></font>", styles["BodySmallBold"]),
        ],
        [
            Paragraph("<b>Documento:</b>", styles["BodySmallBold"]),
            Paragraph(review.document_filename or "N/A", styles["BodySmall"]),
            Paragraph("<b>Puntaje Total:</b>", styles["BodySmallBold"]),
            Paragraph(f"<b>{score_text}</b> (Mínimo: {review.passing_score:.0f})", styles["BodySmallBold"]),
        ],
        [
            Paragraph("<b>Rúbrica:</b>", styles["BodySmallBold"]),
            Paragraph(f"{review.rubric_code} (v{review.rubric_version})", styles["BodySmall"]),
            Paragraph("<b>Motor IA:</b>", styles["BodySmallBold"]),
            Paragraph(review.evaluated_by_model or "Local Heuristic", styles["BodySmall"]),
        ],
        [
            Paragraph("<b>Fecha:</b>", styles["BodySmallBold"]),
            Paragraph(date_str, styles["BodySmall"]),
            Paragraph("<b>Estado:</b>", styles["BodySmallBold"]),
            Paragraph(review.status.value, styles["BodySmall"]),
        ],
    ]

    t_meta = Table(meta_data, colWidths=[80, 170, 90, 164])
    t_meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # Executive Summary
    if review.summary:
        story.append(Paragraph("Resumen Ejecutivo y Fundamentación", styles["SectionHeading"]))
        story.append(
            Table(
                [[Paragraph(review.summary, styles["BodySmall"])]],
                colWidths=[504],
                style=[
                    ("BACKGROUND", (0, 0), (-1, -1), v_bg),
                    ("BOX", (0, 0), (-1, -1), 1, v_fg),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ],
            )
        )
        story.append(Spacer(1, 10))

    # Criteria Table
    story.append(Paragraph("Evaluación por Criterios de la Rúbrica", styles["SectionHeading"]))
    crit_table_data = [
        [
            Paragraph("<b>Criterio</b>", styles["BodySmallBold"]),
            Paragraph("<b>Peso</b>", styles["BodySmallBold"]),
            Paragraph("<b>Puntaje</b>", styles["BodySmallBold"]),
            Paragraph("<b>Ponderado</b>", styles["BodySmallBold"]),
            Paragraph("<b>Citas / Págs.</b>", styles["BodySmallBold"]),
        ]
    ]

    for c in review.criteria_scores:
        citations_str = ", ".join(f"Pág. {p}" for p in c.citations) if c.citations else "N/A"
        crit_table_data.append(
            [
                Paragraph(c.name, styles["BodySmall"]),
                Paragraph(f"{c.weight:.0f}%", styles["BodySmall"]),
                Paragraph(f"{c.score:.1f} / 100", styles["BodySmallBold"]),
                Paragraph(f"{c.weighted_score:.2f} pts", styles["BodySmall"]),
                Paragraph(citations_str, styles["BodySmall"]),
            ]
        )

    t_crit = Table(crit_table_data, colWidths=[174, 45, 75, 75, 135])
    t_crit.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]
        )
    )
    story.append(t_crit)
    story.append(Spacer(1, 12))

    # Detailed Findings per Criterion
    story.append(Paragraph("Detalle de Hallazgos y Evidencias Documentales", styles["SectionHeading"]))
    for c in review.criteria_scores:
        finding_elements = [
            Paragraph(f"<b>{c.name}</b> (Puntaje: {c.score:.1f}/100 — Peso: {c.weight:.0f}%)", styles["SubSectionHeading"]),
        ]
        if c.observations:
            finding_elements.append(Paragraph(f"<i>Observación:</i> {c.observations}", styles["BodySmall"]))

        if c.strengths:
            str_text = "<b>Fortalezas:</b><br/>• " + "<br/>• ".join(c.strengths)
            finding_elements.append(Paragraph(str_text, styles["BodySmall"]))

        if c.weaknesses:
            weak_text = "<b>Deficiencias a subsanar:</b><br/>• " + "<br/>• ".join(c.weaknesses)
            finding_elements.append(Paragraph(weak_text, styles["BodySmall"]))

        if c.evidence_quotes:
            quote_text = "<b>Evidencias textuales extraídas:</b><br/>" + "<br/>".join(f"• {q}" for q in c.evidence_quotes)
            finding_elements.append(Paragraph(quote_text, styles["FindingQuote"]))

        finding_elements.append(Spacer(1, 6))
        story.append(KeepTogether(finding_elements))

    # Actionable Recommendations
    if review.recommendations:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Recomendaciones Técnicas Priorizadas", styles["SectionHeading"]))
        rec_table_data = [
            [
                Paragraph("<b>Prioridad</b>", styles["BodySmallBold"]),
                Paragraph("<b>Título y Recomendación</b>", styles["BodySmallBold"]),
                Paragraph("<b>Plan de Acción Sugerido</b>", styles["BodySmallBold"]),
            ]
        ]
        for r in review.recommendations:
            p_color = (
                "#DC2626"
                if r.priority == RecommendationPriority.HIGH
                else ("#D97706" if r.priority == RecommendationPriority.MEDIUM else "#2563EB")
            )
            rec_table_data.append(
                [
                    Paragraph(f"<font color='{p_color}'><b>{r.priority.value}</b></font>", styles["BodySmallBold"]),
                    Paragraph(f"<b>{r.title}</b><br/>{r.description}", styles["BodySmall"]),
                    Paragraph(r.action_plan, styles["BodySmall"]),
                ]
            )

        t_rec = Table(rec_table_data, colWidths=[65, 230, 209])
        t_rec.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(t_rec)

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


def generate_specification_pdf(spec: TechnicalSpecification, project_name: str, review_number: int) -> bytes:
    """Generates a formal Software Technical Specification document in PDF format."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = get_custom_styles()
    story = []

    # Title & Metadata
    story.append(Paragraph(spec.title, styles["ReportTitle"]))
    story.append(
        Paragraph(
            f"ClassForge 2.0 • Proyecto: <b>{project_name}</b> • Derivado de Revisión #{review_number}",
            styles["ReportSubtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0D9488"), spaceAfter=12))

    # Overview
    story.append(Paragraph("1. Resumen y Alcance Funcional", styles["SectionHeading"]))
    story.append(Paragraph(spec.overview, styles["BodySmall"]))
    story.append(Spacer(1, 6))

    if spec.functional_scope:
        scope_text = "<b>Alcance formal del producto:</b><br/>• " + "<br/>• ".join(spec.functional_scope)
        story.append(Paragraph(scope_text, styles["BodySmall"]))
    story.append(Spacer(1, 10))

    # System Architecture
    story.append(Paragraph("2. Arquitectura de Software del Sistema", styles["SectionHeading"]))
    story.append(Paragraph(spec.system_architecture, styles["BodySmall"]))
    story.append(Spacer(1, 10))

    # Components Table
    if spec.components:
        story.append(Paragraph("3. Especificación de Componentes", styles["SectionHeading"]))
        comp_data = [
            [
                Paragraph("<b>Componente</b>", styles["BodySmallBold"]),
                Paragraph("<b>Rol / Responsabilidad</b>", styles["BodySmallBold"]),
                Paragraph("<b>Tecnología</b>", styles["BodySmallBold"]),
                Paragraph("<b>Descripción</b>", styles["BodySmallBold"]),
            ]
        ]
        for c in spec.components:
            comp_data.append(
                [
                    Paragraph(f"<b>{c.name}</b>", styles["BodySmall"]),
                    Paragraph(c.role, styles["BodySmall"]),
                    Paragraph(c.technology, styles["BodySmall"]),
                    Paragraph(c.description, styles["BodySmall"]),
                ]
            )

        t_comp = Table(comp_data, colWidths=[100, 130, 100, 174])
        t_comp.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#CCFBF1")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#99F6E4")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0FDFA")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t_comp)
        story.append(Spacer(1, 10))

    # API Endpoints
    if spec.api_endpoints:
        story.append(Paragraph("4. Especificación de Endpoints y Servicios REST", styles["SectionHeading"]))
        api_data = [
            [
                Paragraph("<b>Método</b>", styles["BodySmallBold"]),
                Paragraph("<b>Ruta / Endpoint</b>", styles["BodySmallBold"]),
                Paragraph("<b>Descripción</b>", styles["BodySmallBold"]),
            ]
        ]
        for ep in spec.api_endpoints:
            m_color = "#15803D" if ep.method == "GET" else ("#2563EB" if ep.method == "POST" else "#D97706")
            api_data.append(
                [
                    Paragraph(f"<font color='{m_color}'><b>{ep.method}</b></font>", styles["BodySmallBold"]),
                    Paragraph(f"<code>{ep.path}</code>", styles["BodySmall"]),
                    Paragraph(ep.description, styles["BodySmall"]),
                ]
            )

        t_api = Table(api_data, colWidths=[55, 185, 264])
        t_api.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t_api)
        story.append(Spacer(1, 10))

    # Data Model
    if spec.data_model:
        story.append(Paragraph("5. Modelo de Datos y Entidades de Negocio", styles["SectionHeading"]))
        model_data = [
            [
                Paragraph("<b>Entidad</b>", styles["BodySmallBold"]),
                Paragraph("<b>Atributos Principales</b>", styles["BodySmallBold"]),
                Paragraph("<b>Relaciones</b>", styles["BodySmallBold"]),
            ]
        ]
        for ent in spec.data_model:
            attrs = "<br/>• ".join(ent.attributes) if ent.attributes else "N/A"
            rels = "<br/>• ".join(ent.relationships) if ent.relationships else "N/A"
            model_data.append(
                [
                    Paragraph(f"<b>{ent.name}</b>", styles["BodySmallBold"]),
                    Paragraph(f"• {attrs}", styles["BodySmall"]),
                    Paragraph(f"• {rels}", styles["BodySmall"]),
                ]
            )

        t_model = Table(model_data, colWidths=[110, 204, 190])
        t_model.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t_model)
        story.append(Spacer(1, 10))

    # Non-functional requirements & deployment
    if spec.non_functional_requirements or spec.deployment_and_security:
        story.append(Paragraph("6. Requisitos No Funcionales y Despliegue Seguro", styles["SectionHeading"]))
        if spec.non_functional_requirements:
            nfr_text = "<b>Requisitos de Calidad y Rendimiento:</b><br/>• " + "<br/>• ".join(spec.non_functional_requirements)
            story.append(Paragraph(nfr_text, styles["BodySmall"]))
            story.append(Spacer(1, 6))

        if spec.deployment_and_security:
            sec_text = "<b>Directrices de Despliegue y Seguridad:</b><br/>• " + "<br/>• ".join(spec.deployment_and_security)
            story.append(Paragraph(sec_text, styles["BodySmall"]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
