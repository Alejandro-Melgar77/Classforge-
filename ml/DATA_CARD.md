# Data Card: ClassForge UML Synthetic Dataset

**Versión:** 1.0.0  
**Fecha:** 1 de noviembre de 2026  
**Tarea:** Traducción de Lenguaje Natural en Español/Inglés a Comandos JSON de Arquitectura UML (`UMLCommandResponse`).  
**Repositorio:** `ml/data/`

---

## 1. Puertas Legales (Bloque 0)

### 1.1. Términos del API de Gemini (Decisión sobre Profesor)
- **Análisis Legal:** Los Términos de Servicio Adicionales de Google Generative AI / Gemini API (Sección 3.2: Restricciones de Uso) establecen expresamente que el usuario no puede utilizar las salidas de los modelos de Gemini para entrenar o mejorar modelos de lenguaje de la competencia o servicios fundacionales sustitutivos.
- **Veredicto:** Conforme a la regla del Bloque 0.1 (*«Si no está claro o no se permite → no uses a Gemini como profesor»*), **GEMINI ESTÁ ESTRICTAMENTE EXCLUIDO COMO PROFESOR DE DESTILACIÓN O ENTRENAMIENTO**.
- **Metodología Adoptada:** El 100 % de los datos de entrenamiento y validación se genera **por construcción de oro (sintético determinista)** mediante el generador gramatical `gen_synthetic.py`, utilizando el esquema canónico de ClassForge, el motor heurístico determinista y permutaciones formales de plantillas con ruido de voz y mecanografía.

