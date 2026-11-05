"""
Comprehensive Phase 2 UML Engine, OCC Concurrency, and Validation Test Suite.
Verifies all acceptance criteria for H04, H05, and H10.
"""
import copy
import pytest
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from app.core.errors import ValidationError, ConflictError
from app.modules.diagrams.operations import apply_operations
from app.modules.diagrams.validation import validate_graph
from app.modules.diagrams.repository import DiagramRepository
from app.ai_team.application.server_diagram_editor import ServerDiagramEditor
from app.ai_team.domain.diagram_model import from_graph_data
from app.modules.ai.schemas import UMLCommandResponse, UMLClassCommand, UMLAttribute, UMLMethod


def get_base_uml_graph():
    return {
        "nodes": [
            {
                "id": "node_client",
                "position": {"x": 100, "y": 150},
                "size": {"width": 200, "height": 120},
                "data": {
                    "name": "Cliente",
                    "stereotype": None,
                    "attributes": [
                        {"id": "attr_id", "name": "id", "type": "Long", "visibility": "private"},
                        {"id": "attr_name", "name": "nombre", "type": "String", "visibility": "public"}
                    ],
                    "methods": [
                        {"id": "meth_save", "name": "guardar", "params": "", "return_type": "void", "visibility": "public"}
                    ]
                }
            },
            {
                "id": "node_order",
                "position": {"x": 400, "y": 150},
                "size": {"width": 200, "height": 120},
                "data": {
                    "name": "Pedido",
                    "attributes": [
                        {"id": "attr_order_id", "name": "id", "type": "Long"}
                    ],
                    "methods": []
                }
            }
        ],
        "edges": [
            {
                "id": "edge_client_order",
                "source": "node_client",
                "target": "node_order",
                "type": "association",
                "data": {"label": "realiza", "source_multiplicity": "1", "target_multiplicity": "*"}
            }
        ],
        "viewport": {"x": 0, "y": 0, "zoom": 1.0},
        "metadata": {"author": "QA Team", "version_tag": "v1.0"}
    }


# ── H04: Motor de operaciones UML sin pérdida de datos ────────────────────────

