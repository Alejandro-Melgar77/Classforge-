# DOCUMENTACIÓN INTEGRAL DEL SOFTWARE: CLASSFORGE 🚀

> **Documento Maestro de Arquitectura, Funcionalidades, Módulos, Contexto Operativo y Estado de Calidad**  
> **Sistema:** ClassForge (Modelado UML 2.5+, NLU Heurístico, Codegen Clean Architecture y Colaboración en Tiempo Real)  
> **Alcance:** Monorepo (`classforge-backend`, `classforge-frontend`, `classforge-mobile`, `ml`, `scripts`)

---

<!-- METADATOS_DINAMICOS_INICIO -->
### 📌 Metadatos de Seguimiento y Estado del Repositorio
* **Última Actualización Automática:** 2026-11-05 10:30:37
* **Rama Activa:** `main`
* **Último Commit:** `5ae2d06` - *fix(mobile): solucionar arranque de app, conectar con backend cloud, filtrado de diagramas por usuario, visor en tiempo real, comando de voz en backend y notificaciones push nativas*
* **Autor:** Alejandro-Melgar77 <ale.melgararteaga@gmail.com>
* **Estado del Árbol de Trabajo:** 6 archivo(s) con cambios pendientes
* **Batería de Pruebas Backend (Pytest):** 274 pasadas, 0 fallidas (100% éxito en 21.08s)
* **Archivos de Prueba en Backend:** 81 suites de prueba
* **Estado Operativo General:** **PRODUCCIÓN / ESTABLE** (Defectos C1–C7, A1–A36, M1–M12 cerrados y verificados)
<!-- METADATOS_DINAMICOS_FIN -->

---

## 1. Manifiesto y Visión del Proyecto

### 1.1. ¿Qué es ClassForge?
**ClassForge** es una suite de ingeniería de software distribuida, colaborativa y asistida por inteligencia artificial diseñada para acelerar y formalizar el ciclo de diseño conceptual de software. Permite a equipos ágiles modelar diagramas de clases **UML 2.5+**, colaborar en tiempo real sobre lienzos interactivos de alta precisión, interactuar mediante lenguaje natural (voz y texto) y generar automáticamente arquitecturas completas de backend listas para producción (**Clean Architecture / DDD**) en **Spring Boot 3** y **FastAPI**, así como interfaces gráficas y especificaciones para modelos de lenguaje.

### 1.2. Principio Rector: *Offline-First & Cloud-Ready*
A diferencia de las herramientas CASE convencionales que dependen exclusivamente de la nube o que carecen de colaboración moderna, ClassForge opera bajo dos pilares:
1. **Autonomía Local (Offline-First):**
   - Incorpora motores de procesamiento de lenguaje natural (**NLU Heurístico**) deterministas y ultrarrápidos (<0.5 ms en backend, <1 ms on-device en procesadores móviles ARM), capaces de interpretar comandos de voz/texto, inferir tipos de datos y sintetizar sistemas enteros sin conexión a internet ni consumo de APIs de pago.
   - Permite el diseño y visualización continua de diagramas sin latencia externa.
2. **Potencia Aumentada en la Nube (Cloud-Ready):**
   - Integra modelos de visión multimodal de **Google Gemini** (`gemini-3.8-flash`) para digitalizar bocetos a mano alzada, pizarras o capturas de pantalla convirtiéndolos en diagramas UML vectoriales estructurados.
   - Conexión con modelos locales mediante servidores **Ollama** para entornos corporativos con restricciones estrictas de privacidad.
   - Colaboración multi-usuario en tiempo real mediante **WebSockets nativos**, bloqueo optimista de elementos (*node locks*) y cursores sincronizados.

### 1.3. Ventajas frente a Soluciones Tradicionales
| Dimensión | Herramientas Tradicionales (Enterprise Architect, StarUML) | Diagramadores Genéricos (Draw.io, Miro, Lucidchart) | **ClassForge** |
|---|---|---|---|
| **Semántica UML** | Rigurosa pero rígida y compleja | Ninguna (grafos visuales sin significado técnico) | **UML 2.5+ estricto con exportación XMI formal** |
| **Generación de Código** | Esqueletos anémicos desactualizados | Inexistente | **Clean Architecture / DDD completa con Spring Boot 3 y FastAPI** |
| **Colaboración** | Basada en bloqueos de archivos o nula | Colaboración visual libre | **Tiempo real con bloqueos optimistas por nodo y presencia** |
| **Asistencia IA** | No disponible o complementos externos | Chatbots desconectados del grafo | **NLU Heurístico local (<1ms) + Gemini Multimodal Vision + Agente de equipo** |
| **Soporte Móvil** | Inexistente o visor web lento | Visor web responsivo | **App nativa Flutter a 60 FPS con NLU on-device** |

---

## 2. Arquitectura Global del Monorepo

El sistema está concebido como una arquitectura modular desacoplada en tres capas principales interconectadas por contratos RESTful y WebSockets asíncronos:

```mermaid
flowchart TD
    subgraph Clientes["🖥️ Clientes de Usuario"]
        Web["🌐 ClassForge Web (Angular 17)\n• AntV X6 Canvas\n• Web Speech API\n• Signals & OnPush"]
        Mobile["📱 ClassForge Mobile (Flutter 3.x)\n• CustomPainter 60 FPS\n• On-Device NLU (<1ms)\n• WebSockets & Local Notifs"]
    end

    subgraph Gateway["🛡️ Infraestructura & Gateway"]
        Nginx["Proxy Inverso NGINX / Cloudflare Tunnel"]
        Limiter["Rate Limiting (SlowAPI)\nTrusted Proxies CIDR"]
    end

    subgraph Backend["⚙️ ClassForge Backend (FastAPI / Python)"]
        API["FastAPI REST Engine\n(Endpoints /api/v1)"]
        WS["WebSocket ConnectionManager\n(Salas, Presencia, Node Locks)"]
        NLU["Motor NLU Heurístico\n(<0.5ms, Inferencia de Tipos)"]
        CodeGen["Generador de Código\n(Spring Boot 3, FastAPI, ZIP)"]
        AIWorker["AiWorker Autónomo\n(Tareas en 2do Plano, Digests)"]
        LLM["Router Multimodal\n(Gemini 3.8 Flash, Ollama)"]
    end

    subgraph Persistencia["💾 Capa de Persistencia & Almacenamiento"]
        Mongo[("MongoDB 6.0\n• users, teams, projects\n• diagrams, audit_logs\n• ai_feedback, notifications")]
    end

    Web -->|HTTP / REST| Nginx
    Web -->|WebSockets| Nginx
    Mobile -->|HTTP / REST| Nginx
    Mobile -->|WebSockets| Nginx

    Nginx --> Limiter
    Limiter --> API
    Limiter --> WS

    API --> Mongo
    API --> NLU
    API --> CodeGen
    API --> LLM
    WS --> Mongo
    AIWorker --> Mongo
    AIWorker --> LLM
```

