import pytest
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient

from app.modules.ai_chat.service import AiChatService
from app.modules.ai_chat.schemas import ProposalStateUpdateRequest


@pytest.mark.anyio
async def test_proposal_lifecycle_review():
    db = AsyncMongoMockClient().test
    service = AiChatService(db)

    project_id = str(ObjectId())
    user_id = str(ObjectId())
    msg_id = "msg_prop_review_test"
    prop_id = "prop_rev_1"

    # Seed team/project and message with pending proposal
    await db.ai_messages.insert_one({
        "_id": msg_id,
        "project_id": project_id,
        "thread": "project",
        "visibility": "team",
        "role": "assistant",
        "content": "Here is a proposal for your review",
        "proposals": [
            {
                "id": prop_id,
                "kind": "structure",
                "title": "Add Order entity",
                "rationale": "Missing persistence entity",
                "severity": "info",
                "state": {"status": "pending"},
            }
        ],
        "created_at": datetime.now(timezone.utc),
    })

    # 1. Approve proposal
    req_approve = ProposalStateUpdateRequest(status="approved")
    res_app = await service.update_proposal_state(project_id, msg_id, prop_id, req_approve, user_id=user_id)
    assert res_app["status"] == "approved"
    assert res_app["reviewed_by"] == user_id

    # 2. Reject proposal
    req_reject = ProposalStateUpdateRequest(status="rejected")
    res_rej = await service.update_proposal_state(project_id, msg_id, prop_id, req_reject, user_id=user_id)
    assert res_rej["status"] == "rejected"

    # 3. Dismiss proposal
    req_dismiss = ProposalStateUpdateRequest(status="dismissed")
    res_dis = await service.update_proposal_state(project_id, msg_id, prop_id, req_dismiss, user_id=user_id)
    assert res_dis["status"] == "dismissed"


