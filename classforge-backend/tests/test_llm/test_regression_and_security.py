from __future__ import annotations

import os
import re
from pathlib import Path
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.core.errors import ValidationError
from app.llm.fake import FakeLlmProvider
from app.llm.models import LlmMessage, LlmRequest, LlmResponse
from app.llm.registry import reset_providers, set_global_provider
from app.modules.ai.schemas import PromptRequest, UMLCommandResponse
from app.modules.ai.service import process_prompt
from app.modules.codegen.schemas import CodegenPreviewRequest, FrontendPromptRequest
from app.modules.diagrams.schemas import DiagramAiPromptRequest, DiagramFromImageRequest


@pytest.fixture(autouse=True)
def cleanup():
    reset_providers()
    yield
    reset_providers()


def test_zero_occurrences_of_key_query_param_in_app():
    """
    CRITICAL SECURITY TEST:
    Fails if '?key=' appears anywhere in Python files inside app/.
    Ensures API keys are NEVER transmitted in query strings.
    """
    app_dir = Path(__file__).resolve().parent.parent.parent / "app"
    assert app_dir.exists() and app_dir.is_dir(), f"app directory not found at {app_dir}"

    matches = []
    for py_file in app_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        if "?key=" in content:
            matches.append(str(py_file))

    assert not matches, f"CRITICAL: Found '?key=' in files: {matches}"


def test_zero_gemini_http_endpoints_outside_app_llm():
    """
    ARCHITECTURE RULE:
    Zero HTTP calls to generativelanguage.googleapis.com outside app/llm/.
    All Gemini traffic must flow through the unified app/llm layer.
    """
    app_dir = Path(__file__).resolve().parent.parent.parent / "app"
    disallowed_matches = []

    for py_file in app_dir.rglob("*.py"):
        # Exclude app/llm/ itself
        if "app" in py_file.parts and "llm" in py_file.parts:
            continue
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        if "generativelanguage.googleapis.com" in content:
            disallowed_matches.append(str(py_file))

    assert not disallowed_matches, f"Found direct Gemini endpoint calls outside app/llm/: {disallowed_matches}"


@pytest.mark.asyncio
async def test_process_prompt_regression_with_fake_provider():
    """
    REGRESSION TEST:
    process_prompt returns valid UMLCommandResponse using FakeLlmProvider.
    """
    fake = FakeLlmProvider()
    set_global_provider(fake)

    prompt = "crear clase Producto con atributos precio, stock, codigo"
    res = await process_prompt(prompt)

    assert isinstance(res, UMLCommandResponse)
    assert res.action == "generate_system"
    assert len(res.classes) > 0
    assert res.classes[0].name == "Producto"
    assert len(fake.calls) == 1
    assert fake.calls[0].purpose == "task"


@pytest.mark.asyncio
async def test_process_prompt_fallback_to_heuristic_when_llm_fails():
    """
    REGRESSION TEST:
    When LLM provider raises an exception or fails, process_prompt
    falls back cleanly to the deterministic heuristic engine.
    """
    fake = FakeLlmProvider()
    fake.set_error(RuntimeError("Gemini outage"))
    set_global_provider(fake)

    # Prompt matching deterministic heuristic engine
    prompt = "crear clase Factura con atributos total, fecha"
    res = await process_prompt(prompt)

    assert isinstance(res, UMLCommandResponse)
    assert res.source in ("offline_nlu", "nlu_heuristic", "heuristic")
    assert len(res.classes) == 1
    assert res.classes[0].name == "Factura"


def test_api_key_hidden_from_schema_repr():
    """
    SECURITY TEST:
    Ensures that api_key / gemini_api_key fields in request bodies are excluded
    from __repr__ to prevent accidental leaks in logs or APM monitors.
    """
    secret_val = "SUPER-SECRET-GEMINI-KEY-DO-NOT-LEAK"

    req1 = PromptRequest(prompt="test", api_key=secret_val)
    assert secret_val not in repr(req1)

    req2 = DiagramAiPromptRequest(prompt="test", api_key=secret_val)
    assert secret_val not in repr(req2)

    req3 = DiagramFromImageRequest(image_base64="aGVsbG8=", api_key=secret_val)
    assert secret_val not in repr(req3)

    req4 = FrontendPromptRequest(gemini_api_key=secret_val)
    assert secret_val not in repr(req4)


def test_secretstr_settings_repr():
    """Verify GEMINI_API_KEY in settings is hidden as SecretStr('**********')."""
    settings.GEMINI_API_KEY = SecretStr("secret-1234")
    assert "secret-1234" not in repr(settings.GEMINI_API_KEY)
    assert repr(settings.GEMINI_API_KEY) == "SecretStr('**********')"
