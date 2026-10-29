# DOCUMENTACIÓN TÉCNICA MAESTRA: PROYECTO CLASSFORGE 🚀

> **Documento de Contexto y Especificación Arquitectónica Integral**  
> **Destinatarios:** Ingenieros de Software, Arquitectos de Sistemas y Modelos de Inteligencia Artificial (LLMs).  
> **Propósito:** Proporcionar la totalidad del conocimiento arquitectónico, funcional, operativo y técnico del sistema ClassForge en un único documento autocontenido.

---

## 1. Manifiesto y Propósito del Proyecto

**ClassForge** es una plataforma de software distribuida y colaborativa concebida para el **modelado conceptual UML 2.5+**, la **generación automatizada de código de grado de producción (Clean Architecture)** y la **asistencia inteligente mediante Procesamiento de Lenguaje Natural (NLU) y comandos de voz**. 

El sistema fue diseñado bajo el principio fundamental **Offline-First & Cloud-Ready**:
- Opera de forma autónoma en entornos desconectados (con motores NLU heurísticos y validaciones locales en sub-milisegundos).
- Ofrece capacidades aumentadas en la nube mediante modelos multimodales **Google Gemini** (`gemini-3.8-flash` y Gemini Multimodal Vision) o servidores locales **Ollama**.
- Integra colaboración concurrente en tiempo real mediante **WebSockets nativos**, bloqueo optimista de elementos (*node locks*) y sincronización de cursores multi-usuario.

---

## 2. Mapa del Repositorio y Arquitectura Global

El repositorio es un monorepo modular organizado en tres aplicaciones principales y herramientas de orquestación:

```
Classforge-/
├── classforge-backend/            # API RESTful asíncrona, WebSockets, NLU heurístico y Codegen (Python / FastAPI)
│   ├── app/
│   │   ├── core/                  # Configuración, Base de Datos, Seguridad, Middleware
│   │   │   ├── config.py          # Configuración tipada vía Pydantic BaseSettings
│   │   │   ├── database.py        # Driver asíncrono Motor para MongoDB
│   │   │   ├── dependencies.py    # Inyectores de dependencias FastAPI (get_current_user, RBAC)
│   │   │   ├── middleware.py      # Rate limiting (SlowAPI) y manejadores de excepción
│   │   │   └── security.py        # Cifrado Bcrypt y emisión/validación de JWT (Access/Refresh)
│   │   ├── modules/
│   │   │   ├── ai/                # Motor NLU heurístico, Vision Service (Gemini) y cliente Ollama
│   │   │   ├── auth/              # Endpoints de autenticación, renovación y control de inactividad
│   │   │   ├── codegen/           # Generadores de código Spring Boot 3, FastAPI, Prompts UI y Zip
│   │   │   ├── collaboration/     # ConnectionManager, WebSockets, presencia, cursores y locks
│   │   │   ├── dashboard/         # Endpoints de agregación de métricas y analítica
│   │   │   ├── diagrams/          # CRUD de diagramas, versionado, rollback y exportación XMI 2.1
│   │   │   ├── folders/           # Agrupamiento jerárquico de diagramas
│   │   │   ├── notifications/     # Centro de notificaciones in-app persistidas
│   │   │   ├── projects/          # Organización de proyectos (personales y de equipo)
│   │   │   ├── teams/             # Gestión de equipos ágiles y Scrum Masters
│   │   │   └── users/             # Perfiles de usuario y gestión administrativa
│   │   └── main.py                # Entrada principal FastAPI, ciclo lifespan y middleware CORS
│   ├── tests/                     # Batería de pruebas unitarias e integración con pytest
│   ├── Dockerfile                 # Contenedorización multi-stage backend
│   ├── requirements.txt           # Dependencias de Python
│   ├── seed_users.py              # Script inicializador de usuarios
│   └── seed_team_and_users.py     # Script integral de usuarios y equipos demo
│
├── classforge-frontend/           # SPA interactiva y diagramador vectorial (Angular 17 / AntV X6)
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/              # Guards (auth, role), Interceptors (JWT Bearer) y AuthService
│   │   │   ├── features/
│   │   │   │   ├── admin/         # Gestión de usuarios, equipos y configuración global
│   │   │   │   ├── auth/          # Login, Registro y recuperación
│   │   │   │   ├── dashboard/     # Métricas de actividad, accesos rápidos y proyectos
│   │   │   │   ├── diagrams/      # NÚCLEO: Canvas AntV X6, Nodos SVG, Asistente NLU, Codegen
│   │   │   │   ├── projects/      # Repertorio de proyectos, carpetas y tarjetas de estado
│   │   │   │   └── support/       # Asistente de soporte NLU y tours guiados interactivos
│   │   │   ├── layout/            # Shell general, sidebar y header responsive
│   │   │   └── shared/            # Componentes reutilizables, modales y pipes
│   │   └── environments/          # Variables de entorno (producción Render y desarrollo local)
│   ├── Dockerfile                 # Construcción en Node 18/20 y publicación en NGINX
│   ├── nginx.conf                 # Configuración de NGINX con reescritura para SPA
│   ├── package.json               # Dependencias de npm
│   └── tailwind.config.js         # Tema visual personalizado Forge Dark / Light
│
├── classforge-mobile/             # App móvil nativa (Flutter 3.x / Dart 3.x)
│   ├── lib/
│   │   ├── core/
│   │   │   ├── constants/         # URLs de red (10.0.2.2 para emulador, IP LAN o Render)
│   │   │   ├── services/          # API REST, WebSockets, NLU on-device y Notificaciones locales
│   │   │   └── theme/             # Tema "Forge Dark Professional"
│   │   ├── models/                # Modelos de datos Dart (Diagram, Project, Team, User, Notification)
│   │   ├── screens/               # Pantallas (Dashboard, Visor UML Readonly, Asistente, Test Panel)
│   │   └── widgets/               # CustomPainters UML y tarjetas táctiles interactivas
│   ├── test/                      # Tests unitarios Dart (NLU <1ms y serialización)
│   └── pubspec.yaml               # Dependencias de Flutter
│
├── docker-compose.yml             # Orquestador multi-contenedor (MongoDB 6, FastAPI, NGINX)
├── start_local.bat                # Script de inicio local 100% offline en Windows
├── start_all_and_tunnel.bat       # Script de inicio con túnel Cloudflare HTTPS público
└── README.md                      # Documentación introductoria rápida
```

