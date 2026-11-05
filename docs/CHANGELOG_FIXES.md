# CHANGELOG: Correcciones del Backend ClassForge

Este documento registra la resolución de todas las fallas verificadas del catálogo (C1–C7, A1–A36, M1–M12), organizadas por fases de corrección, junto con los cambios de contrato público y los hallazgos nuevos detectados.

---

## Resumen de Fases y Fallas Cerradas

### Fase 1: Desbloqueo y Arranque
- **C1**: Corrección de importación de `db_instance` en `app/main.py`. Se encapsuló el arranque del worker autónomo en `try/except` para garantizar que un fallo en el subsistema de IA nunca impida el arranque del API.
- **Tests**: `tests/test_startup.py` creado y pasando (3 pruebas verificando arranque limpio sin worker, con worker y tolerancia a fallos).

### Fase 2: Identidad, Autorización y Seguridad
- **C2**: Eliminada autopromoción a admin en `PUT /users/{id}`. Se restringió la modificación de `role`, `is_active` y `email` únicamente a usuarios con rol `admin` (403 para usuarios estándar).
- **C3**: Mitigado IDOR en carpetas. Añadida dependencia `require_folder_access` en `app/core/authz.py` y aplicada a `GET`, `PUT`, `DELETE` en `/api/v1/folders/{id}`.
- **A7**: `GET /users/` restringido exclusivamente a administradores (`require_role(["admin"])`). Creado el endpoint previo `GET /users/directory` con proyección mínima (`id`, `name`, `role`) filtrado por pertenencia a equipos para usuarios dev.
- **A8**: Rate limiter configurado en `app/core/middleware.py` para ignorar `X-Forwarded-For`, `CF-Connecting-IP` y `X-Real-IP` salvo que la conexión provenga directamente de una IP autorizada en `TRUSTED_PROXIES` (CIDR). Se retiró `--forwarded-allow-ips *` del `Dockerfile`.
- **A9**: `GET /auth/sessions` proyecta un DTO seguro `SessionPublic` sin exponer `refresh_token_hash`.
- **A10**: `POST /auth/refresh` valida que el usuario no esté deshabilitado (`is_active: false`), eliminado (`is_deleted: true`) ni inactivo más allá del umbral `INACTIVITY_TIMEOUT_MINUTES`. En caso de fallo revoca la sesión inmediatamente y responde 401.
- **A11**: Política de contraseñas de al menos 8 caracteres con validación de complejidad mínima en registro y creación administrativa (HTTP 422). `POST /auth/change-password` revoca todas las demás sesiones activas (`invalidate_all_except`).
- **A12**: Mitigación de SSRF en webhooks (`app/modules/codegen/webhook.py`): resolución DNS con validación de todas las IPs resueltas (rechaza loopback, privadas, link-local, reservadas, multicast, `::ffff:127.0.0.1`, enteros como `2130706433`, octal/hex y `127.0.0.1.nip.io`), con `follow_redirects=False`.
- **Tests**: `tests/test_auth/test_rbac_users.py`, `tests/test_folders/test_folder_isolation.py`.

### Fase 3: Errores Canónicos y Contrato HTTP
- **A1**: Mapeo canónico de excepciones nativas: `PermissionError` → 403 (`FORBIDDEN`), `ValueError` → 400 (`VALIDATION_ERROR`). Migrados los servicios correspondientes a excepciones de dominio.
- **A2**: Corregido `projects/service.py` importando `HTTPException` y homologando respuestas a 4xx.
- **A3**: `/ai/generate` y `/ai/generate-from-image` devuelven códigos HTTP 502/503 (`EXTERNAL_SERVICE_ERROR`) ante fallos upstream en lugar de 200 con `success:false`.
- **A21**: `gemini_generator.py` sanitizado: el fallback determinista no filtra el mensaje de excepción `str(e)` al cliente.
- **Tests**: `tests/test_errors/test_native_exception_mapping.py`, `tests/test_ai/test_error_status_codes.py`.

