"""Reproducciones de auditoria: solo MongoDB en memoria, sin servicios externos.
Ejecutar con classforge-backend/venv/Scripts/python.exe docs/audit_v2_probes.py.
Los asserts describen defectos observados, NO requisitos correctos ni tests de CI.
"""
import asyncio
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'classforge-backend'))
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient
from app.modules.diagrams.repository import DiagramRepository
from app.modules.ai_chat.service import AiChatService
from app.modules.ai_chat.router import set_proposal_state
from app.modules.ai_chat.schemas import ProposalStateUpdateRequest
from app.modules.ai_chat.infrastructure.repositories.message_repository import AiMessageRepository
from app.ai_team.application.server_diagram_editor import ServerDiagramEditor
from app.ai_team.domain.diagram_model import Diagram, Node, Attribute, Method
from app.modules.ai.schemas import UMLCommandResponse, UMLClassCommand, UMLAttribute


async def main():
    db = AsyncMongoMockClient()['audit_in_memory_only']
    results = {}
    project_a, project_b, did = ObjectId(), ObjectId(), ObjectId()
    await db.diagrams.insert_one({'_id': did, 'project_id': project_b, 'is_deleted': False})
    leaked = await AiChatService(db)._get_diagram(str(did), str(project_a))
    assert leaked['project_id'] == project_b
    results['foreign_diagram_context'] = 'El chat de A obtiene el diagrama de B por ID.'

    await db.ai_messages.insert_one({'_id': 'foreign-message', 'project_id': str(project_b),
                                    'content': 'foreign-content', 'proposals': [{'id': 'p1'}]})
    with patch('app.modules.ai_chat.router.manager.broadcast', new=AsyncMock()):
        result = await set_proposal_state(str(project_a), 'foreign-message', 'p1',
                    ProposalStateUpdateRequest(status='applied'), project={'_id': project_a},
                    current_user={'_id': ObjectId()}, db=db)
    assert result['message']['project_id'] == str(project_b)
    results['foreign_proposal_update'] = 'Handler autorizado para A modifica y devuelve mensaje de B.'

    diagram = Diagram(nodes=[Node(id='n1', name='Cliente', attributes=[Attribute(name='id')],
                                 methods=[Method(name='guardar')])])
    editor = ServerDiagramEditor(db)
    command = UMLCommandResponse(action='update_class', explanation='Agregar email',
                   classes=[UMLClassCommand(name='Cliente', attributes=[UMLAttribute(name='email')])])
    ok, _ = editor._simulate_apply(diagram, command)
    assert ok and [a.name for a in diagram.nodes[0].attributes] == ['email']
    assert diagram.nodes[0].methods == []
    results['partial_update_data_loss'] = 'Agregar email elimina id y el metodo guardar.'

    timestamp = datetime.now(timezone.utc)
    await db.ai_messages.insert_many([{'_id': f'equal-{i}', 'project_id': 'pagination',
                                      'created_at': timestamp} for i in range(3)])
    repo = AiMessageRepository(db)
    first, _, cursor = await repo.get_history('pagination', limit=2)
    second, _, _ = await repo.get_history('pagination', after=cursor, limit=2)
    assert len(first) == 2 and len(second) == 0
    results['timestamp_cursor_loss'] = '3 mensajes con igual fecha: pagina de 2 deja inaccesible el tercero.'

    graph_repo = DiagramRepository(db)
    created = await graph_repo.create({'name': 'Race', 'created_by': str(ObjectId())})
    diagram_id = str(created['_id'])
    original_get = graph_repo.get_by_id
    barrier = asyncio.Event()
    readers = 0
    async def synchronized_get(identifier):
        nonlocal readers
        snapshot = await original_get(identifier)
        readers += 1
        if readers <= 2:
            if readers == 2:
                barrier.set()
            await barrier.wait()
        return snapshot
    with patch.object(graph_repo, 'get_by_id', side_effect=synchronized_get):
        await asyncio.gather(*[graph_repo.save_graph(diagram_id, {'nodes': [], 'edges': [], 'marker': x},
                             str(ObjectId()), x) for x in ['A', 'B']])
    saved = await original_get(diagram_id)
    versions = await graph_repo.list_history(diagram_id)
    assert saved['version'] == 2 and len(versions) == 2
    results['concurrent_save_collision'] = 'Dos guardados desde v1 terminan en v2 y solo un snapshot nuevo.'

    valid = await graph_repo.create({'name': 'Broadcast', 'graph_data': {'nodes': [], 'edges': []}})
    events = []
    async def publish(*args, **kwargs):
        events.append('broadcast')
    async def fail_save(*args, **kwargs):
        events.append('save_failed')
        raise RuntimeError('Injected persistence failure')
    create_cmd = UMLCommandResponse(action='create_class', explanation='Crear Cliente',
                                   classes=[UMLClassCommand(name='Cliente')])
    with patch('app.ai_team.application.server_diagram_editor.manager.broadcast', side_effect=publish), \
         patch.object(editor.repo, 'save_graph', side_effect=fail_save):
        try:
            await editor.apply_command(str(valid['_id']), 'architect', create_cmd)
        except RuntimeError:
            pass
    assert events.index('broadcast') < events.index('save_failed')
    results['broadcast_before_persistence'] = events
    from app.core.config import settings
    from app.llm.registry import get_provider
    with patch.object(settings, 'AI_LOCAL_ONLY', True), \
         patch.object(settings, 'LLM_PROVIDER', 'gemini'), \
         patch.object(settings, 'LLM_ROUTING', '{"role_chat":["gemini"]}'), \
         patch('app.llm.registry._GLOBAL_PROVIDER', None), \
         patch('app.llm.registry.get_gemini_provider', return_value='CLOUD_SELECTED'):
        assert get_provider('role_chat') == 'CLOUD_SELECTED'
    results['local_only_cloud_fallback'] = 'AI_LOCAL_ONLY=True selecciona Gemini si la cadena queda vacia; sin llamada de red.'
    print(json.dumps(results, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
