"""Codegen regressions (audit A19, A20, M10, M12)."""
import io
import json
import zipfile

import pytest

from app.core.errors import ValidationError
from app.modules.codegen.fastapi_generator import generate_fastapi_project
from app.modules.codegen.generator import generate_spring_boot_project
from app.modules.codegen.verification import verify_generated_project
from app.modules.codegen.zip_service import create_project_zip


def _class_node(node_id, name, attrs=None):
    return {
        "id": node_id,
        "shape": "classNode",
        "data": {"name": name, "attributes": attrs or [], "methods": []},
    }


def _graph(nodes, edges=None):
    return {"nodes": nodes, "edges": edges or []}


def test_vscode_json_files_are_valid():
    """A19: settings/extensions used to be emitted with '{{' and '}}'."""
    files = generate_spring_boot_project(_graph([_class_node("n1", "Usuario")]), package_name="com.demo")

    for path in (".vscode/settings.json", ".vscode/extensions.json", ".vscode/launch.json"):
        json.loads(files[path])  # must not raise


def test_interface_node_is_not_dropped():
    """A20: interfaceNode was filtered out and its realization silently lost."""
    graph = _graph([
        _class_node("n1", "Usuario"),
        {"id": "n2", "shape": "interfaceNode", "data": {"name": "Auditable", "attributes": [], "methods": []}},
    ], [
        {"id": "e1", "source": "n1", "target": "n2", "type": "realization"},
    ])

    spring = generate_spring_boot_project(graph, package_name="com.demo")
    fastapi = generate_fastapi_project(graph)

    assert any("Auditable" in path for path in spring)
    assert any("auditable" in path.lower() for path in fastapi)


def test_many_to_many_with_flat_multiplicities():
    """A20: flat multiplicities (source_multiplicity) must not collapse N-N."""
    graph = _graph([
        _class_node("n1", "Estudiante"),
        _class_node("n2", "Curso"),
    ], [
        {"id": "e1", "source": "n1", "target": "n2", "type": "association",
         "source_multiplicity": "*", "target_multiplicity": "*"},
    ])

    spring = generate_spring_boot_project(graph, package_name="com.demo")
    joined = "\n".join(spring.values())
    assert "@ManyToMany" in joined

    fastapi = generate_fastapi_project(graph)
    fastapi_joined = "\n".join(fastapi.values())
    assert "Table(" in fastapi_joined
    assert "secondary=" in fastapi_joined


def test_zip_marks_shell_scripts_executable():
    """M12: run.sh/mvnw must keep the executable bit inside the archive."""
    files = {"run.sh": "#!/bin/sh\necho hi\n", "mvnw": "#!/bin/sh\n", "README.md": "# x"}
    blob = create_project_zip(files, root_dir="proj")

    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        modes = {info.filename: (info.external_attr >> 16) & 0o777 for info in zf.infolist()}

    assert modes["proj/run.sh"] == 0o755
    assert modes["proj/mvnw"] == 0o755
    assert modes["proj/README.md"] == 0o644


def test_generated_python_is_verified_before_delivery():
    """M10: invalid generated Python must be rejected, not zipped."""
    with pytest.raises(ValidationError):
        verify_generated_project({"app/main.py": "def broken(:\n"})

    # Valid output passes.
    verify_generated_project(generate_fastapi_project(_graph([_class_node("n1", "A")])))