### 2.1. Estructura de Directorios del Repositorio
```
segundo examen parcial/
├── classforge-backend/            # Backend asíncrono (Python / FastAPI / Motor)
│   ├── app/
│   │   ├── core/                  # Configuración Pydantic, MongoDB, Auth, RBAC, Rate Limiting
│   │   ├── modules/               # Dominios funcionales desacoplados
│   │   │   ├── ai/                # NLU heurístico, visión Gemini, circuit breaker, feedback
│   │   │   ├── ai_chat/           # Agente autónomo AiWorker, triggers, digests de proyecto
│   │   │   ├── audit/             # Registro inmutable de acciones críticas (audit_logs)
│   │   │   ├── auth/              # Tokens JWT, refresh tokens, sesiones, inactividad
│   │   │   ├── codegen/           # Generadores Spring Boot 3, FastAPI, ZIP, webhooks seguros
│   │   │   ├── collaboration/     # ConnectionManager, WebSockets, salas, presencia, locks
│   │   │   ├── dashboard/         # Analítica y agregaciones de actividad
│   │   │   ├── diagrams/          # Grafo canónico, versionado N+1, XMI 2.1, rollback
│   │   │   ├── folders/           # Carpetas aisladas por proyecto y usuario
│   │   │   ├── notifications/     # Alertas de equipo y fan-out idempotente
│   │   │   ├── projects/          # Proyectos personales y de equipo con control de acceso
│   │   │   ├── teams/             # Equipos ágiles, Scrum Masters y miembros
│   │   │   └── users/             # Gestión de identidades, directorio seguro y RBAC
│   │   └── main.py                # Entrada ASGI, lifespan resiliente, manejadores de excepción
│   ├── tests/                     # 274 pruebas pytest (unitarias, integración, seguridad)
│   ├── Dockerfile                 # Contenedor optimizado de producción
│   └── requirements.txt           # Dependencias fijadas (incluye mongomock-motor)
│
├── classforge-frontend/           # SPA interactiva (Angular 17 / AntV X6 / TailwindCSS)
│   ├── src/app/
│   │   ├── core/                  # Interceptors JWT, Guards de ruta y servicios de sesión
│   │   ├── features/
│   │   │   ├── admin/             # Panel de administración de usuarios y configuración
│   │   │   ├── auth/              # Inicio de sesión, registro y restablecimiento
│   │   │   ├── dashboard/         # Visualización de métricas y acceso rápido a diagramas
│   │   │   ├── diagrams/          # Lienzo AntV X6, nodos SVG personalizados, asistente NLU
│   │   │   └── projects/          # Explorador de proyectos, jerarquía de carpetas
│   └── tailwind.config.js         # Sistema de diseño "Forge Dark / Light"
│
├── classforge-mobile/             # App nativa multiplataforma (Flutter 3.x / Dart)
│   ├── lib/
│   │   ├── core/                  # NLU on-device (<1ms), WebSocket client, notificaciones locales
│   │   ├── screens/               # Visor UML solo lectura a 60 FPS, panel de diagnóstico
│   │   └── widgets/               # CustomPainters vectoriales de clases y relaciones UML
│   └── test/                      # Batería de pruebas Dart para NLU y modelos
│
├── ml/                            # Entornos de entrenamiento, tarjetas de datos y evaluación NLU
├── scripts/                       # Scripts de mantenimiento, siembra, conciliación y automatización
│   ├── update_software_context.py # Script de actualización automática de este documento
│   ├── reconcile_diagram_versions.py # Conciliación de versiones de diagramas legados
│   └── seed_team_and_users.py     # Carga de usuarios y equipos para demostración
├── docs/                          # Documentación complementaria y changelog de blindaje
│   └── CHANGELOG_FIXES.md         # Registro detallado de defectos C1–C7, A1–A36, M1–M12
├── docker-compose.yml             # Orquestación de producción con MongoDB autenticado
└── contexto del software.md       # Este documento maestro autocontenido
```

---

## 3. Módulos Implementados y Especificación Técnica

### 3.1. Backend (`classforge-backend`)

#### A. Core & Infraestructura Base (`app/core/`)
* **Lifespan Context Manager (`app/main.py`):** Inicializa de forma ordenada la conexión a MongoDB mediante el driver asíncrono Motor (`connect_to_mongo()`). El arranque del subsistema autónomo de IA (`AiWorker`) está encapsulado con tolerancia a fallos, asegurando que una indisponibilidad temporal de modelos externos jamás bloquee el arranque del API (Falla C1).
* **Manejo Centralizado de Excepciones:** Registro de manejadores canónicos para:
  - `DomainError` y subclases (`ForbiddenError` → 403, `NotFoundError` → 404, `ValidationError` → 400).
  - Excepciones nativas mapeadas de seguridad (`PermissionError` → 403, `ValueError` → 400) para garantizar que ningún fallo de validación lance errores HTTP 500 no controlados (Fallas A1, A2).
* **Seguridad y Control de Sesión (`app/core/security.py`, `app/modules/auth/`):**
  - Cifrado seguro de contraseñas con `bcrypt`. Política obligatoria de complejidad mínima de 8 caracteres con validación de caracteres (HTTP 422 en caso de incumplimiento) (Falla A11).
  - Emisión de par de tokens JWT: `access_token` (vida corta) y `refresh_token` (7 días).
  - Proyección estricta de sesiones activas en `GET /auth/sessions` sin exponer `refresh_token_hash` (Falla A9).
  - Control de inactividad de sesión: validación en cada petición de `last_activity` con umbral configurable de 30 minutos.
  - Validación rigurosa en `POST /auth/refresh`: rechaza usuarios deshabilitados (`is_active: false`), eliminados (`is_deleted: true`) o inactivos, revocando inmediatamente la sesión en caso de anomalía (Falla A10).
  - `POST /auth/change-password` revoca proactivamente todas las demás sesiones activas (`invalidate_all_except`).
* **Rate Limiting Contextual (`app/core/middleware.py`):**
  - Protección de endpoints sensibles con `SlowAPI`.
  - Validación de cabeceras de proxy (`X-Forwarded-For`, `CF-Connecting-IP`, `X-Real-IP`): solo se leen si la IP directa del socket pertenece a la lista permitida `TRUSTED_PROXIES` (CIDR), previniendo la evasión de límites de tasa mediante spoofing de cabeceras (Falla A8).

#### B. Gestión de Identidades, Equipos y Proyectos (`users`, `teams`, `projects`, `folders`)
* **Matriz RBAC Blindada (`app/core/authz.py`, `app/core/dependencies.py`):**
  - Roles jerárquicos: `admin`, `scrum_master`, `dev`.
  - `PUT /users/{id}`: Blindado contra autopromoción. La modificación de roles (`role`), estado (`is_active`) o correo electrónico está reservada estrictamente a usuarios con rol `admin` (403 para usuarios estándar) (Falla C2).
  - `GET /users/`: Restringido exclusivamente a administradores para evitar la exposición indiscriminada de correos y actividades de la organización (Falla A7).
  - `GET /users/directory`: Endpoint seguro previo que provee una proyección mínima (`id`, `name`, `role`) filtrada por equipos para usuarios con rol `dev`.
* **Aislamiento de Recursos y Mitigación de IDOR (Insecure Direct Object References):**
  - Las operaciones sobre carpetas (`GET`, `PUT`, `DELETE` en `/api/v1/folders/{id}`) verifican de forma obligatoria la pertenencia del recurso al proyecto y usuario activo mediante `require_folder_access` (Falla C3).
  - Los proyectos y diagramas validan rigurosamente el propietario (`owner_id`), la lista de miembros (`member_ids`) o la pertenencia al equipo correspondiente.
  - La eliminación de tareas de proyecto (`DELETE /projects/{id}/tasks/{task_id}`) está restringida al creador o a administradores (Falla A29).

