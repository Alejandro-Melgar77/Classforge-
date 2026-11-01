# 30 — Generación de Código: Spring Boot y FastAPI

El módulo de generación de código de ClassForge (`app/modules/codegen/`) traduce automáticamente el modelo UML canónico a proyectos de backend ejecutables con arquitectura limpia y por capas.

## 1. Generador Spring Boot (`app/modules/codegen/generator.py`, `templates.py`)

Produce un proyecto Maven con Java 17 y Spring Boot 3.x estructurado en:
```
com.classforge.generated/
├── model/           # Entidades JPA (@Entity, @Table)
├── repository/      # Interfaces Spring Data JPA (JpaRepository)
├── service/         # Servicios de negocio (@Service, @Transactional)
├── controller/      # Controladores REST (@RestController, @RequestMapping)
├── dto/             # Data Transfer Objects
└── Application.java # Clase principal @SpringBootApplication
```

### Convenciones y Anotaciones JPA
- **Entidades**: Se anotan con `@Entity` y `@Table(name = "plural_snake_case")`.
- **Clave Primaria**: Se genera automáticamente `@Id` con `@GeneratedValue(strategy = GenerationType.IDENTITY)` si no se especifica.
- **Mapeo de Tipos**:
  - `String`, `varchar`, `text` → `java.lang.String`
  - `int`, `integer` → `java.lang.Integer`
  - `long`, `bigint` → `java.lang.Long`
  - `double`, `float`, `decimal` → `java.lang.Double`
  - `bool`, `boolean` → `java.lang.Boolean`
  - `date` → `java.time.LocalDate`
  - `datetime`, `timestamp` → `java.time.LocalDateTime`
- **Relaciones**:
  - Composición / Asociación 1 a N: `@ManyToOne(fetch = FetchType.LAZY)` en el hijo y `@OneToMany(mappedBy = "...", cascade = CascadeType.ALL)` en el padre.
  - Herencia: Mapeada con `@Inheritance(strategy = InheritanceType.JOINED)` o `@MappedSuperclass`.

## 2. Generador FastAPI (`app/modules/codegen/fastapi_generator.py`, `fastapi_templates.py`)

Produce un proyecto modular moderno en Python 3.10+ con SQLAlchemy 2.0 y Pydantic v2:
```
app/
├── models/         # Modelos declarativos SQLAlchemy (Base)
├── schemas/        # Esquemas de validación Pydantic (Base, Create, Response)
├── crud/           # Repositorios / Servicios CRUD
├── routers/        # Rutas APIRouter por entidad
├── database.py     # Sesión y motor de base de datos
└── main.py         # Punto de entrada de la aplicación FastAPI
```

### Convenciones Python
- **Nombres**:
  - Clases y esquemas en `PascalCase` (`Usuario`, `UsuarioCreate`, `UsuarioResponse`).
  - Tablas, columnas, atributos, variables y archivos en `snake_case` (`fecha_creacion`, `calcular_total()`).
  - Palabras reservadas protegidas (ej. `class`, `def`, `from` se sanean automáticamente).
- **Mapeo de Tipos**:
  - `String` → Python `str`, SQLAlchemy `String(255)`
  - `Integer` → Python `int`, SQLAlchemy `Integer`
  - `Float` / `Double` → Python `float`, SQLAlchemy `Float`
  - `Boolean` → Python `bool`, SQLAlchemy `Boolean`
  - `DateTime` → Python `datetime`, SQLAlchemy `DateTime`
- **Pydantic v2**:
  - Esquema `Response` con `model_config = ConfigDict(from_attributes=True)` para serialización ORM directa.

## Reglas que el Asistente de IA Debe Cuidar
1. Si un usuario solicita añadir campos o clases pensando en Spring Boot o FastAPI, asegurar nombres de atributos y clases válidos en ambos lenguajes.
2. Cada entidad persistible debe contar con un identificador unívoco (`id`).
3. Evitar atributos que colisionen con palabras clave de Java (`final`, `class`, `public`) o Python (`pass`, `yield`, `import`).
