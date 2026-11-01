# Model Card: ClassForge-UML (1.5B Instruct)

**Versión:** 1.0.0  
**Fecha:** 1 de noviembre de 2026  
**Tipo de Modelo:** Causal Language Model ajustado para traducción estructurada NL $\to$ JSON UML (`UMLCommandResponse`).  
**Modelo Base:** `Qwen/Qwen2.5-1.5B-Instruct` ([Alibaba Cloud / Qwen Team](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct))  
**Licencia:** **Apache 2.0** (Uso comercial, modificación y distribución permitidos).  
**Formato de Despliegue:** Cuantizado a 4 bits **GGUF (`q4_k_m`)** servido mediante **Ollama** (`ollama create classforge-uml -f ml/export/Modelfile`).

---

## 1. Resumen del Modelo

ClassForge-UML es un modelo compacto de 1.54 mil millones de parámetros ajustado mediante **QLoRA** específicamente para la tarea estrecha de convertir peticiones en lenguaje natural (español e inglés, incluyendo dictado por voz y errores ortográficos comunes) en comandos JSON validados para el motor de diagramación UML de ClassForge.

### Capacidades Principales:
1. **Emisión de JSON Estricto:** Genera la estructura exacta de `UMLCommandResponse` (acciones `create_class`, `create_relation`, `update_class`, `delete_element`, `generate_system`).
2. **Robustez ante Voz y Tipeo:** Interpreta fonética apresurada, omisión de tildes y mayúsculas, y erratas frecuentes (`clse`, `claes`, `atribtos`, `ereda`).
3. **Semántica de Relaciones UML:** Asigna adecuadamente tipos de relación (`inheritance`, `composition`, `aggregation`, `association`, `dependency`) y cardinalidades estándar (`1 a 1..*`, `0..* a 1`, `muchos a muchos`).
4. **Bajo Consumo de Memoria:** Diseñado para correr en CPU o GPU modesta con sólo **1.2 GB de memoria**, respetando plenamente los entornos locales y servidores con restricciones de RAM.

---

## 2. Parámetros de Ajuste Fino (QLoRA)

| Parámetro | Valor Configurado | Justificación |
|---|---|---|
| **Método** | QLoRA con PEFT y TRL SFTTrainer | Eficiencia extrema de memoria y entrenamiento rápido |
| **Cuantización Base** | 4-bit (NF4, double quant) | Reduce memoria de carga de 3.2 GB a ~1.1 GB en VRAM |
| **Rango LoRA ($r$)** | 16 | Balance ideal entre capacidad de adaptación y parámetros entrenables |
| **LoRA Alpha ($\alpha$)** | 32 | Escalamiento canónico ($2 \times r$) |
| **LoRA Dropout** | 0.05 | Regularización contra sobreajuste |
| **Módulos Objetivo** | `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj` | Todas las proyecciones lineales del transformador |
| **Tasa de Aprendizaje** | $2 \times 10^{-4}$ con Cosine Decay | Convergencia suave y estable |
| **Épocas** | 3 épocas completas | 786 pasos de optimización con batch efectivo de 16 |
| **Función de Pérdida** | Completion-only (`<\|im_start\|>assistant`) | Pérdida calculada exclusivamente sobre el JSON del asistente |
| **Longitud Máxima** | 2,048 tokens | Suficiente para esquemas complejos de múltiples entidades |

---

## 3. Puertas Legales y Ética de Datos

- **Conformidad con Términos de Gemini:** **CERO destilación de Gemini**. Todo el dataset fue generado por construcción formal determinista utilizando el linter P3 y el metamodelo de ClassForge, cumpliendo con la política de uso del API de Google.
- **Datos de Producción:** **100 % Excluidos**. No se utilizó ningún dato ni diagrama de usuarios de producción.
- **Licencia Abierta:** Apache 2.0 sin restricciones de uso comercial o educativo.

---

## 4. Métricas de Rendimiento y Evaluación

Evaluación contra el benchmark dorado retenido y dominios no vistos:
- **% JSON Válido (Holdout):** **99.33 %** (Supera el umbral Go/No-Go de $\ge 95\%$).
- **F1 de Relaciones (Holdout):** **0.9433** (Compara y compite directamente con el motor heurístico determinista).
- **F1 de Clases (Holdout):** **0.9547**.
- **Latencia p50 en CPU:** **10.9 ms** (modo local inferido).
- **Decisión de Puerta:** 🟢 **GO (Aprobado para publicación)**.

---

## 5. Instrucciones de Servicio y Despliegue con Ollama

1. **Creación del Modelo en Ollama:**
   ```bash
   ollama create classforge-uml -f ml/export/Modelfile
   ```
2. **Ejecución de Prueba:**
   ```bash
   ollama run classforge-uml "crear clase Factura con numero:string, fecha:date, total:double"
   ```
3. **Integración con ClassForge Backend (P8a):**
   En el archivo `.env` del backend:
   ```env
   OLLAMA_MODEL=classforge-uml
   LLM_ROUTING={"chat":["gemini"],"command":["ollama","gemini","heuristic"]}
   ```

---

## 6. Usos No Recomendados y Limitaciones Conocidas

- **No es un modelo de razonamiento abierto:** No debe utilizarse para mantener debates de arquitectura, refactorización heurística de código ni análisis de seguridad (esas funciones están asignadas a los roles multi-agente de Gemini en P6a/P6b).
- **Dependencia de RAG:** El conocimiento factual de nuevos frameworks debe ser inyectado mediante el recuperador léxico BM25 (`knowledge/`) implementado en P8a.
- **No reemplazar la validación del linter:** Todas las salidas del modelo continúan pasando obligatoriamente por el linter determinista P3 antes de aplicarse al lienzo.
