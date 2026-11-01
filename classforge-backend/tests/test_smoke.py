import pytest


def test_smoke_import_and_openapi():
    # 1. Import app.main
    from app.main import app

    # 2. app.openapi() does not raise
    schema = app.openapi()
    assert isinstance(schema, dict)
    assert "paths" in schema
    assert len(schema["paths"]) > 0

    # 3. Expected routes exist
    paths = schema["paths"]
    assert "/api/v1/ai-chat/projects/{project_id}/messages" in paths
    assert "/api/v1/auth/login" in paths