### Fase 4: Diagramas, Versionado y XMI
- **C4**: Corregida persistencia en `POST /ai/feedback` (`app/modules/ai/router.py`), guardando adecuadamente en la colección `ai_feedback` con anonimización de correos e IPs.
- **C5**: `POST /diagrams/{id}/from-image` adapta la salida de visión al esquema canónico (`nodes`, `edges`, `viewport`) garantizando `nodes` no vacío antes de persistir.
- **C6 & A36**: `POST /diagrams/{id}/import/xmi` valida el XML antes de tocar el diagrama; XML corrupto o grafo vacío rechaza con 400 sin modificar la base de datos. Se ejecuta `parse_xmi` en `run_in_threadpool` y se rechazan archivos superiores a 10 MB con HTTP 413.
- **C7**: Corrección de versionado off-by-one: `diagram.version` representa el snapshot actual. Cada guardado inserta `version = current + 1` conteniendo el grafo nuevo. Se creó el script `scripts/reconcile_diagram_versions.py` para reconciliación opcional de diagramas legados.
- **A6**: Exportación XMI serializa fielmente `interfaceNode` como `uml:Interface`, `enumNode` como `uml:Enumeration`, geometría (`x`, `y`, `width`, `height`), multiplicidades y `memberEnd`.
- **A14**: `DiagramService.list_diagrams` alineado con `can_access_diagram`, incluyendo diagramas de los proyectos y equipos del usuario.
- **A28**: Servicio de visión emite shapes soportados por el canvas (`classNode`, etc.).
- **M5**: Eliminada la lógica muerta de `xmi_data` forzado a `None`.
- **Tests**: `tests/test_ai/test_feedback_persistence.py`, `tests/test_diagrams/test_vision_contract.py`, `tests/test_diagrams/test_xmi_import_invalid.py`, `tests/test_diagrams/test_versioning_semantics.py`.

### Fase 5: Colaboración en Tiempo Real
- **A15**: `ROOM_STATE` incluye `locks`. La desconexión del último usuario en sala libera `locks` y `chat_history`. Validación de acceso al conectar por WS devuelve código 4003 si el recurso no es accesible.
- **A16**: Persistencia antes de difusión (`broadcast`) para evitar desincronización de clientes si la base de datos falla.
- **M7**: Tareas en segundo plano retenidas mediante `app/core/tasks.py` (`spawn`) con `add_done_callback` para evitar recolección por el GC.
- **M11**: Color de presencia de usuario calculado de forma determinista usando SHA1 sobre el identificador de usuario.
- **Tests**: `tests/test_collaboration/test_room_lifecycle.py`.

### Fase 6: Capa LLM y Resiliencia
- **A22**: `/ai/health` protegido con autenticación, rate limit y caché en memoria de 30 segundos.
- **A23**: Manejo explícito de HTTP 404 en Gemini (fail-fast sin agotar intentos inútiles pasando al siguiente modelo); 401/403 abren el breaker; `candidatesTokensDetails` soporta tanto `list` como `dict`.
- **A24**: `get_provider(purpose=...)` honra la cadena de enrutamiento `LLM_ROUTING` para `role_chat`, `vision` y `uml_command`.
- **A25**: Telemetría `ai_usage` desacoplada y no bloqueante, propagando `project_id` y `user_id`.
- **M6**: Eliminado `ollama_client.py` legado; `stream()` documentado con fallback entre modelos.
- **Tests**: `tests/test_llm/test_gemini_status_matrix.py`, `tests/test_llm/test_routing_by_purpose.py`.

