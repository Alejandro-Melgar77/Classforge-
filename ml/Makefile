# Makefile — ClassForge ML Pipeline (P8b)
# Reproduce data generation, training, evaluation, and GGUF export from scratch.

PYTHON ?= python3

.PHONY: all data train eval export feedback clean help

help:
	@echo "ClassForge ML Pipeline Targets:"
	@echo "  make data     - Genera datasets sintéticos por construcción (train, val, holdout, golden)"
	@echo "  make train    - Ejecuta pipeline de ajuste fino QLoRA (o dry-run en CPU)"
	@echo "  make eval     - Ejecuta suite de evaluación y compuerta Go/No-Go sobre golden y holdout"
	@echo "  make export   - Fusiona LoRA, exporta GGUF y genera MANIFEST.json para Ollama"
	@echo "  make feedback - Exporta correcciones humanas anonimizadas a feedback.jsonl"
	@echo "  make all      - Ejecuta el ciclo completo data -> train -> eval -> export"

all: data train eval export

data:
	@echo "==> [P8b Bloque A] Generando datos sintéticos de oro..."
	$(PYTHON) data/gen_synthetic.py

train:
	@echo "==> [P8b Bloque B] Ejecutando pipeline de entrenamiento QLoRA..."
	$(PYTHON) train/train.py --dry_run

eval:
	@echo "==> [P8b Bloque C] Ejecutando evaluación y compuerta Go/No-Go..."
	$(PYTHON) eval/eval.py

export:
	@echo "==> [P8b Bloque D] Fusionando pesos y preparando exportación GGUF..."
	$(PYTHON) export/export_gguf.py

feedback:
	@echo "==> [P8b Bloque E] Exportando feedback humano..."
	$(PYTHON) data/export_feedback.py

clean:
	@echo "Limpiando artefactos temporales..."
	rm -rf train/output/*.safetensors train/output/*.bin export/*.gguf