#### C. Dominio de Diagramas UML y Versionado (`app/modules/diagrams/`)
* **Esquema Canónico de Grafos:** Todos los diagramas almacenan su estructura visual y conceptual bajo el contrato estricto:
  ```json
  {
    "nodes": [
      {
        "id": "uuid",
        "shape": "classNode | interfaceNode | abstractNode | enumNode | packageNode | noteNode",
        "x": 100, "y": 120, "width": 240, "height": 180,
        "data": { "name": "Entidad", "attributes": [...], "methods": [...] }
      }
    ],
    "edges": [
      {
        "id": "uuid",
        "source": "uuid-1", "target": "uuid-2",
        "type": "association | inheritance | composition | aggregation | dependency | realization",
        "data": { "sourceMultiplicity": "1", "targetMultiplicity": "0..*", "label": "relacion" }
      }
    ],
    "viewport": { "x": 0, "y": 0, "zoom": 1 }
  }
  ```
* **Semántica de Versionado Exacta (Falla C7):**
  - `diagram.version` representa con fidelidad la versión del snapshot actual.
  - Al invocar `POST /diagrams/{id}/save`, se persiste el grafo nuevo e incrementa la versión a `version = current + 1`. Se incluye además el script `scripts/reconcile_diagram_versions.py` para normalizar grafos legados.
* **Integración e Intercambio XMI 2.1 (OMG UML 2.5) (Fallas A6, C6, A36):**
  - **Exportación:** Mapeo formal de estereotipos e interfaces: `interfaceNode` se serializa como `uml:Interface`, `enumNode` como `uml:Enumeration`, `classNode` como `uml:Class`. Se preserva la geometría (`x`, `y`, `width`, `height`), multiplicidades de extremos y referencias `memberEnd`.
  - **Importación Segura:** Procesamiento asíncrono con `run_in_threadpool`. Validación previa del XML antes de alterar el diagrama: ante XML malformado o grafos vacíos se responde HTTP 400 sin alterar la base de datos.
  - **Protección DoS:** Límite estricto de tamaño de subida de 10 MB, respondiendo HTTP 413 (Payload Too Large) si se supera.

#### D. Colaboración Concurrente en Tiempo Real (`app/modules/collaboration/`)
* **Protocolo WebSocket (`/api/v1/ws/diagrams/{id}`):**
  - Autenticación mediante token JWT en handshake. Validación de acceso al diagrama: responde código de cierre **4003** si el usuario carece de permisos de lectura/escritura (Falla A15).
  - **Presencia Determinista:** El color identificativo del usuario se calcula mediante un hash SHA-1 de su ID para garantizar consistencia visual en todos los clientes (Falla M11).
  - **Bloqueo Optimista de Nodos (`node_lock`):** Bloqueo en memoria por usuario. Al desenfocar o desconectarse el usuario, los bloqueos se liberan automáticamente. Al desconectarse el último usuario de la sala, se limpia el estado efímero (`locks` y `chat_history`).
  - **Consistencia de Persistencia:** En los eventos de cambio de grafo remoto (`graph_change`), la persistencia en base de datos se realiza de forma previa a la difusión (`broadcast`) a otros clientes, evitando estados desincronizados ante fallos de escritura (Falla A16).
  - Retención de tareas asíncronas en segundo plano mediante `app/core/tasks.py` (`spawn`) con `add_done_callback` para prevenir su recolección involuntaria por el recolector de basura (Falla M7).

#### E. Asistencia Inteligente, NLU y Capa LLM (`app/modules/ai/`, `app/modules/ai_chat/`)
* **Motor NLU Heurístico Offline (`heuristic_engine.py`):**
  - Análisis léxico y sintáctico sin modelos pesados ni llamadas de red.
  - Normalización fonética y ortográfica (remoción de acentos Unicode NFD).
  - Inferencia inteligente de tipos de atributos (`codigo` $\rightarrow$ `Long`, `fecha`/`creado` $\rightarrow$ `Date`, `precio`/`monto` $\rightarrow$ `Double`, etc.) (Falla A27).
  - Normalización de cardinalidades y rangos invertidos (e.g. `2..1` $\rightarrow$ `1..2`) (Falla A27).
  - Respuesta explícita `unknown` ante entradas conversacionales o ambiguas, sin inventar entidades espurias (Falla A26).
  - Plantillas instantáneas de dominio completo (*e-commerce*, *banca*, *hospital*, *facturación*) en menos de 0.5 milisegundos.
* **Capa LLM Multimodal y Enrutamiento Inteligente (`app/modules/ai/`):**
  - Enrutador por propósito (`LLM_ROUTING`) que dirige consultas según su caso de uso (`role_chat`, `vision`, `uml_command`) a Google Gemini o proveedores locales (Falla A24).
  - Resiliencia y Circuit Breaker: Manejo explícito de códigos HTTP 404 en upstream (fail-fast inmediato al siguiente proveedor sin agotar reintentos inútiles); errores 401/403 activan el breaker de forma segura (Falla A23).
  - Manejo homogéneo de respuestas de tokens (`candidatesTokensDetails` como lista o diccionario).
  - Endpoint de salud `/ai/health` protegido con autenticación, rate limiting y caché en memoria de 30 segundos (Falla A22).
  - Sanitización de respuestas de fallback para no filtrar mensajes crudos de excepción al usuario final (Falla A21).
  - **Dataset de Mejora (`ai_feedback`):** Persistencia real y verificada en `POST /ai/feedback` con anonimización de correos electrónicos y direcciones IP (Falla C4).
* **Agente Autónomo de Equipo y Chat (`app/modules/ai_chat/`):**
  - **Vía única de ejecución:** Eliminada la doble ejecución por mensaje; el worker autónomo (`AiWorker`) es el único responsable de procesar tareas encoladas (Falla A4).
  - Respeto del flag de activación `AI_AUTONOMY_ENABLED` antes de consumir recursos (Falla A33).
  - Ventana deslizante para digests de proyecto (`summarize_digest`), consultando los mensajes más recientes con orden descendente (Falla A5).
  - `ServerDiagramEditor`: Validación estricta de dependencias en relaciones antes de aplicar cambios para evitar enlaces huérfanos (Falla A32).
  - Propuestas de arquitectura evaluables por el usuario con validación de existencia (404 si la propuesta no pertenece al mensaje) (Falla A30).
