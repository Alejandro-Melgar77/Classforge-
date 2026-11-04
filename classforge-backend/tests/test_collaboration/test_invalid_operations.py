import json
from unittest.mock import AsyncMock, patch

import pytest
from starlette.websockets import WebSocketDisconnect
from app.modules.collaboration.router import websocket_endpoint


@pytest.mark.anyio
@pytest.mark.parametrize('message', [
    {'type': 'NODE_OPERATION', 'op': 'nonsense', 'node_id': 'n', 'data': {}},
    {'type': 'NODE_OPERATION', 'op': 'update', 'node_id': 'n', 'data': 'bad'},
    {'type': 'EDGE_OPERATION', 'op': 'move', 'edge_id': 'e', 'data': {}},
    {'type': 'EDGE_OPERATION', 'op': 'add', 'edge_id': [], 'data': {}},
])
async def test_invalid_operations_are_rejected_without_persistence(message):
    ws = AsyncMock()
    ws.receive_text.side_effect = [json.dumps(message), WebSocketDisconnect()]
    with patch('app.modules.collaboration.router.verify_ws_token', new=AsyncMock(return_value={'_id': 'u'})), \
         patch('app.modules.collaboration.router.get_db', return_value=None), \
         patch('app.modules.collaboration.router.manager.connect', new=AsyncMock()), \
         patch('app.modules.collaboration.router.manager.disconnect', new=AsyncMock()), \
         patch('app.modules.collaboration.router.manager.broadcast', new=AsyncMock()), \
         patch('app.modules.collaboration.router.update_diagram_graph_data', new=AsyncMock()) as persist:
        await websocket_endpoint(ws, 'd', 'token')
    persist.assert_not_awaited()
    assert any(call.args[0].get('reason') == 'invalid_operation' for call in ws.send_json.await_args_list)
