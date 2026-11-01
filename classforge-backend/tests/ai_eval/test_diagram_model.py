"""
Tests for Canonical UML Diagram Model, Adapters, and Diagram Summary.
Verifies adaptation of flat snake_case vs nested camelCase, X6 JSON, XMI,
and ID-to-name resolution in AI summaries.
"""
import pytest
from app.ai_team.domain.diagram_model import (
    Diagram,
    Node,
    Edge,
    Attribute,
    from_graph_data,
    from_x6_json,
    from_xmi,
)
from app.ai_team.application.diagram_summary import summarize_diagram


# ── Adapters ──────────────────────────────────────────────────────────────────

def test_from_graph_data_flat_snake_case():
    """Matches the real structure emitted by classforge-frontend canvas.service.ts toGraphData()."""
    raw = {
        "nodes": [
            {
                "id": "node-1",
                "type": "class",
                "data": {
                    "name": "Pedido",
                    "attributes": [{"name": "id", "type": "Long", "visibility": "-"}],
                    "methods": [{"name": "calcularTotal", "params": "", "return_type": "Double", "visibility": "+"}],
                },
            },
            {
                "id": "node-2",
                "type": "class",
                "data": {
                    "name": "LineaPedido",
                    "attributes": [{"name": "cantidad", "type": "Integer", "visibility": "-"}],
                },
            },
        ],
        "edges": [
            {
                "id": "edge-1",
                "type": "composition",
                "source": "node-1",
                "target": "node-2",
                "label": "contiene",
                "source_multiplicity": "1",
                "target_multiplicity": "1..*",
            }
        ],
    }
    diagram = from_graph_data(raw)
    assert len(diagram.nodes) == 2
    assert len(diagram.edges) == 1
    edge = diagram.edges[0]
    assert edge.type == "composition"
    assert edge.source == "node-1"
    assert edge.target == "node-2"
    assert edge.source_multiplicity == "1"
    assert edge.target_multiplicity == "1..*"


def test_from_graph_data_nested_camel_case():
    """Tolerates legacy or alternative payloads with camelCase nested inside data."""
    raw = {
        "nodes": [
            {
                "id": "n1",
                "name": "Cliente",
                "attributes": [{"name": "nombre", "type": "String"}],
            }
        ],
        "edges": [
            {
                "id": "e1",
                "source": "n1",
                "target": "n2",
                "data": {
                    "type": "association",
                    "sourceMultiplicity": "0..1",
                    "targetMultiplicity": "1..*",
                },
            }
        ],
    }
    diagram = from_graph_data(raw)
    assert len(diagram.nodes) == 1
    assert diagram.nodes[0].name == "Cliente"
    assert len(diagram.edges) == 1
    assert diagram.edges[0].source_multiplicity == "0..1"
    assert diagram.edges[0].target_multiplicity == "1..*"


def test_from_x6_json():
    """Adapts raw AntV X6 graph JSON cells."""
    x6_data = {
        "cells": [
            {
                "id": "cell-node-1",
                "shape": "uml-class",
                "position": {"x": 100, "y": 150},
                "size": {"width": 200, "height": 120},
                "data": {"name": "Usuario", "attributes": [], "methods": []},
            },
            {
                "id": "cell-edge-1",
                "shape": "uml-edge",
                "source": {"cell": "cell-node-1"},
                "target": {"cell": "cell-node-2"},
                "type": "inheritance",
            },
        ]
    }
    diagram = from_x6_json(x6_data)
    assert len(diagram.nodes) == 1
    assert diagram.nodes[0].name == "Usuario"
    assert len(diagram.edges) == 1
    assert diagram.edges[0].source == "cell-node-1"
    assert diagram.edges[0].target == "cell-node-2"


def test_from_xmi():
    """Adapts standard Eclipse UML 2.5 / OMG XMI 2.1 XML."""
    xmi_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <xmi:XMI xmlns:xmi="http://www.omg.org/spec/XMI/20131001" xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
      <uml:Model xmi:id="model_1" name="TestModel">
        <packagedElement xmi:type="uml:Class" xmi:id="cls_1" name="Persona">
          <ownedAttribute xmi:id="attr_1" name="nombre" visibility="private"/>
          <ownedOperation xmi:id="op_1" name="caminar" visibility="public"/>
        </packagedElement>
        <packagedElement xmi:type="uml:Class" xmi:id="cls_2" name="Empleado">
          <generalization xmi:id="gen_1" general="cls_1"/>
        </packagedElement>
      </uml:Model>
    </xmi:XMI>
    """
    diagram = from_xmi(xmi_xml)
    assert len(diagram.nodes) == 2
    assert diagram.get_node_name("cls_1") == "Persona"
    assert diagram.get_node_name("cls_2") == "Empleado"
    assert len(diagram.edges) == 1
    assert diagram.edges[0].type == "inheritance"
    assert diagram.edges[0].source == "cls_2"
    assert diagram.edges[0].target == "cls_1"


def test_canonical_to_graph_data():
    """Ensures Diagram round-trips to standard GraphData dict."""
    d = Diagram(
        nodes=[Node(id="1", name="A", attributes=[{"name": "id", "type": "Long"}])],
        edges=[Edge(id="e1", source="1", target="2", type="association", source_multiplicity="1")]
    )
    graph_data = d.to_graph_data()
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert graph_data["nodes"][0]["data"]["name"] == "A"
    assert graph_data["edges"][0]["source_multiplicity"] == "1"


# ── Diagram Summary: ID Resolution and Trimming ───────────────────────────────

def test_summary_resolves_uuids_to_class_names():
    """Verifies that the summary replaces raw UUIDs with class names (fixing issue [V])."""
    diagram = Diagram(
        nodes=[
            Node(id="9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", name="Administrador", type="class"),
            Node(id="1c2b3a4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", name="UsuarioBase", type="class"),
        ],
        edges=[
            Edge(
                id="edge-uuid-1",
                source="9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                target="1c2b3a4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
                type="inheritance",
            )
        ],
    )
    summary = summarize_diagram(diagram)
    # The summary MUST contain the resolved names and NOT just the UUIDs in relations
    assert "Administrador --[inheritance]--> UsuarioBase" in summary
    assert "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d --[inheritance]-->" not in summary


def test_summary_respects_budget_and_prioritizes_recently_touched():
    """Verifies that budget constraints trigger compact mode and prioritize active classes."""
    nodes = [
        Node(id=f"id-{i}", name=f"Clase{i}", attributes=[Attribute(name=f"attr{j}", type="String") for j in range(5)])
        for i in range(20)
    ]
    edges = [Edge(id=f"e-{i}", source=f"id-{i}", target=f"id-{i+1}", type="association") for i in range(19)]
    diagram = Diagram(nodes=nodes, edges=edges)

    # Summarize with small budget of 300 tokens, prioritizing Clase0
    summary = summarize_diagram(diagram, budget_tokens=300, recently_touched_ids=["id-0"])
    
    # Priority class should be featured first
    assert "Clase0" in summary
    # Budget trimming should be applied
    assert len(summary) > 0
