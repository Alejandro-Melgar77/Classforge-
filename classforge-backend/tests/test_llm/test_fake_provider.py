from __future__ import annotations

import pytest
from app.llm.fake import FakeLlmProvider
from app.llm.models import LlmMessage, LlmRequest, LlmResponse, LlmUsage
from app.llm.ports import LlmProvider


@pytest.mark.asyncio
async def test_fake_llm_provider_protocol_compliance():
    """Verify that FakeLlmProvider satisfies the LlmProvider Protocol."""
    fake = FakeLlmProvider()
    assert isinstance(fake, LlmProvider)


@pytest.mark.asyncio
async def test_fake_llm_programmable_response():
    """Verify that programmed responses are delivered as configured."""
    fake = FakeLlmProvider()
    fake.set_response(
        text='{"custom": "response"}',
        raw_json={"custom": "response"},
        usage=LlmUsage(prompt_tokens=5, candidates_tokens=10, total_tokens=15),
        model="custom-fake",
    )

    req = LlmRequest(messages=[LlmMessage(role="user", text="hello")])
    res = await fake.generate(req)

    assert res.text == '{"custom": "response"}'
    assert res.raw_json == {"custom": "response"}
    assert res.usage.total_tokens == 15
    assert res.model == "custom-fake"
    assert len(fake.calls) == 1
    assert fake.calls[0].messages[0].text == "hello"


@pytest.mark.asyncio
async def test_fake_llm_programmable_error():
    """Verify that set_error raises the configured exception."""
    fake = FakeLlmProvider()
    fake.set_error(RuntimeError("Simulated LLM outage"))

    req = LlmRequest(messages=[LlmMessage(role="user", text="hello")])
    with pytest.raises(RuntimeError) as exc_info:
        await fake.generate(req)

    assert "Simulated LLM outage" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fake_llm_default_uml_schema():
    """Verify sensible default UML response when json_schema requests classes and relations."""
    fake = FakeLlmProvider()
    schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "classes": {"type": "array"},
            "relations": {"type": "array"},
        },
    }
    req = LlmRequest(
        purpose="task",
        json_schema=schema,
        messages=[LlmMessage(role="user", text="crear clase Factura")],
    )
    res = await fake.generate(req)
    assert res.raw_json is not None
    assert "classes" in res.raw_json
    assert len(res.raw_json["classes"]) > 0
    assert res.raw_json["action"] == "generate_system"


@pytest.mark.asyncio
async def test_fake_llm_default_codegen_schema():
    """Verify sensible default codegen response when json_schema requests files."""
    fake = FakeLlmProvider()
    schema = {
        "type": "object",
        "properties": {
            "files": {"type": "object"},
            "summary": {"type": "string"},
        },
    }
    req = LlmRequest(
        purpose="codegen",
        json_schema=schema,
        messages=[LlmMessage(role="user", text="generate backend")],
    )
    res = await fake.generate(req)
    assert res.raw_json is not None
    assert "files" in res.raw_json
    assert "pom.xml" in res.raw_json["files"]


@pytest.mark.asyncio
async def test_fake_llm_streaming():
    """Verify streaming chunks over AsyncIterator[str]."""
    fake = FakeLlmProvider()
    fake.set_response(text="Hello world from fake LLM stream")

    req = LlmRequest(messages=[LlmMessage(role="user", text="say hello")])
    chunks = []
    async for chunk in fake.stream(req):
        chunks.append(chunk)

    full_text = "".join(chunks)
    assert full_text == "Hello world from fake LLM stream"
