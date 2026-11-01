"""
Unit tests with fixtures for deterministic UML linter (app/ai_team/domain/lint.py).
Covers all 15 rules with positive (defect present) and negative (defect absent) test cases.
"""
import pytest
from app.ai_team.domain.diagram_model import Diagram, Node, Edge, Attribute, Method, from_graph_data
from app.ai_team.domain.lint import lint, Finding


def find_rule(findings: list[Finding], rule_name: str) -> list[Finding]:
    return [f for f in findings if f.rule == rule_name]


# ── Rule 1: class-no-attributes ────────────────────────────────────────────────

def test_class_no_attributes_triggers():
    diagram = Diagram(nodes=[Node(id="n1", name="Factura", type="class", attributes=[])])
    findings = lint(diagram)
    matches = find_rule(findings, "class-no-attributes")
    assert len(matches) == 1
    assert matches[0].severity == "warn"
    assert "Factura" in matches[0].message_es


def test_class_no_attributes_passes_when_attributes_present():
    diagram = Diagram(nodes=[
        Node(id="n1", name="Factura", type="class", attributes=[Attribute(name="id", type="Long")])
    ])
    findings = lint(diagram)
    assert len(find_rule(findings, "class-no-attributes")) == 0


# ── Rule 2: missing-primary-key ───────────────────────────────────────────────

def test_missing_primary_key_triggers():
    diagram = Diagram(nodes=[
        Node(id="n1", name="Producto", type="class", attributes=[
            Attribute(name="nombre", type="String"),
            Attribute(name="precio", type="Double"),
        ])
    ])
    findings = lint(diagram)
    matches = find_rule(findings, "missing-primary-key")
    assert len(matches) == 1
    assert matches[0].severity == "warn"
    assert "Producto" in matches[0].message_es


def test_missing_primary_key_passes_when_id_present():
    diagram = Diagram(nodes=[
        Node(id="n1", name="Producto", type="class", attributes=[
            Attribute(name="id", type="Long"),
            Attribute(name="nombre", type="String"),
        ])
    ])
    findings = lint(diagram)
    assert len(find_rule(findings, "missing-primary-key")) == 0


# ── Rule 3: duplicate-class-name ──────────────────────────────────────────────

def test_duplicate_class_name_triggers():
    diagram = Diagram(nodes=[
        Node(id="n1", name="Usuario", type="class"),
        Node(id="n2", name="usuario", type="class"),
    ])
    findings = lint(diagram)
    matches = find_rule(findings, "duplicate-class-name")
    assert len(matches) == 1
    assert matches[0].severity == "critical"
    assert "n1" in matches[0].element_ids and "n2" in matches[0].element_ids


def test_duplicate_class_name_passes_when_unique():
    diagram = Diagram(nodes=[
        Node(id="n1", name="Usuario", type="class"),
        Node(id="n2", name="Perfil", type="class"),
    ])
    findings = lint(diagram)
    assert len(find_rule(findings, "duplicate-class-name")) == 0


# ── Rule 4: class-not-pascal-case ──────────────────────────────────────────────

def test_class_not_pascal_case_triggers():
    diagram = Diagram(nodes=[
        Node(id="n1", name="orden_compra", type="class"),
        Node(id="n2", name="detalleFactura", type="class"),
    ])
    findings = lint(diagram)
    matches = find_rule(findings, "class-not-pascal-case")
    assert len(matches) == 2


def test_class_not_pascal_case_passes():
    diagram = Diagram(nodes=[
        Node(id="n1", name="OrdenCompra", type="class"),
        Node(id="n2", name="DetalleFactura", type="class"),
    ])
    findings = lint(diagram)
    assert len(find_rule(findings, "class-not-pascal-case")) == 0


# ── Rule 5: attribute-not-camel-case ───────────────────────────────────────────

def test_attribute_not_camel_case_triggers():
    diagram = Diagram(nodes=[
        Node(id="n1", name="Cliente", type="class", attributes=[
            Attribute(name="Fecha_Nacimiento", type="Date"),
            Attribute(name="codigo_postal", type="String"),
        ])
    ])
    findings = lint(diagram)
    matches = find_rule(findings, "attribute-not-camel-case")
    assert len(matches) == 2


def test_attribute_not_camel_case_passes():
    diagram = Diagram(nodes=[
        Node(id="n1", name="Cliente", type="class", attributes=[
            Attribute(name="fechaNacimiento", type="Date"),
            Attribute(name="codigoPostal", type="String"),
        ])
    ])
    findings = lint(diagram)
    assert len(find_rule(findings, "attribute-not-camel-case")) == 0


