# -*- coding: utf-8 -*-
"""
Pruebas doradas y de compilación real para los generadores de código de ClassForge.
Verifica:
1. Diagramas de prueba: simple, herencia, composición, muchos a muchos (N-N), enums, y nombres con tildes/reservadas.
2. Compilación real en FastAPI con compileall + importación dinámica + TestClient smoke test.
3. Validación estructural y sintáctica de Spring Boot 3.
4. Seguridad del generador: mitigación de Zip-Slip y límites de tamaño en zip_service.py.
5. Mitigación de SSRF en webhook.py.
"""
import compileall
import importlib.util
import os
import subprocess
import sys
import tempfile
import pytest
from fastapi.testclient import TestClient

from app.modules.codegen.fastapi_generator import generate_fastapi_project
from app.modules.codegen.generator import generate_spring_boot_project
from app.modules.codegen.zip_service import (
    create_project_zip,
    sanitize_zip_path,
    ZipSecurityError,
    MAX_FILE_BYTES
)
from app.modules.codegen.webhook import is_safe_webhook_url


# ── Fixtures de Diagramas Dorados ─────────────────────────────────────────────

def get_simple_diagram():
    return {
        "nodes": [
            {
                "id": "node-1",
                "type": "class",
                "data": {
                    "name": "Cliente",
                    "attributes": [
                        {"name": "nombre", "type": "string"},
                        {"name": "email", "type": "string"},
                        {"name": "telefono", "type": "string"},
                        {"name": "activo", "type": "bool"}
                    ]
                }
            }
        ],
        "edges": []
    }


def get_inheritance_diagram():
    return {
        "nodes": [
            {
                "id": "parent-1",
                "type": "class",
                "data": {
                    "name": "Persona",
                    "attributes": [
                        {"name": "nombre", "type": "string"},
                        {"name": "documento", "type": "string"}
                    ]
                }
            },
            {
                "id": "child-1",
                "type": "class",
                "data": {
                    "name": "Empleado",
                    "attributes": [
                        {"name": "salario", "type": "double"},
                        {"name": "cargo", "type": "string"}
                    ]
                }
            }
        ],
        "edges": [
            {
                "id": "edge-inh",
                "type": "inheritance",
                "source": "child-1",
                "target": "parent-1"
            }
        ]
    }


def get_composition_diagram():
    return {
        "nodes": [
            {
                "id": "c-1",
                "type": "class",
                "data": {
                    "name": "Factura",
                    "attributes": [
                        {"name": "numero", "type": "string"},
                        {"name": "total", "type": "double"}
                    ]
                }
            },
            {
                "id": "c-2",
                "type": "class",
                "data": {
                    "name": "ItemFactura",
                    "attributes": [
                        {"name": "descripcion", "type": "string"},
                        {"name": "cantidad", "type": "int"},
                        {"name": "precioUnitario", "type": "double"}
                    ]
                }
            }
        ],
        "edges": [
            {
                "id": "edge-comp",
                "type": "composition",
                "source": "c-1",
                "target": "c-2"
            }
        ]
    }


def get_many_to_many_diagram():
    return {
        "nodes": [
            {
                "id": "m-1",
                "type": "class",
                "data": {
                    "name": "Estudiante",
                    "attributes": [
                        {"name": "matricula", "type": "string"},
                        {"name": "nombreCompleto", "type": "string"}
                    ]
                }
            },
            {
                "id": "m-2",
                "type": "class",
                "data": {
                    "name": "Curso",
                    "attributes": [
                        {"name": "codigo", "type": "string"},
                        {"name": "titulo", "type": "string"}
                    ]
                }
            }
        ],
        "edges": [
            {
                "id": "edge-nn",
                "type": "manytomany",
                "source": "m-1",
                "target": "m-2",
                "data": {
                    "sourceMultiplicity": "*",
                    "targetMultiplicity": "*"
                }
            }
        ]
    }


