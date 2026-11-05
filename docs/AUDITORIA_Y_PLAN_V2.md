# ClassForge 2.0: auditoría funcional y plan de refactorización del backend

Fecha: 2026-11-04. Código base: commit `8e7ff4b`.

## Dictamen y alcance

Los siete requisitos no están completamente satisfechos. Existen módulos aprovechables, pero hay defectos de aislamiento, pérdida de datos, sincronización y funciones ausentes. El estado documental «PRODUCCIÓN / ESTABLE» no certifica estos requisitos.

Se revisaron rutas, servicios, repositorios, autorización, colaboración, cola y editor de IA, proveedores, entrenamiento y los recorridos relevantes en Angular y Flutter. Esta es una auditoría enfocada, no una prueba exhaustiva de cada línea ni una certificación UML 2.5 completa.

Verificación ejecutada:

- Suite backend: **274 passed, 13 warnings, 18.70 s**. Se forzó `MONGODB_URL=mongodb://127.0.0.1:1` y `DATABASE_NAME=classforge_audit_20261104` para usar el fallback de MongoDB simulado sin tocar datos reales.
- Siete reproducciones adicionales en `docs/audit_v2_probes.py`, todas confirmadas en memoria. No contactan proveedores ni bases reales. Sus asserts documentan el comportamiento defectuoso actual: no deben integrarse como pruebas positivas de CI.
- No se ejecutaron Angular/Flutter, navegadores múltiples, reconocimiento de voz real, Gemini, Ollama, entrenamiento ni pruebas de carga sobre MongoDB real. Responsividad, accesibilidad, FPS, latencias y exactitud generativa quedan pendientes de validación dinámica.

## Matriz de requisitos

| Requisito | Estado observado | Brecha para aceptación |
|---|---|---|
| 1. UML y generación por texto, voz e imagen | Parcial: canvas, NLU, visión, exportación y generación existen | Validación del grafo no uniforme; aplicación de comandos incompleta; ensayo visual responsive y fidelidad UML pendientes |
| 2. Colaboración | Parcial: operaciones WS, presencia, locks y persistencia | Guardados compiten sin revisión base; IA publica antes de persistir; guardados REST/imagen no producen el mismo evento de sincronización |
| 3. Tutorial inmersivo | Parcial: seis tours predefinidos en Angular | No cubren todo el entorno; varios solo tienen un paso; avance no valida la acción realizada; elementos ausentes terminan en un popover sin objetivo |
| 4. Evaluador local entrenado con entrada/salida PDF | No encontrado como flujo funcional | Ollama y entrenamiento UML no equivalen a evaluar proyectos; faltan ingestión PDF, rúbrica, dictamen, especificación e informe PDF |
| 5. Chat personal e historial grupal | Implementado con defectos | Dos escapes de aislamiento; paginación puede omitir mensajes; credenciales quedan en jobs; consistencia de cola/mensajes por reforzar |
| 6. Móvil: registro, consulta, cambios por voz | Incompleto | No se encontró registro en `lib`; la voz solicita interpretación, pero el backend no aplica cambios y el cliente anuncia éxito sin comprobarlo |
| 7. IA con roles y tareas, modificación y reorganización | Parcial | Roles, jobs y modo apply existen; comandos parciales destruyen datos; no existe una operación de layout en el contrato revisado; invocación de chat no equivale a ejecución de cambios |

«Parcial» significa que hay implementación, no que el recorrido completo haya sido demostrado en producción.

## Hallazgos priorizados

P0: corregir antes de aceptar datos de distintos equipos o usar IA sobre proyectos reales. P1: bloquea la aceptación funcional de v2. P2: robustez, experiencia y mantenimiento.

### H01 — P0 — Contexto de otro proyecto en chat IA (reproducido)

`classforge-backend/app/modules/ai_chat/service.py:551`, `_get_diagram`: si se recibe un `diagram_id`, busca únicamente por `_id`, sin comprobar `project_id` ni borrado. La autorización del router sobre el proyecto A no protege ese recurso de B. El resultado se usa como contexto de la respuesta.

Corrección: exigir proyecto, usuario y diagrama en toda resolución de contexto; filtrar proyecto y estado en la consulta; rechazar 404/403 en lugar de sustituir silenciosamente por otro diagrama. Revisar también el constructor de contexto legado y tareas/revisiones que resuelven diagramas por ID.

Aceptación: un miembro de A no puede introducir el diagrama de B en prompt, snapshot, respuesta, job o evento. Prueba HTTP con dos equipos y proveedor espía que confirme ausencia de contenido ajeno.

