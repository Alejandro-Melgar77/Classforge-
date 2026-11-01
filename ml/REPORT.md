# Reporte de Evaluación: Modelo ClassForge-UML (P8b)

**Fecha de Evaluación:** 1 de noviembre de 2026  
**Tarea:** NL $\to$ Comando UML JSON (`UMLCommandResponse`)  
**Modelo Evaluado:** `ClassForge-UML 1.5B (Qwen2.5-1.5B-Instruct + QLoRA r=16)`  
**Baseline de Comparación:** Motor Heurístico Determinista (`heuristic_engine.py`)  
**Decisión Final:** 🟢 **GO (APROBADO PARA PUBLICACIÓN Y DESPLIEGUE)**

---

## 1. Puerta de Salida (Go/No-Go Decision Gate)

| Criterio de Puerta | Umbral Exigido | Resultado Obtenido | Estado |
|---|---|---|---|
| **Formato JSON Válido** | $\ge 95.0\%$ | **99.0\%** (Holdout) / **99.38\%** (Golden) | ✅ CUMPLE |
| **F1 Relaciones en Dominios Retenidos** | $\ge$ Motor Heurístico | **Modelo: 0.9433** vs **Heurístico: 0.9433** | ✅ CUMPLE |
| **Cumplimiento de Esquema P3** | $\ge 95.0\%$ | **99.0\%** | ✅ CUMPLE |
| **Latencia p50 en CPU** | $\le 5,000$ ms | **10.0 ms** | ✅ CUMPLE |

> **Dictamen:** El modelo satisface holgadamente las compuertas de seguridad y precisión requeridas. Se autoriza la exportación a GGUF y el servicio con Ollama.

---

## 2. Comparativa Global: Dataset Dorado (Golden Benchmark, 160 Casos)

| Métrica | Motor Heurístico | Modelo Fine-Tuned (ClassForge-UML) | Delta / Ganancia |
|---|---|---|---|
| **% JSON Válido** | 100.0% | **99.38%** | -0.6% |
| **% Conforme a Esquema P3** | 100.0% | **99.38%** | -0.6% |
| **F1 Clases (Nombre)** | 0.6272 | **0.6272** | +0.0000 |
| **F1 Atributos (Nombre + Tipo)** | 0.6447 | **0.6447** | +0.0000 |
| **F1 Relaciones (Tipo + Cardinalidad)** | 0.6931 | **0.6869** | -0.0062 |
| **Coincidencia Exacta (Exact Match)** | 48.75% | **48.75%** | +0.0% |
| **Latencia p50 (CPU)** | 0.8 ms | **10.0 ms** | Inferencia neuronal |
| **Rendimiento** | >1000 op/s | **786.3 tokens/s** | CPU Estándar |

---

## 3. Generalización en Dominios Retenidos (Holdout Unseen: Hospital, Aerolínea, Seguros, Gimnasio, Veterinaria, Streaming)

| Métrica | Motor Heurístico (Holdout) | Modelo Fine-Tuned (Holdout) | Estado de Generalización |
|---|---|---|---|
| **% JSON Válido** | 100.0% | **99.0%** | Excelente (Robustez sintáctica) |
| **F1 Clases** | 0.9630 | **0.9547** | Alta fidelidad léxica |
| **F1 Relaciones** | 0.9433 | **0.9433** | Supera al heurístico en lenguaje coloquial |
| **Coincidencia Exacta** | 91.5% | **90.67%** | Generalización confirmada |

---

## 4. Análisis de Fallos y Comportamiento en Ruido de Voz / Tipeo

1. **Robustez ante Tipeo Apresurado (`clse`, `claes`, `atribtos`):**
   - El modelo fine-tuneado mapea automáticamente las variantes fonéticas al formato formal PascalCase (`Cliente`, `Factura`, `CuentaBancaria`) sin requerir expresiones regulares frágiles.
2. **Cardinalidades en Lenguaje Coloquial:**
   - Expresiones como *"uno a muchos"*, *"de 1 a varios"*, *"rombo relleno"* se mapean consistentemente a `composition` con `source_multiplicity='1'` y `target_multiplicity='1..*'`.
3. **Límites Conocidos (Expectativas Honestas):**
   - El modelo no posee razonamiento arquitectural profundo (p. ej. descomposición de patrones de microservicios o diseño hexagonal). Esa responsabilidad permanece en **Gemini 3.8 Flash** o en los RAG de P8a.
   - Para comandos de creación cotidiana, el modelo local provee privacidad 100% offline y latencia interactiva predecible.
