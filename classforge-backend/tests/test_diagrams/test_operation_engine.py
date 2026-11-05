import copy
import pytest

from app.core.errors import ValidationError
from app.modules.diagrams.operations import apply_operations
from app.ai_team.application.server_diagram_editor import ServerDiagramEditor
from app.ai_team.domain.diagram_model import from_graph_data
from app.modules.ai.schemas import UMLAttribute, UMLClassCommand, UMLCommandResponse
from mongomock_motor import AsyncMongoMockClient
from unittest.mock import patch
from app.modules.diagrams.repository import DiagramRepository


def sample():
    return {'nodes': [
        {'id': 'a', 'position': {'x': 1, 'y': 2}, 'data': {'name': 'Cliente', 'attributes': [
            {'id': 'id1', 'name': 'id', 'type': 'Long', 'custom': 'keep'}], 'methods': [
            {'id': 'm1', 'name': 'guardar', 'params': 'x', 'extension': 42}]}},
        {'id': 'b', 'position': {'x': 3, 'y': 4}, 'data': {'name': 'Pedido'}}],
        'edges': [{'id': 'e', 'source': {'cell': 'a'}, 'target': 'b', 'custom': 'edge'}],
        'viewport': {'zoom': 2}, 'extension': {'keep': True}}


def test_patch_preserves_graph_and_member_fields():
    graph = sample()
    result = apply_operations(graph, [
        {'type': 'add_attribute', 'id': 'a', 'member_id': 'id2', 'data': {'name': 'email'}},
        {'type': 'update_method', 'id': 'a', 'member_id': 'm1', 'patch': {'name': 'save'}},
        {'type': 'move_node', 'id': 'a', 'patch': {'x': 10}},
        {'type': 'update_edge', 'id': 'e', 'patch': {'label': 'orders'}},
    ])
    assert result['nodes'][0]['data']['attributes'][0] == graph['nodes'][0]['data']['attributes'][0]
    assert result['nodes'][0]['data']['methods'][0]['extension'] == 42
    assert result['nodes'][0]['position'] == {'x': 10, 'y': 2}
    assert result['edges'][0]['custom'] == 'edge'
    assert result['extension'] == graph['extension']
    assert graph == sample()


def test_failed_batch_has_no_partial_effect_and_removal_cascades():
    graph = sample()
    before = copy.deepcopy(graph)
    with pytest.raises(ValidationError):
        apply_operations(graph, [{'type': 'remove_node', 'id': 'a'}, {'type': 'unknown', 'id': 'b'}])
    assert graph == before
    result = apply_operations(graph, [{'type': 'remove_node', 'id': 'a'}])
    assert not result['edges']


def test_ai_patch_preserves_unknown_fields_and_omitted_defaults():
    graph = sample()
    editor = ServerDiagramEditor(AsyncMongoMockClient().test)
    original = from_graph_data(graph)
    simulated = copy.deepcopy(original)
    command = UMLCommandResponse(action='update_class', explanation='change', classes=[
        UMLClassCommand(name='Cliente', attributes=[UMLAttribute(name='id'), UMLAttribute(name='email')])])
    assert editor._simulate_apply(simulated, command)[0]
    result = editor._apply_to_raw_graph(graph, original, simulated, command)
    assert result['nodes'][0]['data']['attributes'][0] == graph['nodes'][0]['data']['attributes'][0]
    assert result['nodes'][0]['data']['methods'] == graph['nodes'][0]['data']['methods']
    assert result['edges'] == graph['edges']
    assert result['extension'] == graph['extension']


def test_ai_preserves_legacy_top_level_members():
    graph = sample()
    node = graph['nodes'][0]
    node['attributes'] = node['data'].pop('attributes')
    editor = ServerDiagramEditor(AsyncMongoMockClient().test)
    original = from_graph_data(graph)
    simulated = copy.deepcopy(original)
    command = UMLCommandResponse(action='update_class', explanation='add', classes=[
        UMLClassCommand(name='Cliente', attributes=[UMLAttribute(name='email')])])
    assert editor._simulate_apply(simulated, command)[0]
    result = editor._apply_to_raw_graph(graph, original, simulated, command)
    assert result['nodes'][0]['attributes'][0] == node['attributes'][0]
    assert result['nodes'][0]['attributes'][1]['name'] == 'email'
    assert 'attributes' not in result['nodes'][0]['data']


@pytest.mark.anyio
async def test_legacy_history_survives_save():
    repo = DiagramRepository(AsyncMongoMockClient().test)
    diagram = await repo.create({'name': 'D'})
    diagram_id = str(diagram['_id'])
    legacy = {'version': 0, 'graph_data': sample()}
    await repo.collection.update_one({'_id': diagram['_id']}, {'$set': {'history': [legacy]}})
    await repo.save_graph(diagram_id, sample(), 'u', None, base_version=1)
    assert (await repo.get_history_entry(diagram_id, 0))['graph_data'] == legacy['graph_data']
    assert 0 in [v['version'] for v in await repo.list_history(diagram_id)]


@pytest.mark.anyio
async def test_initial_snapshot_recovers_after_history_failure():
    repo = DiagramRepository(AsyncMongoMockClient().test)
    with patch.object(repo.versions_collection, 'update_one', side_effect=RuntimeError('unavailable')):
        diagram = await repo.create({'name': 'D', 'graph_data': sample()})
    diagram_id = str(diagram['_id'])
    assert (await repo.get_history_entry(diagram_id, 1))['graph_data'] == sample()
    await repo.list_history(diagram_id)
    assert '_pending_snapshot' not in await repo.get_by_id(diagram_id)