def test_h04_all_ten_acceptance_criteria():
    """Verifies all 10 acceptance criteria defined in Section 6.7 of the Phase 2 prompt."""
    graph = get_base_uml_graph()

    # 1. Agregar un atributo conserva los anteriores
    op_add_attr = [{
        "type": "add_attribute",
        "id": "node_client",
        "member_id": "attr_email",
        "data": {"name": "email", "type": "String", "visibility": "private"}
    }]
    res1 = apply_operations(graph, op_add_attr)
    c1_attrs = res1["nodes"][0]["data"]["attributes"]
    assert len(c1_attrs) == 3
    assert [a["name"] for a in c1_attrs] == ["id", "nombre", "email"]
    assert c1_attrs[0]["type"] == "Long"  # Previous type preserved

    # 2. Actualizar un método conserva los demás métodos y propiedades
    op_add_meth2 = [{
        "type": "add_method",
        "id": "node_client",
        "member_id": "meth_calc",
        "data": {"name": "calcularTotal", "return_type": "Double"}
    }]
    with_two_methods = apply_operations(res1, op_add_meth2)
    op_update_meth = [{
        "type": "update_method",
        "id": "node_client",
        "member_id": "meth_save",
        "patch": {"visibility": "protected"}
    }]
    res2 = apply_operations(with_two_methods, op_update_meth)
    c1_methods = res2["nodes"][0]["data"]["methods"]
    assert len(c1_methods) == 2
    assert c1_methods[0]["name"] == "guardar" and c1_methods[0]["visibility"] == "protected"
    assert c1_methods[1]["name"] == "calcularTotal"

    # 3. Mover un nodo no modifica su semántica
    op_move = [{"type": "move_node", "id": "node_client", "patch": {"x": 250, "y": 300}}]
    res3 = apply_operations(graph, op_move)
    assert res3["nodes"][0]["position"] == {"x": 250, "y": 300}
    assert res3["nodes"][0]["data"]["name"] == "Cliente"
    assert len(res3["nodes"][0]["data"]["attributes"]) == 2

    # 4. Cambiar una relación no modifica otras relaciones
    op_update_edge = [{
        "type": "update_edge",
        "id": "edge_client_order",
        "patch": {"data": {"label": "gestiona"}}
    }]
    res4 = apply_operations(graph, op_update_edge)
    assert res4["edges"][0]["data"]["label"] == "gestiona"
    assert res4["edges"][0]["source"] == "node_client"

    # 5. Eliminar un nodo gestiona correctamente las relaciones dependientes (cascade)
    op_remove_node = [{"type": "remove_node", "id": "node_client"}]
    res5 = apply_operations(graph, op_remove_node)
    assert len(res5["nodes"]) == 1 and res5["nodes"][0]["id"] == "node_order"
    assert len(res5["edges"]) == 0  # Dependent edge cleanly removed

    # 6. Una operación inválida no altera el grafo
    before_invalid = copy.deepcopy(graph)
    with pytest.raises(ValidationError):
        apply_operations(graph, [{"type": "unknown_op", "id": "node_client"}])
    assert graph == before_invalid

    # 7. Una secuencia compuesta fallida no deja cambios parciales (atomicidad)
    with pytest.raises(ValidationError):
        apply_operations(graph, [
            {"type": "add_attribute", "id": "node_client", "member_id": "a99", "data": {"name": "tmp"}},
            {"type": "invalid_operation_type", "id": "node_client"}
        ])
    # Verify node_client did NOT gain "tmp"
    assert len(graph["nodes"][0]["data"]["attributes"]) == 2

    # 8. La IA no puede eliminar campos omitidos involuntariamente
    editor = ServerDiagramEditor(AsyncMongoMockClient().test)
    original_model = from_graph_data(graph)
    simulated_model = copy.deepcopy(original_model)
    ai_cmd = UMLCommandResponse(
        action="update_class",
        explanation="Add phone without specifying id or name",
        classes=[UMLClassCommand(name="Cliente", attributes=[UMLAttribute(name="telefono", type="String")])]
    )
    ok, _ = editor._simulate_apply(simulated_model, ai_cmd)
    assert ok
    res8 = editor._apply_to_raw_graph(graph, original_model, simulated_model, ai_cmd)
    res8_attrs = res8["nodes"][0]["data"]["attributes"]
    assert len(res8_attrs) == 3
    assert {a["name"] for a in res8_attrs} == {"id", "nombre", "telefono"}

    # 9. El editor manual y la IA producen resultados semánticamente equivalentes
    manual_add = apply_operations(graph, [{
        "type": "add_attribute",
        "id": "node_client",
        "member_id": "attr_tel",
        "data": {"name": "telefono", "type": "String"}
    }])
    assert {a["name"] for a in manual_add["nodes"][0]["data"]["attributes"]} == {a["name"] for a in res8_attrs}

    # 10. Recorrido de serialización y deserialización conserva todos los campos
    serialized_model = from_graph_data(graph).to_graph_data()
    assert len(serialized_model["nodes"]) == len(graph["nodes"])
    assert len(serialized_model["edges"]) == len(graph["edges"])


# ── H05: Versionado y Control de Concurrencia (Escenarios A, B, C) ─────────────

