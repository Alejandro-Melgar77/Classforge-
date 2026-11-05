import asyncio
from unittest.mock import patch
import pytest
from mongomock_motor import AsyncMongoMockClient
from app.modules.diagrams.repository import DiagramRepository
from app.core.errors import ConflictError


@pytest.mark.anyio
async def test_same_base_version_cannot_be_saved_twice():
    repo = DiagramRepository(AsyncMongoMockClient().test)
    created = await repo.create({'name': 'D'})
    did = str(created['_id'])
    results = await asyncio.gather(
        repo.save_graph(did, {'nodes': [], 'edges': [], 'marker': 'a'}, 'user', None, base_version=1),
        repo.save_graph(did, {'nodes': [], 'edges': [], 'marker': 'b'}, 'user', None, base_version=1),
        return_exceptions=True,
    )
    assert sum(isinstance(r, ConflictError) for r in results) == 1
    current = await repo.get_by_id(did)
    assert current['version'] == 2
    assert (await repo.get_history_entry(did, 2))['graph_data'] == current['graph_data']


@pytest.mark.anyio
async def test_snapshot_is_recoverable_after_history_write_failure():
    db = AsyncMongoMockClient().test
    repo = DiagramRepository(db)
    created = await repo.create({'name': 'D'})
    did = str(created['_id'])
    graph = {'nodes': [], 'edges': [], 'marker': 'committed'}
    with patch.object(repo.versions_collection, 'update_one', side_effect=RuntimeError('unavailable')):
        saved = await repo.save_graph(did, graph, 'user', None, base_version=1)
    assert saved['version'] == 2
    assert (await repo.get_history_entry(did, 2))['graph_data'] == graph
    # A new repository instance repairs the interrupted materialization.
    recovered = DiagramRepository(db)
    await recovered.list_history(did)
    assert '_pending_snapshot' not in await recovered.get_by_id(did)
    assert (await recovered.get_history_entry(did, 2))['graph_data'] == graph