### 1.2. Licencia del Modelo Base
- **Modelo Base Seleccionado:** `Qwen/Qwen2.5-1.5B-Instruct` (Alibaba Cloud / Qwen Team).
- **Licencia:** **Apache 2.0** ([licencia oficial](https://github.com/QwenLM/Qwen2.5/blob/main/LICENSE)).
- **Permisos de la Licencia:** Permite expresamente uso comercial, modificación, ajuste fino (fine-tuning / LoRA), redistribución de pesos fusionados y conversión a formatos cuantizados (GGUF / llama.cpp) sin regalías.
- **Compatibilidad con P8a:** Corresponde exactamente a la familia de modelos servida en local por Ollama (`qwen2.5:1.5b`), garantizando compatibilidad de plantilla de chat (`<|im_start|>` / `<|im_end|>`) y tamaño en memoria (< 1.5 GB en cuantización Q4_K_M).

### 1.3. Datos de Usuarios de Producción
- **Política de Privacidad:** **Exclusión por defecto (Zero Data Leakage)**.
- Ningún diagrama, lienzo, chat de equipo ni texto ingresado por usuarios en producción forma parte del conjunto de entrenamiento ni de validación.
- El módulo de mejora continua (Bloque E) exige consentimiento explícito del proyecto (`allow_ai_feedback: true`), anonimización estricta (eliminación de correos, nombres de usuario, IPs y UUIDs de sesión) y una puerta de revisión humana antes de cualquier exportación a `feedback.jsonl`.

---

## 2. Composición y Estructura del Dataset

### 2.1. Dominios del Sistema (Total: 22 Dominios)
El dataset cubre exhaustivamente 22 dominios del mundo real, divididos formalmente en:
1. **Dominios de Entrenamiento (16 dominios):**
   - `ecommerce` (Comercio electrónico y carritos)
   - `banco` (Cuentas, transferencias, préstamos)
   - `universidad` (Estudiantes, docentes, materias, carreras)
   - `logistica` (Envíos, almacenes, rutas, transporte)
   - `biblioteca` (Libros, préstamos, autores, ejemplares)
   - `cine` (Películas, salas, funciones, entradas)
   - `hotel` (Habitaciones, reservas, huéspedes, servicios)
   - `restaurante` (Mesas, comandas, platos, meseros)
   - `farmacia` (Medicamentos, recetas, proveedores, lotes)
   - `inmobiliaria` (Propiedades, contratos, agentes, visitas)
   - `recursos_humanos` (Empleados, departamentos, nóminas, cargos)
   - `taller_mecanico` (Vehículos, órdenes de trabajo, repuestos, mecánicos)
   - `redes_sociales` (Publicaciones, perfiles, comentarios, seguidores)
   - `facturacion` (Facturas, detalles, impuestos, clientes)
   - `inventario` (Productos, almacenes, categorías, movimientos)
   - `gestion_proyectos` (Proyectos, tareas, sprints, asignaciones)
2. **Dominios Retenidos / Holdout (6 dominios - NUNCA en entrenamiento):**
   - `hospital` (Pacientes, médicos, citas, historiales clínicos)
   - `aerolinea` (Vuelos, aviones, aeropuertos, billetes)
   - `seguros` (Pólizas, siniestros, asegurados, coberturas)
   - `gimnasio` (Miembros, membresías, entrenadores, rutinas)
   - `veterinaria` (Mascotas, dueños, consultas, vacunas)
   - `streaming` (Series, episodios, usuarios, suscripciones)

### 2.2. Distribución de Ejemplos
| Partición | Formato | Ejemplos | Descripción |
|---|---|---|---|
| `train.jsonl` | Chat (`messages` + `meta`) | 4,200 | Entrenamiento QLoRA en los 16 dominios base |
| `val.jsonl` | Chat (`messages` + `meta`) | 600 | Validación durante entrenamiento (in-domain) |
| `holdout.jsonl` | Chat (`messages` + `meta`) | 600 | Evaluación fuera de dominio (6 dominios retenidos) |
| `golden.jsonl` | Benchmark estructurado | 160 | 160 casos dorados revisados a mano (cero entrenamiento) |
| `feedback.jsonl` | Chat / Correcciones | Variable | Cola de retroalimentación de usuarios con opt-in |

### 2.3. Acciones y Operaciones UML Soportadas
- `create_class`: Creación de una o varias clases con atributos tipados (`id:Long`, `precio:Double`, `fecha:Date`, etc.) y métodos.
- `create_relation`: Relaciones formales con cardinalidad y dirección:
  - `inheritance` (Herencia / generalización: "X hereda de Y", "X es un tipo de Y")
  - `composition` (Composición fuerte: "1 a 1..*", "1 a muchos", "rombo relleno")
  - `aggregation` (Agregación débil: "1 a 0..*", "rombo vacío")
  - `association` (Asociación simple: "0..* a 1", "muchos a muchos")
  - `dependency` (Dependencia: "X depende de Y", línea discontinua con flecha)
- `update_class`: Modificaciones en caliente (agregar atributo, agregar método, renombrar).
- `delete_element`: Eliminación de clases o relaciones del lienzo.
- `generate_system`: Plantillas completas de dominio (3 a 5 clases interconectadas).

### 2.4. Ruido de Voz y Errores de Tipeo (Robustez NLU)
El dataset incluye transformaciones programáticas para modelar entradas del mundo real:
- **Transcripción de voz:** Ausencia total de mayúsculas, omisión sistemática de tildes (`á` $\to$ `a`), ausencia de comas y signos de puntuación, frases orales como *"por favor crea una clase llamada..."*, *"asociame la clase cliente con factura"*.
- **Tipeo apresurado:** Sustitución de palabras clave por variantes frecuentes (`clse`, `claes`, `atribtos`, `relasionar`, `erencia`, `canpo`, `propiadad`).
- **Normalización esperada:** El modelo aprende a mapear estas variantes fonéticas al JSON canónico estricto con nombres en PascalCase y atributos en camelCase.

---

## 3. Esquema del Registro JSONL
Cada línea de los archivos de entrenamiento y validación cumple con la estructura estándar de chat:
```json
{
  "messages": [
    {
      "role": "system",
      "content": "Eres el asistente de ClassForge especializado en convertir lenguaje natural en comandos JSON estructurados de arquitectura UML."
    },
    {
      "role": "user",
      "content": "crear clase Factura con numero:string, fecha:date, total:double"
    },
    {
      "role": "assistant",
      "content": "{\"action\": \"create_class\", \"classes\": [{\"name\": \"Factura\", \"attributes\": [{\"name\": \"id\", \"type\": \"Long\", \"visibility\": \"+\"}, {\"name\": \"numero\", \"type\": \"String\", \"visibility\": \"+\"}, {\"name\": \"fecha\", \"type\": \"Date\", \"visibility\": \"+\"}, {\"name\": \"total\", \"type\": \"Double\", \"visibility\": \"+\"}], \"methods\": []}], \"relations\": [], \"deleted_elements\": [], \"explanation\": \"Clase Factura creada exitosamente con 4 atributo(s).\", \"source\": \"local\"}"
    }
  ],
  "meta": {
    "domain": "facturacion",
    "source": "synthetic_construction_v1",
    "version": "1.0.0",
    "has_noise": false
  }
}
```

---

## 4. Auditoría y Control de Calidad
1. **Validación de Esquema P3:** El 100 % de los comandos generados pasa la validación Pydantic `UMLCommandResponse`.
2. **Validación Linter:** Ninguna muestra contiene infracciones críticas de UML (sin ciclos de herencia, sin relaciones hacia clases inexistentes, sin cardinalidades invertidas).
3. **Deduplicación:** Deduplicación por hash SHA-256 del contenido normalizado de `user` prompt.