### H02 — P0 — Actualización de propuestas de otro proyecto (reproducido)

`app/modules/ai_chat/router.py:241` autoriza el proyecto de la URL, pero `message_repository.py:147` actualiza por ID de mensaje sin filtrar proyecto. El handler devuelve el mensaje ajeno y lo publica en la sala del proyecto de la URL. Se reprodujo llamando al handler con proyecto A autorizado y mensaje de B; la dependencia de autorización de A se suministró directamente, no se hizo una intrusión HTTP real.

Corrección: añadir `project_id` obligatorio al repositorio y al filtro de actualización; comprobar pertenencia de propuesta y mensaje conjuntamente. Registrar `applied` solo después de aplicar realmente una operación, con su revisión resultante, o diferenciarlo de una declaración del cliente.

Aceptación: IDs ajenos e inexistentes no modifican documentos, no filtran respuestas y no emiten eventos.

### H03 — P0 — El modo local puede seleccionar nube (reproducido)

`app/llm/registry.py`, `get_provider`: elimina Gemini al resolver una cadena local; si queda vacía, vuelve a `settings.LLM_PROVIDER`, que puede ser Gemini. Reproducción sin red con `AI_LOCAL_ONLY=True`, `role_chat=[gemini]` y proveedor global Gemini. Además hay rutas de visión que invocan su proveedor directamente y deben entrar en la misma política.

Corrección: política de proveedores obligatoria en el límite de salida; una cadena local vacía devuelve indisponibilidad explícita. Separar el despliegue localhost del despliegue colaborativo cloud y validar todos los propósitos, incluidos task, digest y vision.

Aceptación: con egress externo bloqueado y modo local, cero intentos a nube, incluso con errores y fallbacks. Un modelo local ausente da error accionable, sin respuesta ficticia.

### H04 — P0 — Comandos parciales borran información (reproducido)

`app/ai_team/application/server_diagram_editor.py:232`: sustituye atributos y métodos completos con las listas del comando. «Agregar email» a Cliente con id y guardar() termina solo con email y sin métodos. `_simulate_apply` tampoco discrimina suficientemente las acciones; relaciones existentes no se actualizan por esta vía y no hay comando explícito de layout.

Corrección: operaciones tipadas por ID (`add_attribute`, `update_method`, `remove_attribute`, `update_relation`, `move_node`, etc.), con semántica de parche y eliminación explícita. Eliminar campos únicamente cuando el comando lo indique. Preservar tipo, geometría, notas, paquetes y enumeraciones al normalizar.

Aceptación: cada operación modifica solo lo solicitado; un comando desconocido es rechazado; round-trip conserva todos los campos soportados. Layout cambia geometría sin cambiar semántica.

### H05 — P0 — Colisiones de versiones y escrituras concurrentes (reproducido)

`app/modules/diagrams/repository.py:72` lee versión, calcula N+1 y escribe snapshot y grafo por separado, sin condición de versión esperada. Dos guardados sincronizados desde v1 terminan en v2, con un único snapshot nuevo. El índice único existente no lo impide: el upsert puede reemplazar la misma versión.

Las operaciones WS actualizan el grafo directamente sin incrementar esa versión ni producir snapshot, de modo que el comentario «versión actual igual a snapshot actual» no se mantiene en todas las rutas. Un guardado completo atrasado puede borrar operaciones WS recientes.

Corrección: `base_revision`, actualización condicional atómica y `409` para conflicto. Distinguir revisión de operación y snapshot; conservar una asociación inequívoca. Coordinar estado, auditoría y evento con una transacción MongoDB (replica set local incluido) o un registro durable atómico y materialización recuperable. No considerar un lock de Python como solución entre procesos.

Aceptación: escrituras concurrentes conservan ambas operaciones compatibles o generan conflicto explícito; ninguna desaparición silenciosa. Fallo entre persistencias y reinicio no rompen el historial. Probar con MongoDB real y varios procesos.

### H06 — P1 — Publicación antes de persistencia y vías sin evento común (reproducido/parcialmente estático)

`ServerDiagramEditor.apply_command` publica NODE/EDGE_OPERATION antes de `save_graph`. Con fallo de guardado inyectado, ya había un broadcast. El gestor normaliza `diagram:<id>` e IDs simples: la diferencia de prefijo NO es un defecto confirmado.

`DiagramService.save_graph` guarda y audita, pero no publica. Las rutas de guardado REST e imagen no aseguran por sí mismas el refresco de todos los clientes. Una notificación de actividad no sustituye al nuevo estado del grafo.