* **Fase 4 — Chat Colaborativo, Agentes de IA, Ejecución Autónoma, Historial y Normalización Inteligente UML:**
  - **Aislamiento Estricto y Chat Colaborativo (`AI-CHAT-01`, `AI-CHAT-02`):** Cada usuario posee su hilo personal persistente (`thread="personal"`), garantizando que ningún usuario B pueda visualizar ni manipular mensajes privados del usuario A. El chat grupal de proyecto (`/projects/{id}/history`) ofrece una vista unificada de las decisiones y propuestas del equipo (`visibility="team"`, `thread="project"`), con soporte para publicación voluntaria de mensajes privados al equipo mediante `POST /messages/{id}/publish`.
  - **Paginación Robusta por Cursor Compuesto (`H08`):** Algoritmo de cursor `(created_at, _id)` con codificación opaca `v2:` que previene la pérdida o duplicación de mensajes cuando múltiples registros comparten el mismo timestamp. Validación estricta que devuelve HTTP 400 ante cursores corruptos.
  - **Confiabilidad de Tareas y Workers Autónomos (`H09`, `AI-TASK-01`):** `AiJobRepository` con semántica de leases atómicos (`acquire_next`, `renew_lease`, `reap_expired_leases`, `cancel_job`). Renovación activa de leases durante procesamiento intensivo para prevenir reapings prematuros. Detección y transición limpia a estado de error (`AUTONOMY_DISABLED`) para mensajes encolados cuando la autonomía está deshabilitada, impidiendo estados pendientes huérfanos. Deduplicación atómica por `active_dedupe_key`. Cancelación formal de tareas mediante `POST /projects/{id}/tasks/{id}/cancel` con aborto de trabajos asociados en `ai_jobs`.
  - **Roles y Especialidades de Agentes (`AI-ROLE-01`):** Definición de roles especializados (`software_architect`, `tech_lead`, `backend_developer`, `qa_engineer`, `scrum_master`) con matriz de capacidades según la autonomía configurada en el proyecto (consultar vs proponer vs ejecutar autónomamente).
  - **Propuestas Estructuradas y Mutación UML Segura (`AI-PROP-01`, `AI-EXEC-01`):** Flujo de revisión integral (`pending` -> `approved` / `rejected` / `dismissed` -> `applied`). Endpoint `POST /proposals/{id}/apply` que ejecuta las modificaciones a través del motor común de la Fase 2 (`apply_operations`), incrementa la versión del diagrama, genera snapshots en el historial de versiones, y previene condiciones de carrera con HTTP 409 Conflict si la versión base no coincide con la actual. Preservación garantizada del 100% de atributos y métodos existentes.
  - **Motor Determinista de Reorganización Automática UML (`AI-LAYOUT-01`):** Algoritmo estratificado y jerárquico determinista (`app/modules/diagrams/layout.py`) que posiciona superclases por encima de subclases en jerarquías de herencia/realización, previene colisiones mediante AABB y emite operaciones tipadas `move_node`. Endpoint `POST /diagrams/{id}/layout` con verificación de versión base y auditoría `AI_LAYOUT`.
  - **Motor de Normalización Inteligente UML (`AI-NORM-01`):** Diagnóstico no destructivo (`app/modules/diagrams/normalization.py`) que detecta inconsistencias en nombres de clases (PascalCase), atributos/métodos (camelCase), mapeo de tipos a estándares UML canónicos, inversión de rangos de multiplicidad y atributos duplicados. Emisión de operaciones tipadas Phase 2 (`update_node`, `update_attribute`, `update_edge`) vía `POST /diagrams/{id}/normalization/apply` sin pérdida destructiva de datos.
  - **Auditoría y Trazabilidad Exhaustiva (`AI-TRACE-01`):** Registro de cada acción de IA (`AI_APPLY_PROPOSAL`, `AI_LAYOUT`, `AI_NORMALIZE`, etc.) en `audit_logs` con trazabilidad completa de actor, proyecto, diagrama, versiones anterior y nueva, y metadatos operativos.
  - **Integración Frontend Angular (`AI-WEB-01`):** Clientes de API en `AiTeamApiService` (`applyProposal`, `publishMessage`, `cancelTask`), métodos en `DiagramService` (`autoLayout`, `getNormalization`, `applyNormalization`), y toolbar interactiva (`canvas-toolbar.component.ts`) conectada al motor de layout con fallback offline automático.

#### F. Generación de Código de Grado de Producción (`app/modules/codegen/`)
* **Spring Boot 3 (Clean Architecture / DDD):**
  - Estructura Maven lista para compilar: `pom.xml`, `mvnw`, `mvnw.cmd` con bit de ejecución Unix `0o755` preservado (Falla M12).
  - Soporte completo para `interfaceNode` (generando interfaces Java con métodos de contrato) y `enumNode` (Falla A20).
  - Entidades JPA (`@Entity`, `@Table`) con soporte para cardinalidades Muchos a Muchos (`@ManyToMany`), Uno a Muchos (`@OneToMany`) y Muchos a Uno (`@ManyToOne`), soportando esquemas canónicos y planos (Falla A20).
  - Capa de Repositorios (`JpaRepository`), Servicios transaccionales (`@Service`), Controladores REST documentados con OpenAPI 3 (`@Tag`, `@Operation`), DTOs de petición y respuesta desacoplados, y `@ControllerAdvice` global.
  - Generación de archivos de entorno `.vscode/` (`settings.json`, `extensions.json`, `launch.json`) con JSON sintácticamente válido (Falla A19).
* **FastAPI (Python):**
  - Modelos SQLAlchemy 2.0 asíncronos y esquemas de validación Pydantic v2.
  - Validación previa del código generado con el compilador nativo de Python (`compileall`) antes de empaquetar el archivo ZIP, garantizando que el usuario jamás reciba código con errores de sintaxis (Falla M10).
* **Webhooks Asíncronos Seguros contra SSRF (Falla A12):**
  - Verificación exhaustiva de URLs de destino en `app/modules/codegen/webhook.py`.
  - Resolución DNS con `socket.getaddrinfo` para validar todas las IPs resueltas.
  - Rechazo de direcciones de loopback, redes privadas (RFC 1918), enlaces locales (169.254.x.x), direcciones reservadas, multicast, representaciones IPv4-mapeadas en IPv6 (`::ffff:127.0.0.1`), formatos numéricos enteros (`2130706433`), octales, hexadecimales y dominios DNS comodín (`127.0.0.1.nip.io`).
  - Cliente HTTP con redirecciones desactivadas (`follow_redirects=False`) para evitar bypasses por saltos HTTP.

#### G. Auditoría, Notificaciones y Dashboard (`audit`, `notifications`, `dashboard`)
* **Esquema Unificado de Auditoría (`audit_logs`):**
  - Registro estructurado con `user_id`, `action`, `resource`, `resource_id`, `metadata` y `created_at` (Fallas A17, M9).
* **Centro de Notificaciones con Fan-Out Idempotente:**
  - Envío dirigido al propietario (`owner_id`) y miembros activos del equipo (Falla A18).
  - Operaciones idempotentes: marcar una notificación leída repetidas veces responde 200 sin lanzar 404 (Falla M4).
* **Dashboard y Analítica Tolerante a Fallos:**
  - Agregación resiliente de proyectos, diagramas y eventos de auditoría mediante `.get()` seguro para evitar caídas por documentos heterogéneos sin campos opcionales (`status`, `name`).

---

#### H. Evaluador Inteligente Local de Proyectos (Fase 5 - `app/modules/project_reviews/`)
* **Ingesta y Validación Segura de PDFs (`PDF-01`, `PDF-02`, `PDF-03`):**
  - Almacenamiento seguro por proyecto en `uploads/project_reviews/{project_id}/{document_id}.pdf`.
  - Verificación estricta de firma mágica `%PDF-`, cálculo de hash criptográfico SHA-256 para unicidad e integridad.
  - Límites de seguridad: rechazo con HTTP 413 ante archivos mayores a 25 MB; rechazo con HTTP 400 ante documentos superiores a 300 páginas o PDFs protegidos con contraseña.
  - Protección rigurosa contra vulnerabilidades de *Path Traversal* mediante resolución canónica de rutas (`get_safe_document_path`).
  - Extractor semántico estructurado página a página (`pypdf`) que detecta PDFs escaneados o carentes de texto digital OCR (< 50 palabras -> `has_sufficient_text=False`).
  - Mapeo semántico automatizado de secciones de ingeniería de software (Alcance, Requisitos, Arquitectura/UML, Base de Datos/Persistencia, QA/Pruebas, Seguridad y Riesgos).
