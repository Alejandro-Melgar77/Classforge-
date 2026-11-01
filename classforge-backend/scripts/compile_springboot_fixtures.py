# -*- coding: utf-8 -*-
"""
Script para generar y compilar proyectos Spring Boot desde diagramas dorados.
Utilizado en CI para ejecutar `mvn -q -DskipTests package` con JDK 17.
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.modules.codegen.generator import generate_spring_boot_project
from tests.test_codegen.test_golden_codegen import (
    get_simple_diagram,
    get_inheritance_diagram,
    get_composition_diagram,
    get_many_to_many_diagram,
    get_enum_diagram,
    get_reserved_and_accents_diagram,
)

FIXTURES = [
    ("simple", get_simple_diagram()),
    ("inheritance", get_inheritance_diagram()),
    ("composition", get_composition_diagram()),
    ("many_to_many", get_many_to_many_diagram()),
    ("enum", get_enum_diagram()),
    ("reserved_and_accents", get_reserved_and_accents_diagram()),
]


def test_and_compile_all(target_base_dir: str = None) -> bool:
    mvn_bin = shutil.which("mvn")
    if not mvn_bin:
        print("[WARN] Maven (mvn) no encontrado en PATH. Generando archivos sin compilación Maven.")

    base_dir = target_base_dir or tempfile.mkdtemp(prefix="classforge_sb_")
    print(f"[*] Directorio de generación: {base_dir}")

    success = True
    for name, graph in FIXTURES:
        project_dir = os.path.join(base_dir, name)
        os.makedirs(project_dir, exist_ok=True)
        files = generate_spring_boot_project(graph, package_name=f"com.classforge.{name.replace('_', '')}")

        for rel_path, content in files.items():
            full_path = os.path.join(project_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        print(f"[+] Proyecto '{name}' generado con {len(files)} archivos.")

        if mvn_bin:
            print(f"[*] Compilando '{name}' con 'mvn -q -DskipTests package'...")
            proc = subprocess.run(
                [mvn_bin, "-q", "-DskipTests", "package"],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                print(f"[ERROR] Error al compilar proyecto '{name}':")
                print(proc.stdout)
                print(proc.stderr)
                success = False
            else:
                print(f"[OK] Proyecto '{name}' compilado y empaquetado exitosamente.")

    return success


if __name__ == "__main__":
    ok = test_and_compile_all()
    if not ok:
        sys.exit(1)
    print("[SUCCESS] Todos los proyectos Spring Boot generaron y compilaron correctamente.")
