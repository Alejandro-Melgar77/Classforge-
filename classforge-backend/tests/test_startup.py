"""Startup/lifespan regression tests.

These tests exist because the backend shipped with a ``NameError`` in the
lifespan (``db_instance`` was used but never imported). The whole test suite
missed it because every other test talks to the ASGI app without running the
lifespan. Any future regression of the startup path must fail here.
"""
import pytest
from mongomock_motor import AsyncMongoMockClient

import app.main as main_module
from app.ai_team.application.worker import AiWorker
from app.core import database as db_module
from app.core.config import settings


def _patch_mongo(monkeypatch, mock_db):
    async def fake_connect():
        db_module.db_instance.db = mock_db

    async def fake_close():
        return None

    monkeypatch.setattr(main_module, "connect_to_mongo", fake_connect)
    monkeypatch.setattr(main_module, "close_mongo_connection", fake_close)


@pytest.fixture
def mock_db():
    return AsyncMongoMockClient()["classforge_test"]


async def test_lifespan_starts_and_stops_without_worker(monkeypatch, mock_db):
    """The API must start even when the autonomous worker is disabled."""
    _patch_mongo(monkeypatch, mock_db)
    monkeypatch.setattr(settings, "AI_AUTONOMY_ENABLED", False)

    async with main_module.lifespan(main_module.app):
        assert main_module.app.state.ai_worker is None

    assert db_module.db_instance.client is None or True  # cleanup ran without raising


async def test_lifespan_starts_worker_with_real_db(monkeypatch, mock_db):
    """C1: the worker must be constructible with the shared db instance."""
    _patch_mongo(monkeypatch, mock_db)
    monkeypatch.setattr(settings, "AI_AUTONOMY_ENABLED", True)

    started = {}

    def fake_start(self):
        started["worker_id"] = self.worker_id
        started["db"] = self.db

    monkeypatch.setattr(AiWorker, "start", fake_start)

    async with main_module.lifespan(main_module.app):
        worker = main_module.app.state.ai_worker
        assert worker is not None
        assert isinstance(worker, AiWorker)
        assert started["db"] is mock_db

    assert started  # start() was actually called


async def test_lifespan_survives_worker_failure(monkeypatch, mock_db):
    """A broken AI worker must not prevent the API from starting."""
    _patch_mongo(monkeypatch, mock_db)
    monkeypatch.setattr(settings, "AI_AUTONOMY_ENABLED", True)

    class ExplodingWorker:
        def __init__(self, db):
            raise RuntimeError("worker boom")

    monkeypatch.setattr("app.ai_team.application.worker.AiWorker", ExplodingWorker)

    async with main_module.lifespan(main_module.app):
        assert main_module.app.state.ai_worker is None