* **Motor Híbrido de Evaluación y Rúbrica Técnica (`EVAL-01` a `EVAL-05`):**
  - Rúbrica formal versionada `CF-SE-2026.1` con 6 criterios ponderados y umbral de aprobación de 70.0/100.
  - Defensa activa contra ataques de *Prompt Injection* en documentos no confiables (`sanitize_untrusted_text`), neutralizando comandos adversarios ("ignore previous instructions", "score 100").
  - Ejecución local mediante Ollama con caché de conectividad y fallback inmediato al motor de reglas semánticas deterministas de alta precisión sin llamadas a servicios cloud de pago.
  - Tasa de alucinación del 0.0%: todas las citas de página corresponden a páginas reales verificables en el documento.
  - Generación de recomendaciones técnicas accionables ordenadas por criticidad (`HIGH`, `MEDIUM`, `LOW`).
  - Síntesis y emisión automática de pliegos de especificaciones técnicas (`TechnicalSpecification`) para proyectos con dictamen `APROBADO`.
* **Generación de Informes Profesionales PDF (`REPORT-01`):**
  - Renderizado vectorial de alta fidelidad mediante `reportlab` con numeración de dos pasadas ("Página X de Y").
  - Emisión de dos documentos independientes:
    1. *Dictamen de Evaluación de Proyecto*: Resumen ejecutivo, cuadro de puntajes, desglose de hallazgos por criterio con evidencias textuales y citas, y matriz de recomendaciones priorizadas.
    2. *Pliego de Especificaciones Técnicas de Software*: Resumen funcional, arquitectura multicapa, especificación de componentes, endpoints REST y modelo de entidades relacional/NoSQL.
* **Persistencia, Historial Secuencial y Auditoría (`HIST-01`, `SEC-01`):**
  - Colecciones `review_documents` y `project_reviews` con aislamiento estricto por proyecto.
  - Numeración secuencial garantizada (`review_number` 1, 2, 3...) sin colisiones entre proyectos.
  - Registro inmutable en `audit_logs` con la acción `PROJECT_REVIEW_EVALUATED`.
* **Machine Learning, Dataset y Evaluación Rigurosa (`ML-01`, `ML-02`, `ML-03`):**
  - Dataset de 22 proyectos de software exhaustivamente anotados en `ml/data/reviews_dataset.jsonl`.
  - Benchmark automatizado (`ml/eval/eval_reviews.py`): **Exactitud del 90.91%**, **Macro F1 de 0.9048**, **Validez de esquema 100%**, **Alucinaciones 0%** y **Latencia media de 103 ms**.
  - Pipeline de fine-tuning LoRA en `ml/train/train_reviews_adapter.py` con auditoría honesta de hardware (entorno CPU sin CUDA documentado) y manifiesto QLoRA reproducible para aceleradores GPU.
* **Integración Frontend Angular 17 (`WEB-01`):**
  - Modelos TypeScript (`review.model.ts`), servicio reactivo (`project-reviews.service.ts`), componente `project-reviews.component.ts` integrado en las pestañas del Centro de Proyecto (`evaluaciones`).
  - Carga interactiva de PDFs, visualización de progreso, tarjetas de dictámenes, acordeones de hallazgos y botones de descarga directa de PDFs.

---


#### I. Calidad Integral, Concurrencia y Resiliencia del Sistema (Fase 6 - `tests/test_phase6/`)
* **Suite de Regresión de Seguridad (`SEC-01` - `test_security_regressions.py`):**
  - Validación estricta contra vulnerabilidades IDOR en proyectos y diagramas (`can_access_project`, `can_access_diagram`, `require_project_member`, `require_diagram_access`), impidiendo el acceso cruzado entre usuarios no miembros.
  - Verificación del bypass de auditoría para roles `admin` sin bloquear la trazabilidad.
  - Sanitización exhaustiva contra *Prompt Injection* adversario (`sanitize_untrusted_text` e `INJECTION_PATTERNS`), garantizando que directivas maliciosas embebidas en especificaciones de software no alteren la evaluación de la rúbrica ni ejecuten comandos en el host.
* **Resiliencia, Concurrencia y Leases (`REL-01` - `test_system_reliability.py`):**
  - Ciclo de vida robusto de leases en `AiJobRepository` (`acquire_next`, `renew_lease`, `reap_expired_leases` con backoff exponencial), garantizando que trabajos huérfanos por caída de workers se recuperen automáticamente.
  - Mecanismo de bloqueo colaborativo atómico en `ConnectionManager` (`acquire_lock`, `release_lock`, `get_lock_owner`, `release_all_user_locks`), impidiendo que dos colaboradores colisionen al editar simultáneamente el mismo nodo UML.
  - Control de concurrencia optimista en diagramas con detección de versiones obsoletas (`base_version`), rechazando guardados en conflicto con HTTP 409 Conflict.
* **Benchmarks de Rendimiento en Tiempo Real (`PERF-01` - `test_performance_benchmarks.py`):**
  - Evaluación determinista de rúbrica técnica: **p50 < 15 ms, p95 < 30 ms**.
  - Generación vectorial de reportes oficiales PDF (`ReportLab`): **latencia media < 20 ms**.
  - Guardado y versionado atómico de grafos UML en MongoDB: **p50 < 5 ms, p95 < 15 ms**.
* **Pruebas Integrales de Flujo de Extremo a Extremo (`QA-01` a `QA-05` - `test_flows_e2e.py`):**
  - Verificación del flujo completo: Autenticación -> Creación de Proyecto -> Modelado UML de Clases -> Generación de Código Spring Boot y prompts frontend -> Extracción y Evaluación Documental -> Emisión del Reporte Oficial en PDF con dictamen APROBADO.

---

### 3.2. Frontend (`classforge-frontend`)

* **Framework y Principios Modernos:**
  - **Angular 17** con componentes 100% *Standalone* (sin módulos tradicionales `AppModule`).
  - Inyección de dependencias funcional mediante la API `inject()`.
  - Estrategia de detección de cambios `ChangeDetectionStrategy.OnPush` para un rendimiento fluido a altas frecuencias de refresco.
  - Reactividad basada en **Signals** para la gestión del estado de interfaces (paneles de propiedades, presencia de colaboradores, capas de código).
* **Lienzo UML con AntV X6 (`diagram-canvas.component.ts`):**
  - Motor de renderizado vectorial SVG de alto rendimiento.
  - Rejilla magnética (*grid snapping*) y guías inteligentes de alineación.
  - Nodos personalizados con compartimentos estándar UML (título con estereotipo, lista de atributos con visibilidad `+`, `-`, `#`, y métodos).
  - Diferenciación visual de estereotipos:
    - `<<interface>>`: Verde azulado
    - `<<abstract>>`: Púrpura
    - `<<enum>>`: Ámbar
    - Clases estándar: Azul profesional
    - Notas y paquetes: Pizarra y amarillo
  - Minimapa flotante interactivo y pila de historial para atajos de teclado universales (Ctrl+Z deshacer, Ctrl+Y rehacer).
