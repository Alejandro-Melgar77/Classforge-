"""
Tests for P3 AI Chat Endpoints: Knowledge manifest (admin only),
global roles catalog with UI skins, and role contrast validation.
"""
import pytest
from httpx import AsyncClient
from bson import ObjectId

from app.core.database import db_instance
from app.core.security import create_access_token
from app.ai_team.domain.roles import list_roles, ROLES_REGISTRY


# ── Color Contrast Calculation Helper (WCAG AA >= 4.5:1) ───────────────────────

def _hex_to_rgb(hex_str: str) -> tuple[float, float, float]:
    hex_clean = hex_str.lstrip("#")
    r = int(hex_clean[0:2], 16) / 255.0
    g = int(hex_clean[2:4], 16) / 255.0
    b = int(hex_clean[4:6], 16) / 255.0
    return r, g, b


def _relative_luminance(r: float, g: float, b: float) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def calculate_contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculates WCAG relative luminance contrast ratio between two hex colors."""
    r1, g1, b1 = _hex_to_rgb(hex1)
    r2, g2, b2 = _hex_to_rgb(hex2)
    l1 = _relative_luminance(r1, g1, b1)
    l2 = _relative_luminance(r2, g2, b2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_all_role_skins_meet_contrast_requirements():
    """Requirement: contraste >= 4,5:1 (WCAG AA)."""
    for role in list_roles():
        skin = role.skin
        ratio = calculate_contrast_ratio(skin.text, skin.bg)
        assert ratio >= 4.5, (
            f"Role {role.id} skin contrast ratio {ratio:.2f} is below 4.5:1 between text {skin.text} and bg {skin.bg}"
        )


def test_all_role_skins_have_distinct_visual_identifiers():
    """Requirement: cada rol distinguible por color + icono + forma de burbuja (no solo color)."""
    icons = set()
    shapes = set()
    for role in list_roles():
        assert role.skin.icon, f"Role {role.id} must have an icon"
        assert role.skin.bubble_shape, f"Role {role.id} must have a bubble shape"
        icons.add(role.skin.icon)
        shapes.add(role.skin.bubble_shape)

    # Ensure icons and shapes are genuinely distinct across roles
    assert len(icons) == len(list_roles()), "Every role must have a distinct icon"
    assert len(shapes) >= 4, "Roles should use diverse bubble shapes"


# ── Endpoint Tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_knowledge_manifest_admin_only(async_client: AsyncClient, admin_token_headers):
    """Requirement: con tamaños en GET /api/v1/ai-chat/knowledge/manifest (solo admin)."""
    # 1. Anonymous request -> 401 Unauthorized
    resp = await async_client.get("/api/v1/ai-chat/knowledge/manifest")
    assert resp.status_code in (401, 403)

    # 2. Non-admin user -> 403 Forbidden
    db = db_instance.db
    dev_oid = ObjectId()
    await db["users"].insert_one({
        "_id": dev_oid,
        "name": "Dev User",
        "email": f"dev_{dev_oid}@example.com",
        "role": "dev",
        "is_active": True,
        "is_deleted": False,
        "team_ids": [],
    })
    dev_token = create_access_token(subject=str(dev_oid))
    resp = await async_client.get(
        "/api/v1/ai-chat/knowledge/manifest",
        headers={"Authorization": f"Bearer {dev_token}"}
    )
    assert resp.status_code == 403

    # 3. Admin user -> 200 OK with full manifest
    resp = await async_client.get(
        "/api/v1/ai-chat/knowledge/manifest",
        headers=admin_token_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_documents"] == 8
    assert data["total_bytes"] > 0
    assert data["total_tokens"] > 0
    assert len(data["documents"]) == 8
    assert any(d["filename"] == "00_producto.md" for d in data["documents"])
    assert any(d["filename"] == "10_modelo_uml.md" for d in data["documents"])


@pytest.mark.asyncio
async def test_global_roles_endpoint(async_client: AsyncClient, admin_token_headers):
    """Verifies that GET /api/v1/ai-chat/roles returns all roles and skins for frontend consumption."""
    resp = await async_client.get("/api/v1/ai-chat/roles", headers=admin_token_headers)
    assert resp.status_code == 200
    roles = resp.json()
    assert len(roles) >= 7
    role_ids = [r["id"] for r in roles]
    assert "architect" in role_ids
    assert "qa" in role_ids
    assert "tech_lead" in role_ids
    assert "mentor" in role_ids
    assert "dba" in role_ids
    assert "security" in role_ids
    assert "analyst" in role_ids

    for r in roles:
        assert "skin" in r
        assert "accent" in r["skin"]
        assert "icon" in r["skin"]
        assert "bubble_shape" in r["skin"]
        assert "triggers" in r
        assert len(r["triggers"]) > 0


@pytest.mark.asyncio
async def test_project_roles_includes_skin(async_client: AsyncClient, admin_token_headers):
    """Verifies that GET /api/v1/ai-chat/projects/{id}/roles includes skin and triggers."""
    db = db_instance.db
    proj_oid = ObjectId()
    admin_id = "507f1f77bcf86cd799439011"
    await db["projects"].insert_one({
        "_id": proj_oid,
        "name": "Proyecto Roles",
        "owner_id": admin_id,
        "is_deleted": False,
    })

    resp = await async_client.get(
        f"/api/v1/ai-chat/projects/{proj_oid}/roles",
        headers=admin_token_headers
    )
    assert resp.status_code == 200
    statuses = resp.json()
    assert len(statuses) >= 7
    for s in statuses:
        assert "role_id" in s
        assert "skin" in s
        assert s["skin"] is not None
        assert "icon" in s["skin"]
