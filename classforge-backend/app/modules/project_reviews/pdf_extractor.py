import io
import re
from pathlib import Path
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
import pypdf

from app.core.errors import ValidationError
from app.modules.project_reviews.storage import MAX_PDF_PAGES

MIN_WORDS_SUFFICIENT_TEXT = 50

SECTION_PATTERNS: Dict[str, List[re.Pattern]] = {
    "definicion_problema_alcance": [
        re.compile(r"(definici[oó]n\s+del\s+problema|planteamiento\s+del\s+problema)", re.IGNORECASE),
        re.compile(r"(alcance\s+del\s+(proyecto|sistema)|objetivos?\s+(del\s+proyecto|general|espec[ií]ficos?))", re.IGNORECASE),
        re.compile(r"(introducci[oó]n|justificaci[oó]n|descripci[oó]n\s+general\s+del\s+proyecto)", re.IGNORECASE),
    ],
    "especificacion_requisitos": [
        re.compile(r"(requisitos?\s+funcionales?|requerimientos?\s+funcionales?|RF-\d+)", re.IGNORECASE),
        re.compile(r"(requisitos?\s+no\s+funcionales?|requerimientos?\s+no\s+funcionales?|RNF-\d+)", re.IGNORECASE),
        re.compile(r"(especificaci[oó]n\s+de\s+requisitos?|casos?\s+de\s+uso|historias?\s+de\s+usuario)", re.IGNORECASE),
    ],
    "arquitectura_diagrama_uml": [
        re.compile(r"(diagrama\s+de\s+clases?|modelo\s+de\s+clases?|diagrama\s+uml)", re.IGNORECASE),
        re.compile(r"(arquitectura\s+del\s+sistema|diseño\s+arquitect[oó]nico|patr[oó]n(es)?\s+de\s+diseño)", re.IGNORECASE),
        re.compile(r"(componentes?\s+del\s+sistema|diagrama\s+de\s+paquetes?|diagrama\s+de\s+componentes?)", re.IGNORECASE),
    ],
    "modelo_persistencia_datos": [
        re.compile(r"(modelo\s+de\s+datos?|base\s+de\s+datos?|modelo\s+entidad[- ]relaci[oó]n|diagrama\s+e-r)", re.IGNORECASE),
        re.compile(r"(esquema\s+relacional|diccionario\s+de\s+datos?|persistencia\s+de\s+datos?)", re.IGNORECASE),
        re.compile(r"(tablas?\s+de\s+la\s+base\s+de\s+datos|colecciones?\s+(mongodb|nosql)|postgresql|mysql|sqlite)", re.IGNORECASE),
    ],
    "plan_pruebas_qa": [
        re.compile(r"(plan\s+de\s+pruebas?|estrategia\s+de\s+pruebas?|casos?\s+de\s+prueba)", re.IGNORECASE),
        re.compile(r"(pruebas?\s+unitarias?|pruebas?\s+de\s+integraci[oó]n|pruebas?\s+end-to-end|e2e)", re.IGNORECASE),
        re.compile(r"(aseguramiento\s+de\s+(la\s+)?calidad|qa|criterios?\s+de\s+aceptaci[oó]n|cobertura\s+de\s+c[oó]digo)", re.IGNORECASE),
    ],
    "seguridad_riesgos": [
        re.compile(r"(an[aá]lisis\s+de\s+riesgos?|gesti[oó]n\s+de\s+riesgos?|matriz\s+de\s+riesgos?)", re.IGNORECASE),
        re.compile(r"(seguridad\s+del\s+sistema|mecanismos?\s+de\s+seguridad|autenticaci[oó]n|autorizaci[oó]n|rbac)", re.IGNORECASE),
        re.compile(r"(cifrado|control\s+de\s+acceso|vulnerabilidades?|protecci[oó]n\s+de\s+datos)", re.IGNORECASE),
    ],
}


class PageContent(BaseModel):
    page_number: int
    text: str
    word_count: int


class ExtractedDocument(BaseModel):
    page_count: int
    total_word_count: int
    has_sufficient_text: bool
    pages: List[PageContent]
    detected_sections: List[str] = Field(default_factory=list)
    section_pages: Dict[str, List[int]] = Field(default_factory=dict)
    full_text: str = ""

    def get_text_for_pages(self, pages: List[int]) -> str:
        """Returns concatenated text for specific page numbers."""
        page_set = set(pages)
        matched = [p.text for p in self.pages if p.page_number in page_set]
        return "\n\n".join(matched)


def sanitize_text(raw_text: str) -> str:
    """Removes null bytes and control chars while keeping line breaks."""
    if not raw_text:
        return ""
    clean = raw_text.replace("\x00", " ")
    clean = re.sub(r"[\r\t]+", " ", clean)
    clean = re.sub(r" +", " ", clean)
    return clean.strip()


def extract_pdf_data(pdf_input: Union[bytes, Path, io.BytesIO]) -> ExtractedDocument:
    """
    Extracts text per page, validates page count and encryption,
    detects scanned/insufficient PDFs, and maps software project sections.
    """
    if isinstance(pdf_input, Path):
        with open(pdf_input, "rb") as f:
            stream = io.BytesIO(f.read())
    elif isinstance(pdf_input, bytes):
        stream = io.BytesIO(pdf_input)
    else:
        stream = pdf_input

    try:
        reader = pypdf.PdfReader(stream)
    except Exception as e:
        raise ValidationError(f"No se pudo parsear el archivo PDF: {str(e)}")

    if reader.is_encrypted:
        try:
            # Try empty password default
            decrypted = reader.decrypt("")
            if decrypted == 0:
                raise ValidationError("El documento PDF está protegido por contraseña y no se puede leer")
        except Exception:
            raise ValidationError("El documento PDF está protegido por contraseña y no se puede leer")

    page_count = len(reader.pages)
    if page_count > MAX_PDF_PAGES:
        raise ValidationError(
            f"El documento excede el límite máximo de {MAX_PDF_PAGES} páginas (tiene {page_count} páginas)"
        )

    pages: List[PageContent] = []
    total_words = 0
    full_text_parts: List[str] = []
    section_pages: Dict[str, List[int]] = {sec: [] for sec in SECTION_PATTERNS}

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        try:
            raw_text = page.extract_text() or ""
        except Exception:
            raw_text = ""

        cleaned = sanitize_text(raw_text)
        words = len(cleaned.split()) if cleaned else 0
        total_words += words

        pages.append(PageContent(page_number=page_num, text=cleaned, word_count=words))
        full_text_parts.append(f"[Página {page_num}]\n{cleaned}")

        # Scan for sections on this page
        for sec_code, patterns in SECTION_PATTERNS.items():
            for pat in patterns:
                if pat.search(cleaned):
                    if page_num not in section_pages[sec_code]:
                        section_pages[sec_code].append(page_num)
                    break

    has_sufficient_text = total_words >= MIN_WORDS_SUFFICIENT_TEXT
    detected_sections = [sec for sec, pgs in section_pages.items() if len(pgs) > 0]

    return ExtractedDocument(
        page_count=page_count,
        total_word_count=total_words,
        has_sufficient_text=has_sufficient_text,
        pages=pages,
        detected_sections=detected_sections,
        section_pages=section_pages,
        full_text="\n\n".join(full_text_parts),
    )