---

## 3. Matriz Tecnológica y Versiones

| Módulo | Componente / Capa | Tecnología / Biblioteca | Versión | Rol y Justificación |
|---|---|---|---|---|
| **Backend** | Runtime & Core | Python | 3.11 / 3.12 / 3.14 | Lenguaje base tipado y asíncrono |
| **Backend** | Framework Web | FastAPI | `>=0.103.2` | Enrutamiento asíncrono ASGI de alto rendimiento |
| **Backend** | Servidor ASGI | Uvicorn (standard) | `>=0.23.2` | Servidor HTTP y WebSockets de baja latencia |
| **Backend** | Base de Datos | MongoDB | 6.0 | Base documental flexible para grafos y JSONs de diagramas |
| **Backend** | Driver Asíncrono | Motor | `>=3.3.1` | Cliente no bloqueante para MongoDB |
| **Backend** | Validación / Tipado | Pydantic / Pydantic Settings | `>=2.4.2` | Validación en tiempo de ejecución y tipado estricto |
| **Backend** | Seguridad & Auth | python-jose + passlib[bcrypt] | `>=3.3.0` / `>=1.7.4` | Cifrado de contraseñas y firma JWT (HS256) |
| **Backend** | Rate Limiting | SlowAPI | `>=0.1.8` | Protección contra fuerza bruta y DoS en endpoints |
| **Backend** | Cliente HTTP | HTTPX | `>=0.25.0` | Conexión asíncrona hacia Gemini API y Ollama |
| **Frontend** | Framework SPA | Angular | 17.0.0 | Arquitectura basada en componentes Standalone y Signals |
| **Frontend** | Motor Gráfico UML | @antv/x6 | `2.18.1` | Renderizado SVG interactivo de diagramas y grafos |
| **Frontend** | Extensiones Canvas | @antv/x6-plugins | `~2.1` | Minimapa, historial, snapline, portapapeles, atajos |
| **Frontend** | Estilos UI | TailwindCSS | `3.4.1` | Sistema de utilidades CSS moderno con modo oscuro |
| **Frontend** | Iconografía | lucide-angular | `0.330.0` | Conjunto de iconos vectoriales consistentes |
| **Frontend** | Exportación PDF | jspdf + html2canvas | `2.5.1` / `1.4.1` | Renderizado y descarga de planos en PDF vectorial |
| **Mobile** | Framework Móvil | Flutter SDK | `>=3.0.0 <4.0.0` | Renderizado nativo multiplataforma (Android / iOS) |
| **Mobile** | Estado y Contexto | Provider | `^6.1.1` | Inyección de estado y reactividad |
| **Mobile** | WebSockets Móvil | web_socket_channel | `^3.0.3` | Comunicación bidireccional continua con el backend |
| **Mobile** | Reconocimiento Voz | speech_to_text | `^7.5.0` | Captura de audio y transcripción nativa en el dispositivo |
| **Mobile** | Notificaciones | flutter_local_notifications | `^21.0.0` | Alertas de sistema sin requerir servicios externos (FCM) |
| **Infra** | Contenedores | Docker & Docker Compose | Engine 28+ | Empaquetado portable de base de datos y servicios |
| **Infra** | Servidor Web Prod | NGINX | Alpine | Proxy inverso y servidor estático de la SPA Angular |
| **Infra** | Red de Pruebas | Cloudflare Tunnel | cloudflared CLI | Exposición pública segura con túnel HTTP/2 HTTPS |

---

## 4. Esquema de Base de Datos (MongoDB)

ClassForge utiliza MongoDB por su capacidad de almacenar esquemas variables correspondientes a los modelos UML (`graph_data` con nodos y aristas de AntV X6).

