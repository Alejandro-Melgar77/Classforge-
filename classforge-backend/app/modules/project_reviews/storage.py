import os
import re
import hashlib
from pathlib import Path
from typing import Optional

from app.core.errors import ValidationError, DomainError

MAX_PDF_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_PDF_PAGES = 300
PDF_MAGIC_BYTES = b"%PDF-"
BASE_STORAGE_DIR = Path("uploads/project_reviews").resolve()

SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


def validate_pdf_content(content: bytes) -> None:
    """Validates basic PDF integrity, size, and magic bytes."""
    if not content:
        raise ValidationError("El archivo subido está vacío")

    if len(content) > MAX_PDF_SIZE_BYTES:
        raise DomainError(
            message=f"El documento excede el tamaño máximo permitido de 25 MB (recibido: {len(content) / (1024 * 1024):.2f} MB)",
            code="PAYLOAD_TOO_LARGE",
            status_code=413,
        )

    if not content.startswith(PDF_MAGIC_BYTES):
        raise ValidationError("El archivo no es un documento PDF válido (falta la firma %PDF-)")


def compute_sha256(content: bytes) -> str:
    """Computes SHA-256 hex digest of file bytes."""
    return hashlib.sha256(content).hexdigest()


def get_safe_document_path(project_id: str, document_id: str) -> Path:
    """Validates identifiers and returns a canonical safe path within BASE_STORAGE_DIR."""
    clean_project_id = str(project_id).strip()
    clean_doc_id = str(document_id).strip()

    if not SAFE_ID_REGEX.match(clean_project_id):
        raise ValidationError("Identificador de proyecto inválido para almacenamiento")

    if not SAFE_ID_REGEX.match(clean_doc_id):
        raise ValidationError("Identificador de documento inválido para almacenamiento")

    project_dir = (BASE_STORAGE_DIR / clean_project_id).resolve()
    target_path = (project_dir / f"{clean_doc_id}.pdf").resolve()

    # Security: Path traversal verification
    if not str(target_path).startswith(str(BASE_STORAGE_DIR)):
        raise ValidationError("Ruta de archivo no autorizada detectada (intento de path traversal)")

    return target_path


def save_pdf_file(project_id: str, document_id: str, content: bytes) -> Path:
    """Validates and persists PDF bytes securely to disk."""
    validate_pdf_content(content)
    target_path = get_safe_document_path(project_id, document_id)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(content)

    return target_path


def delete_pdf_file(project_id: str, document_id: str) -> bool:
    """Deletes persisted PDF file if it exists."""
    target_path = get_safe_document_path(project_id, document_id)
    if target_path.exists():
        try:
            target_path.unlink()
            return True
        except OSError:
            return False
    return False
