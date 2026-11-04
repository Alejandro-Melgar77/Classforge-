import pytest
from unittest.mock import AsyncMock, patch
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient
from app.modules.ai_chat.service import AiChatService
from app.modules.ai_chat.infrastructure.repositories.message_repository import AiMessageRepository
from app.ai_team.application.server_diagram_editor import ServerDiagramEditor
from app.ai_team.domain.diagram_model import Diagram, Node, Attribute, Method
from app.modules.ai.schemas import UMLCommandResponse, UMLClassCommand, UMLAttribute


@pytest.mark.anyio
async def test_foreign_diagram_cannot_be_used_as_context():
    db = AsyncMongoMockClient().test
    project, foreign = ObjectId(), ObjectId()
    did = ObjectId()
    await db.diagrams.insert_one({'_id': did, 'project_id': foreign, 'is_deleted': False})
    assert await AiChatService(db)._get_diagram(str(did), str(project)) is None


@pytest.mark.anyio
async def test_proposal_update_is_scoped_to_project():
    db = AsyncMongoMockClient().test
    await db.ai_messages.insert_one({'_id': 'm', 'project_id': 'b', 'proposals': [{'id': 'p'}]})
    repo = AiMessageRepository(db)
    assert await repo.update_proposal_state('m', 'p', 'applied', 'u', 'a') is None
    assert 'proposal_state' not in await db.ai_messages.find_one({'_id': 'm'})


def test_partial_command_preserves_existing_members():
    diagram = Diagram(nodes=[Node(id='n', name='Cliente', attributes=[Attribute(name='id')], methods=[Method(name='guardar')])])
    cmd = UMLCommandResponse(action='update_class', explanation='agregar', classes=[UMLClassCommand(name='Cliente', attributes=[UMLAttribute(name='email')])])
    ok, _ = ServerDiagramEditor(AsyncMongoMockClient().test)._simulate_apply(diagram, cmd)
    assert ok
    assert {a.name for a in diagram.nodes[0].attributes} == {'id', 'email'}
    assert [m.name for m in diagram.nodes[0].methods] == ['guardar']


@pytest.mark.anyio
async def test_failed_ai_save_does_not_broadcast():
    db = AsyncMongoMockClient().test
    editor = ServerDiagramEditor(db)
    diagram = await editor.repo.create({'name': 'D', 'graph_data': {'nodes': [], 'edges': []}})
    cmd = UMLCommandResponse(action='create_class', explanation='crear', classes=[UMLClassCommand(name='Cliente')])
    broadcast = AsyncMock()
    with patch.object(editor.repo, 'save_graph', new=AsyncMock(side_effect=RuntimeError('write failed'))), \
         patch('app.ai_team.application.server_diagram_editor.manager.broadcast', new=broadcast):
        with pytest.raises(RuntimeError):
            await editor.apply_command(str(diagram['_id']), 'architect', cmd)
    broadcast.assert_not_awaited()
