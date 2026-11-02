"""Regression test for A19: Validate all generated .vscode/*.json files."""
import json
from app.modules.codegen.generator import generate_spring_boot_project


def _class_node(node_id, name):
    return {
        "id": node_id,
        "shape": "classNode",
        "data": {"name": name, "attributes": [], "methods": []},
    }


def test_all_three_vscode_json_files_parse_cleanly():
    """A19: .vscode/settings.json, .vscode/extensions.json, and .vscode/launch.json must parse as valid JSON."""
    graph = {"nodes": [_class_node("n1", "TestEntity")], "edges": []}
    files = generate_spring_boot_project(graph, package_name="com.test")

    vscode_files = [
        ".vscode/settings.json",
        ".vscode/extensions.json",
        ".vscode/launch.json",
    ]

    for path in vscode_files:
        assert path in files, f"Missing file: {path}"
        content = files[path]
        parsed = json.loads(content)
        assert isinstance(parsed, dict), f"{path} did not parse into a dict"
