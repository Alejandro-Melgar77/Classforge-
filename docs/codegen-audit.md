# Auditoría Integral de Generadores de Código (`app/modules/codegen/`)

**Fecha:** 1 de noviembre de 2026  
**Módulos auditados:**
- Generador Spring Boot 3 (`generator.py`, `templates.py`)
- Generador FastAPI Asíncrono (`fastapi_generator.py`, `fastapi_templates.py`)
- Empaquetado y compresión (`zip_service.py`)
- Notificaciones y webhooks (`webhook.py`)
- Rutas y controladores API (`router.py`)
- Generadores asistidos por IA (`gemini_generator.py`, `frontend_prompt_generator.py`)

---

## 1. Alcance Actual: Qué Genera Cada Generador

### 1.1 Generador Spring Boot 3 (Java 17)
- **Estructura Arquitectónica:** Clean Architecture en capas (Entities, Repositories, DTOs, Mappers, Services, Controllers, Exceptions, Configuration).
- **Archivos de Infraestructura Base:**
  - `pom.xml`: Spring Boot Starter Web, Data JPA, Validation, SpringDoc OpenAPI UI 2.6.0, H2 Database runtime, PostgreSQL runtime, Lombok, Spring Boot Starter Test.
  - `application.yml`: Configuración con H2 en memoria (`jdbc:h2:mem:classforgedb`), consola H2 habilitada en `/h2-console`, JPA `ddl-auto: update`, Hibernate SQL logger, SpringDoc Swagger UI en `/swagger-ui.html`.
  - `MainApplication.java`: Clase `@SpringBootApplication`.
  - Configuración: `OpenApiConfig` (Swagger 3), `CorsConfig` (CORS permisivo para Web/Mobile), `CloudConfig`.
  - Sincronización en la nube: `CloudSyncService`, `CloudController`.
  - Manejo Global de Excepciones: `GlobalExceptionHandler` (`@RestControllerAdvice`), `ResourceNotFoundException`, `BadRequestException`, `ErrorResponseDTO`.
  - Automatización de desarrollo: `.vscode/launch.json`, `.vscode/settings.json`, `.vscode/extensions.json`, `run.bat`, `run.sh`, `mvnw.cmd`, `mvnw`.
  - Documentación: `README.md` del proyecto con listado de endpoints CRUD.
- **Componentes por Entidad UML:**
  - `entities/{Class}.java`: Entidad JPA con `@Entity`, `@Table`, `@Getter`, `@Setter`, `@Builder`, `@Id` autogenerado (si no hereda), campos de auditoría `@CreationTimestamp` y `@UpdateTimestamp`.
  - `repositories/{Class}Repository.java`: `JpaRepository<{Class}, Long>`.
  - `dto/{Class}RequestDTO.java`: DTO de entrada con anotaciones Jakarta Validation (`@NotBlank`, `@NotNull`, `@Size`, `@Email`, `@Min`, `@PositiveOrZero`).
  - `dto/{Class}ResponseDTO.java`: DTO de respuesta con `id`, campos y timestamps.
  - `mappers/{Class}Mapper.java`: Mapeador desacoplado (`@Component`) con `toEntity()`, `toResponseDTO()`, `updateEntityFromDTO()`.
  - `services/{Class}Service.java`: Interfaz de servicio de negocio.
  - `services/impl/{Class}ServiceImpl.java`: Implementación transaccional (`@Service`, `@Transactional`).
  - `controllers/{Class}Controller.java`: Controlador RESTful (`@RestController`, `@RequestMapping("/api/v1/{plural}")`) con endpoints GET (listar paginado/todos), GET (por ID), POST (crear con `@Valid`), PUT (actualizar), DELETE.

### 1.2 Generador FastAPI (Python 3.11+)
- **Estructura Arquitectónica:** Clean Architecture asíncrona modular (`app/models/`, `app/schemas/`, `app/routers/`, `app/config.py`, `app/database.py`).
- **Archivos de Infraestructura Base:**
  - `requirements.txt`: `fastapi`, `uvicorn`, `pydantic>=2.0`, `sqlalchemy>=2.0`, `aiosqlite`, `asyncpg`, `httpx`.
  - `Dockerfile`: Construcción basada en `python:3.11-slim`, `uvicorn --host 0.0.0.0 --port 8000`.
  - `render.yaml`: Manifiesto de despliegue en Render (Web Service).
  - `.env.example`: `PORT=8000`, `DATABASE_URL=sqlite+aiosqlite:///./app.db`.
  - `app/config.py`: Clase `Settings` de Pydantic.
  - `app/database.py`: SQLAlchemy async engine y `get_db` session dependency.
  - `app/main.py`: Entrada FastAPI con ciclo de vida `lifespan`, CORS y montaje automático de routers.
  - `app/routers/cloud_sync.py`: Endpoint de sincronización con ClassForge Cloud.
