from unittest.mock import AsyncMock

import pytest

from app.modules.collaboration.connection_manager import ConnectionManager


@pytest.mark.anyio
async def test_other_tab_stays_connected_and_receives_changes():
    manager = ConnectionManager()
    one, two = AsyncMock(), AsyncMock()
    user = {'_id': 'u', 'name': 'A'}
    await manager.connect('d', user, one)
    await manager.connect('d', user, two)
    assert len(manager.get_room_users('d')) == 1
    manager.acquire_lock('d', 'u', 'n')
    await manager.broadcast('d', {'type': 'UPDATE'}, exclude_websocket=one)
    two.send_json.assert_awaited_once()
    one.send_json.assert_not_awaited()
    await manager.disconnect('d', 'u', one)
    assert len(manager.get_room_users('d')) == 1
    assert manager.get_locks('d') == {'n': 'u'}
    await manager.disconnect('d', 'u', two)
    assert manager.get_room_users('d') == []


@pytest.mark.anyio
async def test_revoked_passive_connection_cannot_receive_broadcast():
    manager = ConnectionManager()
    revoked, allowed = AsyncMock(), AsyncMock()
    await manager.connect('d', {'_id': 'a'}, revoked, authorize=AsyncMock(return_value=False))
    await manager.connect('d', {'_id': 'b'}, allowed, authorize=AsyncMock(return_value=True))
    await manager.broadcast('d', {'private': 'diagram content'})
    revoked.send_json.assert_not_awaited()
    revoked.close.assert_awaited_once()
    allowed.send_json.assert_awaited_once()


@pytest.mark.anyio
async def test_three_tabs_disconnect_independently():
    manager = ConnectionManager()
    sockets = [AsyncMock() for _ in range(3)]
    for socket in sockets:
        await manager.connect('d', {'_id': 'u'}, socket)
    await manager.disconnect('d', 'u', sockets[1])
    await manager.broadcast('d', {'type': 'PING'})
    sockets[0].send_json.assert_awaited_once()
    sockets[1].send_json.assert_not_awaited()
    sockets[2].send_json.assert_awaited_once()
    assert len(manager.get_room_users('d')) == 1


@pytest.mark.anyio
async def test_failed_delivery_does_not_disconnect_other_tab():
    manager = ConnectionManager()
    failed, healthy = AsyncMock(), AsyncMock()
    failed.send_json.side_effect = RuntimeError('closed')
    for ws in (failed, healthy):
        await manager.connect('d', {'_id': 'u'}, ws)
    await manager.broadcast('d', {'type': 'event'})
    healthy.send_json.assert_awaited_once()
    assert len(manager.get_room_users('d')) == 1


@pytest.mark.anyio
async def test_personal_ai_message_is_sent_only_to_owner():
    manager = ConnectionManager()
    owner, colleague = AsyncMock(), AsyncMock()
    await manager.connect('project:p', {'_id': 'owner'}, owner)
    await manager.connect('project:p', {'_id': 'colleague'}, colleague)
    await manager.broadcast('project:p', {'type': 'AI_MESSAGE_UPDATED', 'message': {
        'thread': 'personal', 'owner_id': 'owner', 'content': 'private'}})
    owner.send_json.assert_awaited_once()
    colleague.send_json.assert_not_awaited()


def test_only_lock_owner_can_release():
    manager = ConnectionManager()
    assert manager.acquire_lock('d', 'a', 'n')
    assert not manager.release_lock('d', 'b', 'n')
    assert manager.get_locks('d') == {'n': 'a'}
    assert manager.release_lock('d', 'a', 'n')