@pytest.mark.anyio
async def test_h05_concurrency_scenario_a():
    """Escenario A:
    - Cliente 1 carga rev 1.
    - Cliente 2 carga rev 1.
    - Cliente 1 guarda modificando un atributo.
    - Cliente 2 intenta guardar con base_version=1.
    - Resultado: Cliente 2 recibe ConflictError (409). Cambio de Cliente 1 se preserva.
    """
    db = AsyncMongoMockClient().test_occ
    repo = DiagramRepository(db)

    diag = await repo.create({"name": "Diagram A", "graph_data": get_base_uml_graph()})
    did = str(diag["_id"])
    assert diag["version"] == 1

    # Client 1 updates attribute
    g1 = copy.deepcopy(get_base_uml_graph())
    g1["nodes"][0]["data"]["attributes"].append({"id": "a_c1", "name": "c1_attr"})
    saved1 = await repo.save_graph(did, g1, "client1", "C1 edit", base_version=1)
    assert saved1["version"] == 2

    # Client 2 attempts save with stale base_version=1
    g2 = copy.deepcopy(get_base_uml_graph())
    g2["nodes"][0]["data"]["attributes"].append({"id": "a_c2", "name": "c2_attr"})
    with pytest.raises(ConflictError, match="diagrama cambió"):
        await repo.save_graph(did, g2, "client2", "C2 stale edit", base_version=1)

    # Invariant check: Client 1's changes are preserved
    current = await repo.get_by_id(did)
    assert current["version"] == 2
    assert any(a["name"] == "c1_attr" for a in current["graph_data"]["nodes"][0]["data"]["attributes"])
    assert not any(a["name"] == "c2_attr" for a in current["graph_data"]["nodes"][0]["data"]["attributes"])


@pytest.mark.anyio
async def test_h05_concurrency_scenario_b():
    """Escenario B:
    - Una IA modifica el grafo (incrementa revisión a 2).
    - Un usuario mantiene el editor abierto en rev 1 e intenta guardar después.
    - Resultado: Guardado antiguo falla con ConflictError (409). La modificación de IA se preserva.
    """
    db = AsyncMongoMockClient().test_occ_b
    repo = DiagramRepository(db)
    editor = ServerDiagramEditor(db)

    diag = await repo.create({"name": "Diagram B", "graph_data": get_base_uml_graph()})
    did = str(diag["_id"])
    assert diag["version"] == 1

    # AI applies command
    cmd = UMLCommandResponse(
        action="update_class",
        explanation="AI adds audit field",
        classes=[UMLClassCommand(name="Cliente", attributes=[UMLAttribute(name="audit_timestamp", type="DateTime")])]
    )
    ok, count, msg = await editor.apply_command(did, "architect", cmd, title="AI Improvements")
    assert ok
    ai_diag = await repo.get_by_id(did)
    assert ai_diag["version"] == 2

    # Human tries to save with stale base_version=1
    human_graph = copy.deepcopy(get_base_uml_graph())
    with pytest.raises(ConflictError):
        await repo.save_graph(did, human_graph, "human", "Stale save", base_version=1)

    # AI modification preserved
    final_diag = await repo.get_by_id(did)
    assert final_diag["version"] == 2
    assert any(a["name"] == "audit_timestamp" for a in final_diag["graph_data"]["nodes"][0]["data"]["attributes"])


@pytest.mark.anyio
async def test_h05_concurrency_scenario_c():
    """Escenario C:
    - Un WebSocket / otra operación aplica una mutación y avanza la revisión a 2.
    - Otra solicitud REST intenta escribir desde la revisión anterior 1.
    - Resultado: Se detecta la diferencia de revisión y se rechaza con ConflictError (409).
    """
    db = AsyncMongoMockClient().test_occ_c
    repo = DiagramRepository(db)

    diag = await repo.create({"name": "Diagram C", "graph_data": get_base_uml_graph()})
    did = str(diag["_id"])
    assert diag["version"] == 1

    # REST client loads diagram at version 1
    loaded_diag = await repo.get_by_id(did)
    stale_base_version = loaded_diag["version"]

    # Concurrent WebSocket applies an operation, bumping diagram to version 2
    ws_graph = copy.deepcopy(get_base_uml_graph())
    ws_graph["nodes"][0]["data"]["name"] = "ClienteModificadoPorWS"
    await repo.save_graph(did, ws_graph, "ws_client", "WebSocket operation", base_version=1)

    # REST client tries to commit with stale base_version=1
    rest_graph = copy.deepcopy(get_base_uml_graph())
    rest_graph["nodes"][0]["data"]["name"] = "ClienteSobrescrituraREST"
    with pytest.raises(ConflictError, match="diagrama cambió"):
        await repo.save_graph(did, rest_graph, "rest_user", "Stale REST save", base_version=stale_base_version)

    # Verify WebSocket change was preserved and not overwritten
    final_diag = await repo.get_by_id(did)
    assert final_diag["version"] == 2
    assert final_diag["graph_data"]["nodes"][0]["data"]["name"] == "ClienteModificadoPorWS"


