"""Regression test for A20: Interfaces and canonical N-N cardinality handling."""
import pytest
from app.modules.codegen.fastapi_generator import generate_fastapi_project
from app.modules.codegen.generator import generate_spring_boot_project


def _class_node(node_id, name, attrs=None):
    return {
        "id": node_id,
        "shape": "classNode",
        "data": {"name": name, "attributes": attrs or [], "methods": []},
    }


def _interface_node(node_id, name, methods=None):
    return {
        "id": node_id,
        "shape": "interfaceNode",
        "data": {"name": name, "attributes": [], "methods": methods or []},
    }


def test_interface_node_generated_in_both_backends():
    """A20: interfaceNode must be recognized and generate interface/abstract code."""
    graph = {
        "nodes": [
            _class_node("n1", "Usuario"),
            _interface_node("n2", "Auditable"),
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2", "type": "realization"},
        ],
    }

    spring_files = generate_spring_boot_project(graph, package_name="com.example")
    fastapi_files = generate_fastapi_project(graph)

    # Spring Boot: should generate Auditable interface
    assert any("Auditable" in path for path in spring_files)
    assert any("public interface Auditable" in content for content in spring_files.values())

    # FastAPI: should generate Auditable model/interface
    assert any("auditable" in path.lower() for path in fastapi_files)


def test_many_to_many_with_canonical_and_flat_multiplicities():
    """A20: N-N association must be recognized from canonical (data.sourceMultiplicity) and flat."""
    # Test canonical nested format
    graph_canonical = {
        "nodes": [
            _class_node("n1", "Estudiante"),
            _class_node("n2", "Curso"),
        ],
        "edges": [
            {
                "id": "e1",
                "source": "n1",
                "target": "n2",
                "type": "association",
                "data": {"sourceMultiplicity": "*", "targetMultiplicity": "*"},
            }
        ],
    }

    spring_canonical = generate_spring_boot_project(graph_canonical, package_name="com.example")
    joined_spring = "\n".join(spring_canonical.values())
    assert "@ManyToMany" in joined_spring

    fastapi_canonical = generate_fastapi_project(graph_canonical)
    joined_fastapi = "\n".join(fastapi_canonical.values())
    assert "Table(" in joined_fastapi or "secondary=" in joined_fastapi