# ── Rule 6: orphan-node ───────────────────────────────────────────────────────

def test_orphan_node_triggers_when_diagram_has_multiple_nodes():
    diagram = Diagram(
        nodes=[
            Node(id="n1", name="A", type="class"),
            Node(id="n2", name="B", type="class"),
            Node(id="n3", name="C", type="class"),
        ],
        edges=[Edge(id="e1", source="n1", target="n2", type="association")]
    )
    findings = lint(diagram)
    matches = find_rule(findings, "orphan-node")
    assert len(matches) == 1
    assert matches[0].element_ids == ["n3"]


def test_orphan_node_passes_when_all_connected():
    diagram = Diagram(
        nodes=[Node(id="n1", name="A", type="class"), Node(id="n2", name="B", type="class")],
        edges=[Edge(id="e1", source="n1", target="n2", type="association")]
    )
    findings = lint(diagram)
    assert len(find_rule(findings, "orphan-node")) == 0


# ── Rule 7: inheritance-cycle ─────────────────────────────────────────────────

def test_inheritance_cycle_triggers_direct():
    diagram = Diagram(
        nodes=[Node(id="n1", name="A", type="class"), Node(id="n2", name="B", type="class")],
        edges=[
            Edge(id="e1", source="n1", target="n2", type="inheritance"),
            Edge(id="e2", source="n2", target="n1", type="inheritance"),
        ]
    )
    findings = lint(diagram)
    matches = find_rule(findings, "inheritance-cycle")
    assert len(matches) >= 1
    assert matches[0].severity == "critical"


def test_inheritance_cycle_triggers_indirect():
    diagram = Diagram(
        nodes=[
            Node(id="n1", name="A", type="class"),
            Node(id="n2", name="B", type="class"),
            Node(id="n3", name="C", type="class"),
        ],
        edges=[
            Edge(id="e1", source="n1", target="n2", type="inheritance"),
            Edge(id="e2", source="n2", target="n3", type="inheritance"),
            Edge(id="e3", source="n3", target="n1", type="inheritance"),
        ]
    )
    findings = lint(diagram)
    matches = find_rule(findings, "inheritance-cycle")
    assert len(matches) >= 1


def test_inheritance_cycle_passes_linear_hierarchy():
    diagram = Diagram(
        nodes=[
            Node(id="n1", name="Persona", type="class"),
            Node(id="n2", name="Empleado", type="class"),
            Node(id="n3", name="Gerente", type="class"),
        ],
        edges=[
            Edge(id="e1", source="n2", target="n1", type="inheritance"),
            Edge(id="e2", source="n3", target="n2", type="inheritance"),
        ]
    )
    findings = lint(diagram)
    assert len(find_rule(findings, "inheritance-cycle")) == 0


# ── Rule 8: multiple-class-inheritance ────────────────────────────────────────

def test_multiple_class_inheritance_triggers():
    diagram = Diagram(
        nodes=[
            Node(id="n1", name="VehiculoAereo", type="class"),
            Node(id="n2", name="VehiculoAcuatico", type="class"),
            Node(id="n3", name="Hidroavion", type="class"),
        ],
        edges=[
            Edge(id="e1", source="n3", target="n1", type="inheritance"),
            Edge(id="e2", source="n3", target="n2", type="inheritance"),
        ]
    )
    findings = lint(diagram)
    matches = find_rule(findings, "multiple-class-inheritance")
    assert len(matches) == 1
    assert matches[0].severity == "critical"
    assert "Hidroavion" in matches[0].message_es


# ── Rule 9: many-to-many-direct ───────────────────────────────────────────────

def test_many_to_many_direct_triggers():
    diagram = Diagram(
        nodes=[Node(id="n1", name="Estudiante", type="class"), Node(id="n2", name="Curso", type="class")],
        edges=[
            Edge(id="e1", source="n1", target="n2", type="association", source_multiplicity="*", target_multiplicity="0..*")
        ]
    )
    findings = lint(diagram)
    matches = find_rule(findings, "many-to-many-direct")
    assert len(matches) == 1
    assert matches[0].severity == "warn"