def get_enum_diagram():
    return {
        "nodes": [
            {
                "id": "enum-1",
                "type": "enum",
                "data": {
                    "name": "EstadoOrden",
                    "attributes": [
                        {"name": "PENDIENTE"},
                        {"name": "PROCESANDO"},
                        {"name": "COMPLETADA"},
                        {"name": "CANCELADA"}
                    ]
                }
            },
            {
                "id": "node-order",
                "type": "class",
                "data": {
                    "name": "Pedido",
                    "attributes": [
                        {"name": "codigoSeguimiento", "type": "string"},
                        {"name": "estado", "type": "EstadoOrden"},
                        {"name": "montoTotal", "type": "double"}
                    ]
                }
            }
        ],
        "edges": []
    }


def get_reserved_and_accents_diagram():
    return {
        "nodes": [
            {
                "id": "res-1",
                "type": "class",
                "data": {
                    "name": "Categoría",
                    "attributes": [
                        {"name": "descripción", "type": "string"},
                        {"name": "año_fiscal", "type": "int"},
                        {"name": "class", "type": "string"},
                        {"name": "from", "type": "string"},
                        {"name": "import", "type": "string"},
                        {"name": "def", "type": "string"},
                        {"name": "precio", "type": "double"}
                    ]
                }
            },
            {
                "id": "res-2",
                "type": "class",
                "data": {
                    "name": "Orden",
                    "attributes": [
                        {"name": "código_postal", "type": "string"},
                        {"name": "order", "type": "string"},
                        {"name": "group", "type": "string"}
                    ]
                }
            }
        ],
        "edges": []
    }


# ── Pruebas de Compilación Real de FastAPI ─────────────────────────────────────

@pytest.mark.parametrize("diagram_factory,name", [
    (get_simple_diagram, "simple"),
    (get_inheritance_diagram, "herencia"),
    (get_composition_diagram, "composicion"),
    (get_many_to_many_diagram, "many_to_many"),
    (get_enum_diagram, "enum"),
    (get_reserved_and_accents_diagram, "reservadas_y_acentos"),
])
def test_fastapi_compilation_and_smoke(diagram_factory, name):
    graph = diagram_factory()
    files = generate_fastapi_project(graph)

    assert "app/main.py" in files
    assert "app/database.py" in files

    with tempfile.TemporaryDirectory() as temp_dir:
        for rel_path, content in files.items():
            full_path = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        # 1. compileall real: checks 100% of generated Python files for syntax errors
        compile_result = compileall.compile_dir(temp_dir, quiet=1, force=True)
        assert compile_result == 1, f"Fallo de compilación sintáctica en proyecto generado '{name}'"

        # 2. Dynamic import and smoke test of FastAPI app in clean isolated environment
        smoke_script = """
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
r1 = client.get('/')
assert r1.status_code == 200, f'Status {r1.status_code}'
assert r1.json()['status'] == 'online'
r2 = client.get('/health')
assert r2.status_code == 200
assert r2.json() == {'status': 'healthy'}
r3 = client.get('/docs')
assert r3.status_code == 200
print('SMOKE_TEST_SUCCESS')
"""
        proc = subprocess.run(
            [sys.executable, "-c", smoke_script],
            cwd=temp_dir,
            capture_output=True,
            text=True
        )
        assert proc.returncode == 0, f"Fallo al importar o ejecutar smoke test en '{name}':\\n{proc.stderr}\\n{proc.stdout}"
        assert "SMOKE_TEST_SUCCESS" in proc.stdout


# ── Pruebas de Generación de Spring Boot ────────────────────────────────────────

