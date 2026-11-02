"""Regression test for A26 and A27: NLU unknown handling and relation cardinality."""
import pytest

from app.modules.ai.heuristic_engine import (
    infer_type_from_name,
    parse_cardinality_str,
    parse_heuristic,
)


def test_garbage_input_returns_unknown_action_without_classes():
    """A26: Garbage / conversational text must yield action='unknown' without invented classes."""
    for prompt in ("hola buenas tardes", "el clima esta nublado hoy", "palabras aleatorias sin sentido"):
        result = parse_heuristic(prompt)
        assert result.action == "unknown"
        assert result.classes == []


def test_relation_with_cardinality_produces_one_relation_and_no_garbage_classes():
    """A26 / A27: An explicit relation command must produce 1 relation and 0 garbage classes."""
    prompt = "crear relacion uno a muchos entre Cliente y Pedido"
    result = parse_heuristic(prompt)

    assert result.action == "create_relation"
    assert result.classes == []
    assert len(result.relations) == 1
    rel = result.relations[0]
    assert rel.source == "Cliente"
    assert rel.target == "Pedido"
    assert rel.type == "association"


def test_type_inference_codigo_and_creado():
    """A27: `codigo` -> Long and `creado` -> Date (not generic String)."""
    assert infer_type_from_name("codigo") == "Long"
    assert infer_type_from_name("creado") == "Date"


def test_impossible_multiplicity_reversed():
    """A27: Inverted range '2..1' is normalised to '1..2'."""
    src, tgt = parse_cardinality_str("2..1")
    assert src == "1"
    assert tgt == "1..2"
