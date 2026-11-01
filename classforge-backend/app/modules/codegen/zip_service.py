# -*- coding: utf-8 -*-
"""
Zip archive service with Zip-Slip protection, strict path sanitization,
and denial-of-service / resource exhaustion limits.
"""
import io
import posixpath
import re
import zipfile
from typing import Dict, Union

MAX_ZIP_FILES = 500
MAX_FILE_BYTES = 10 * 1024 * 1024       # 10 MB per file
MAX_TOTAL_BYTES = 50 * 1024 * 1024      # 50 MB total uncompressed

class ZipSecurityError(ValueError):
    """Raised when a zip entry violates path safety or size restrictions."""
    pass


def sanitize_zip_path(raw_path: str) -> str:
    """
    Prevents Zip-Slip and path traversal vulnerabilities.
    Returns a safe relative POSIX path. Raises ZipSecurityError if unsafe.
    """
    if not raw_path or not isinstance(raw_path, str):
        raise ZipSecurityError("Ruta de archivo vacía o inválida para el archivo ZIP.")

    # Normalize backslashes to forward slashes
    clean = raw_path.replace("\\", "/").strip()

    # Reject absolute paths (UNIX or Windows drive letter)
    if clean.startswith("/") or re.match(r"^[a-zA-Z]:", clean):
        raise ZipSecurityError(f"Ruta absoluta no permitida en archivo ZIP: {raw_path}")

    # Normalize relative path segments
    norm = posixpath.normpath(clean)

    # Disallow traversing out of root directory
    if norm == ".." or norm.startswith("../") or "/../" in norm or norm.startswith("/"):
        raise ZipSecurityError(f"Intento de Zip-Slip o path traversal detectado: {raw_path}")

    # Remove any leading dot-slashes
    if norm.startswith("./"):
        norm = norm[2:]

    return norm


def create_project_zip(files: Dict[str, Union[str, bytes]], root_dir: str = "classforge-backend") -> bytes:
    """
    Compresses project files into a secure in-memory ZIP archive.
    Enforces maximum file count, maximum individual file size, and total uncompressed size.
    """
    if len(files) > MAX_ZIP_FILES:
        raise ZipSecurityError(f"Número de archivos excede el límite permitido ({len(files)} > {MAX_ZIP_FILES})")

    total_uncompressed_bytes = 0
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for raw_path, content in files.items():
            safe_rel_path = sanitize_zip_path(raw_path)

            content_bytes = content.encode("utf-8") if isinstance(content, str) else content

            file_size = len(content_bytes)
            if file_size > MAX_FILE_BYTES:
                raise ZipSecurityError(f"El archivo '{raw_path}' supera el límite máximo de {MAX_FILE_BYTES} bytes")

            total_uncompressed_bytes += file_size
            if total_uncompressed_bytes > MAX_TOTAL_BYTES:
                raise ZipSecurityError(f"El proyecto supera el límite de descompresión total de {MAX_TOTAL_BYTES} bytes")

            archive_path = f"{root_dir}/{safe_rel_path}" if root_dir else safe_rel_path
            zip_file.writestr(archive_path, content_bytes)

    return zip_buffer.getvalue()
