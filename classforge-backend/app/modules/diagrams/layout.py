"""
Deterministic UML Layout Engine for ClassForge (AI-LAYOUT-01).

Calculates an optimal, non-destructive, and deterministic distribution of nodes
in a UML class diagram without altering semantic data (IDs, names, attributes,
methods, types, relationships, multiplicities, or stereotypes).

Emits a sequence of typed 'move_node' operations compatible with the Phase 2
mutation engine (apply_operations).
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Set, Tuple


def _get_node_endpoint(endpoint: Any) -> str:
    if isinstance(endpoint, dict):
        return str(endpoint.get("cell") or endpoint.get("id") or "")
    return str(endpoint or "")


def calculate_auto_layout(
    graph_data: Dict[str, Any],
    start_x: float = 80.0,
    start_y: float = 80.0,
    gap_x: float = 90.0,
    gap_y: float = 110.0,
    default_node_width: float = 240.0,
    default_node_height: float = 160.0,
) -> List[Dict[str, Any]]:
    """
    Computes deterministic new positions for all nodes in the graph.
    
    Returns:
        List of 'move_node' operation dicts:
        [{"type": "move_node", "id": node_id, "patch": {"x": new_x, "y": new_y}}]
    """
    if not isinstance(graph_data, dict):
        return []

    nodes: List[Dict[str, Any]] = graph_data.get("nodes", [])
    edges: List[Dict[str, Any]] = graph_data.get("edges", [])

    if not nodes:
        return []

    # Filter valid nodes
    valid_nodes = [n for n in nodes if isinstance(n, dict) and isinstance(n.get("id"), str) and n.get("id")]
    if not valid_nodes:
        return []

    # Sort node list deterministically by ID to ensure strict reproducibility
    valid_nodes.sort(key=lambda n: str(n["id"]))
    node_ids = {n["id"] for n in valid_nodes}

    # If only 1 node, position at start coordinates if needed
    if len(valid_nodes) == 1:
        single_id = valid_nodes[0]["id"]
        return [{
            "type": "move_node",
            "id": single_id,
            "patch": {"x": float(start_x), "y": float(start_y)},
        }]

    # Build adjacency & hierarchy DAG
    # In UML, inheritance/generalization and realization go: child -> parent
    # In a top-to-bottom layout, parent should be at Layer 0 (top), child at Layer 1+ (bottom)
    parents_of: Dict[str, Set[str]] = {nid: set() for nid in node_ids}
    children_of: Dict[str, Set[str]] = {nid: set() for nid in node_ids}
    neighbors: Dict[str, Set[str]] = {nid: set() for nid in node_ids}

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        src = _get_node_endpoint(edge.get("source"))
        tgt = _get_node_endpoint(edge.get("target"))
        if src in node_ids and tgt in node_ids and src != tgt:
            neighbors[src].add(tgt)
            neighbors[tgt].add(src)
            edge_type = str(edge.get("type") or (edge.get("data") or {}).get("type") or "").lower()
            if edge_type in ("inheritance", "generalization", "realization"):
                # src is child, tgt is parent
                parents_of[src].add(tgt)
                children_of[tgt].add(src)

    # 1. Identify Connected Components
    visited_components: Set[str] = set()
    components: List[List[str]] = []

    for n in valid_nodes:
        nid = n["id"]
        if nid not in visited_components:
            comp: List[str] = []
            queue = [nid]
            visited_components.add(nid)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for nbr in sorted(neighbors.get(curr, set())):
                    if nbr not in visited_components:
                        visited_components.add(nbr)
                        queue.append(nbr)
            comp.sort()
            components.append(comp)

    # 2. Determine layer assignment for each component using Topological Ranking
    node_to_node_dict = {n["id"]: n for n in valid_nodes}
    node_dims: Dict[str, Tuple[float, float]] = {}

    for n in valid_nodes:
        nid = n["id"]
        size = n.get("size") if isinstance(n.get("size"), dict) else {}
        w = size.get("width", n.get("width", default_node_width))
        h = size.get("height", n.get("height", default_node_height))
        # Ensure dimensions are finite and positive
        w = float(w) if isinstance(w, (int, float)) and math.isfinite(w) and w > 0 else default_node_width
        h = float(h) if isinstance(h, (int, float)) and math.isfinite(h) and h > 0 else default_node_height
        node_dims[nid] = (w, h)

    operations: List[Dict[str, Any]] = []
    current_cluster_y = float(start_y)

    for comp in components:
        comp_set = set(comp)

        # Topological ranking inside component
        layer_map: Dict[str, int] = {}

        # Roots: nodes that have no parents within this component
        roots = [nid for nid in comp if not (parents_of.get(nid, set()) & comp_set)]
        if not roots:
            roots = [comp[0]]

        # Assign layers via BFS/Longest Path
        for r in roots:
            layer_map[r] = 0

        # Iteratively assign layer = max(layer(parent) + 1)
        changed = True
        iterations = 0
        while changed and iterations < len(comp) + 2:
            changed = False
            iterations += 1
            for nid in comp:
                parents_in_comp = parents_of.get(nid, set()) & comp_set
                if parents_in_comp:
                    max_p_layer = max(layer_map.get(p, 0) for p in parents_in_comp)
                    new_l = max_p_layer + 1
                    if layer_map.get(nid) != new_l:
                        layer_map[nid] = new_l
                        changed = True

        # Non-inheritance nodes in component: if unassigned or flat, assign based on neighbors
        for nid in comp:
            if nid not in layer_map:
                assigned_nbrs = [layer_map[nbr] for nbr in neighbors.get(nid, set()) if nbr in layer_map]
                layer_map[nid] = min(assigned_nbrs) if assigned_nbrs else 0

        # Group nodes by layer
        layers: Dict[int, List[str]] = {}
        for nid, l in layer_map.items():
            layers.setdefault(l, []).append(nid)

        sorted_layer_nums = sorted(layers.keys())

        # Layout each layer
        layer_y = current_cluster_y
        max_layer_width = 0.0

        for l_num in sorted_layer_nums:
            layer_nodes = sorted(layers[l_num])
            curr_x = float(start_x)
            max_h_in_layer = default_node_height

            for nid in layer_nodes:
                w, h = node_dims[nid]
                max_h_in_layer = max(max_h_in_layer, h)

                operations.append({
                    "type": "move_node",
                    "id": nid,
                    "patch": {
                        "x": round(curr_x, 1),
                        "y": round(layer_y, 1),
                    },
                })
                curr_x += w + gap_x

            max_layer_width = max(max_layer_width, curr_x)
            layer_y += max_h_in_layer + gap_y

        # Next component is separated vertically
        current_cluster_y = layer_y + 40.0

    return operations
