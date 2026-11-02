"""Heuristic NLU regressions (audit A26, A27)."""
import pytest

from app.modules.ai.heuristic_engine import (
    infer_type_from_name,
    parse_cardinality_str,
    parse_heuristic,
)


def test_garbage_input_is_not_interpreted():
    """A26: unknown input must not invent classes from random words."""
    for prompt in ("hola buenas tardes", "el clima esta nublado hoy", "xyz"):
        result = parse_heuristic(prompt)
        assert result.action == "unknown"
        assert result.classes == []


@pytest.mark.parametrize("prompt,expected_type", [
    ("crear relacion uno a muchos entre Cliente y Pedido", "association"),
    ("relacion muchos a muchos entre Estudiante y Curso", "association"),
    ("crear una relacion de composicion entre Factura y Cliente", "composition"),
    ("relacion de herencia entre Perro y Animal", "inheritance"),
])
def test_relation_phrasings_do_not_generate_domain_systems(prompt, expected_type):
    """A26: keywords like 'estudiante' must not hijack an explicit relation."""
    result = parse_heuristic(prompt)

    assert result.action == "create_relation"
    assert result.classes == []
    assert len(result.relations) == 1
    assert result.relations[0].type == expected_type


def test_relation_cardinality_is_mapped():
    result = parse_heuristic("crear relacion uno a muchos entre Cliente y Pedido")
    relation = result.relations[0]
    assert relation.source == "Cliente"
    assert relation.target == "Pedido"


def test_domain_template_still_works():
    result = parse_heuristic("generar sistema e-commerce")
    assert result.action == "generate_system"
    assert len(result.classes) >= 4


def test_creation_still_works_after_relation_rules():
    result = parse_heuristic("crear clase Estudiante con atributos nombre, semestre")
    assert result.action == "create_class"
    assert result.classes[0].name == "Estudiante"


def test_type_inference_matches_documentation():
    """A27: `codigo` -> Long and `creado` -> Date were returning String."""
    assert infer_type_from_name("codigo") == "Long"
    assert infer_type_from_name("creado") == "Date"
    assert infer_type_from_name("precio") == "Double"
    assert infer_type_from_name("stock") == "Integer"
    assert infer_type_from_name("esActivo") == "Boolean"
    assert infer_type_from_name("nombre") == "String"


def test_impossible_multiplicity_is_normalised():
    """A27: "2..1" used to produce the impossible range ('2', '2..1')."""
    assert parse_cardinality_str("2..1") == ("1", "1..2")