### 4.1. Colección: `users`
Almacena las cuentas de usuario y sus credenciales:
```json
{
  "_id": "ObjectId",
  "name": "Alejandro Melgar",
  "email": "alejandro@classforge.com",
  "password_hash": "$2b$12$...",
  "role": "admin" | "scrum_master" | "dev",
  "avatar_url": null,
  "team_ids": ["ObjectId"],
  "is_active": true,
  "is_deleted": false,
  "deleted_at": null,
  "last_activity": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 4.2. Colección: `teams`
Modela los equipos de desarrollo conforme al marco de trabajo Scrum:
```json
{
  "_id": "ObjectId",
  "name": "Equipo Alfa",
  "description": "Desarrollo del módulo Core",
  "scrum_master_id": "ObjectId",
  "member_ids": ["ObjectId"],
  "is_deleted": false,
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 4.3. Colección: `projects`
Espacios de trabajo organizacionales que agrupan diagramas y carpetas:
```json
{
  "_id": "ObjectId",
  "name": "Sistema Bancario Central",
  "description": "Modelado de microservicios y pagos",
  "type": "team" | "personal",
  "team_id": "ObjectId | null",
  "owner_id": "ObjectId",
  "status": "in_progress" | "completed" | "archived",
  "is_deleted": false,
  "created_by": "ObjectId",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 4.4. Colección: `folders`
Estructura en árbol opcional dentro de cada proyecto:
```json
{
  "_id": "ObjectId",
  "name": "Módulo de Facturación",
  "project_id": "ObjectId",
  "parent_id": "ObjectId | null",
  "created_by": "ObjectId",
  "is_deleted": false,
  "created_at": "ISODate"
}
```

### 4.5. Colección: `diagrams`
Entidad principal del sistema que almacena el grafo conceptual y su historial:
```json
{
  "_id": "ObjectId",
  "name": "Diagrama de Dominio E-Commerce",
  "description": "Clases para carrito, pedidos y clientes",
  "project_id": "ObjectId",
  "team_id": "ObjectId | null",
  "folder_id": "ObjectId | null",
  "image_url": "String | null",
  "created_by": "ObjectId",
  "member_ids": ["ObjectId"],
  "status": "draft" | "review" | "approved",
  "is_deleted": false,
  "graph_data": {
    "nodes": [
      {
        "id": "node-uuid-1",
        "shape": "classNode" | "interfaceNode" | "abstractNode" | "enumNode" | "packageNode" | "noteNode",
        "x": 100,
        "y": 120,
        "width": 240,
        "height": 180,
        "data": {
          "name": "Usuario",
          "stereotype": null,
          "attributes": [
            { "name": "id", "type": "Long", "visibility": "+", "is_static": false },
            { "name": "email", "type": "String", "visibility": "-", "is_static": false }
          ],
          "methods": [
            { "name": "autenticar", "params": "pass: String", "return_type": "Boolean", "visibility": "+", "is_abstract": false }
          ]
        }
      }
    ],
    "edges": [
      {
        "id": "edge-uuid-1",
        "source": "node-uuid-1",
        "target": "node-uuid-2",
        "type": "association" | "inheritance" | "composition" | "aggregation" | "dependency" | "realization",
        "data": {
          "sourceMultiplicity": "1",
          "targetMultiplicity": "0..*",
          "label": "realiza"
        }
      }
    ]
  },
  "history": [
    {
      "version": 1,
      "saved_by": "ObjectId",
      "saved_at": "ISODate",
      "comment": "Creación inicial con NLU",
      "graph_data": { "..." }
    }
  ],
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 4.6. Colección: `audit_logs`
Registro de trazabilidad de acciones críticas para control de calidad:
```json
{
  "_id": "ObjectId",
  "action": "CREATE_DIAGRAM" | "SAVE_GRAPH" | "DELETE_DIAGRAM" | "ROLLBACK_GRAPH" | "UPDATE_PARTICIPANTS",
  "user_id": "ObjectId",
  "diagram_id": "ObjectId | null",
  "timestamp": "ISODate",
  "metadata": { "..." }
}
```

### 4.7. Colección: `notifications`
Alertas generadas por interacciones del equipo:
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "title": "Asignado a nuevo diagrama",
  "message": "Alejandro te asignó como participante en 'Facturación'",
  "diagram_id": "ObjectId | null",
  "is_read": false,
  "created_at": "ISODate"
}
```

---

## 5. Arquitectura Detallada del Backend (`classforge-backend`)

### 5.1. Ciclo de Vida y Middlewares (`app/main.py` y `app/core/`)
- **Lifespan Context Manager:** Gestiona la apertura de conexión a MongoDB (`connect_to_mongo()`) al arrancar Uvicorn y el cierre ordenado de pools de sockets (`close_mongo_connection()`) al terminar.
- **CORS Dinámico:** Configurado mediante `CORS_ORIGINS` y complementado con expresión regular (`allow_origin_regex=r"https://.*\.trycloudflare\.com"`) para admitir túneles de desarrollo de Cloudflare sin recompilar.
- **Rate Limiting:** Implementado con `SlowAPI` sobre las rutas sensibles de autenticación (`/auth/login`) para evitar ataques de fuerza bruta.

### 5.2. Autenticación y Control de Sesión
- **Esquema de Tokens:** Genera un `access_token` JWT firmado con HMAC-SHA256 (`SECRET_KEY`), con expiración por defecto de 15 a 60 minutos, y un `refresh_token` con validez de 7 días.
- **Timeout por Inactividad:** Se valida en cada petición contra la marca de tiempo `last_activity` del usuario en la base de datos (`INACTIVITY_TIMEOUT_MINUTES = 30`). Si se supera dicho límite, la petición es rechazada con código HTTP 401.

### 5.3. Sistema de Roles (RBAC)
La matriz de permisos se resuelve mediante dependencias en `dependencies.py`:
- `admin`: Superusuario. Administra usuarios, configuraciones globales, equipos y tiene acceso de lectura/escritura/borrado sobre cualquier proyecto o diagrama.
- `scrum_master`: Administrador de proyectos y equipos asignados. Puede crear proyectos, asignar participantes a diagramas y modificar metadatos.
- `dev`: Desarrollador. Solo puede visualizar y colaborar en los diagramas donde figure explícitamente en la lista `member_ids` o en aquellos que hayan sido creados por él.

### 5.4. Motor NLU Heurístico (`app/modules/ai/heuristic_engine.py`)
Un componente crítico del proyecto que garantiza autonomía frente a fallos de red o falta de saldo en APIs de IA:
1. **Normalizador:** Descompone acentos ortográficos (Unicode NFD) y limpia caracteres especiales conservando números y letras.
2. **Inferencia Automática de Tipos en Atributos:**
   - Si el atributo se llama `id`, `usuario_id`, `codigo` $\rightarrow$ `Long`
   - Si incluye `precio`, `total`, `monto`, `saldo`, `sueldo`, `costo`, `tarifa` $\rightarrow$ `Double`
   - Si incluye `stock`, `cantidad`, `edad`, `nro`, `anio`, `semestre` $\rightarrow$ `Integer`
   - Si incluye `fecha`, `date`, `nacimiento`, `creado` $\rightarrow$ `Date`
   - Si comienza con `es`, `is` o contiene `activo`, `valido`, `habilitado` $\rightarrow$ `Boolean`
   - En cualquier otro caso $\rightarrow$ `String`
3. **Mapeo de Cardinalidades Idiomáticas:**
   - *"uno a muchos"*, *"1 a \*"*, *"1 a n"* $\rightarrow$ `(1, 1..*)`
   - *"cero a muchos"*, *"0 a \*"* $\rightarrow$ `(1, 0..*)`
   - *"muchos a uno"*, *"\* a 1"* $\rightarrow$ `(0..*, 1)`
   - *"muchos a muchos"*, *"\* a \*"* $\rightarrow$ `(0..*, 0..*)`
   - *"uno a uno"*, *"1 a 1"* $\rightarrow$ `(1, 1)`
4. **Plantillas de Sistemas Integrales:**
   - Comandos como *"generar sistema e-commerce"*, *"crear facturacion"*, *"sistema bancario"* o *"sistema hospital"* generan de forma inmediata colecciones completas de 4 a 6 clases UML conectadas por herencias, composiciones y asociaciones con sus multiplicidades y atributos base.
5. **Rendimiento:** Ejecución en menos de 0.5 milisegundos con cero dependencias de memoria externa.

### 5.5. Servicio de Visión Computacional (`app/modules/ai/vision_service.py`)
- Recibe imágenes de diagramas UML (fotos de pizarras, bosquejos a lápiz o capturas de pantalla) en base64.
- Invoca la API de **Gemini** con un prompt de arquitectura estricto que exige un esquema JSON puro con clases, atributos, métodos y relaciones.
- Ejecuta una rutina de **Auto-Layout en Cuadrícula** ($Cols = 3$, ancho de nodo $240\text{ px}$, alto base $140\text{ px}$, con separaciones calculadas) para transformar el JSON semántico en celdas válidas de AntV X6 compatibles con el lienzo del frontend.

### 5.6. Motor de Generación de Código (`app/modules/codegen/`)
Transforma la estructura de nodos y aristas del diagrama en aplicaciones de backend listas para producción:

#### A) Spring Boot 3 (Clean Architecture / DDD) — [`generator.py`](file:///c:/Users/Ale/Documents/SW1%202-2026/segundo%20examen%20parcial/classforge-backend/app/modules/codegen/generator.py)
Genera un proyecto Maven estructurado:
- `pom.xml`: Incluye `spring-boot-starter-web`, `spring-boot-starter-data-jpa`, `springdoc-openapi-starter-webmvc-ui` y base de datos relacional.
- **Entidades JPA:** Con anotaciones de persistencia (`@Entity`, `@Table`, `@Id`, `@GeneratedValue`), relaciones (`@OneToMany`, `@ManyToOne`, `@ManyToMany`) y validaciones Jakarta (`@NotBlank`, `@Email`, `@NotNull`, `@Min`, `@PositiveOrZero`).
- **DTOs:** Objetos de transferencia (`RequestDTO` y `ResponseDTO`) desacoplados del modelo de datos de persistencia.
- **Repositorios:** Interfaces que extienden `JpaRepository<T, ID>` con métodos de consulta.
- **Servicios:** Capa de lógica de negocio transaccional (`@Service`, `@Transactional`).
- **Controladores REST:** Puntos de entrada HTTP con anotaciones OpenAPI 3 (`@RestController`, `@Tag`, `@Operation`).
- **Manejo Global de Errores:** `@ControllerAdvice` con respuestas estructuradas ante validaciones fallidas y recursos no encontrados.
- **Configuración de Ejecución:** Scripts `run.bat`, `run.sh`, wrappers Maven (`mvnw`, `mvnw.cmd`) y configuraciones de VS Code (`.vscode/launch.json`).

#### B) FastAPI (Python) — [`fastapi_generator.py`](file:///c:/Users/Ale/Documents/SW1%202-2026/segundo%20examen%20parcial/classforge-backend/app/modules/codegen/fastapi_generator.py)
Genera modelos declarativos en SQLAlchemy 2.0, esquemas de entrada y salida con Pydantic v2 y rutas asíncronas con operaciones CRUD estándar.

#### C) Empaquetado en Memoria (`zip_service.py`)
Construye dinámicamente un archivo `.zip` en memoria (`io.BytesIO`) con la jerarquía completa de directorios del proyecto generado para su descarga directa mediante `StreamingResponse`.

### 5.7. Exportación a XMI 2.1 OMG
En `diagrams/service.py`, la función `generate_xmi()` serializa los grafos en el estándar formal de intercambio **XMI 2.1** bajo el espacio de nombres de **Eclipse UML 2.5** (`http://www.eclipse.org/uml2/5.0.0/UML`). Esto permite que los diagramas construidos en ClassForge puedan ser importados directamente en suites de modelado enterprise como *Enterprise Architect*, *Visual Paradigm* o *StarUML*.

### 5.8. Colaboración en Tiempo Real (`app/modules/collaboration/`)
- Mantiene salas WebSocket aisladas por `diagram_id` en `ConnectionManager`.
- **Presencia:** Informa a los clientes cuando un usuario se conecta o desconecta, transmitiendo nombre, rol y un color identificativo determinista.
- **Multi-Cursor:** Emite eventos `cursor_move` con coordenadas normalizadas para mostrar punteros en tiempo real.
- **Bloqueo Optimista de Nodos (`node_lock`):** Cuando un usuario hace foco en una clase para editarla, el nodo queda bloqueado para el resto de usuarios de la sala, previniendo condiciones de carrera y sobrescrituras destructivas. El bloqueo se libera automáticamente al desenfocar o al desconectarse el usuario.
- **Chat Integrado:** Historial de mensajería efímero en memoria transmitido a todos los colaboradores del diagrama.

---

## 6. Arquitectura Detallada del Frontend (`classforge-frontend`)

### 6.1. Estructura y Patrones de Angular 17
- **Standalone Components:** Elimina la necesidad de `AppModule` y submódulos; cada componente declara sus dependencias directas en `imports: [...]`.
- **Inyección Funcional:** Uso extensivo de `inject(ServiceName)` en lugar de inyecciones de constructor verbozas.
- **ChangeDetectionStrategy.OnPush:** Optimización de renderizado para evitar comprobaciones innecesarias en el ciclo de detección de cambios durante la edición intensiva del lienzo.
- **Signals y Efectos:** Empleados para el control reactivo de estados (paneles abiertos/cerrados, selección actual, lista de colaboradores).

### 6.2. Motor de Diagramado Vectorial AntV X6
- Implementado en [`diagram-canvas.component.ts`](file:///c:/Users/Ale/Documents/SW1%202-2026/segundo%20examen%20parcial/classforge-frontend/src/app/features/diagrams/canvas/diagram-canvas.component.ts) con soporte para:
  - **Grid interactivo:** Puntos y rejilla magnética para facilitar la alineación de componentes.
  - **Nodos UML personalizados ([`uml-nodes.ts`](file:///c:/Users/Ale/Documents/SW1%202-2026/segundo%20examen%20parcial/classforge-frontend/src/app/features/diagrams/nodes/uml-nodes.ts)):** Nodos divididos en compartimentos estándar UML (título con estereotipo, atributos y métodos). Cálculo dinámico de altura para evitar desbordes de texto.
  - **Marcadores de Estereotipos:** Distinción visual inmediata de `<<interface>>` (verde azulado), `<<abstract>>` (púrpura), `<<enum>>` (ámbar), clases estándar (azul) y notas explicativas (amarillo/pizarra).
  - **Relaciones Vectoriales:** Flechas dirigidas, triángulos cerrados para herencia, rombos rellenos para composición, rombos vacíos para agregación y líneas segmentadas para dependencias.
  - **Minimapa:** Visualizador flotante interactivo para navegación en diagramas extensos.
  - **Gestión de Historial:** Pila de operaciones con atajos universales (Ctrl+Z para deshacer, Ctrl+Y para rehacer).

### 6.3. Asistente NLU y Reconocimiento de Voz Web
- **Web Speech API:** Captura continua mediante el micrófono a través de `voice-recognition.service.ts`.
- **NLU en el Navegador ([`nlu-parser.service.ts`](file:///c:/Users/Ale/Documents/SW1%202-2026/segundo%20examen%20parcial/classforge-frontend/src/app/features/diagrams/ai-assistant/services/nlu-parser.service.ts)):** Implementación homóloga en TypeScript del motor heurístico del backend. Permite al usuario hablar o escribir y previsualizar los cambios en tarjetas interactivas (`command-preview-card.component`) antes de inyectarlos al canvas.

### 6.4. Drawer de Código en Vivo (`live-code-drawer.component.ts`)
- Panel lateral deslizable que muestra en tiempo real la traducción del modelo a código ejecutable.
- Árbol de navegación interactivo de archivos y carpetas del backend.
- Resaltado de sintaxis optimizado de un solo paso (*single-pass syntax highlighting*) y botón de descarga directa del paquete `.zip`.

---

## 7. Arquitectura Detallada de la Aplicación Móvil (`classforge-mobile`)

### 7.1. Principios y Decisiones de Diseño
1. **Visor 100% Solo Lectura (Readonly):** Los diagramas UML requieren precisión milimétrica para edición, tarea ideal para el entorno de escritorio. En la app móvil, el canvas está restringido a exploración mediante gestos táctiles (*pinch-to-zoom*, *pan* a 60 FPS con `InteractiveViewer`) e inspección de detalles de clases y métodos sin riesgo de alterar el modelo accidentalmente.
2. **Motor NLU On-Device en Dart ([`offline_nlu_service.dart`](file:///c:/Users/Ale/Documents/SW1%202-2026/segundo%20examen%20parcial/classforge-mobile/lib/core/services/offline_nlu_service.dart)):** Ejecuta la lógica de interpretación de comandos en el procesador del teléfono móvil en menos de $1\text{ ms}$, sin necesidad de descargar modelos de lenguaje pesados.
3. **Notificaciones Colaborativas Nativas:** Conexión directa mediante WebSockets al backend para recibir notificaciones cuando otros usuarios editan un diagrama o envían mensajes al chat, mostrando alertas locales con `flutter_local_notifications`.
4. **Panel de Diagnóstico y Pruebas ([`test_panel_screen.dart`](file:///c:/Users/Ale/Documents/SW1%202-2026/segundo%20examen%20parcial/classforge-mobile/lib/screens/test_panel/test_panel_screen.dart)):** Herramienta integrada en la aplicación que permite evaluar en vivo la latencia del NLU, probar alertas locales y verificar la integridad de la conexión WebSocket.

---

## 8. Catálogo de Endpoints de la API REST

Prefijo global: `/api/v1`

### 8.1. Autenticación (`/auth`)
| Método | Ruta | Descripción | Rol Mínimo |
|---|---|---|---|
| `POST` | `/auth/register` | Registro de nuevos usuarios | Público |
| `POST` | `/auth/login` | Inicio de sesión, retorna JWT access y refresh token | Público |
| `POST` | `/auth/refresh` | Renovación del access token mediante refresh token | Público |
| `GET` | `/auth/me` | Obtiene el perfil del usuario autenticado | Autenticado |
| `POST` | `/auth/logout` | Cierre de sesión e invalidación | Autenticado |

### 8.2. Usuarios (`/users`)
| Método | Ruta | Descripción | Rol Mínimo |
|---|---|---|---|
| `GET` | `/users/` | Listado paginado de usuarios | `admin` |
| `GET` | `/users/{id}` | Detalle de un usuario específico | Autenticado |
| `PUT` | `/users/{id}` | Actualización de perfil o roles | `admin` / Propietario |
| `DELETE` | `/users/{id}` | Baja lógica del usuario | `admin` |

### 8.3. Equipos (`/teams`)
| Método | Ruta | Descripción | Rol Mínimo |
|---|---|---|---|
| `GET` | `/teams/` | Listar equipos del usuario | Autenticado |
| `POST` | `/teams/` | Crear un nuevo equipo ágil | `admin` / `scrum_master` |
| `GET` | `/teams/{id}` | Detalle del equipo y miembros | Miembro del equipo |
| `PUT` | `/teams/{id}` | Modificar equipo o Scrum Master asignado | `admin` / `scrum_master` |
| `DELETE` | `/teams/{id}` | Eliminar equipo | `admin` |

### 8.4. Proyectos y Carpetas (`/projects`, `/folders`)
| Método | Ruta | Descripción | Rol Mínimo |
|---|---|---|---|
| `GET` | `/projects/` | Listar proyectos accesibles | Autenticado |
| `POST` | `/projects/` | Crear proyecto personal o de equipo | Autenticado |
| `GET` | `/projects/{id}` | Consultar detalle de proyecto | Miembro / Propietario |
| `PUT` | `/projects/{id}` | Actualizar datos del proyecto | `admin` / Propietario |
| `DELETE` | `/projects/{id}` | Baja lógica del proyecto | `admin` / Propietario |
| `POST` | `/folders/` | Crear carpeta contenedora de diagramas | Autenticado |

### 8.5. Diagramas (`/diagrams`)
| Método | Ruta | Descripción | Rol Mínimo |
|---|---|---|---|
| `GET` | `/diagrams/` | Listado de diagramas según permisos RBAC | Autenticado |
| `POST` | `/diagrams/` | Creación de nuevo diagrama UML | Autenticado |
| `GET` | `/diagrams/{id}` | Obtener grafo, metadatos y participantes | Asignado / SM / Admin |
| `PUT` | `/diagrams/{id}` | Actualizar metadatos del diagrama | `admin` / SM / Creador |
| `POST` | `/diagrams/{id}/save` | Guardar grafo con nueva versión en historial | Asignado / SM / Admin |
| `GET` | `/diagrams/{id}/participants` | Consultar participantes asignados y disponibles | Autenticado |
| `PUT` | `/diagrams/{id}/participants` | Asignar o revocar participantes | `admin` / SM / Creador |
| `POST` | `/diagrams/{id}/rollback/{version}`| Restaurar grafo a una versión previa | `admin` / SM / Creador |
| `GET` | `/diagrams/{id}/export/xmi` | Exportar diagrama al estándar XML XMI 2.1 | Asignado / SM / Admin |
| `DELETE` | `/diagrams/{id}` | Eliminación lógica de diagrama con auditoría | `admin` |

### 8.6. Asistente NLU e IA (`/ai`)
| Método | Ruta | Descripción | Rol Mínimo |
|---|---|---|---|
| `POST` | `/ai/command` | Procesa texto/voz mediante motor heurístico NLU | Autenticado |
| `POST` | `/ai/vision` | Analiza imágenes de diagramas con Gemini Multimodal | Autenticado |
| `POST` | `/ai/ollama` | Consulta a modelos locales de Ollama | Autenticado |

### 8.7. Generación de Código (`/codegen`)
| Método | Ruta | Descripción | Rol Mínimo |
|---|---|---|---|
| `POST` | `/codegen/spring-boot` | Genera código Spring Boot 3 en JSON plano | Autenticado |
| `POST` | `/codegen/spring-boot/zip` | Descarga archivo `.zip` con el proyecto Maven | Autenticado |
| `POST` | `/codegen/fastapi` | Genera código FastAPI / SQLAlchemy | Autenticado |
| `POST` | `/codegen/frontend-prompt` | Genera especificación y prompt para IAs frontend | Autenticado |

---

## 9. Especificación del Protocolo WebSocket

Endpoint: `/api/v1/ws/diagrams/{diagram_id}?token={jwt_token}`

Al conectarse, el servidor valida el token JWT, comprueba los permisos de acceso al diagrama en la base de datos y suscribe la conexión a la sala correspondiente.

### 9.1. Mensajes Enviados por el Cliente (`Client -> Server`)
1. **Movimiento de Cursor:**
   ```json
   { "action": "cursor_move", "x": 450.5, "y": 210.0 }
   ```
2. **Bloqueo de Nodo:**
   ```json
   { "action": "lock_node", "node_id": "node-uuid-1" }
   ```
3. **Liberación de Nodo:**
   ```json
   { "action": "unlock_node", "node_id": "node-uuid-1" }
   ```
4. **Sincronización de Grafo:**
   ```json
   { "action": "graph_change", "graph_data": { "nodes": [...], "edges": [...] } }
   ```
5. **Mensaje de Chat:**
   ```json
   { "action": "chat_message", "message": "¿Alguien puede revisar la herencia de Cliente?" }
   ```

### 9.2. Mensajes Emitidos por el Servidor (`Server -> Client`)
1. **Estado Inicial de Sala:**
   ```json
   {
     "event": "room_state",
     "users": [{ "user_id": "...", "user_name": "Nicol", "user_color": "#00C896", "role": "dev" }],
     "locks": { "node-uuid-1": "user-id-abc" },
     "chat_history": [...]
   }
   ```
2. **Actualización de Presencia:**
   ```json
   { "event": "user_joined" | "user_left", "user_id": "...", "user_name": "..." }
   ```
3. **Cursor Remoto:**
   ```json
   { "event": "cursor_update", "user_id": "...", "x": 450.5, "y": 210.0, "user_name": "..." }
   ```
4. **Notificación de Bloqueo:**
   ```json
   { "event": "node_locked" | "node_unlocked", "node_id": "...", "user_id": "...", "user_name": "..." }
   ```
5. **Cambio de Grafo Remoto:**
   ```json
   { "event": "remote_graph_change", "graph_data": { "..." }, "user_id": "..." }
   ```

---

## 10. Estado Actual del Proyecto y Funcionalidades Operativas

### Estado de Componentes:
- [x] **Backend REST FastAPI:** 100% Funcional y probado.
- [x] **Persistencia MongoDB:** Conexión asíncrona, colecciones, repositorios e índices operativos.
- [x] **Colaboración WebSockets:** Salas, presencia, sincronización de cursores y bloqueos optimistas implementados y validados.
- [x] **Generador de Código Spring Boot 3:** Genera proyectos completos con Maven, JPA, OpenAPI y VS Code runners.
- [x] **Generador de Código FastAPI:** Modelos SQLAlchemy y endpoints CRUD operativos.
- [x] **Motor NLU Heurístico (Offline):** Operativo en Python (Backend), TypeScript (Frontend) y Dart (Mobile).
- [x] **Visión Multimodal (Gemini):** Ingesta de imágenes de diagramas y conversión a celdas de AntV X6 operativa.
- [x] **Frontend Angular 17:** Standalone Components, AntV X6, minimapa, atajos de teclado, paleta de nodos y exportaciones funcionales.
- [x] **Mobile Flutter:** Visor solo lectura a 60 FPS, NLU local (<1ms), WebSocket client y panel de pruebas funcionales.
- [x] **Despliegue Contenedorizado:** `docker-compose.yml` probado y listo para levantar MongoDB, Backend y Frontend.

---

## 11. Errores Conocidos, Limitaciones y Deuda Técnica

Para que cualquier ingeniero o IA comprenda las restricciones y áreas de precaución del sistema:

1. **Persistencia en Memoria de Bloqueos WebSocket:**
   - *Detalle:* El `ConnectionManager` almacena los `locks` y salas en diccionarios en memoria de Python (`self.rooms` y `self.locks`).
   - *Impacto:* Si el servidor corre con múltiples workers de Uvicorn o se escala horizontalmente en múltiples instancias detrás de un balanceador de carga, los clientes conectados a workers distintos no compartirán los bloqueos ni los cursores.
   - *Solución Recomendada:* Integrar **Redis** mediante Pub/Sub para centralizar el estado de las salas y los locks distribuidos.

2. **Divergencia de URLs entre Entornos en Frontend:**
   - *Detalle:* El archivo `src/environments/environment.ts` apunta por defecto al backend productivo en Render (`https://classforge-backend-8a14.onrender.com/api/v1`).
   - *Impacto:* Si se ejecuta `npm run start` en local sin conexión a internet y sin usar el archivo de proxy `proxy.conf.json`, la aplicación intentará contactar a Render en lugar de `localhost:8000`.
   - *Solución:* Usar siempre el script `start_local.bat` o verificar que `environment.ts` apunte a `http://localhost:8000/api/v1` al trabajar sin internet.

3. **Restricción Intencional de Edición en la App Móvil:**
   - *Detalle:* La aplicación móvil no permite crear nodos arrastrando ni modificar aristas mediante interacción táctil directa; es estrictamente un visor interactivo (*readonly viewer*) con asistente NLU.
   - *Impacto:* Las modificaciones desde el móvil deben realizarse a través del asistente de comandos NLU o planificarse desde la versión web.

4. **Compatibilidad de Versión de Python:**
   - *Detalle:* Las librerías del backend fueron desarrolladas sobre Python 3.11/3.12. En versiones extremadamente recientes como Python 3.14, paquetes como `passlib` o librerías C-extension pueden emitir advertencias de deprecación (*DeprecationWarning* en módulos como `cgi` o `crypt`).

---

## 12. Guía de Despliegue y Ejecución

### Opción 1: Despliegue Automatizado con Docker Compose (Recomendado)
```bash
# 1. Clonar el proyecto
git clone https://github.com/Alejandro-Melgar77/Classforge-.git
cd Classforge-

# 2. Levantar todos los servicios en segundo plano
docker compose up -d --build
```
- **Frontend:** `http://localhost` (Puerto 80)
- **Backend API & Swagger:** `http://localhost:8000/docs`
- **MongoDB:** `localhost:27017`

### Opción 2: Ejecución Local en Modo Desarrollo (Offline en Windows)
Ejecutar el archivo batch:
```cmd
start_local.bat
```
El script inicia el contenedor de MongoDB, activa el entorno virtual de Python para el backend en `localhost:8000` y levanta el servidor de desarrollo de Angular en `localhost:4200`.

### Opción 3: Exposición Pública con Cloudflare Tunnel
```cmd
start_all_and_tunnel.bat
```
Levanta los servicios locales y arranca una sesión de `cloudflared` con HTTP/2, generando una URL pública segura del tipo `https://xxxx.trycloudflare.com` accesible desde cualquier dispositivo o red móvil.

---

## 13. Cuentas de Acceso Pre-configuradas (Credenciales de Prueba)

Generadas mediante el script `classforge-backend/seed_team_and_users.py`:

| Rol | Nombre | Correo Electrónico | Contraseña | Permisos Principales |
|---|---|---|---|---|
| **Admin** | Administrador | `admin@classforge.com` | `1234` o `Admin123!` | Acceso total al sistema, borrado de diagramas y usuarios |
| **Scrum Master** | Alejandro | `alejandro@classforge.com` | `1234` | Gestión de proyectos, equipos y asignación de participantes |
| **Developer** | Fernando | `fernando@classforge.com` | `1234` | Modelado y colaboración en diagramas asignados |
| **Developer** | Nicol | `nicol@classforge.com` | `1234` | Modelado y colaboración en diagramas asignados |
| **Developer** | Nathaly | `nathaly@classforge.com` | `1234` | Modelado y colaboración en diagramas asignados |
| **Developer** | Michael | `michael@classforge.com` | `1234` | Modelado y colaboración en diagramas asignados |

En la pantalla de login de la aplicación móvil (`classforge-mobile`), existen además botones de acceso rápido de un toque para:
- `admin@classforge.io` (`Admin123!`)
- `scrum@classforge.io` (`Scrum123!`)
- `dev@classforge.io` (`Dev12345!`)

---

## 14. Suite de Pruebas Automatizadas

### Backend (Python / Pytest):
```bash
cd classforge-backend
# Ejecutar todas las pruebas unitarias y de integración
pytest
```
Cubre:
- `tests/test_codegen/`: Verificación de generación de Spring Boot 3, FastAPI, DTOs y prompts de frontend.
- `tests/test_ai/`: Pruebas de parsing y extracción de entidades con el motor heurístico NLU.
- `tests/test_collaboration/`: Pruebas del ciclo de conexión y mensajería WebSocket.
- `tests/test_diagrams/`: Pruebas de rutas de creación, edición y participantes.

### Mobile (Flutter Test):
```bash
cd classforge-mobile
flutter test
```
Cubre:
- `test/offline_nlu_test.dart`: Validación de latencia (<1ms) y exactitud del NLU para creación, actualización, eliminación y relaciones de clases.
- `test/diagram_model_test.dart`: Deserialización JSON de grafos complejos de AntV X6 a estructuras de datos nativas de Dart.