* **Asistente NLU y Voz en el Navegador:**
  - Captura de audio en tiempo real mediante **Web Speech API** nativa del navegador.
  - Parser NLU en TypeScript (`nlu-parser.service.ts`) que refleja la lógica del backend para ofrecer previsualizaciones locales inmediatas en tarjetas interactivas antes de impactar el canvas.
* **Drawer de Código en Vivo (`live-code-drawer.component.ts`):**
  - Panel deslizante con explorador de archivos en árbol.
  - Resaltador de sintaxis optimizado de un solo paso para Java y Python.
  - Botón de descarga instantánea del proyecto comprimido en `.zip`.
* **Sistema Integral de Tutoriales Interactivos Guiados (`H13`, `UX-01`):**
  - Catálogo de 10 tours guiados en `support-tour.service.ts`: Navegación General, Gestión de Proyectos, Equipos y Roles, Creación de Diagramas UML, Modelado y Propiedades, Asistente IA & Voz, Equipo de IA Participativa, Colaboración en Tiempo Real, Generación de Código y Evaluador Inteligente de Proyectos.
  - **Filtrado Dinámico por Roles (`getAvailableTours`):** Aislamiento de tours según el rol del usuario autenticado (`admin`, `scrum_master`, `dev`), garantizando que usuarios estándar no visualicen tutoriales de funciones administrativas restringidas.
  - **Avance por Acción Real en el DOM (`actionType: 'click'`):** El tutorial avanza automáticamente cuando el usuario interactúa o hace clic en el elemento destacado en pantalla.
  - **Desplazamiento Suave y Posicionamiento Seguro:** Centrado automático con `scrollIntoView` suave y reintentos para elementos con renderizado asíncrono.
* **Accesibilidad Universal WCAG 2.2 AA y Responsividad (`ACC-01`, `UX-02`):**
  - Navegación integral por teclado en `tour-overlay.component.ts`: tecla `Escape` para cancelar el tutorial en cualquier instante, flecha derecha (`ArrowRight`) para avanzar y flecha izquierda (`ArrowLeft`) para retroceder.
  - Semántica ARIA completa: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby` y etiquetas `aria-label` en controles de navegación.
  - Selectores `data-tour` estandarizados en la barra de navegación del Shell (`dataTour`) y en la barra de herramientas del canvas UML (`data-tour="toolbar"`), eliminando modales flotantes sin anclaje visual.
* **Colaboración Gráfica:**
  - Renderizado en vivo de cursores multi-usuario con nombres e insignias de presencia.
  - Borde resaltado en nodos bloqueados por otros usuarios para advertir de edición concurrente.

---

### 3.3. Aplicación Móvil — ClassForge Visualizer (`classforge-mobile`)

* **Identidad y Paquete:**
  - **Nombre de la Aplicación:** `Classforge Visualizer`
  - **Paquete Android:** `com.classforge.classforge_mobile`
  - **Ícono Temático:** Logo personalizado de ingeniería de software y modelado UML en alta resolución (`res/mipmap-*/ic_launcher.png` e `ic_launcher_round.png`).
  - **Binario de Producción:** `Classforge-Visualizer.apk` (53.4 MB / 56,037,483 bytes) compilado en modo Release sin compresión R8 destructiva (`isMinifyEnabled = false`, `isShrinkResources = false`) para garantizar estabilidad total en cualquier dispositivo Android.
* **Conectividad Cloud en Tiempo Real:**
  - Conexión predeterminada al backend cloud de producción en Render: `https://classforge-backend-8a14.onrender.com/api/v1`.
  - Conexión WebSocket segura para eventos de colaboración bidireccionales: `wss://classforge-backend-8a14.onrender.com/api/v1/ws/diagrams/{id}?token={ws_token}`.
* **Flujo de Inicio de Sesión y Control de Acceso (RBAC):**
  - Pantalla de inicio de sesión formal (`LoginScreen`) que se activa automáticamente al abrir la aplicación si no existe una sesión previa válida.
  - Autenticación real contra el backend cloud (`POST /auth/login`), recepción de token JWT y sincronización de perfil (`GET /auth/me`).
  - Credenciales demo accesibles de un toque para perfiles corporativos (`admin@classforge.com`, `alejandro@classforge.com`, `fernando@classforge.com`).
* **Filtrado Estricto de Proyectos y Diagramas:**
  - En la vista móvil, cada proyecto se mapea a su diagrama UML correspondiente.
  - Verificación rigurosa de pertenencia: la lista de diagramas se filtra dinámicamente para mostrar **únicamente aquellos diagramas donde el usuario logueado es creador (`createdBy == user.id`) o miembro asignado (`member_ids.contains(user.id)`)**, o todos si posee rol de Administrador.
* **Visualizador UML en Tiempo Real (100% Solo Lectura):**
  - Lienzo interactivo optimizado con `InteractiveViewer` a 60 FPS con zoom, paneo y renderizado vectorial de nodos de clase (`UMLClassCard`) y relaciones (`UMLRelationshipPainter`).
  - Modo estrictamente solo lectura para evitar alteraciones accidentales con gestos táctiles.
  - Escucha activa del canal WebSocket: ante eventos `DIAGRAM_COMMITTED`, `NODE_OPERATION`, `EDGE_OPERATION` o `SYNC_GRAPH`, el visor recarga automáticamente el diagrama en pantalla sin necesidad de refresco manual.
* **Asistente de Voz Integrado con Modificación en Servidor:**
  - Botón de micrófono flotante en la vista del diagrama que captura solicitudes habladas mediante `speech_to_text`.
  - Envía la transcripción al endpoint del servidor `POST /api/v1/diagrams/{id}/ai-prompt`.
  - El backend interpreta la petición con NLU/Gemini, genera las operaciones sobre el grafo, guarda la versión atómicamente y difunde el evento a la sala WebSocket, actualizando tanto el visor web como el móvil en tiempo real.
* **Notificaciones Push Nativas de Android:**
  - Integradas en la barra de notificaciones del sistema operativo mediante `flutter_local_notifications` y retroalimentación háptica física (`HapticFeedback.heavyImpact`):
    1. **Notificación por Colaboración Remota:** Cada vez que otro integrante del diagrama realiza un cambio en tiempo real, el dispositivo emite una notificación push nativa indicando el nombre del diagrama actualizado.
    2. **Notificación por Comando de Voz:** Al finalizar el procesamiento de una orden por micrófono, emite una notificación push informando si la modificación fue exitosa (`🎤 Comando de Voz Exitoso`) o si ocurrió algún error en el backend (`❌ Error en Comando de Voz`).

---

### 3.4. Inteligencia Artificial y Machine Learning (`ml/`, `shared/`)

* **Casos Sintéticos Homologados (`shared/nlu_cases.json`):**
  - Suite de evaluación con más de 50 intenciones canónicas utilizadas para verificar de forma simultánea la coherencia entre el motor Python del backend, el parser TypeScript del frontend y el motor Dart del móvil.
* **Pipelines de Entrenamiento (`ml/train/`, `ml/eval/`):**
  - Scripts y Makefiles para experimentación y ajuste de modelos ligeros para procesamiento de lenguaje natural en terminales móviles.