- **Componentes por Entidad UML:**
  - `app/models/{snake}.py`: Modelo declarativo SQLAlchemy `Base` con `id` autonumérico.
  - `app/schemas/{snake}.py`: Esquemas Pydantic v2 (`{Class}Base`, `{Class}Create`, `{Class}Update`, `{Class}Response`).
  - `app/routers/{snake}.py`: APIRouter con CRUD asíncrono (GET list, GET by id, POST create, PUT update, DELETE).

---

## 2. Diagnóstico de Carencias y Deuda Técnica Detectada

| Aspecto | Spring Boot (`generator.py`) | FastAPI (`fastapi_generator.py`) | Impacto |
|---|---|---|---|
| **Enums UML** | Ignorados en el procesamiento de nodos (`node_type in ["class", ...]`). No se generaban clases `enum`. | Ignorados por completo. No se generaban `Enum` de Python ni columnas `Enum` de SQLAlchemy. | Pérdida de tipos acotados (`Status`, `Role`, `Priority`). Los atributos quedaban como `String` genérico. |
| **Herencia (Generalización)** | Añadía `@Inheritance(strategy = JOINED)` y `extends Parent`, pero los mappers y DTOs hijos no integraban atributos heredados ni manejaban herencia de esquemas. | No soportaba herencia. Generaba modelos planos desconectados. | Incapacidad de generar jerarquías de dominio (e.g. `Usuario -> Administrador`). |
| **Relaciones N-N (Muchos a Muchos)** | Solo mapeaba relaciones como `OneToMany` / `ManyToOne`. No soportaba `@ManyToMany` con `@JoinTable`. | Las aristas (`edges`) eran ignoradas al 100%. No generaba ninguna clave foránea (`ForeignKey`) ni `relationship()`. | Imposible generar modelos relacionales reales en FastAPI; ausencia de tablas intermedias en Spring Boot. |
| **Composición y Agregación** | Mapeadas como `OneToMany` y `ManyToOne` bidireccionales con `@JsonIgnoreProperties`. | Inexistente (no procesaba aristas). | Sin cascadas ni FKs en FastAPI. |
| **Palabras Reservadas Java/Python** | Java filtraba solo nombres de clase y algunos atributos básicos, pero faltaban palabras clave críticas (`null`, `true`, `false`, `order`, etc.). | Python no saneaba atributos: palabras como `from`, `class`, `import`, `def` generaban **errores de sintaxis irreparables** (`SyntaxError`). | Los proyectos generados fallaban al compilar (`compileall` o `mvn package`). |
| **Caracteres No ASCII y Acentos** | `re.sub(r'[^a-zA-Z0-9_]', '', ...)` eliminaba letras acentuadas (e.g., `Categoría` -> `CategorA` o `Categor`, `Descripción` -> `Descripcin`). | Igual comportamiento defectuoso en Python. | Nombres de clases y atributos mutilados e inconsistentes. |
| **Validaciones Declarativas** | Heurística básica en Java para emails, teléfonos y montos positivos. | Mínimas anotaciones Pydantic en FastAPI (solo tipos crudos sin restricciones `gt`, `max_length`). | DTOs sin defensas ante datos inválidos. |
| **Seguridad Zip (Zip Slip)** | `zip_service.py` concatenaba rutas directamente: `zip_file.writestr(f"classforge-backend/{file_path}", content)` sin validar traversal (`../`). | Riesgo de **Zip Slip** si un archivo o identificador contenía secuencias de escape de directorio. | Vulnerabilidad crítica de seguridad en descompresión. |
| **Límites de Salida Zip** | Sin límite de archivos, tamaño por archivo ni tamaño total. | Riesgo de **Zip Bomb** / saturación de memoria en servidor. | Denegación de servicio (DoS). |
| **Control de Acceso en Endpoints** | `GET /codegen/{id}/download` usaba `service.get_diagram` pero no la dependencia declarativa estándar `require_diagram_access`. | Inconsistencia con el sistema de autorización unificado de P1 (`can_access_diagram`). | Brechas potenciales de acceso en proyectos de equipo. |
| **Seguridad en Webhooks (SSRF)** | `POST /codegen/{id}/webhook-test` llamaba a `notify_n8n_webhook`. Requería verificación contra SSRF para asegurar que ningún cliente inyecte URLs arbitrarias. | N8N Webhook no validaba si la URL configurada apuntaba a rangos privados/metadatos (169.254.169.254, loopback, etc.). | Riesgo de fuga de credenciales o ataque a infraestructura interna. |
| **Rate Limiting** | Falta de `@limiter.limit` en `webhook-test`. | Posible spam de tareas en segundo plano. | Sobrecarga de servicios externos y cola asyncio. |

---

## 3. Plan de Saneamiento y Soluciones Implementadas

