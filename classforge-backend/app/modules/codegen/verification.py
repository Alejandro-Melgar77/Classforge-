"""Post-generation sanity checks for Codegen (audit M10).

The API used to hand back a ZIP without ever checking that the generated
sources were syntactically valid. Python is cheap to verify in-process; Java
compilation requires a JDK and is delegated to the CI fixture job.
"""
from typing import Dict

from app.core.errors import ValidationError


def verify_generated_project(files: Dict[str, str]) -> None:
    """Compiles every generated Python file and raises 400 on invalid syntax."""
    for path, content in files.items():
        if not str(path).endswith(".py"):
            continue
        try:
            compile(content, path, "exec")
        except SyntaxError as exc:
            raise ValidationError(
                f"El proyecto generado contiene Python inválido en '{path}': {exc.msg}"
            ) from exc
