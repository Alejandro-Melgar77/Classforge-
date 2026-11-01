from .diagram_model import (
    Diagram,
    Node,
    Edge,
    Attribute,
    Method,
    from_graph_data,
    from_x6_json,
    from_xmi,
    from_ws_message,
)
from .lint import lint, Finding
from .roles import (
    RoleSkin,
    RoleDefinition,
    ROLES_REGISTRY,
    get_role,
    list_roles,
    build_role_persona_prompt,
)

__all__ = [
    "Diagram",
    "Node",
    "Edge",
    "Attribute",
    "Method",
    "from_graph_data",
    "from_x6_json",
    "from_xmi",
    "from_ws_message",
    "lint",
    "Finding",
    "RoleSkin",
    "RoleDefinition",
    "ROLES_REGISTRY",
    "get_role",
    "list_roles",
    "build_role_persona_prompt",
]
