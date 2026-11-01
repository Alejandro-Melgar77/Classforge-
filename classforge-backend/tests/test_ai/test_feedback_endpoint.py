"""
tests/test_ai/test_feedback_endpoint.py — Tests for POST /api/v1/ai/feedback endpoint (P8b Bloque E).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.dependencies import get_current_user

@pytest.fixture
def override_user():
    mock_user = {"id": "usr_test123", "email": "test@classforge.com", "role": "dev"}
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield mock_user
    app.dependency_overrides.pop(get_current_user, None)

@pytest.mark.asyncio
async def test_feedback_requires_explicit_opt_in(override_user):
    transport = ASGITransport(app=app)
    url = f"{settings.API_V1_STR}/ai/feedback"
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "prompt": "crear clase Factura con numero:string",
            "corrected_command": {
                "action": "create_class",
                "classes": [{"name": "Factura", "attributes": [{"name": "numero", "type": "String", "visibility": "+"}], "methods": []}],
                "relations": [],
                "deleted_elements": [],
                "explanation": "Factura creada",
                "source": "local"
            },
            "allow_feedback": False,  # Opt-in is FALSE
        }
        res = await ac.post(url, json=payload)
        assert res.status_code == 400
        msg = res.json().get("message") or res.json().get("detail", "")
        assert "consentimiento" in msg.lower()

@pytest.mark.asyncio
async def test_feedback_accepted_when_opt_in_true(override_user):
    transport = ASGITransport(app=app)
    url = f"{settings.API_V1_STR}/ai/feedback"
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "prompt": "crear clase Factura con contacto usuario@empresa.com en IP 192.168.1.10",
            "corrected_command": {
                "action": "create_class",
                "classes": [{"name": "Factura", "attributes": [{"name": "contacto", "type": "String", "visibility": "+"}], "methods": []}],
                "relations": [],
                "deleted_elements": [],
                "explanation": "Factura creada",
                "source": "local"
            },
            "allow_feedback": True,
            "comment": "Revisar contacto soporte@test.com",
        }
        res = await ac.post(url, json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pending_review"