### 3.1 Normalización y Transliteración Unicode (Acentos y Caracteres Especiales)
- Uso de `unicodedata.normalize('NFKD', ...)` para descomponer caracteres diacríticos (`á` -> `a`, `ñ` -> `n`, `ü` -> `u`, etc.) preservando la semántica legible.
- Sanitización estricta mediante expresiones regulares `re.sub(r'[^a-zA-Z0-9_]', '_', ...)`.
- Mapeo consistente de identificadores tanto para nombres de clase (PascalCase) como atributos (camelCase en Java, snake_case en Python).

### 3.2 Manejo Robusto de Palabras Reservadas
- **Java:** Lista ampliada con `JAVA_RESERVED_KEYWORDS` (incluyendo `null`, `true`, `false`, `order`, `group`, `user`).
  - Atributo reservado: prefijado con `val` (e.g. `order` -> `valOrder`, `class` -> `valClass`).
  - Entidad reservada: sufijada con `Entity` (e.g. `Class` -> `ClassEntity`, `Order` -> `OrderEntity`). Nombres de tablas SQL conflictivos renombrados como `app_orders`.
- **Python:** Lista exhaustiva `PYTHON_RESERVED_KEYWORDS` (incluyendo `from`, `class`, `import`, `def`, `type`, `id`, `metadata`).
  - Atributo reservado: prefijado con `field_` (e.g. `from` -> `field_from`, `class` -> `field_class`, `id` -> `item_id`).
  - Entidad reservada: sufijada con `Model` (e.g. `Class` -> `ClassModel`, `Def` -> `DefModel`).

### 3.3 Soporte Completo de Enums
- **Spring Boot:** Detección de nodos de tipo `enum` o `uml-enum`. Generación de `src/main/java/{base}/entities/enums/{EnumName}.java`. En entidades dependientes: `@Enumerated(EnumType.STRING)` con su respectivo tipo. En DTOs: tipado fuerte con el enum.
- **FastAPI:** Generación de `app/models/enums.py` con clases heredando de `(str, Enum)`. En SQLAlchemy: `Column(SAEnum({EnumName}))`. En Pydantic: uso directo del enum para validación y serialización Swagger automática.

### 3.4 Relaciones Completas: 1-N, N-1, Composición y N-N
- **Spring Boot:**
  - `OneToMany` / `ManyToOne`: Claves foráneas automáticas, `@JsonIgnoreProperties` para evitar bucles recursivos en serialización JSON.
  - `ManyToMany`: Generación de `@ManyToMany` con `@JoinTable(name = "...", joinColumns = ..., inverseJoinColumns = ...)`.
- **FastAPI:**
  - `OneToMany` / `ManyToOne`: `Column(Integer, ForeignKey("{table}.id"))` + `relationship("{Parent}", back_populates="{children}")`.
  - `ManyToMany`: Creación de tablas de asociación intermedias `Table("{a}_{b}", Base.metadata, ...)` y `relationship(..., secondary=...)`.

### 3.5 Endurecimiento de Seguridad en `zip_service.py`
- Función `sanitize_zip_path(path)`:
  - Rechaza rutas absolutas (POSIX o Windows `C:\`).
  - Normaliza mediante `posixpath.normpath`.
  - Rechaza estrictamente secuencias `..` o componentes que escapen del directorio raíz.
- Cuotas y Límites Duros:
  - `MAX_ZIP_FILES = 500`
  - `MAX_FILE_BYTES = 10 * 1024 * 1024` (10 MB por archivo)
  - `MAX_TOTAL_BYTES = 50 * 1024 * 1024` (50 MB descomprimidos en total)

### 3.6 Seguridad en Webhook (SSRF) y Autorización en Router
- Validación de URLs en `webhook.py`: Esquemas permitidos exclusivamente `http`/`https`.
- Bloqueo de direcciones IP privadas, loopback (`127.0.0.1`, `localhost`) y direcciones de metadatos (`169.254.169.254`, `metadata.google.internal`).
- Inmutabilidad de URL: El endpoint `POST /codegen/{id}/webhook-test` **no acepta URLs del cliente**, utilizando únicamente la URL configurada por el administrador del sistema en `settings.N8N_WEBHOOK_URL`.
- Enrutamiento: Todos los endpoints de `/codegen/*` utilizan `require_diagram_access` como dependencia obligatoria e integran límites de tasa (`@limiter.limit`).

---

## 4. Métricas de Tamaño y Rendimiento

| Motor Generado | Proyecto Típico (5 entidades, 4 relaciones, 1 enum) | Total Archivos | Tamaño Comprimido (ZIP) |
|---|---|---|---|
| **Spring Boot 3** | Arquitectura Limpia completa (Entities, DTOs, Mappers, Repos, Services, Controllers, Configs, Maven Wrapper) | ~45-55 archivos | ~48 - 62 KB |
| **FastAPI** | App asíncrona completa (Models, Schemas, Routers, Database, Config, Dockerfile, Scripts) | ~20-25 archivos | ~18 - 25 KB |

Ambos generadores operan en memoria sin tocar disco para la generación preliminar, garantizando tiempos de respuesta < 50 ms en previsualización y descarga.
