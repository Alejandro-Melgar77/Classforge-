import copy
import pytest
from app.core.errors import ValidationError
from app.modules.diagrams.validation import validate_graph


@pytest.mark.parametrize('graph', [
    {'nodes': [{'id': 'a'}, {'id': 'a'}]},
    {'nodes': [{'id': 'a'}], 'edges': [{'id': 'r', 'source': 'a', 'target': 'missing'}]},
    {'nodes': [{'id': 'a'}], 'edges': [{'id': 'r', 'source': 'a', 'target': 'a', 'type': 'inheritance'}]},
    {'nodes': [{'id': 'a', 'position': {'x': float('nan')}}]},
])
def test_invalid_graph_rejected(graph):
    with pytest.raises(ValidationError):
        validate_graph(graph)


def test_validation_preserves_custom_fields_and_allows_empty_graph():
    graph = {'nodes': [{'id': 'a', 'custom': {'unknown': True}}], 'edges': [], 'extra': 42}
    original = copy.deepcopy(graph)
    validate_graph(graph)
    assert graph == original
    validate_graph({'nodes': [], 'edges': []})