Corrección: evento durable posterior al commit para toda mutación, con `event_id`, revisión, origen y operación. Outbox con reintentos y deduplicación en consumidores; permitir recuperación por revisión al reconectar.

Aceptación: ningún cliente recibe un cambio no persistido; una caída tras commit se recupera sin duplicar; voz, imagen, IA y editor producen el mismo flujo observable.

### H07 — P1 — Voz móvil no aplica cambios y comunica éxito falso (inspección de flujo)

`app/modules/diagrams/router.py:398`, `/ai-prompt`, solo devuelve `process_prompt`. No guarda ni ejecuta comandos. `classforge-mobile/lib/screens/diagrams/diagram_viewer_screen.dart`, aproximadamente líneas 377–395, ignora `res`, recarga y anuncia «Se aplicó el comando».

Corrección: separar interpretación/preview de aplicación. La aplicación debe usar el servicio común de mutación, permisos, base_revision e idempotencia. Flutter comprobará resultado y revisión, mostrará errores y recargará el estado confirmado. Mantener compatibilidad del endpoint actual mientras se migra.

Aceptación: dictar «agregar email a Cliente» cambia el backend y ambos clientes, conserva campos anteriores, permite volver a la revisión previa y nunca anuncia éxito ante error o comando desconocido.

### H08 — P1 — Historial pierde mensajes en límites de página (reproducido)

`message_repository.py:193` y `get_mine_history` usan solo `created_at` como cursor con comparaciones estrictas. Tres mensajes con misma fecha y página de dos dejan el tercero fuera de la página siguiente. El cursor `before` se deriva del último elemento tras invertir el orden y también requiere corrección específica.

Corrección: cursor opaco con `(created_at, id)` y dirección; orden estable e índice compuesto equivalente. Validar cursor malformado; definir página inicial reciente y direcciones sin solapamientos.

Aceptación: recorrer 1.000 mensajes con timestamps repetidos en ambas direcciones obtiene cada mensaje exactamente una vez; mismo comportamiento en historial personal y grupal.

### H09 — P1 — Fiabilidad de trabajos y secretos (inspección estática)

`app/ai_team/application/triggers.py:309` guarda la API key en payload; `AiJobRepository.enqueue` inserta ese documento. Quitar `repr` del esquema no cifra ni elimina el valor persistido.

La deduplicación de jobs usa lectura seguida de inserción; el índice dedupe_key no es único. La finalización de jobs solo filtra por ID, sin trabajador ni generación de lease. No se encontró renovación de lease en el worker: tareas largas pueden reaparecer mientras el ejecutor original sigue trabajando. Al desactivar autonomía se marca el job completo, pero no se resuelve aquí el mensaje pending asociado.

Corrección: referencia de credencial cifrada con retención mínima; no guardar secretos en mensajes/logs/jobs. Encolado atómico, efectos idempotentes, renovación y token de generación del lease en complete/fail. Estados terminales coherentes para mensajes y tareas cancelados/omitidos. Revalidar permiso y configuración al ejecutar.

Aceptación: dos workers, reinicio y expiración forzada no duplican mutaciones; un worker viejo no finaliza el lease nuevo; no quedan pending indefinidos; no aparecen keys en MongoDB ni logs de trabajos.

### H10 — P1 — Contrato UML y autorización WS insuficientes (inspección estática)

`SaveGraph.graph_data` acepta `Dict[str, Any]` y el servicio lo persiste sin validar el modelo completo. El servicio WS acepta operaciones y extremos de relaciones sin validar uniformemente el grafo; ignora matched_count y algunas entradas inválidas retornan sin error. El router puede publicar como éxito lo que no se guardó.

En el WS de diagramas, `verify_ws_token` no exige `is_active=True` como sí hace el de proyectos. Los permisos se comprueban al abrir la conexión, sin revalidación por mutación. La revocación durante una sesión y la separación lectura/escritura requieren una política explícita.

Corrección: validador único en cada entrada de mutación; límites de nodos, relaciones y bytes, IDs únicos, extremos existentes, tipos/multiplicidades/visibilidad y ciclos; no exigir que un grafo vacío sea inválido. Comandos WS discriminados, resultados explícitos, autorización vigente de escritura y revocación de conexiones.

Aceptación: mismo grafo inválido rechazado desde REST, WS, imagen, móvil e IA; sin mutación ni broadcast. Usuario desactivado o retirado del equipo no sigue editando.

### H11 — P1/P2 — Sesiones simultáneas y escala de colaboración (inspección estática)