---

## 4. Esquema de Base de Datos (MongoDB)

ClassForge almacena su información en MongoDB (versión 6.0 o superior) organizada en las siguientes colecciones documentales:

```mermaid
erDiagram
    users ||--o{ projects : "crea / posee"
    users }o--o{ teams : "miembro de"
    teams ||--o{ projects : "asignado a"
    projects ||--o{ folders : "contiene"
    projects ||--o{ diagrams : "agrupa"
    folders ||--o{ diagrams : "organiza"
    diagrams ||--o{ audit_logs : "registra eventos"
    users ||--o{ audit_logs : "ejecuta"
    users ||--o{ notifications : "recibe"
```

### 4.1. Resumen de Colecciones Principales
| Colección | Propósito | Campos Clave e Índices |
|---|---|---|
| `users` | Cuentas, credenciales e identidades | `_id`, `email` (único), `password_hash`, `role`, `is_active`, `is_deleted`, `last_activity` |
| `teams` | Equipos ágiles de desarrollo | `_id`, `name`, `scrum_master_id`, `member_ids`, `is_deleted` |
| `projects` | Espacios de trabajo (personales o de equipo) | `_id`, `name`, `type`, `team_id`, `owner_id`, `status`, `is_deleted` |
| `folders` | Jerarquías de agrupación dentro de proyectos | `_id`, `name`, `project_id`, `parent_id`, `created_by`, `is_deleted` |
| `diagrams` | Grafos conceptuales UML y metadatos | `_id`, `name`, `project_id`, `graph_data`, `version`, `history`, `member_ids` |
| `audit_logs` | Trazabilidad inmutable de eventos críticos | `_id`, `action`, `user_id`, `resource`, `resource_id`, `metadata`, `created_at` |
| `notifications` | Notificaciones in-app persistidas | `_id`, `user_id`, `title`, `message`, `diagram_id`, `is_read`, `created_at` |
| `ai_feedback` | Evaluaciones de respuestas de IA para mejora continua | `_id`, `prompt`, `response`, `rating`, `user_id`, `created_at` (datos anonimizados) |
| `ai_usage` | Telemetría de consumo de tokens y modelos | `_id`, `provider`, `model`, `purpose`, `prompt_tokens`, `completion_tokens`, `created_at` |

---

## 5. Matriz de Endpoints y Contratos de Comunicación

Prefijo global del API REST: `/api/v1`

### 5.1. Autenticación y Perfil (`/auth`)
* `POST /auth/register`: Registro de nuevos usuarios (requiere contraseña de 8+ caracteres con complejidad).
* `POST /auth/login`: Autenticación por credenciales, retorna `access_token` y `refresh_token`. Protegido por rate limiter.
* `POST /auth/refresh`: Renovación de token de acceso. Valida estado activo e inactividad antes de reemitir.
* `GET /auth/me`: Información del usuario autenticado.
* `GET /auth/sessions`: Listado de sesiones activas del usuario (sin exponer hashes de tokens).
* `POST /auth/change-password`: Cambio de contraseña y revocación automática de todas las demás sesiones activas.
* `POST /auth/logout`: Cierre de sesión e invalidación de token.

### 5.2. Directorio y Gestión de Usuarios (`/users`)
* `GET /users/`: Listado administrativo completo de usuarios. **Exclusivo para administradores (`admin`)**.
* `GET /users/directory`: Proyección reducida (`id`, `name`, `role`) filtrada para usuarios con rol `dev` en sus equipos.
* `GET /users/{id}`: Detalle de usuario.
* `PUT /users/{id}`: Modificación de perfil. Autopromoción prohibida; campos `role`, `is_active` y `email` solo modificables por `admin`.
* `DELETE /users/{id}`: Baja lógica del usuario.

### 5.3. Equipos, Proyectos y Carpetas (`/teams`, `/projects`, `/folders`)
* `GET /teams/` / `POST /teams/`: Listar y crear equipos ágiles (`admin` / `scrum_master`).
* `GET /projects/` / `POST /projects/`: Listado de proyectos accesibles y creación de proyectos.
* `GET /projects/{id}` / `PUT /projects/{id}` / `DELETE /projects/{id}`: CRUD de proyecto con verificación estricta de pertenencia.
* `GET /folders/{id}` / `PUT /folders/{id}` / `DELETE /folders/{id}`: Gestión de carpetas con verificación IDOR contra usuario y proyecto.

### 5.4. Diagramas UML (`/diagrams`)
* `GET /diagrams/`: Listado de diagramas accesibles según rol y equipo.
* `POST /diagrams/`: Creación de nuevo diagrama.
* `GET /diagrams/{id}`: Consulta de grafo canónico y metadatos.
* `POST /diagrams/{id}/save`: Persistencia del grafo con inserción en historial y avance a `version = current + 1`.
* `POST /diagrams/{id}/rollback/{version}`: Restauración de versión anterior.
* `GET /diagrams/{id}/export/xmi`: Exportación formal al estándar OMG XMI 2.1 (UML 2.5).
* `POST /diagrams/{id}/import/xmi`: Importación segura de archivos XMI (límite 10 MB, validación de sintaxis).
* `POST /diagrams/{id}/from-image`: Conversión de bocetos a grafo mediante visión multimodal.
* `PUT /diagrams/{id}/participants`: Asignación y revocación de permisos de colaboradores.

### 5.5. Asistencia de Inteligencia Artificial (`/ai`)
* `POST /ai/command`: Procesamiento de texto o voz mediante el motor heurístico local NLU.
* `POST /ai/vision`: Análisis visual de bocetos e imágenes de pizarras con Google Gemini.
* `GET /ai/health`: Estado operativo de modelos de IA con rate limiting y caché de 30s.
* `POST /ai/feedback`: Registro de evaluaciones del usuario con datos anonimizados.

### 5.6. Generación de Código (`/codegen`)
* `POST /codegen/spring-boot`: Generación de código Spring Boot 3 en JSON plano.
* `POST /codegen/spring-boot/zip`: Descarga del paquete Maven comprimido en `.zip`.
* `POST /codegen/fastapi`: Generación de código FastAPI con SQLAlchemy 2.0.
* `POST /codegen/frontend-prompt`: Especificación para asistentes IA de frontend.

### 5.7. Protocolo WebSocket (`/api/v1/ws/diagrams/{id}`)
* **Handshake:** Requiere token JWT en query param `?token=...`. Cierra con código **4003** si no tiene acceso.
* **Mensajes Cliente $\rightarrow$ Servidor:**
  - `cursor_move`: Actualización de coordenadas $(x, y)$ del cursor.
  - `lock_node` / `unlock_node`: Solicitud o liberación de bloqueo optimista sobre un nodo.
  - `graph_change`: Transmisión de cambios estructurales del grafo (persiste antes de difundir).
  - `chat_message`: Mensajes de chat en sala.
* **Eventos Servidor $\rightarrow$ Cliente:**
  - `room_state`: Estado inicial (usuarios presentes, nodos bloqueados, historial de chat).
  - `user_joined` / `user_left`: Cambios en la presencia de la sala.
  - `cursor_update`: Posición de cursores remotos con nombre y color del colaborador.
  - `node_locked` / `node_unlocked`: Notificación de bloqueos vigentes.
  - `remote_graph_change`: Difusión de cambios al grafo realizados por otros usuarios.

