"""Pure, non-destructive operations on the persisted ClassForge graph format."""
from copy import deepcopy
from typing import Any

from app.core.errors import ValidationError
from app.modules.diagrams.validation import validate_graph


def _merge(target: dict, patch: dict) -> None:
    for key, value in patch.items():
        if key == 'id':
            raise ValidationError('No se puede cambiar un identificador')
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = deepcopy(value)


def _find(items: list, identifier: str) -> dict:
    matches = [item for item in items if isinstance(item, dict) and item.get('id') == identifier]
    if len(matches) != 1:
        raise ValidationError('Elemento inexistente o duplicado')
    return matches[0]


def _endpoint(value: Any) -> Any:
    return (value.get('cell') or value.get('id')) if isinstance(value, dict) else value


def apply_operations(graph: dict, operations: list[dict]) -> dict:
    """Apply a batch atomically in memory; validate the final graph before returning."""
    if not isinstance(operations, list) or not operations or len(operations) > 100:
        raise ValidationError('La lista de operaciones debe contener entre 1 y 100 elementos')
    validate_graph(graph)
    result = deepcopy(graph)
    nodes = result.setdefault('nodes', [])
    edges = result.setdefault('edges', [])
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValidationError('Operación inválida')
        kind = operation.get('type')
        identifier = operation.get('id')
        if kind == 'replace_graph':
            if len(operations) != 1 or not isinstance(operation.get('graph'), dict):
                raise ValidationError('El reemplazo del grafo debe ser una operación independiente')
            result = deepcopy(operation['graph'])
            break
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValidationError('Identificador de operación inválido')
        if kind in ('add_node', 'add_edge'):
            data = operation.get('data')
            if not isinstance(data, dict) or data.get('id', identifier) != identifier:
                raise ValidationError('Datos de elemento inválidos')
            if any(item.get('id') == identifier for item in nodes + edges):
                raise ValidationError('Identificador duplicado')
            item = deepcopy(data)
            item['id'] = identifier
            (nodes if kind == 'add_node' else edges).append(item)
        elif kind in ('update_node', 'move_node', 'resize_node', 'update_edge'):
            patch = operation.get('patch')
            if not isinstance(patch, dict) or not patch:
                raise ValidationError('Parche inválido')
            target = _find(edges if kind == 'update_edge' else nodes, identifier)
            if kind == 'move_node':
                patch = {'position': deepcopy(patch), **patch}
            elif kind == 'resize_node':
                patch = {'size': deepcopy(patch), **patch}
            _merge(target, patch)
        elif kind == 'remove_node':
            nodes.remove(_find(nodes, identifier))
            edges[:] = [edge for edge in edges if identifier not in (_endpoint(edge.get('source')), _endpoint(edge.get('target')))]
        elif kind == 'remove_edge':
            edges.remove(_find(edges, identifier))
        elif kind in ('add_attribute', 'update_attribute', 'remove_attribute', 'add_method', 'update_method', 'remove_method'):
            node = _find(nodes, identifier)
            node_data = node.setdefault('data', {})
            if not isinstance(node_data, dict):
                raise ValidationError('Datos de nodo inválidos')
            field = 'attributes' if kind.endswith('attribute') else 'methods'
            members = node_data.setdefault(field, [])
            if not isinstance(members, list):
                raise ValidationError('Lista de miembros inválida')
            member_id = operation.get('member_id')
            if not isinstance(member_id, str) or not member_id:
                raise ValidationError('Identificador de miembro inválido')
            if kind.startswith('add_'):
                data = operation.get('data')
                if not isinstance(data, dict) or data.get('id', member_id) != member_id:
                    raise ValidationError('Datos de miembro inválidos')
                if any(m.get('id') == member_id for m in members if isinstance(m, dict)):
                    raise ValidationError('Identificador de miembro duplicado')
                members.append({**deepcopy(data), 'id': member_id})
            elif kind.startswith('remove_'):
                members.remove(_find(members, member_id))
            else:
                patch = operation.get('patch')
                if not isinstance(patch, dict) or not patch:
                    raise ValidationError('Parche inválido')
                _merge(_find(members, member_id), patch)
        else:
            raise ValidationError('Tipo de operación desconocido')
    validate_graph(result)
    return result