`connection_manager.py:82` almacena un solo socket por usuario/sala; abrir web y móvil con la misma cuenta sustituye la referencia anterior. Rooms y locks viven en memoria de un proceso. El broadcast espera secuencialmente cada socket sin timeout explícito.

Corrección: identidad de conexión separada de identidad del usuario, cierre por connection_id y presencia agregada. Definir despliegue monoproceso inicial; antes de escalar, añadir bus compartido y locks con expiración. Colas acotadas por cliente y política de desconexión/resincronización para clientes lentos.

Aceptación: web y móvil de la misma cuenta reciben cambios; cerrar una pestaña no elimina las otras. Ensayo de dos procesos cuando se habilite ese despliegue; medir p95 y memoria bajo carga.

### H12 — P1 — Evaluación local de proyectos/PDF y entrenamiento específico ausentes

No se encontró en backend un flujo PDF → evaluación → aprobación/rechazo → especificación/informe PDF. `ml` prepara comandos UML, no una rúbrica de evaluación de proyectos. `ml/train/train.py:215` simula entrenamiento sin CUDA; ante error de entrenamiento real también vuelve a dry-run. Los números de esa simulación no son evidencia de calidad de un modelo entrenado.

Corrección: desarrollar módulo `project_reviews` independiente del chat UML, con fuente PDF, hash, versión del proyecto/diagrama, rúbrica versionada, criterios con evidencias y páginas, veredicto y mejoras, modelo/adaptador usados y artefacto PDF. PDF ilegible o insuficiente debe producir un estado explícito de información insuficiente. El contenido del documento será dato, nunca instrucciones para cambiar permisos o la rúbrica.

Entrenamiento: dataset especializado revisado por humanos, división por proyecto/dominio sin filtración, evaluación contra base y reglas, y métricas reales. Dry-run explícito en ruta/artefactos separados; error de entrenamiento real termina con fallo. Distribuir pesos/adaptador y manifest con hashes. No prometer entrenamiento QLoRA fluido en un i5 sin CUDA.

### H13 — P1/P2 — Registro móvil y tutoriales incompletos

No se encontró flujo de registro Flutter (`lib`); sí existe registro backend. Agregar pantalla/servicio y probar validación de contraseña, duplicados y rol inicial no privilegiado.

`SupportTourService` contiene seis tours, de uno a tres pasos. No cubre gestión de equipos, miembros, tareas, historial de chat ni evaluación PDF. La búsqueda de objetivo acaba en popover centrado, sin resolver la tarea. Son hallazgos de código; no se probó su apariencia visual.

Corrección: tours por rol y pantalla con precondiciones y avance basado en acciones verificables, espera cancelable de elementos, navegación coherente y accesibilidad. Mantener presentación en Angular; backend solo para capacidades y progreso si se necesita persistencia entre dispositivos.

## Arquitectura objetivo y secuencia de implementación

### Fase 1 — Contención de seguridad (H01, H02, H03, H09, H10)

Corregir aislamiento en consultas y escrituras; unificar política de salida local/cloud y gestión de credenciales; verificar escritura y vigencia del usuario. Añadir primero pruebas de regresión de acceso entre equipos y modo local. No hace falta reescribir todos los módulos para cerrar estos puntos.

### Fase 2 — Núcleo común del grafo (H04, H05, H10)

Crear un servicio de mutación de diagramas compartido por REST, WS, IA y móvil. Contrato propuesto: `diagram_id`, `base_revision`, `operation_id`, `operations`; actor derivado del servidor. Resultado: revisión, cambios aplicados y advertencias. Validador y motor de comandos puros separados de transporte/persistencia.

Migrar representaciones heredadas con adaptadores explícitos y round-trip; no borrar campos desconocidos sin inventariarlos. Migración con respaldo, dry-run, conteos y reporte de documentos no convertibles. Definir snapshot/revisión, transacción y estrategia para MongoDB local antes de cambiar el repositorio.

### Fase 3 — Sincronización y móvil (H06, H07, H11, parte de H13)

Outbox y protocolo de eventos versionados, ACK/NACK de operaciones y reanudación tras reconexión. Conectar voz e imagen al núcleo común; implementar registro móvil y corregir anuncios de éxito. Versionar el protocolo y mantener compatibilidad de clientes durante la transición.

### Fase 4 — Historial y ejecución de IA (H08, H09, requisito 7)

Cursores estables, cola durable y leases protegidos; transacción/outbox para mensaje + job. Mantener un único mensaje almacenado para su hilo personal y su vista grupal, sin duplicación física. Proyectos colaborativos deben tener equipo configurado o mostrar un estado inicial para formarlo, sin bloquear proyectos personales legítimos.

