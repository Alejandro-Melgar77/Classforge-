"""Non-destructive structural checks for canonical diagram snapshots."""
import math
from app.core.errors import ValidationError


def validate_graph(graph: dict) -> None:
    if not isinstance(graph, dict):
        raise ValidationError('El grafo debe ser un objeto')
    nodes, edges = graph.get('nodes', []), graph.get('edges', [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValidationError('nodes y edges deben ser listas')
    if len(nodes) > 5000 or len(edges) > 20000:
        raise ValidationError('El diagrama excede el límite de elementos')
    identifiers = set()
    node_ids = set()
    for collection in (nodes, edges):
        for item in collection:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'].strip():
                raise ValidationError('Cada elemento debe tener un identificador válido')
            if item['id'] in identifiers:
                raise ValidationError('El diagrama contiene identificadores duplicados')
            identifiers.add(item['id'])
            if collection is nodes:
                node_ids.add(item['id'])
                position = item.get('position', {})
                if not isinstance(position, dict):
                    raise ValidationError('Posición inválida')
                for coordinate in ('x', 'y'):
                    value = position.get(coordinate, item.get(coordinate, 0))
                    if not isinstance(value, (float, int)) or not math.isfinite(value):
                        raise ValidationError('Coordenadas inválidas')
                size = item.get('size', {})
                if not isinstance(size, dict):
                    raise ValidationError('Dimensiones inválidas')
                for dimension in ('width', 'height'):
                    if dimension in size:
                        value = size[dimension]
                        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                            raise ValidationError('Dimensiones inválidas')
    parents = {ident: [] for ident in node_ids}
    for edge in edges:
        endpoints = []
        for key in ('source', 'target'):
            endpoint = edge.get(key)
            if isinstance(endpoint, dict):
                endpoint = endpoint.get('cell') or endpoint.get('id')
            if not isinstance(endpoint, str) or endpoint not in node_ids:
                raise ValidationError('La relación referencia un nodo inexistente')
            endpoints.append(endpoint)
        data = edge.get('data') or {}
        if not isinstance(data, dict):
            raise ValidationError('Datos de relación inválidos')
        if (edge.get('type') or data.get('type')) in ('inheritance', 'generalization'):
            parents[endpoints[0]].append(endpoints[1])
    # Kahn's algorithm avoids recursion limits on long inheritance chains.
    indegree = {ident: 0 for ident in node_ids}
    for targets in parents.values():
        for target in targets:
            indegree[target] += 1
    ready = [ident for ident, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        node = ready.pop()
        visited += 1
        for target in parents[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    if visited != len(node_ids):
        raise ValidationError('El diagrama contiene un ciclo de herencia')