@pytest.mark.parametrize("diagram_factory,name", [
    (get_simple_diagram, "simple"),
    (get_inheritance_diagram, "herencia"),
    (get_composition_diagram, "composicion"),
    (get_many_to_many_diagram, "many_to_many"),
    (get_enum_diagram, "enum"),
    (get_reserved_and_accents_diagram, "reservadas_y_acentos"),
])
def test_spring_boot_generation_integrity(diagram_factory, name):
    graph = diagram_factory()
    package = "com.classforge.test"
    files = generate_spring_boot_project(graph, package_name=package)

    assert "pom.xml" in files
    assert "src/main/resources/application.yml" in files
    assert f"src/main/java/com/classforge/test/MainApplication.java" in files

    # Verify Enum generation if present
    if name == "enum":
        assert "src/main/java/com/classforge/test/entities/enums/EstadoOrden.java" in files
        enum_content = files["src/main/java/com/classforge/test/entities/enums/EstadoOrden.java"]
        assert "public enum EstadoOrden" in enum_content
        assert "PENDIENTE" in enum_content

    # Verify Inheritance if present
    if name == "herencia":
        persona_file = files["src/main/java/com/classforge/test/entities/Persona.java"]
        empleado_file = files["src/main/java/com/classforge/test/entities/Empleado.java"]
        assert "@Inheritance(strategy = InheritanceType.JOINED)" in persona_file
        assert "extends Persona" in empleado_file

    # Verify Many-to-Many if present
    if name == "many_to_many":
        est_file = files["src/main/java/com/classforge/test/entities/Estudiante.java"]
        curso_file = files["src/main/java/com/classforge/test/entities/Curso.java"]
        assert "@ManyToMany" in est_file or "@ManyToMany" in curso_file
        assert "@JoinTable" in est_file or "@JoinTable" in curso_file

    # Verify Accents and Reserved words sanitation
    if name == "reservadas_y_acentos":
        # Categoría -> Categoria
        assert "src/main/java/com/classforge/test/entities/Categoria.java" in files
        cat_content = files["src/main/java/com/classforge/test/entities/Categoria.java"]
        assert "valClass" in cat_content  # reserved keyword sanitized
        assert "valFrom" in cat_content
        assert "valImport" in cat_content
        assert "descripcion" in cat_content  # accent transliterated
        assert "anoFiscal" in cat_content


# ── Pruebas de Seguridad: Zip-Slip y Límites ───────────────────────────────────

def test_zip_path_sanitization_against_zip_slip():
    # Valid paths
    assert sanitize_zip_path("src/main/java/App.java") == "src/main/java/App.java"
    assert sanitize_zip_path("README.md") == "README.md"
    assert sanitize_zip_path("dir\\sub\\file.txt") == "dir/sub/file.txt"

    # Zip-Slip / Path Traversal attacks
    with pytest.raises(ZipSecurityError):
        sanitize_zip_path("../../../etc/passwd")

    with pytest.raises(ZipSecurityError):
        sanitize_zip_path("foo/../../bar")

    with pytest.raises(ZipSecurityError):
        sanitize_zip_path("/absolute/path")

    with pytest.raises(ZipSecurityError):
        sanitize_zip_path("C:\\Windows\\System32\\cmd.exe")


def test_zip_service_file_size_limit():
    huge_content = "X" * (MAX_FILE_BYTES + 1024)
    with pytest.raises(ZipSecurityError):
        create_project_zip({"huge.txt": huge_content})


# ── Pruebas de Seguridad: SSRF en Webhooks ─────────────────────────────────────

def test_webhook_ssrf_safety_checks():
    # Blocked targets (loopback, private networks, metadata)
    assert not is_safe_webhook_url("http://localhost:5678/webhook")
    assert not is_safe_webhook_url("http://127.0.0.1:8000/webhook")
    assert not is_safe_webhook_url("http://10.0.0.1/hook")
    assert not is_safe_webhook_url("http://192.168.1.1/hook")
    assert not is_safe_webhook_url("http://169.254.169.254/latest/meta-data")
    assert not is_safe_webhook_url("http://metadata.google.internal/computeMetadata/v1")
    assert not is_safe_webhook_url("ftp://example.com/file")
    assert not is_safe_webhook_url("")
    assert not is_safe_webhook_url(None)

    # Allowed public URLs
    assert is_safe_webhook_url("https://n8n.mycompany.com/webhook/test")
    assert is_safe_webhook_url("https://api.github.com/webhook")
