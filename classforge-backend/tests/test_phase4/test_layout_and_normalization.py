import pytest
from datetime import datetime, timezone
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from app.modules.diagrams.layout import calculate_auto_layout
from app.modules.diagrams.normalization import diagnose_normalization, build_normalization_operations
from app.modules.diagrams.operations import apply_operations
from app.modules.diagrams.service import DiagramService
from app.modules.diagrams.schemas import DiagramLayoutRequest, DiagramNormalizationApplyRequest
from app.core.errors import ConflictError


@pytest.mark.anyio
async def test_layout_deterministic_and_hierarchy():
    """
    Tests that calculate_auto_layout:
    - Places superclasses above subclasses in inheritance hierarchies.
    - Produces zero bounding box overlaps (AABB).
    - Is 100% deterministic (identical inputs yield identical outputs).
    - Preserves all node attributes, methods, and relationship data.
    """
    graph_data = {
        "nodes": [
            {
                "id": "node_vehicle",
                "shape": "uml-class",
                "position": {"x": 500, "y": 800},
                "data": {
                    "name": "Vehicle",
                    "attributes": [{"id": "v_id", "name": "vin", "type": "String", "visibility": "+"}],
                    "methods": [{"id": "v_start", "name": "startEngine", "return_type": "void", "visibility": "+"}]
                }
            },
            {
                "id": "node_car",
                "shape": "uml-class",
                "position": {"x": 100, "y": 100},
                "data": {
                    "name": "Car",
                    "attributes": [{"id": "c_doors", "name": "numDoors", "type": "Integer", "visibility": "+"}],
                    "methods": []
                }
            },
            {
                "id": "node_truck",
                "shape": "uml-class",
                "position": {"x": 900, "y": 100},
                "data": {
                    "name": "Truck",
                    "attributes": [{"id": "t_cap", "name": "payloadCapacity", "type": "Double", "visibility": "+"}],
                    "methods": []
                }
            }
        ],
        "edges": [
            {
                "id": "edge_car_veh",
                "shape": "uml-inheritance",
                "source": "node_car",
                "target": "node_vehicle",
                "data": {"type": "inheritance"}
            },
            {
                "id": "edge_truck_veh",
                "shape": "uml-inheritance",
                "source": "node_truck",
                "target": "node_vehicle",
                "data": {"type": "inheritance"}
            }
        ]
    }

    # Run layout twice to verify determinism
    ops1 = calculate_auto_layout(graph_data)
    ops2 = calculate_auto_layout(graph_data)
    assert ops1 == ops2, "Layout engine must be completely deterministic"
    assert len(ops1) == 3

    # Apply operations to obtain new positions
    new_graph = apply_operations(graph_data, ops1)

    node_map = {n["id"]: n for n in new_graph["nodes"]}
    veh_pos = node_map["node_vehicle"]["position"]
    car_pos = node_map["node_car"]["position"]
    truck_pos = node_map["node_truck"]["position"]

    # Hierarchy verification: Superclass (Vehicle) must be higher (smaller Y) than Subclasses (Car, Truck)
    assert veh_pos["y"] < car_pos["y"], "Vehicle superclass must be positioned above Car subclass"
    assert veh_pos["y"] < truck_pos["y"], "Vehicle superclass must be positioned above Truck subclass"

    # Collision-free verification: check bounding boxes do not overlap
    w, h = 240, 160
    for i, n1 in enumerate(new_graph["nodes"]):
        p1 = n1["position"]
        for j, n2 in enumerate(new_graph["nodes"]):
            if i >= j:
                continue
            p2 = n2["position"]
            overlap_x = abs(p1["x"] - p2["x"]) < (w + 20)
            overlap_y = abs(p1["y"] - p2["y"]) < (h + 20)
            assert not (overlap_x and overlap_y), f"Nodes {n1['id']} and {n2['id']} overlap"

    # Preservation check
    assert node_map["node_vehicle"]["data"]["name"] == "Vehicle"
    assert len(node_map["node_vehicle"]["data"]["attributes"]) == 1
    assert node_map["node_vehicle"]["data"]["methods"][0]["name"] == "startEngine"