---

## 6. Estado Actual del Proyecto y Auditoría de Calidad

El proyecto ClassForge se encuentra en estado **PRODUCCIÓN / ESTABLE**. Todas las fallas del catálogo maestro han sido solventadas de manera verificada:

### 6.1. Cuadro de Resolución del Catálogo de Defectos
| Categoría | Total de Fallas | Estado | Resumen de Corrección |
|---|---|---|---|
| **Críticas (C1–C7)** | 7 / 7 | **Cerradas (100%)** | Lifespan blindado (C1), autopromoción eliminada (C2), IDOR mitigado (C3), persistencia en feedback (C4), esquema canónico en visión (C5), validación XMI y DoS (C6, A36), versionado N+1 coherente (C7). |
| **Altas (A1–A36)** | 36 / 36 | **Cerradas (100%)** | Mapeo canónico de excepciones (A1, A2), códigos de error HTTP 4xx/5xx (A3), ejecución única en chat IA (A4), ventana reciente en digests (A5), XMI 2.1 fiel a UML (A6), `/users/` restringido a admin y directorio público (A7), rate limiting con proxies confiables (A8), hashes ocultos en sesiones (A9), revocación por inactividad y complejidad de contraseñas (A10, A11), mitigación integral de SSRF en webhooks (A12), entre otros. |
| **Medias (M1–M12)** | 12 / 12 | **Cerradas (100%)** | `mongomock-motor` en requirements (M1), Docker Compose con producción y Mongo autenticado (M2), variables P5 en `.env.example` (M3), idempotencia en notificaciones (M4), bit de ejecución `0o755` en runners (M12), eliminación de código muerto (M5, M6), tareas protegidas contra GC (M7), color determinista por SHA-1 (M11). |

### 6.2. Hallazgos Adicionales Resueltos
1. **Crash en Dashboard por campos faltantes:** Manejo con `.get()` defensivo en `app/modules/dashboard/router.py` para prevenir `KeyError` ante proyectos o documentos sin los campos `status` o `name`.
2. **Mitigación Avanzada de SSRF en Webhooks:** Cobertura contra resoluciones DNS complejas, conversiones numéricas enteras (`2130706433`), mapeos IPv4 sobre IPv6 (`::ffff:127.0.0.1`) y evasiones por redirección en `app/modules/codegen/webhook.py`.
3. **Control de Código HTTP 413 en XMI:** Respuesta estricta con código HTTP 413 (Payload Too Large) ante archivos de intercambio superiores a 10 MB.

### 6.3. Cobertura de Pruebas Automatizadas
* **Total de Pruebas en el Backend:** 369 pruebas automatizadas con `pytest`.
* **Total de Pruebas en el Frontend (Karma/Jasmine):** 98 pruebas unitarias pasando al 100% (0.96s).
* **Resultado:** **369 pasadas, 0 fallidas (100% éxito en 21.53s)**.
* **Suites Nuevas de Verificación:** 19 archivos de prueba dedicados garantizan que ninguna de las vulnerabilidades o fallas corregidas pueda reintroducirse en el futuro.

---

## 7. Guía de Despliegue y Puesta en Marcha

### 7.1. Despliegue con Docker Compose (Recomendado para Producción)
El archivo `docker-compose.yml` está configurado para un entorno seguro de producción con autenticación obligatoria en la base de datos:

```bash
# 1. Configurar variables de entorno requeridas
export SECRET_KEY="clave_secreta_de_produccion_extremadamente_larga_y_segura"
export ENVIRONMENT="production"

# 2. Levantar la pila de contenedores
docker compose up -d --build
```
* **Frontend Web:** `http://localhost:80`
* **Backend API & Swagger:** `http://localhost:8000/docs`
* **MongoDB (Autenticado):** `mongodb://classforge_admin:password@localhost:27017/classforge`

### 7.2. Ejecución Local para Desarrollo (Modo Offline en Windows)
ClassForge incluye scripts automáticos para inicializar todos los servicios locales sin configuración manual:

```cmd
# Iniciar MongoDB, Backend y Frontend localmente
start_local.bat
```
O de forma manual por componentes:
1. **Backend:**
   ```bash
   cd classforge-backend
   python -m venv venv
   source venv/Scripts/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
2. **Frontend:**
   ```bash
   cd classforge-frontend
   npm install
   npm run start
   ```
3. **Móvil:**
   ```bash
   cd classforge-mobile
   flutter pub get
   flutter run
   ```

### 7.3. Exposición Segura con Túnel Cloudflare
Para probar la aplicación en dispositivos móviles físicos a través de internet sin abrir puertos en el router:
```cmd
start_all_and_tunnel.bat
```
Genera una URL pública segura `https://*.trycloudflare.com` con soporte para HTTP/2 y WebSockets hacia el backend y frontend locales.

### 7.4. Credenciales de Prueba Pre-configuradas
| Rol | Nombre | Correo Electrónico | Contraseña | Capacidades |
|---|---|---|---|---|
| **Admin** | Administrador | `admin@classforge.com` | `Admin123!` | Control total, gestión de usuarios y configuraciones |
| **Scrum Master** | Alejandro | `alejandro@classforge.com` | `Admin123!` | Creación de proyectos, equipos y asignación de diagramas |
| **Developer** | Fernando | `fernando@classforge.com` | `Dev12345!` | Modelado en diagramas asignados y uso de NLU |
| **Developer** | Nicol | `nicol@classforge.com` | `Dev12345!` | Modelado colaborativo y generación de código |

---

## 8. Mecanismo de Actualización Automática de este Documento 🔄

Para garantizar que este documento se mantenga rigurosamente sincronizado con el código y el estado real del repositorio en todo momento, se ha implementado un mecanismo de automatización integral:

### 8.1. Script de Sincronización: `scripts/update_software_context.py`
El script inspecciona de forma introspectiva el estado del repositorio:
1. Extrae la rama Git activa, el hash del último commit, el autor y el mensaje.
2. Comprueba el estado del árbol de trabajo (archivos modificados, staged o pendientes).
3. Evalúa la presencia y estadísticas de las suites de prueba en `classforge-backend/tests`.
4. Reemplaza dinámicamente el bloque delimitado por `<!-- METADATOS_DINAMICOS_INICIO -->` y `<!-- METADATOS_DINAMICOS_FIN -->` en este archivo.

### 8.2. Hooks de Git (`pre-commit` y `post-commit`)
Se han instalado hooks automáticos en `.git/hooks/`:
* **Hook `pre-commit`:** Se ejecuta de forma transparente cada vez que un desarrollador o agente ejecuta `git commit`. Actualiza los metadatos de `contexto del software.md` y lo agrega al stage (`git add`), asegurando que cada commit contenga el estado documental exacto de los cambios aplicados.
* **Hook `post-commit`:** Confirma la sincronización y refresca el hash definitivo del commit recién generado.

### 8.3. Ejecución Manual
Cualquier desarrollador o proceso de CI/CD puede actualizar manualmente este documento en cualquier momento ejecutando:
```bash
python scripts/update_software_context.py
```
O con validación completa de pruebas backend:
```bash
python scripts/update_software_context.py --run-tests
```

---
*ClassForge Architecture & Engineering Team - Documentación viva y sincronizada con el código fuente.*
