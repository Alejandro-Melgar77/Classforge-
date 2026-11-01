#!/usr/bin/env python3
"""
scripts/run_ml_pipeline.py — Cross-platform runner for ClassForge ML pipeline (P8b).

Equivalent to `make -C ml data|train|eval|export`.
Works on Windows, Linux, and macOS without requiring GNU Make.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
ML_DIR = BASE_DIR / "ml"

def run_step(name: str, script_rel_path: str, extra_args: list[str] = None):
    script_path = ML_DIR / script_rel_path
    cmd = [sys.executable, str(script_path)] + (extra_args or [])
    print(f"\n============================================================")
    print(f"[*] EJECUTANDO ETAPA: {name}")
    print(f"    Comando: {' '.join(cmd)}")
    print(f"============================================================")
    res = subprocess.run(cmd, cwd=str(BASE_DIR))
    if res.returncode != 0:
        print(f"[!] ERROR en la etapa '{name}' (código de salida {res.returncode}).")
        sys.exit(res.returncode)
    print(f"[OK] Etapa '{name}' completada exitosamente.")

def main():
    parser = argparse.ArgumentParser(description="ClassForge ML Pipeline Orchestrator")
    parser.add_argument("stage", choices=["data", "train", "eval", "export", "feedback", "all"], default="all", nargs="?")
    args = parser.parse_args()

    stages = {
        "data": ("Generación de Datos Sintéticos (Bloque A)", "data/gen_synthetic.py", []),
        "train": ("Entrenamiento QLoRA / Dry-Run (Bloque B)", "train/train.py", ["--dry_run"]),
        "eval": ("Evaluación y Decisión Go/No-Go (Bloque C)", "eval/eval.py", []),
        "export": ("Exportación GGUF y Manifest Ollama (Bloque D)", "export/export_gguf.py", []),
        "feedback": ("Exportación de Feedback Humano (Bloque E)", "data/export_feedback.py", []),
    }

    if args.stage == "all":
        for s_key in ["data", "train", "eval", "export", "feedback"]:
            name, script, s_args = stages[s_key]
            run_step(name, script, s_args)
        print("\n" + "=" * 60)
        print("[*] PIPELINE ML REPRODUCIDO EXITOSAMENTE DE PUNTA A PUNTA")
        print("=" * 60)
    else:
        name, script, s_args = stages[args.stage]
        run_step(name, script, s_args)

if __name__ == "__main__":
    main()
