import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.authz import require_project_member
from app.core.database import get_db

@pytest.fixture
def override_deps():
    mock_user = {
        "_id": "507f1f77bcf86cd799439011",
        "id": "507f1f77bcf86cd799439011",
        "email": "tester@classforge.io",
        "name": "Tester",
        "role": "developer",
    }
    mock_project = {
        "_id": "507f1f77bcf86cd799439012",
        "name": "Proyecto Test UML",
        "description": "Proyecto para testing de IA local",
    }
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_project_member] = lambda: mock_project
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_local_ai_status_endpoint(override_deps):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/ai/local-status")
        assert response.status_code == 200
        data = response.json()
        assert "online" in data
        assert "model" in data
        assert "latency_ms" in data
        assert "installed_models" in data
        # Since Ollama is running locally with classforge-local-1.7b:
        assert data["online"] is True
        assert data["model"] == "classforge-local-1.7b"
        assert data["is_classforge_local_active"] is True


@pytest.mark.asyncio
async def test_evaluate_and_chat_local_ai_endpoint(override_deps):
    class MockDiagramCursor:
        async def to_list(self, length=10):
            return [
                {
                    "_id": "507f1f77bcf86cd799439013",
                    "name": "Diagrama de Facturación",
                    "content": {
                        "nodes": [
                            {
                                "id": "n1",
                                "name": "Factura",
                                "type": "class",
                                "data": {
                                    "name": "Factura",
                                    "attributes": [{"name": "id", "type": "Long", "visibility": "+"}, {"name": "total", "type": "Decimal", "visibility": "+"}],
                                    "methods": [{"name": "calcularTotal", "params": "", "return_type": "Decimal", "visibility": "+"}]
                                }
                            },
                            {
                                "id": "n2",
                                "name": "ItemFactura",
                                "type": "class",
                                "data": {
                                    "name": "ItemFactura",
                                    "attributes": [{"name": "id", "type": "Long", "visibility": "+"}, {"name": "cantidad", "type": "Integer", "visibility": "+"}],
                                    "methods": []
                                }
                            }
                        ],
                        "edges": [
                            {
                                "id": "e1",
                                "type": "composition",
                                "source": "n1",
                                "target": "n2",
                                "source_multiplicity": "1",
                                "target_multiplicity": "1..*"
                            }
                        ]
                    }
                }
            ]

    class MockCollection:
        def find(self, *args, **kwargs):
            return self
        def sort(self, *args, **kwargs):
            return MockDiagramCursor()
        async def find_one(self, *args, **kwargs):
            return None
        async def insert_one(self, *args, **kwargs):
            return None
        async def count_documents(self, *args, **kwargs):
            return 1

    class MockDb(dict):
        def __getitem__(self, key):
            return MockCollection()

    app.dependency_overrides[get_db] = lambda: MockDb()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "message": "Evaluar diseño de software de facturación",
            "session_history": []
        }
        response = await ac.post("/api/v1/projects/507f1f77bcf86cd799439012/local-ai/evaluate-and-chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        res_data = data["data"]
        assert "verdict" in res_data
        assert res_data["verdict"] in ("APROBADO", "RECHAZADO")
        assert "total_score" in res_data
        assert "assistant_message" in res_data
        assert len(res_data["assistant_message"]) > 0