### Fase 7: IA de Equipo y Chat
- **A4**: Eliminado el `create_task` duplicado en `send_message_with_role`; el worker autónomo (`AiWorker`) es la única vía de ejecución.
- **A5**: `AiMessageRepository.get_history` con `order="desc"` lee los últimos mensajes más recientes para generación de digests y resúmenes.
- **A29**: `DELETE /projects/{id}/tasks/{task_id}` restringido al creador de la tarea o administradores.
- **A30**: `POST /projects/{id}/messages/{msg_id}/proposals/{prop_id}/state` valida la existencia de la propuesta en el mensaje, respondiendo 404 si no existe.
- **A31**: `TriggersManager` unificado y desacoplado para compartir debounces de proyecto.
- **A32**: `ServerDiagramEditor` valida dependencias de relaciones antes de persistir, evitando enlaces huérfanos y preservando propiedades visuales del grafo.
- **A33**: `worker._execute_job` comprueba `AI_AUTONOMY_ENABLED` antes de procesar tareas encoladas.
- **A34**: Conteo total (`count_documents`) en repositorios de chat respeta los mismos filtros de la consulta.
- **A35**: Presupuesto de contexto de diagramas propagado correctamente en el constructor de prompts.
- **Tests**: `tests/test_ai_chat/test_single_execution.py`, `tests/test_ai_chat/test_digest_window.py`.

### Fase 8: NLU Heurístico
- **A26**: Prompts conversacionales o no reconocidos devuelven acción `unknown` sin inventar entidades espurias.
- **A27**: Inferencia de tipos corregida (`codigo` → `Long`, `creado` → `Date`); normalización de multiplicidades invertidas (e.g., `2..1` → `1..2`).
- **Tests**: `tests/test_ai/test_nlu_unknown.py`.

### Fase 9: Generación de Código
- **A19**: Archivos `.vscode/settings.json`, `.vscode/extensions.json` y `.vscode/launch.json` generan JSON sintácticamente válido (sin dobles llaves sin escapar).
- **A20**: Soporte completo para `interfaceNode` en Spring Boot y FastAPI; soporte para multiplicidades Many-to-Many tanto en estructura anidada canónica (`data.sourceMultiplicity`) como plana.
- **M10**: Validación previa de código Python con `compileall` antes de empaquetar el archivo ZIP entregado al usuario.
- **M12**: Bit de ejecución (`0o755`) preservado en `mvnw` y `run.sh` dentro del ZIP generado.
- **Tests**: `tests/test_codegen/test_vscode_json_valid.py`, `tests/test_codegen/test_interfaces_and_cardinality.py`.

### Fase 10: Auditoría, Notificaciones y Dashboard
- **A17**: Unificación de esquema de `audit_logs` con `created_at`, `resource`, `resource_id`, `metadata`. Dashboard adaptado para consumir `created_at` y `metadata`.
- **A18**: Notificaciones de proyecto corregidas para dirigir al `owner_id` y miembros activos, cubriendo asignación de participantes.
- **M4**: Idempotencia garantizada (marcar notificación leída dos veces o renombrar carpeta con el mismo nombre responde 200 sin lanzar 404).
- **M9**: Corrección de llamada a `log_audit` en `projects/service.py` con semántica `(user_id, action, resource, resource_id)`.
- **Tests**: `tests/test_audit/test_audit_schema.py`, `tests/test_notifications/test_fanout.py`.

### Fase 11: Reproducibilidad, Configuración e Infraestructura
- **M1**: `mongomock-motor>=0.0.34` agregado a `requirements.txt`.
- **M2**: `docker-compose.yml` configurado con `ENVIRONMENT=production`, variable `SECRET_KEY` obligatoria sin default inseguro, y MongoDB autenticado con usuario y contraseña.
- **M3**: `.env.example` actualizado con el bloque de variables P5 (`AI_AUTONOMY_ENABLED`, límites diarios y timeouts).
- **M6**: Eliminado `ollama_client.py`.
- **M8**: `Optional` verificado e importado en `dependencies.py`.
- **Higiene**: Directorio temporal `.tmp_test/` eliminado.