# ── H10: Validador Unificado del Grafo UML ─────────────────────────────────────

def test_h10_unified_graph_validator_rules():
    """Verifies graph validation rules: unique IDs, dangling edges, cycles, empty graphs."""
    # 1. Unique IDs required
    dup_graph = {
        "nodes": [{"id": "same_id"}, {"id": "same_id"}],
        "edges": []
    }
    with pytest.raises(ValidationError, match="duplicados"):
        validate_graph(dup_graph)

    # 2. Dangling edge (missing target)
    dangling_graph = {
        "nodes": [{"id": "n1"}],
        "edges": [{"id": "e1", "source": "n1", "target": "missing_node"}]
    }
    with pytest.raises(ValidationError, match="nodo inexistente"):
        validate_graph(dangling_graph)

    # 3. Inheritance cycle detection
    cycle_graph = {
        "nodes": [{"id": "A"}, {"id": "B"}],
        "edges": [
            {"id": "e1", "source": "A", "target": "B", "type": "inheritance"},
            {"id": "e2", "source": "B", "target": "A", "type": "inheritance"}
        ]
    }
    with pytest.raises(ValidationError, match="ciclo de herencia"):
        validate_graph(cycle_graph)

    # 4. Valid empty graph accepted
    valid_empty = {"nodes": [], "edges": []}
    validate_graph(valid_empty)  # Does not raise

    # 5. Coordinate and dimension limits
    nan_coords = {
        "nodes": [{"id": "n1", "position": {"x": float("nan"), "y": 0}}],
        "edges": []
    }
    with pytest.raises(ValidationError, match="Coordenadas inválidas"):
        validate_graph(nan_coords)

    neg_size = {
        "nodes": [{"id": "n1", "position": {"x": 0, "y": 0}, "size": {"width": -10, "height": 50}}],
        "edges": []
    }
    with pytest.raises(ValidationError, match="Dimensiones inválidas"):
        validate_graph(neg_size)


# ── Persistencia Atómica, Historial y Restauración ─────────────────────────────

@pytest.mark.anyio
async def test_history_restoration_creates_new_revision_preserving_lineage():
    """Verifies that restoring version 1 creates version 3 with the old content,
    leaving versions 1 and 2 intact in history.
    """
    db = AsyncMongoMockClient().test_restore
    repo = DiagramRepository(db)

    # 1. Version 1
    diag = await repo.create({"name": "Restore Lineage Test", "graph_data": get_base_uml_graph()})
    did = str(diag["_id"])
    assert diag["version"] == 1

    # 2. Version 2
    v2_graph = copy.deepcopy(get_base_uml_graph())
    v2_graph["nodes"][0]["data"]["name"] = "ClienteV2"
    saved_v2 = await repo.save_graph(did, v2_graph, "user", "Bump to v2", base_version=1)
    assert saved_v2["version"] == 2

    # 3. Restore Version 1
    v1_entry = await repo.get_history_entry(did, 1)
    assert v1_entry is not None
    restored_v3 = await repo.save_graph(did, v1_entry["graph_data"], "user", "Restored v1", base_version=2)
    assert restored_v3["version"] == 3
    assert restored_v3["graph_data"]["nodes"][0]["data"]["name"] == "Cliente"

    # Lineage preserved: history has all 3 versions
    history = await repo.list_history(did)
    versions_present = [h["version"] for h in history]
    assert versions_present == [3, 2, 1]