@pytest.mark.anyio
async def test_proposal_apply_via_phase2_engine_and_audit():
    """
    Tests applying a proposal using the Phase 2 engine:
    - Mutates diagram graph safely
    - Preserves pre-existing attributes and methods
    - Increments version and creates history entry
    - Writes audit log with action 'AI_APPLY_PROPOSAL'
    - Updates proposal state to 'applied'
    """
    db = AsyncMongoMockClient().test
    service = AiChatService(db)

    project_id = str(ObjectId())
    user_id = str(ObjectId())
    diagram_id = str(ObjectId())
    msg_id = "msg_prop_apply_test"
    prop_id = "prop_apply_1"

    # 1. Seed diagram with existing class having attributes and methods
    initial_graph = {
        "nodes": [
            {
                "id": "node_customer",
                "shape": "uml-class",
                "position": {"x": 100, "y": 100},
                "data": {
                    "name": "Customer",
                    "attributes": [
                        {"id": "attr_id", "name": "id", "type": "Long", "visibility": "+"},
                        {"id": "attr_email", "name": "email", "type": "String", "visibility": "+"}
                    ],
                    "methods": [
                        {"id": "meth_login", "name": "login", "return_type": "Boolean", "visibility": "+"}
                    ]
                }
            }
        ],
        "edges": []
    }

    await db.diagrams.insert_one({
        "_id": ObjectId(diagram_id),
        "name": "E-Commerce Model",
        "project_id": ObjectId(project_id),
        "created_by": ObjectId(user_id),
        "version": 1,
        "is_deleted": False,
        "graph_data": initial_graph,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    # 2. Seed proposal with typed Phase 2 operations:
    # - Add new attribute to existing Customer class
    # - Add a new Invoice class
    operations = [
        {
            "type": "add_attribute",
            "id": "node_customer",
            "member_id": "attr_phone",
            "data": {"id": "attr_phone", "name": "phone", "type": "String", "visibility": "+"}
        },
        {
            "type": "add_node",
            "id": "node_invoice",
            "data": {
                "id": "node_invoice",
                "shape": "uml-class",
                "position": {"x": 400, "y": 100},
                "data": {
                    "name": "Invoice",
                    "attributes": [
                        {"id": "attr_inv_id", "name": "id", "type": "Long", "visibility": "+"}
                    ],
                    "methods": []
                }
            }
        }
    ]

    await db.ai_messages.insert_one({
        "_id": msg_id,
        "project_id": project_id,
        "diagram_id": diagram_id,
        "thread": "project",
        "visibility": "team",
        "role": "assistant",
        "content": "Proposed additions to Customer model",
        "proposals": [
            {
                "id": prop_id,
                "kind": "structure",
                "title": "Add Phone and Invoice",
                "rationale": "Requirement for billing module",
                "severity": "info",
                "operations": operations,
                "state": {"status": "pending"},
            }
        ],
        "created_at": datetime.now(timezone.utc),
    })

    # 3. Apply proposal with base_version=1
    result = await service.apply_proposal(
        project_id=project_id,
        message_id=msg_id,
        proposal_id=prop_id,
        user_id=user_id,
        diagram_id=diagram_id,
        base_version=1,
    )
    assert result["success"] is True
    assert result["status"] == "applied"
    assert result["version"] == 2

    # 4. Verify diagram in db
    updated_diag = await db.diagrams.find_one({"_id": ObjectId(diagram_id)})
    assert updated_diag["version"] == 2
    nodes = updated_diag["graph_data"]["nodes"]
    assert len(nodes) == 2

    # Verify Customer preserved existing attributes AND got new attribute
    customer_node = next(n for n in nodes if n["id"] == "node_customer")
    customer_attrs = customer_node["data"]["attributes"]
    attr_names = [a["name"] for a in customer_attrs]
    assert "id" in attr_names
    assert "email" in attr_names
    assert "phone" in attr_names, "New attribute 'phone' must be added"

    # Verify existing method is preserved
    customer_methods = customer_node["data"]["methods"]
    assert len(customer_methods) == 1
    assert customer_methods[0]["name"] == "login"

    # 5. Verify audit log entry
    audit = await db.audit_logs.find_one({"action": "AI_APPLY_PROPOSAL"})
    assert audit is not None
    assert audit["metadata"]["proposal_id"] == prop_id
    assert audit["metadata"]["old_version"] == 1
    assert audit["metadata"]["new_version"] == 2

    # 6. Verify message proposal state is updated
    msg_after = await db.ai_messages.find_one({"_id": msg_id})
    prop_after = msg_after["proposals"][0]
    assert prop_after["state"]["status"] == "applied"


@pytest.mark.anyio
async def test_proposal_stale_base_revision_conflict_409():
    """
    Verifies that applying a proposal against a stale base revision
    raises HTTP 409 Conflict and makes zero mutations.
    """
    db = AsyncMongoMockClient().test
    service = AiChatService(db)

    project_id = str(ObjectId())
    user_id = str(ObjectId())
    diagram_id = str(ObjectId())
    msg_id = "msg_prop_conflict_test"
    prop_id = "prop_conflict_1"

    # Diagram is already at version 3
    await db.diagrams.insert_one({
        "_id": ObjectId(diagram_id),
        "name": "Model V3",
        "project_id": ObjectId(project_id),
        "created_by": ObjectId(user_id),
        "version": 3,
        "is_deleted": False,
        "graph_data": {"nodes": [], "edges": []},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    # Proposal created when diagram was at version 1
    await db.ai_messages.insert_one({
        "_id": msg_id,
        "project_id": project_id,
        "diagram_id": diagram_id,
        "thread": "project",
        "visibility": "team",
        "role": "assistant",
        "content": "Old proposal",
        "proposals": [
            {
                "id": prop_id,
                "kind": "structure",
                "title": "Add Entity",
                "rationale": "Old requirement",
                "operations": [{"type": "add_node", "node": {"id": "n1", "shape": "uml-class", "data": {"name": "Test"}}}],
                "state": {"status": "pending"},
            }
        ],
        "created_at": datetime.now(timezone.utc),
    })

    # Attempting to apply with base_version=1 must raise HTTP 409
    with pytest.raises(HTTPException) as exc_info:
        await service.apply_proposal(
            project_id=project_id,
            message_id=msg_id,
            proposal_id=prop_id,
            user_id=user_id,
            diagram_id=diagram_id,
            base_version=1,
        )
    assert exc_info.value.status_code == 409

    # Verify diagram remains unchanged at version 3
    diag = await db.diagrams.find_one({"_id": ObjectId(diagram_id)})
    assert diag["version"] == 3

    # Verify proposal remains pending
    msg = await db.ai_messages.find_one({"_id": msg_id})
    assert msg["proposals"][0]["state"]["status"] == "pending"