### Fase 4 (ClassForge 2.0): Chat Colaborativo, Agentes de IA, Ejecución Autónoma, Historial y Normalización Inteligente UML
- **AI-CHAT-01 & AI-CHAT-02**: Aislamiento estricto de hilos personales (`thread="personal"`, `owner_id`), impidiendo que usuarios lean conversaciones privadas ajenas. Historial de proyecto compartido (`/projects/{id}/history`) con visibilidad controlada (`visibility="team"`, `thread="project"`) y soporte para publicación voluntaria de mensajes privados al equipo mediante `POST /projects/{id}/messages/{id}/publish`.
- **H08**: Paginación robusta por cursor compuesto `(created_at, _id)` con codificación opaca `v2:` que previene la pérdida y duplicación de mensajes cuando múltiples registros comparten el mismo timestamp. Validación estricta que devuelve HTTP 400 ante cursores corruptos.
- **H09 & AI-TASK-01**: `AiJobRepository` con semántica de leases atómicos (`acquire_next`, `renew_lease`, `reap_expired_leases`, `cancel_job`). Renovación activa de leases durante procesamiento intensivo para prevenir reapings prematuros. Transición limpia a estado de error (`AUTONOMY_DISABLED`) para mensajes encolados cuando la autonomía está deshabilitada, impidiendo estados pendientes huérfanos. Deduplicación atómica por `active_dedupe_key`. Cancelación formal de tareas mediante `POST /projects/{id}/tasks/{id}/cancel` con aborto de trabajos asociados en `ai_jobs`.
- **AI-ROLE-01**: Roles y especialidades de agentes (`software_architect`, `tech_lead`, `backend_developer`, `qa_engineer`, `scrum_master`) con matriz de capacidades según la autonomía configurada en el proyecto (consultar vs proponer vs ejecutar autónomamente).
- **AI-PROP-01 & AI-EXEC-01**: Flujo de revisión integral (`pending` -> `approved` / `rejected` / `dismissed` -> `applied`). Endpoint `POST /messages/{id}/proposals/{id}/apply` que ejecuta las modificaciones a través del motor común de la Fase 2 (`apply_operations`), incrementa la versión del diagrama, genera snapshots en el historial de versiones, y previene condiciones de carrera con HTTP 409 Conflict si la versión base no coincide con la actual. Preservación garantizada del 100% de atributos y métodos existentes.
- **AI-LAYOUT-01**: Algoritmo estratificado y jerárquico determinista (`app/modules/diagrams/layout.py`) que posiciona superclases por encima de subclases en jerarquías de herencia/realización, previene colisiones mediante AABB y emite operaciones tipadas `move_node`. Endpoint `POST /diagrams/{id}/layout` con verificación de versión base y auditoría `AI_LAYOUT`.
- **AI-NORM-01**: Diagnóstico no destructivo (`app/modules/diagrams/normalization.py`) que detecta inconsistencias en nombres de clases (PascalCase), atributos/métodos (camelCase), mapeo de tipos a estándares UML canónicos, inversión de rangos de multiplicidad y atributos duplicados. Emisión de operaciones tipadas Phase 2 (`update_node`, `update_attribute`, `update_edge`) vía `POST /diagrams/{id}/normalization/apply` sin pérdida destructiva de datos.
- **AI-TRACE-01**: Registro de cada acción de IA (`AI_APPLY_PROPOSAL`, `AI_LAYOUT`, `AI_NORMALIZE`, etc.) en `audit_logs` con trazabilidad completa de actor, proyecto, diagrama, versiones anterior y nueva, y metadatos operativos.
- **AI-WEB-01**: Clientes de API en `AiTeamApiService` (`applyProposal`, `publishMessage`, `cancelTask`), métodos en `DiagramService` (`autoLayout`, `getNormalization`, `applyNormalization`), y toolbar interactiva (`canvas-toolbar.component.ts`) conectada al motor de layout con fallback offline automático.
- **Tests**: Suite completa en `tests/test_phase4/`: `test_chat_privacy_and_pagination.py`, `test_task_and_jobs_reliability.py`, `test_proposals_and_mutation.py`, `test_layout_and_normalization.py` (13 pruebas adicionales, 333 pruebas totales pasando al 100%).

