# 00 — Producto ClassForge: Visión, Módulos y Flujos

ClassForge es una plataforma web colaborativa de ingeniería de software asistida por inteligencia artificial, diseñada para la concepción, modelado UML formal y generación de código de arquitecturas de software orientadas a objetos y microservicios.

## Módulos Principales del Sistema

1. **Autenticación y Seguridad (`app/modules/auth/`)**:
   - Registro e inicio de sesión con JWT (`access_token` de 60 min y `refresh_token` con rotación).
   - Control de sesiones en MongoDB (`sessions`), revocación en servidor vía `sid` (`/api/v1/auth/logout`) e invalidación automática por inactividad (`INACTIVITY_TIMEOUT_MINUTES`).
   - Rutas en `app/modules/auth/router.py`, modelos en `app/modules/auth/schemas.py`.

2. **Gestión de Usuarios y Equipos (`app/modules/users/`, `app/modules/teams/`)**:
   - Usuarios con roles de sistema: `admin`, `scrum_master`, `developer` (`app/modules/users/models.py`).
   - Equipos ágiles con asignación de Scrum Master y miembros desarrolladores (`app/modules/teams/service.py`).

3. **Proyectos y Espacios de Trabajo (`app/modules/projects/`)**:
   - Agrupador raíz de artefactos arquitecturales (`app/modules/projects/service.py`).
   - Asociación a equipos (`team_id`) y propietario (`owner_id`). Control de acceso estricto mediante políticas puras en `app/core/authz.py`.

4. **Modelado Visual y Diagramas UML (`app/modules/diagrams/`)**:
   - Persistencia de grafos estructurados en MongoDB (`diagrams.graph_data`).
   - Versionado histórico con instantáneas (`diagram_versions`) y rollback determinista.
   - Exportación e importación formal al estándar OMG XMI 2.1 (`app/modules/diagrams/service.py:generate_xmi`).

5. **Colaboración en Tiempo Real (`app/modules/collaboration/`)**:
   - Canal WebSocket dúplex `/ws/diagrams/{id}?token={ws_token}` (`app/modules/collaboration/router.py`).
   - Sistema de bloqueo pesimista en memoria por elemento (`NODE_LOCK`, `EDGE_LOCK`, `OP_REJECTED`).
   - Persistencia atómica en MongoDB sin condiciones de carrera (`app/modules/collaboration/service.py`).

6. **Generación de Código Backend (`app/modules/codegen/`)**:
   - Generación determinista y asistida por IA para Spring Boot (Java 17, JPA, Maven) en `app/modules/codegen/generator.py`.
   - Generación determinista y asistida para FastAPI (Python 3.10+, SQLAlchemy, Pydantic) en `app/modules/codegen/fastapi_generator.py`.
   - Empaquetado instantáneo en ZIP descargable y previsualización de archivos.

7. **Asistente y Equipo de IA Colaborativo (`app/modules/ai/`, `app/modules/ai_chat/`, `app/ai_team/`)**:
   - Procesamiento de lenguaje natural a comandos UML (`app/modules/ai/service.py`).
   - Ingeniería inversa visual a partir de bocetos o capturas de diagramas (`app/modules/ai/vision_service.py`).
   - Equipo multidisciplinario de roles de IA (`app/ai_team/domain/roles.py`) que interactúan en el chat grupal del proyecto, analizan el modelo con linter determinista (`app/ai_team/domain/lint.py`) y proponen cambios estructurados.

## Flujos de Trabajo Clave

- **Flujo de Modelado Colaborativo**: El usuario abre el canvas (`classforge-frontend/src/app/features/diagrams/canvas/`), obtiene un token WebSocket de un solo uso, interactúa con el canvas AntV X6; los cambios atómicos se sincronizan vía WebSocket y persisten en MongoDB.
- **Flujo de Asesoría de IA**: En el chat grupal (`/api/v1/ai-chat/projects/{id}/messages`), un rol de IA (ej. `architect` o `qa`) analiza el diagrama actual, ejecuta el linter determinista, evalúa las reglas de diseño y emite una respuesta estructurada con propuestas de comando UML (`UMLCommandResponse`), notas o tareas.
- **Flujo de Codegen**: Al completar el diagrama, el usuario invoca `/api/v1/codegen/{id}/download?framework=spring-boot|fastapi`; el motor analiza clases, atributos, métodos y multiplicidades para compilar un proyecto ejecutable con arquitectura en capas.