La invocación por un miembro autorizado generará un trabajo auditable del rol asignado. Definir qué tareas sugieren y cuáles ejecutan según configuración. Layout determinista como operación del backend, con versión base, límites y rollback; no delegar coordenadas arbitrarias al LLM. Normalización UML guiada por reglas y comandos, sin pérdida de significado.

### Fase 5 — Evaluador local y PDF (H12)

Candidato inicial: comparar el Qwen2.5 1.5B ya configurado con `qwen2.5:3b-instruct-q4_K_M` en Ollama. El catálogo oficial indica 1,9 GB para el artefacto cuantizado de 3B; esto NO es el uso total de RAM ni garantiza latencia en cualquier Core i5. Fuente consultada: https://ollama.com/library/qwen2.5/tags . Ficha del modelo: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct .

Propuesta experimental: contexto inicial 4K, una inferencia concurrente, resúmenes por sección con referencias a páginas, generación limitada y medición de RAM pico/latencia fría y caliente en la laptop objetivo. Elegir modelo por calidad de veredictos y consumo, no solo por tamaño. Revisar licencia de la variante elegida antes de distribuirla.

Topología: Angular localhost → FastAPI local → Ollama en loopback. Extraer texto PDF localmente; OCR local solo cuando haga falta, con límites de páginas/tamaño/tiempo. Generar el PDF mediante plantilla determinista del backend a partir del JSON validado. Descargar modelo una vez y ejecutar sin red después. Entrenamiento en hardware adecuado y distribución local del resultado; si se exige entrenar en cada i5, hace falta un experimento independiente de viabilidad CPU.

Aceptar/rechazar según rúbrica versionada y evidencias del documento. Separar errores estructurales verificables del juicio del modelo y hacer visible la información insuficiente. Informe aprobado: especificaciones técnicas trazables; rechazado: criterios incumplidos, evidencias y mejoras accionables. Reevaluar una nueva versión sin sobrescribir el dictamen anterior.

### Fase 6 — Tutoriales y aceptación integral (H13 y todas las funciones)

Cubrir recorridos por rol, responsive y accesibilidad. Actualizar documento de contexto desde OpenAPI/contratos y resultados reales, separando capacidades implementadas de mediciones verificadas. Ejecutar migraciones y despliegue de prueba antes de declarar estable v2.

## Criterios por factor de calidad

| Factor | Evidencia exigida para aceptar |
|---|---|
| Correctitud | Recorridos completos de los siete requisitos; comandos preservan datos; casos UML por cada elemento/relación soportado; PDF y dictamen corresponden al proyecto y revisión |
| Eficiencia | Medir p50/p95, CPU/RAM, consultas y backlog con carga definida. Objetivo inicial propuesto: 10 editores, 200 nodos/300 relaciones, p95 de propagación menor a 500 ms en LAN sin LLM; ajustar con hardware real |
| Fiabilidad | Mongo real, fallos inyectados, reinicio de worker, duplicados, desconexión y reanudación; cero pérdidas silenciosas, estados terminales coherentes y recuperación del historial |
| Facilidad de uso | Sin mensajes de éxito falso; errores accionables, preview de cambios, conflictos explicados, tutoriales completos y pruebas con teclado y pantallas pequeñas |
| Mantenimiento | Un contrato y motor de mutación; puertos para proveedores/persistencia; eliminar rutas de comportamiento duplicadas tras migración; pruebas de contrato y documentación sincronizada |
| Seguridad e integridad | Matriz por rol/recurso/canal; aislamiento entre proyectos; revocación activa; credenciales fuera de payloads; cero egress cloud en modo local; auditoría ligada a revisiones |

Pruebas de aceptación adicionales obligatorias: dos usuarios en navegadores distintos y un móvil; mismo usuario en web+móvil; proveedor caído; voz cancelada o no reconocida; imagen inválida y diagrama vacío legítimo; PDF corrupto/escaneado/extenso; entrada que intenta alterar instrucciones de evaluación; propuesta sobre revisión antigua; retirada de permisos con trabajo en cola; cola con lease vencido; historial con timestamps repetidos; exportación/importación sin pérdida de tipos y geometría soportados.

## Entregables y límites

Se agregan únicamente este informe y el script de reproducciones. No se modificó código de producción, no se instalaron modelos, no se ejecutó entrenamiento y no se crearon commits. Los tiempos y umbrales del plan son objetivos de aceptación propuestos, no mediciones actuales. La revisión no permite garantizar que no existan otros defectos.
