import io
import pytest
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
import pypdf

from app.core.errors import ValidationError, DomainError
from app.modules.project_reviews.storage import (
    validate_pdf_content,
    compute_sha256,
    get_safe_document_path,
    BASE_STORAGE_DIR,
)
from app.modules.project_reviews.pdf_extractor import (
    extract_pdf_data,
    MIN_WORDS_SUFFICIENT_TEXT,
)


def create_sample_pdf(text_pages: list[str]) -> bytes:
    """Helper to generate in-memory PDF bytes with ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    story = []
    for idx, page_text in enumerate(text_pages):
        story.append(Paragraph(page_text, styles["Normal"]))
        if idx < len(text_pages) - 1:
            story.append(PageBreak())
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def test_validate_pdf_content_valid():
    """Confirms valid PDF bytes pass validation."""
    pdf_bytes = create_sample_pdf(["Este es un documento de prueba para ClassForge."])
    validate_pdf_content(pdf_bytes)
    assert pdf_bytes.startswith(b"%PDF-")


def test_validate_pdf_content_invalid_magic_bytes():
    """Rejects file without valid %PDF- magic bytes."""
    with pytest.raises(ValidationError, match="no es un documento PDF válido"):
        validate_pdf_content(b"PLAIN TEXT CONTENT NOT A PDF")


def test_validate_pdf_content_empty():
    """Rejects empty content."""
    with pytest.raises(ValidationError, match="está vacío"):
        validate_pdf_content(b"")


def test_validate_pdf_content_too_large():
    """Rejects content exceeding 25 MB with 413."""
    fake_large = b"%PDF-" + (b"0" * (26 * 1024 * 1024))
    with pytest.raises(DomainError) as exc_info:
        validate_pdf_content(fake_large)
    assert exc_info.value.status_code == 413
    assert "PAYLOAD_TOO_LARGE" in exc_info.value.code


def test_compute_sha256():
    """Confirms SHA-256 calculation matches hashlib standard."""
    content = b"%PDF-1.4 sample content"
    digest = compute_sha256(content)
    assert len(digest) == 64
    assert digest == compute_sha256(content)


def test_path_traversal_prevention():
    """Verifies that invalid identifiers or path traversal attempts are rejected."""
    with pytest.raises(ValidationError, match="Identificador de proyecto inválido"):
        get_safe_document_path("../etc", "doc123")

    with pytest.raises(ValidationError, match="Identificador de documento inválido"):
        get_safe_document_path("project123", "../../etc/passwd")

    safe_path = get_safe_document_path("proj_1", "doc_1")
    assert str(safe_path).startswith(str(BASE_STORAGE_DIR))
    assert safe_path.name == "doc_1.pdf"


def test_extract_pdf_data_sufficient_text_and_sections():
    """Tests extraction of structured sections from a multi-page software project PDF."""
    p1 = (
        "DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
        "Este proyecto desarrolla una plataforma de comercio electrónico distribuida. "
        "El objetivo general es centralizar las ventas y optimizar tiempos de entrega. "
        "Alcance del proyecto: gestión de catálogo, órdenes de compra y facturación electrónica."
    )
    p2 = (
        "ESPECIFICACIÓN DE REQUISITOS\n"
        "Requisitos Funcionales:\n"
        "RF-01: El usuario debe poder autenticarse.\n"
        "RF-02: Creación de órdenes de compra con tarjeta de crédito.\n"
        "Requisitos No Funcionales:\n"
        "RNF-01: Tiempo de respuesta menor a 300 ms en percentil 95."
    )
    p3 = (
        "ARQUITECTURA DEL SISTEMA Y DIAGRAMA DE CLASES UML\n"
        "Arquitectura multicapa en Clean Architecture.\n"
        "Diagrama de clases UML con herencia y relaciones de asociación entre Producto y Orden."
    )

    pdf_bytes = create_sample_pdf([p1, p2, p3])
    extracted = extract_pdf_data(pdf_bytes)

    assert extracted.page_count == 3
    assert extracted.has_sufficient_text is True
    assert extracted.total_word_count >= MIN_WORDS_SUFFICIENT_TEXT
    assert len(extracted.pages) == 3

    # Check detected sections
    assert "definicion_problema_alcance" in extracted.detected_sections
    assert "especificacion_requisitos" in extracted.detected_sections
    assert "arquitectura_diagrama_uml" in extracted.detected_sections
    assert 1 in extracted.section_pages["definicion_problema_alcance"]
    assert 2 in extracted.section_pages["especificacion_requisitos"]
    assert 3 in extracted.section_pages["arquitectura_diagrama_uml"]


def test_extract_pdf_insufficient_text_scanned_detection():
    """Detects when PDF has less than 50 words (scanned or image-only)."""
    p1 = "Solo un par de palabras."
    pdf_bytes = create_sample_pdf([p1])
    extracted = extract_pdf_data(pdf_bytes)

    assert extracted.page_count == 1
    assert extracted.has_sufficient_text is False
    assert extracted.total_word_count < MIN_WORDS_SUFFICIENT_TEXT


def test_extract_pdf_page_limit_exceeded():
    """Rejects documents exceeding 300 pages limit."""
    writer = pypdf.PdfWriter()
    # Add 305 empty pages
    for _ in range(305):
        writer.add_blank_page(width=100, height=100)

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)

    with pytest.raises(ValidationError, match="excede el límite máximo de 300 páginas"):
        extract_pdf_data(buf.getvalue())


def test_extract_pdf_password_protected():
    """Rejects password-encrypted documents."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("super_secret_password")

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)

    with pytest.raises(ValidationError, match="protegido por contraseña"):
        extract_pdf_data(buf.getvalue())