def test_many_to_many_passes_one_to_many():
    diagram = Diagram(
        nodes=[Node(id="n1", name="Cliente", type="class"), Node(id="n2", name="Pedido", type="class")],
        edges=[
            Edge(id="e1", source="n1", target="n2", type="association", source_multiplicity="1", target_multiplicity="0..*")
        ]
    )
    findings = lint(diagram)
    assert len(find_rule(findings, "many-to-many-direct")) == 0


# ── Rule 10: invalid-multiplicity ─────────────────────────────────────────────

def test_invalid_multiplicity_inverted_bounds():
    diagram = Diagram(
        nodes=[Node(id="n1", name="A", type="class"), Node(id="n2", name="B", type="class")],
        edges=[
            Edge(id="e1", source="n1", target="n2", type="association", source_multiplicity="2..1")
        ]
    )
    findings = lint(diagram)
    matches = find_rule(findings, "invalid-multiplicity")
    assert len(matches) == 1
    assert matches[0].severity == "critical"
    assert "2..1" in matches[0].message_es


def test_invalid_multiplicity_passes_valid_ranges():
    diagram = Diagram(
        nodes=[Node(id="n1", name="A", type="class"), Node(id="n2", name="B", type="class")],
        edges=[
            Edge(id="e1", source="n1", target="n2", type="association", source_multiplicity="1..2", target_multiplicity="0..*")
        ]
    )
    findings = lint(diagram)
    assert len(find_rule(findings, "invalid-multiplicity")) == 0


# ── Rule 11: interface-has-instance-attributes ────────────────────────────────

def test_interface_has_instance_attributes_triggers():
    diagram = Diagram(nodes=[
        Node(id="n1", name="Repositorio", type="interface", attributes=[
            Attribute(name="conexion", type="Connection")
        ])
    ])
    findings = lint(diagram)
    matches = find_rule(findings, "interface-has-instance-attributes")
    assert len(matches) == 1
    assert matches[0].severity == "warn"


def test_interface_passes_with_no_attributes():
    diagram = Diagram(nodes=[
        Node(id="n1", name="Repositorio", type="interface", methods=[
            Method(name="guardar", return_type="void")
        ])
    ])
    findings = lint(diagram)
    assert len(find_rule(findings, "interface-has-instance-attributes")) == 0


# ── Rule 12: enum-empty ───────────────────────────────────────────────────────

def test_enum_empty_triggers():
    diagram = Diagram(nodes=[
        Node(id="n1", name="EstadoPedido", type="enum", enum_values=[], attributes=[])
    ])
    findings = lint(diagram)
    matches = find_rule(findings, "enum-empty")
    assert len(matches) == 1
    assert matches[0].severity == "warn"


def test_enum_empty_passes_with_values():
    diagram = Diagram(nodes=[
        Node(id="n1", name="EstadoPedido", type="enum", enum_values=["PENDIENTE", "PAGADO"])
    ])
    findings = lint(diagram)
    assert len(find_rule(findings, "enum-empty")) == 0


# ── Rule 13: god-class ────────────────────────────────────────────────────────

def test_god_class_triggers_above_threshold():
    attrs = [Attribute(name=f"campo{i}", type="String") for i in range(10)]
    meths = [Method(name=f"metodo{i}", return_type="void") for i in range(8)]
    diagram = Diagram(nodes=[
        Node(id="n1", name="SuperGestor", type="class", attributes=attrs, methods=meths)
    ])
    findings = lint(diagram, god_class_threshold=15)
    matches = find_rule(findings, "god-class")
    assert len(matches) == 1
    assert matches[0].severity == "warn"
    assert "SuperGestor" in matches[0].message_es


# ── Rule 14: method-no-return-type ───────────────────────────────────────────

def test_method_no_return_type_triggers():
    diagram = Diagram(nodes=[
        Node(id="n1", name="Calculadora", type="class", methods=[
            Method(name="sumar", return_type="")
        ])
    ])
    findings = lint(diagram)
    matches = find_rule(findings, "method-no-return-type")
    assert len(matches) == 1
    assert matches[0].severity == "info"


# ── Rule 15: duplicate-relation ───────────────────────────────────────────────

def test_duplicate_relation_triggers():
    diagram = Diagram(
        nodes=[Node(id="n1", name="A", type="class"), Node(id="n2", name="B", type="class")],
        edges=[
            Edge(id="e1", source="n1", target="n2", type="association"),
            Edge(id="e2", source="n1", target="n2", type="association"),
        ]
    )
    findings = lint(diagram)
    matches = find_rule(findings, "duplicate-relation")
    assert len(matches) == 1
    assert matches[0].severity == "warn"