### Fase 5 (ClassForge 2.0): Evaluador Inteligente Local de Proyectos, Análisis Documental, Entrenamiento Especializado y Generación de Informes PDF
- **PDF-01**: Almacenamiento seguro y validación estricta de documentos PDF (`uploads/project_reviews/{project_id}/{document_id}.pdf`). Verificación de firma mágica `%PDF-`, cálculo de digest criptográfico SHA-256, límite de tamaño (máx. 25 MB con HTTP 413), límite de páginas (máx. 300 páginas con HTTP 400), rechazo de archivos encriptados con contraseña, y protección contra ataques de path traversal.
- **PDF-02 & PDF-03**: Extractor estructurado por página (`pypdf`) con conteo de palabras, preservación de citas de página (`[Página X]`), detección de PDFs escaneados o sin capa de texto OCR (< 50 palabras -> `has_sufficient_text=False`), y mapeo semántico de secciones del proyecto de software (Alcance, Requisitos, Arquitectura/UML, Persistencia, Plan de Pruebas QA, Seguridad y Riesgos).
- **EVAL-01 & EVAL-02**: Rúbrica técnica estándar versionada `CF-SE-2026.1` con 6 criterios ponderados (sumatoria = 100.0) y umbral de aprobación de 70.0. Motor de evaluación híbrido inteligente local con defensa contra inyección de prompts (neutralización de directivas adversarias como "Ignore previous instructions" o intentos de forzar puntaje 100), integración con Ollama local (`qwen2.5:1.5b`) con fallback automático y transparente a motor semántico determinista de alta fidelidad sin dependencias de APIs en la nube.
- **EVAL-03**: Validación estricta de citas documentales y tasa de alucinación del 0.0%. Toda evidencia y cita de página corresponde fehacientemente a páginas existentes del documento analizado.
- **EVAL-04**: Generación de recomendaciones técnicas accionables y priorizadas (`HIGH`, `MEDIUM`, `LOW`) para cada criterio que no alcance el nivel óptimo, incluyendo título, descripción y plan de acción sugerido.
- **EVAL-05**: Generación y síntesis automática de pliego de especificaciones técnicas (`TechnicalSpecification`) para proyectos con dictamen `APROBADO`, detallando arquitectura multicapa, componentes, endpoints REST y modelo de datos relacional/NoSQL.
- **REPORT-01**: Motor de generación de reportes PDF de alta fidelidad (`reportlab`) con numeración de dos pasadas ("Página X de Y"), encabezados y pies de página corporativos, tabla de hallazgos por criterio, citas documentales, badge de dictamen y descarga independiente tanto del Dictamen Oficial como del Pliego de Especificaciones Técnicas.
- **HIST-01 & SEC-01**: Aislamiento estricto de documentos y evaluaciones por proyecto en MongoDB (`project_reviews`, `review_documents`). Numeración secuencial garantizada (`review_number` 1, 2, 3...) sin colisiones entre proyectos, y registro inmutable en `audit_logs` con acción `PROJECT_REVIEW_EVALUATED`.
- **ML-01, ML-02 & ML-03**: Dataset estructurado en `ml/data/reviews_dataset.jsonl` con 22 proyectos anotados exhaustivamente. Script de benchmark `ml/eval/eval_reviews.py` que arrojó 90.91% de exactitud, Macro F1 de 0.9048, 100% de validez de esquema y 103 ms de latencia media. Pipeline de entrenamiento LoRA en `ml/train/train_reviews_adapter.py` con diagnóstico honesto de hardware (CPU vs CUDA), manifiesto QLoRA completo y script exportado para GPU.
- **WEB-01**: Módulo en Angular 17 (`classforge-frontend`) con modelos TypeScript (`review.model.ts`), servicio REST (`project-reviews.service.ts`), componente interactivo (`project-reviews.component.ts`), navegación por pestañas en `project-center.component.ts` y ruta hija `evaluaciones` en `projects.routes.ts`.
- **QA-01**: Suite de pruebas integral en `classforge-backend/tests/test_phase5/` con 25 pruebas unitarias y de integración pasando al 100% (358 pruebas totales en backend, 92 pruebas en frontend).

