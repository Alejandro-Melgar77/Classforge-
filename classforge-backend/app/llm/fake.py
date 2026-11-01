from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, List, Optional
from app.llm.models import LlmMessage, LlmRequest, LlmResponse, LlmUsage
from app.llm.usage import record_ai_usage


class FakeLlmProvider:
    """
    In-memory mock LLM provider for unit, regression, and E2E tests.
    Does not require network access or API keys.
    """

    def __init__(self) -> None:
        self.calls: List[LlmRequest] = []
        self._responses: List[LlmResponse] = []
        self._error: Optional[Exception] = None

    def set_response(
        self,
        text: str,
        raw_json: Optional[Dict[str, Any]] = None,
        usage: Optional[LlmUsage] = None,
        model: str = "fake-model",
    ) -> None:
        """Sets a single programmed response."""
        self._responses = [
            LlmResponse(
                text=text,
                raw_json=raw_json,
                usage=usage or LlmUsage(prompt_tokens=10, candidates_tokens=20, total_tokens=30),
                model=model,
                latency_ms=1.0,
            )
        ]
        self._error = None

    def set_responses(self, responses: List[LlmResponse]) -> None:
        """Sets a queue of programmed responses."""
        self._responses = list(responses)
        self._error = None

    def set_error(self, exc: Exception) -> None:
        """Forces the next generate/stream call to raise an exception."""
        self._error = exc

    def reset(self) -> None:
        """Clears calls history and programmed responses/errors."""
        self.calls.clear()
        self._responses.clear()
        self._error = None

    def _default_response_for(self, req: LlmRequest) -> LlmResponse:
        """Generates a schema-aware sensible default response."""
        model = req.model or "fake-gemini-3.8-flash"
        usage = LlmUsage(prompt_tokens=25, candidates_tokens=50, total_tokens=75)

        if req.json_schema:
            props = req.json_schema.get("properties", {})
            if "classes" in props and "relations" in props:
                # UML generation schema
                data = {
                    "action": "generate_system",
                    "classes": [
                        {
                            "name": "Producto",
                            "stereotype": None,
                            "attributes": [
                                {"name": "id", "type": "Long", "visibility": "-"},
                                {"name": "nombre", "type": "String", "visibility": "+"},
                                {"name": "precio", "type": "Double", "visibility": "-"},
                            ],
                            "methods": [],
                        }
                    ],
                    "relations": [],
                    "deleted_elements": [],
                    "explanation": "Diagrama de prueba generado por FakeLlmProvider.",
                }
                return LlmResponse(text=json.dumps(data), raw_json=data, usage=usage, model=model, latency_ms=1.0)
            elif "files" in props:
                # Codegen schema
                data = {
                    "files": {
                        "pom.xml": "<project><modelVersion>4.0.0</modelVersion></project>",
                        ".vscode/launch.json": "{}",
                        "run.bat": "@echo off\necho Running fake project...",
                        "src/main/java/com/classforge/generated/Application.java": "package com.classforge.generated;\npublic class Application {}\n",
                    },
                    "summary": "Proyecto generado por FakeLlmProvider.",
                }
                return LlmResponse(text=json.dumps(data), raw_json=data, usage=usage, model=model, latency_ms=1.0)
            elif "relationships" in props and "classes" in props:
                # Vision schema
                data = {
                    "classes": [
                        {
                            "name": "Factura",
                            "isInterface": False,
                            "attributes": [{"name": "id", "type": "Long", "visibility": "+"}],
                            "methods": [],
                        }
                    ],
                    "relationships": [],
                    "summary": "Diagrama vision generado por FakeLlmProvider.",
                }
                return LlmResponse(text=json.dumps(data), raw_json=data, usage=usage, model=model, latency_ms=1.0)
            elif "reply_markdown" in props:
                # AiTeamResponse schema
                data = {
                    "reply_markdown": "Respuesta fundamentada del asistente de IA para el equipo.",
                    "proposals": [
                        {
                            "id": "prop-1",
                            "kind": "uml_command",
                            "title": "Sugerencia arquitectural",
                            "rationale": "Mejora cohesión y desacoplamiento.",
                            "severity": "info",
                            "command": None,
                            "target_element_ids": [],
                        }
                    ],
                    "questions": [],
                    "needs_context": False,
                }
                return LlmResponse(text=json.dumps(data), raw_json=data, usage=usage, model=model, latency_ms=1.0)
            else:
                data = {"status": "ok", "message": "Fake structured response"}
                return LlmResponse(text=json.dumps(data), raw_json=data, usage=usage, model=model, latency_ms=1.0)

        last_text = req.messages[-1].text if req.messages else "Hola"
        return LlmResponse(
            text=f"Respuesta simulada para: {last_text}",
            raw_json=None,
            usage=usage,
            model=model,
            latency_ms=1.0,
        )

    async def generate(self, req: LlmRequest) -> LlmResponse:
        self.calls.append(req)
        if self._error:
            err = self._error
            self._error = None
            await record_ai_usage(
                project_id=req.project_id,
                user_id=req.user_id,
                purpose=req.purpose,
                model=req.model or "fake-model",
                tokens={"prompt": 0, "candidates": 0, "total": 0, "thoughts": None},
                latency_ms=1.0,
                ok=False,
                error=str(err),
            )
            raise err

        if self._responses:
            resp = self._responses.pop(0)
        else:
            resp = self._default_response_for(req)

        await record_ai_usage(
            project_id=req.project_id,
            user_id=req.user_id,
            purpose=req.purpose,
            model=resp.model,
            tokens=resp.usage,
            latency_ms=resp.latency_ms,
            ok=True,
        )
        return resp

    async def stream(self, req: LlmRequest) -> AsyncIterator[str]:
        resp = await self.generate(req)
        # Yield in chunks
        words = resp.text.split(" ")
        for i, w in enumerate(words):
            yield w + (" " if i < len(words) - 1 else "")
