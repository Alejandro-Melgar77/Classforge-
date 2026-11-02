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