### Fase 6 (ClassForge 2.0): Tutoriales Interactivos, Accesibilidad, Pruebas Integrales, Calidad y Preparación para Producción
- **H13 & UX-01**: Sistema integral de 10 tutoriales interactivos guiados en Angular 17 (`support-tour.service.ts`), filtrados dinámicamente por rol de usuario (`admin`, `scrum_master`, `dev`), con avance basado en acciones reales del usuario en el DOM (`actionType: 'click'`), desplazamiento suave con reintento automático y cancelación limpia sin modales residuales ni bloqueos de pantalla.
- **ACC-01 & UX-02**: Accesibilidad WCAG 2.2 AA y responsividad reforzada en `tour-overlay.component.html/.ts`: atajos de teclado globales (`Escape` para cancelar, flechas izquierda/derecha para navegación secuencial), atributos ARIA semánticos (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby`), y selectores `data-tour` estandarizados en el shell de navegación y la barra de herramientas del canvas UML.
- **SEC-01**: Suite de regresión de seguridad (`tests/test_phase6/test_security_regressions.py`) validando prevención de IDOR en proyectos y diagramas, acceso de auditoría para administradores, y neutralización estricta de directivas de prompt injection en documentos de entrada.
- **REL-01**: Pruebas de resiliencia y concurrencia (`tests/test_phase6/test_system_reliability.py`) verificando el ciclo de vida de leases de workers de IA (`acquire_next`, expiración, reaper con backoff y reactivación), contención y liberación de bloqueos colaborativos de elementos (`ConnectionManager`), e incremento atómico de versión con control estricto de concurrencia y prevención de conflictos (HTTP 409).
- **PERF-01**: Benchmarks reales de rendimiento (`tests/test_phase6/test_performance_benchmarks.py`): evaluación determinista de rúbrica con p50 < 15ms (p95 < 30ms), generación de reportes PDF de dictamen en < 20ms, y guardado de versiones de grafos UML con p50 < 5ms.
- **QA-01 a QA-05**: Flujo funcional de extremo a extremo verificado (`tests/test_phase6/test_flows_e2e.py`): modelado UML de clases, generación de código Spring Boot y prompts de frontend, análisis y evaluación documental con dictamen APROBADO, y emisión del reporte oficial en PDF.
- **DEPLOY-01**: Preparación para producción auditada y consolidada: healthchecks activos en `docker-compose.yml` para MongoDB (`mongosh`) y backend FastAPI (`curl`), orden de inicio coordinado (`condition: service_healthy`), contenedor no-root (`appuser`), y plantillas de configuración `.env.example` en la raíz y en el backend.
- **Resultados de Pruebas**: Backend: **369 pruebas pasando al 100%** (21.53s). Frontend: **98 pruebas pasando al 100%** (0.96s).

---

## Hallazgos Nuevos (No incluidos en el catálogo original)

1. **Crash en Dashboard por `KeyError: 'status'` y `KeyError: 'name'`**:
   - *Ubicación*: `app/modules/dashboard/router.py:113-114`.
   - *Problema*: Proyectos almacenados en MongoDB sin el campo explícito `status` o `name` producían un `KeyError` no capturado, provocando HTTP 500 en `/api/v1/dashboard/stats`.
   - *Corrección*: Uso de `.get("status", "active")` y `.get("name", "Sin nombre")`.

2. **Bypasses de SSRF en Webhook (`is_safe_webhook_url`)**:
   - *Ubicación*: `app/modules/codegen/webhook.py`.
   - *Problema*: La comprobación solo comparaba strings literales contra una lista estática. Pasaban enteros (`2130706433`), IPv4-mapped IPv6 (`::ffff:127.0.0.1`), octales/hexadecimales, y dominios DNS comodín (`127.0.0.1.nip.io`).
   - *Corrección*: Se incorporó parser tolerante de representaciones crudas de IP (`_try_parse_raw_ip`), verificación de `ip.ipv4_mapped`, resolución DNS con `socket.getaddrinfo` para validar todas las IPs de destino, y deshabilitación de redirecciones (`follow_redirects=False`) en `httpx.AsyncClient`.

3. **Código de estado incorrecto en subida XMI excedida**:
   - *Ubicación*: `app/modules/diagrams/router.py:282`.
   - *Problema*: Subidas de archivos XMI superiores a 10 MB lanzaban `ValidationError` (HTTP 400) en lugar de HTTP 413 (Payload Too Large).
   - *Corrección*: Lanzar `HTTPException(status_code=413, detail="El archivo XMI supera el límite de 10 MB")`.
