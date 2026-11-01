"""
Tests for KnowledgeLoader, manifest generation, token estimation, and role slicing.
Verifies that all 8 knowledge markdown files cite real code paths and observe token limits.
"""
import pytest
from app.ai_team.infrastructure.knowledge_loader import (
    KnowledgeLoader,
    knowledge_loader,
    estimate_tokens,
)
from app.ai_team.domain.roles import list_roles


EXPECTED_FILES = [
    "00_producto.md",
    "10_modelo_uml.md",
    "20_comandos_uml.md",
    "30_codegen.md",
    "40_colaboracion.md",
    "50_roles_permisos.md",
    "60_glosario_es.md",
    "70_buenas_practicas_uml.md",
]


def test_all_expected_knowledge_files_loaded():
    manifest = knowledge_loader.get_manifest()
    loaded_filenames = [d["filename"] for d in manifest["documents"]]
    for expected in EXPECTED_FILES:
        assert expected in loaded_filenames, f"File {expected} was not loaded"
    assert manifest["total_documents"] == len(EXPECTED_FILES)


def test_each_file_cites_real_code_paths():
    """Requirement: Cada archivo cita rutas de archivo (app/...)"""
    for expected in EXPECTED_FILES:
        doc = knowledge_loader.get_document(expected)
        assert doc is not None
        assert "app/" in doc.content, f"{expected} does not cite real app/ paths"


def test_each_file_observes_token_limit():
    """Requirement: Cada archivo se mantiene <= 1.500 tokens salvo indicación."""
    for expected in EXPECTED_FILES:
        doc = knowledge_loader.get_document(expected)
        assert doc is not None
        assert doc.token_count <= 1500, (
            f"File {expected} has {doc.token_count} tokens, exceeding limit of 1500"
        )


def test_manifest_metadata_integrity():
    manifest = knowledge_loader.get_manifest()
    assert manifest["total_bytes"] > 0
    assert manifest["total_tokens"] > 0
    assert "gemini_cache_threshold_tokens" in manifest
    assert len(manifest["documents"]) == 8


def test_role_slices_respect_budget():
    """Requirement: Presupuesto conocimiento <= 6.000 tokens por llamada."""
    for role in list_roles():
        slice_text = knowledge_loader.get_slice_for_role(role.id, max_budget_tokens=6000)
        tokens = estimate_tokens(slice_text)
        assert len(slice_text) > 0
        assert tokens <= 6000, f"Role {role.id} knowledge slice exceeds 6000 tokens: {tokens}"


def test_role_slices_are_byte_identical_across_calls():
    """Requirement: El prefijo estático va primero y byte-idéntico entre llamadas para beneficiarse de caché."""
    for role in list_roles():
        s1 = knowledge_loader.get_slice_for_role(role.id)
        s2 = knowledge_loader.get_slice_for_role(role.id)
        assert s1 == s2, f"Knowledge slice for {role.id} is not byte-identical across calls"