@pytest.mark.anyio
async def test_normalization_diagnosis_and_apply():
    """
    Tests that:
    - diagnose_normalization detects class naming, member naming, types, and multiplicities.
    - build_normalization_operations creates typed Phase 2 operations.
    - apply_operations updates graph while preserving all existing untouched elements.
    """
    graph_data = {
        "nodes": [
            {
                "id": "node_1",
                "shape": "uml-class",
                "position": {"x": 100, "y": 100},
                "data": {
                    "name": "user_account",  # should be UserAccount
                    "attributes": [
                        {"id": "attr_1", "name": "UserName", "type": "str", "visibility": "+"},  # should be userName: String
                        {"id": "attr_2", "name": "user_email", "type": "varchar", "visibility": "+"},  # should be userEmail: String
                        {"id": "attr_3", "name": "user_email", "type": "varchar", "visibility": "+"}   # duplicate
                    ],
                    "methods": [
                        {"id": "m_1", "name": "validate_token", "return_type": "bool", "visibility": "+"}
                    ]
                }
            }
        ],
        "edges": [
            {
                "id": "edge_1",
                "shape": "uml-association",
                "source": "node_1",
                "target": "node_1",
                "data": {
                    "sourceMultiplicity": "2..1",  # inverted range -> 1..2
                    "targetMultiplicity": "*"       # * -> 0..*
                }
            }
        ]
    }

    # 1. Diagnose
    findings = diagnose_normalization(graph_data)
    rule_names = {f["rule"] for f in findings}
    assert "class-naming" in rule_names
    assert "member-naming" in rule_names
    assert "type-normalization" in rule_names
    assert "multiplicity-normalization" in rule_names
    assert "duplicate-attribute" in rule_names

    # 2. Build operations
    ops = build_normalization_operations(graph_data)
    assert len(ops) > 0

    # 3. Apply operations
    normalized_graph = apply_operations(graph_data, ops)
    norm_node = normalized_graph["nodes"][0]

    # Verify class name normalized to PascalCase
    assert norm_node["data"]["name"] == "UserAccount"

    # Verify attributes normalized to camelCase and standard UML types
    attr_map = {a["id"]: a for a in norm_node["data"]["attributes"]}
    assert attr_map["attr_1"]["name"] == "userName"
    assert attr_map["attr_1"]["type"] == "String"
    assert attr_map["attr_2"]["name"] == "userEmail"
    assert attr_map["attr_2"]["type"] == "String"

    # Verify methods were preserved
    assert len(norm_node["data"]["methods"]) == 1
    assert norm_node["data"]["methods"][0]["name"] == "validate_token"

    # Verify edges multiplicity normalized
    norm_edge = normalized_graph["edges"][0]
    assert norm_edge["data"]["sourceMultiplicity"] == "1..2"
    assert norm_edge["data"]["targetMultiplicity"] == "0..*"


@pytest.mark.anyio
async def test_layout_and_normalization_endpoints_with_conflict():
    """
    Tests router endpoints for layout and normalization:
    - Base version validation (409 Conflict on mismatch)
    - Audit log recording
    - Successful execution bumping version
    """
    from app.modules.diagrams.router import apply_diagram_layout, apply_diagram_normalization
    db = AsyncMongoMockClient().test
    service = DiagramService(db)

    diagram_id = str(ObjectId())
    user_id = str(ObjectId())
    current_user = {"_id": ObjectId(user_id), "role": "admin"}

    graph = {
        "nodes": [
            {
                "id": "node_order",
                "shape": "uml-class",
                "position": {"x": 50, "y": 50},
                "data": {"name": "order_record", "attributes": [{"id": "a1", "name": "order_id", "type": "int"}]}
            }
        ],
        "edges": []
    }

    await db.diagrams.insert_one({
        "_id": ObjectId(diagram_id),
        "name": "Order Model",
        "created_by": ObjectId(user_id),
        "version": 2,
        "is_deleted": False,
        "graph_data": graph,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    # 1. Base version mismatch for Layout -> ConflictError (409)
    req_layout_conflict = DiagramLayoutRequest(base_version=1)
    with pytest.raises(ConflictError):
        await apply_diagram_layout(
            diagram_id=diagram_id,
            data=req_layout_conflict,
            current_user=current_user,
            service=service,
        )

    # 2. Base version match for Layout -> Succeeds and bumps to version 3
    req_layout_ok = DiagramLayoutRequest(base_version=2)
    res_layout = await apply_diagram_layout(
        diagram_id=diagram_id,
        data=req_layout_ok,
        current_user=current_user,
        service=service,
    )
    assert res_layout.success is True
    assert res_layout.data["version"] == 3

    # Audit check
    audit_layout = await db.audit_logs.find_one({"action": "AI_LAYOUT"})
    assert audit_layout is not None
    assert audit_layout["metadata"]["old_version"] == 2
    assert audit_layout["metadata"]["new_version"] == 3

    # 3. Base version mismatch for Normalization -> ConflictError (409)
    req_norm_conflict = DiagramNormalizationApplyRequest(base_version=2)
    with pytest.raises(ConflictError):
        await apply_diagram_normalization(
            diagram_id=diagram_id,
            data=req_norm_conflict,
            current_user=current_user,
            service=service,
        )

    # 4. Base version match for Normalization -> Succeeds and bumps to version 4
    req_norm_ok = DiagramNormalizationApplyRequest(base_version=3)
    res_norm = await apply_diagram_normalization(
        diagram_id=diagram_id,
        data=req_norm_ok,
        current_user=current_user,
        service=service,
    )
    assert res_norm.success is True
    assert res_norm.data["version"] == 4
    assert res_norm.data["graph_data"]["nodes"][0]["data"]["name"] == "OrderRecord"

    # Audit check
    audit_norm = await db.audit_logs.find_one({"action": "AI_NORMALIZE"})
    assert audit_norm is not None
    assert audit_norm["metadata"]["old_version"] == 3
    assert audit_norm["metadata"]["new_version"] == 4
