"""
ClassForge 2.0 - Generador de Dataset de Evaluaciones y Gestor de Proyectos UML
Revisión y especialización para IA Local (Liquid AI LFM 1.7B / classforge-local-1.7b).
Opera estrictamente sobre el resumen estructural y relaciones UML 2.5+ del proyecto,
eliminando completamente cualquier dependencia o mención de archivos PDF.
"""

import json
from pathlib import Path

DATASET_PATH = Path("ml/data/reviews_dataset.jsonl")

samples = [
    # ── APROBADO 1: E-Commerce Microservicios Hexagonal ───────────────────────
    {
        "id": "proj-uml-01-ecommerce-hexagonal",
        "title": "Plataforma de Comercio Electrónico Distribuida",
        "diagram_summary": (
            "DIAGRAMA UML: E-Commerce Core\n"
            "CLASES:\n"
            "  CLASE: Usuario (entity) [id: Long, email: String, passwordHash: String, rol: Rol]\n"
            "    Métodos: + autenticar(): Boolean, + cambiarPassword(nuevo: String): Boolean\n"
            "  CLASE: Orden (entity) [id: Long, codigo: String, fecha: Date, total: Decimal, estado: EstadoOrden]\n"
            "    Métodos: + calcularTotal(): Decimal, + cancelar(): Boolean\n"
            "  CLASE: LineaItem (entity) [id: Long, cantidad: Integer, precioUnitario: Decimal, subtotal: Decimal]\n"
            "    Métodos: + calcularSubtotal(): Decimal\n"
            "  CLASE: Producto (entity) [id: Long, sku: String, nombre: String, precio: Decimal, stock: Integer]\n"
            "    Métodos: + reservarStock(cant: Integer): Boolean, + reponerStock(cant: Integer): void\n"
            "  CLASE: Pago (entity) [id: Long, transaccionId: String, monto: Decimal, metodo: MetodoPago, estado: EstadoPago]\n"
            "    Métodos: + procesar(): Boolean, + reembolsar(): Boolean\n"
            "  CLASE: <<enumeration>> EstadoOrden (enum) [Valores: PENDIENTE, PAGADA, ENVIADA, CANCELADA]\n"
            "  CLASE: <<enumeration>> EstadoPago (enum) [Valores: INICIADO, APROBADO, RECHAZADO]\n"
            "  CLASE: <<interface>> IPagoGateway (interface)\n"
            "    Métodos: + autorizarPago(monto: Decimal): Boolean, + capturar(transaccionId: String): Boolean\n"
            "RELACIONES:\n"
            "  - Usuario --[association]--> Orden [1:0..*] (rol: 'realiza')\n"
            "  - Orden --[composition]--> LineaItem [1:1..*] (rol: 'detalles')\n"
            "  - LineaItem --[association]--> Producto [0..*:1] (rol: 'referencia')\n"
            "  - Orden --[aggregation]--> Pago [1:0..1] (rol: 'liquidadoCon')\n"
            "  - Pago --[dependency]--> IPagoGateway (rol: 'invoca')"
        ),
        "user_message": "Evaluar la arquitectura y diagrama UML del proyecto para aprobación de sprint.",
        "ground_truth": {
            "verdict": "APROBADO",
            "total_score": 92.0,
            "passing_score": 70.0,
            "summary": "Excelente modelado UML 2.5+. Cohesión alta, composición estricta en ítems de orden y desacoplamiento con interfaz IPagoGateway.",
            "criteria_scores": [
                {
                    "criterion_code": "arquitectura_diagrama_uml",
                    "name": "Arquitectura y Diagrama de Clases UML",
                    "weight": 25.0,
                    "score": 95.0,
                    "strengths": [
                        "Composición correcta Orden -> LineaItem garantizando ciclo de vida.",
                        "Uso idiomático de interfaces (IPagoGateway) y enumeraciones tipadas.",
                        "Encapsulamiento adecuado de visibilidad privada y métodos públicos de negocio."
                    ],
                    "weaknesses": []
                },
                {
                    "criterion_code": "modelo_persistencia_datos",
                    "name": "Modelo de Persistencia y Base de Datos",
                    "weight": 15.0,
                    "score": 90.0,
                    "strengths": [
                        "Todas las entidades poseen clave primaria id: Long definida.",
                        "Multiplicidades 1..* resuelven tablas orden y orden_items limpiamente."
                    ],
                    "weaknesses": []
                },
                {
                    "criterion_code": "especificacion_requisitos",
                    "name": "Especificación de Requisitos",
                    "weight": 20.0,
                    "score": 90.0,
                    "strengths": ["Cubre flujo transaccional de órdenes, catálogo y pagos."],
                    "weaknesses": []
                },
                {
                    "criterion_code": "definicion_problema_alcance",
                    "name": "Definición del Problema y Alcance",
                    "weight": 15.0,
                    "score": 92.0,
                    "strengths": ["Alcance bien acotado al dominio de e-commerce."],
                    "weaknesses": []
                },
                {
                    "criterion_code": "plan_pruebas_qa",
                    "name": "Plan de Pruebas y Aseguramiento de Calidad",
                    "weight": 15.0,
                    "score": 90.0,
                    "strengths": ["Diseño testeable gracias a la inyección de IPagoGateway."],
                    "weaknesses": []
                },
                {
                    "criterion_code": "seguridad_riesgos",
                    "name": "Seguridad y Gestión de Riesgos",
                    "weight": 10.0,
                    "score": 92.0,
                    "strengths": ["PasswordHash aislado y tipos seguros de estado de pago."],
                    "weaknesses": []
                }
            ],
            "technical_specification": {
                "title": "Especificación Técnica Recomendada - Plataforma E-Commerce",
                "overview": "Implementación basada en arquitectura hexagonal modular en Spring Boot / FastAPI con PostgreSQL.",
                "functional_scope": ["Gestión de catálogo", "Creación de órdenes", "Pasarela de pagos tokenizada"],
                "system_architecture": "Arquitectura Hexagonal (Ports & Adapters) con microservicios para Catálogo, Órdenes y Pagos.",
                "components": [
                    {"name": "OrderService", "role": "Orquestador de órdenes", "technology": "FastAPI / Spring Boot", "description": "Maneja ciclo de vida de la orden."},
                    {"name": "PaymentGatewayAdapter", "role": "Adaptador de pagos", "technology": "Stripe/PayPal SDK", "description": "Implementa IPagoGateway."}
                ],
                "api_endpoints": [
                    {"method": "POST", "path": "/api/v1/orders", "description": "Crea una nueva orden de compra con sus ítems."},
                    {"method": "GET", "path": "/api/v1/orders/{id}", "description": "Obtiene estado y detalles de la orden."},
                    {"method": "POST", "path": "/api/v1/orders/{id}/pay", "description": "Procesa el pago de la orden mediante pasarela."}
                ],
                "data_model": [
                    {"name": "orders", "attributes": ["id BIGSERIAL PK", "code VARCHAR(64) UNIQUE", "user_id BIGINT NOT NULL", "total NUMERIC(12,2)", "status VARCHAR(32)"], "relationships": ["FK user_id -> users(id)"]},
                    {"name": "order_items", "attributes": ["id BIGSERIAL PK", "order_id BIGINT NOT NULL", "product_id BIGINT NOT NULL", "quantity INT", "price NUMERIC(10,2)"], "relationships": ["FK order_id -> orders(id) ON DELETE CASCADE", "FK product_id -> products(id)"]}
                ],
                "non_functional_requirements": ["Latencia < 200ms en p95", "Persistencia ACID en PostgreSQL", "Idempotencia en pagos"],
                "deployment_and_security": ["Contenedores Docker", "Autenticación JWT con rotación de claves", "Cifrado en reposo AES-256"]
            },
            "required_improvements": []
        }
    },

    # ── RECHAZADO 1: Clases huérfanas, muchos a muchos directo, falta de tipos ──
    {
        "id": "proj-uml-02-clinica-deficiente",
        "title": "Sistema de Gestión de Turnos Clínicos",
        "diagram_summary": (
            "DIAGRAMA UML: Gestión de Citas Médicas\n"
            "CLASES:\n"
            "  CLASE: Medico (entity) [nombre, especialidad, telefono]\n"
            "    Métodos: + verAgenda(): void\n"
            "  CLASE: Paciente (entity) [nombreCompleto, edad]\n"
            "    Métodos: + pedirCita(): void\n"
            "  CLASE: AuditoriaLogs (entity) [datos, timestamp]\n"
            "    Métodos: (Sin métodos)\n"
            "RELACIONES:\n"
            "  - Medico --[association]--> Paciente [*..*] (rol: 'atiende')"
        ),
        "user_message": "Revisar diagrama preliminar de citas clínicas para paso a desarrollo.",
        "ground_truth": {
            "verdict": "RECHAZADO",
            "total_score": 44.0,
            "passing_score": 70.0,
            "summary": "Diseño rechazado por violaciones críticas de ingeniería UML 2.5+: asociación *..* directa sin clase intermedia, ausencia de llaves primarias y tipos de datos, y clase AuditoriaLogs huérfana.",
            "criteria_scores": [
                {
                    "criterion_code": "arquitectura_diagrama_uml",
                    "name": "Arquitectura y Diagrama de Clases UML",
                    "weight": 25.0,
                    "score": 35.0,
                    "strengths": ["Identificación conceptual de las entidades centrales."],
                    "weaknesses": [
                        "Relación *..* directa entre Medico y Paciente sin clase de asociación intermedia (ej. Turno o CitaMedica).",
                        "Clase 'AuditoriaLogs' aislada en el grafo (huérfana sin relaciones).",
                        "Falta de estereotipos y visibilidad en atributos."
                    ]
                },
                {
                    "criterion_code": "modelo_persistencia_datos",
                    "name": "Modelo de Persistencia y Base de Datos",
                    "weight": 15.0,
                    "score": 40.0,
                    "strengths": [],
                    "weaknesses": [
                        "Ninguna entidad define clave primaria identificadora (id: Long o UUID).",
                        "Atributos sin especificación de tipo de dato (ej. nombre, edad, telefono sin String/Integer)."
                    ]
                },
                {
                    "criterion_code": "seguridad_riesgos",
                    "name": "Seguridad y Gestión de Riesgos",
                    "weight": 10.0,
                    "score": 45.0,
                    "strengths": [],
                    "weaknesses": ["No se contemplan credenciales ni separación de historiales médicos confidenciales."]
                }
            ],
            "technical_specification": None,
            "required_improvements": [
                "Crear una clase intermedia 'Turno' o 'CitaMedica' con atributos 'id: Long', 'fechaHora: DateTime', 'estado: EstadoTurno' y asociar Medico 1 -- * CitaMedica * -- 1 Paciente.",
                "Agregar claves primarias 'id: Long' o 'id: UUID' a todas las clases del modelo.",
                "Especificar tipos de datos formales para cada atributo (ej. nombre: String, especialidad: String, edad: Integer).",
                "Conectar la clase 'AuditoriaLogs' al flujo transaccional o modelo mediante relaciones de dependencia o patrón observer.",
                "Añadir visibilidad privada (-) a los atributos y definir métodos de encapsulamiento."
            ]
        }
    },

    # ── APROBADO 2: Biblioteca Universitaria y Préstamos ─────────────────────
    {
        "id": "proj-uml-03-biblioteca-academica",
        "title": "Sistema de Préstamos y Biblioteca Universitaria",
        "diagram_summary": (
            "DIAGRAMA UML: Biblioteca Universitaria\n"
            "CLASES:\n"
            "  CLASE: <<abstract>> MiembroUniversitario (entity) [id: Long, matricula: String, nombre: String, email: String, activo: Boolean]\n"
            "    Métodos: + {abstract} calcularLimitePrestamos(): Integer\n"
            "  CLASE: Estudiante (entity) [carrera: String, semestre: Integer]\n"
            "    Métodos: + calcularLimitePrestamos(): Integer\n"
            "  CLASE: Docente (entity) [departamento: String, categoria: String]\n"
            "    Métodos: + calcularLimitePrestamos(): Integer\n"
            "  CLASE: Prestamo (entity) [id: Long, fechaPrestamo: Date, fechaDevolucionEsperada: Date, fechaDevolucionReal: Date, estado: EstadoPrestamo]\n"
            "    Métodos: + registrarDevolucion(): void, + calcularMulta(): Decimal\n"
            "  CLASE: Ejemplar (entity) [id: Long, codigoBarras: String, disponible: Boolean]\n"
            "    Métodos: + marcarPrestado(): void, + marcarDisponible(): void\n"
            "  CLASE: Libro (entity) [id: Long, isbn: String, titulo: String, autor: String, editorial: String, edicion: Integer]\n"
            "    Métodos: + contarEjemplaresDisponibles(): Integer\n"
            "  CLASE: <<enumeration>> EstadoPrestamo (enum) [Valores: ACTIVO, DEVUELTO, EN_MORA, PERDIDO]\n"
            "RELACIONES:\n"
            "  - Estudiante --[inheritance]--> MiembroUniversitario\n"
            "  - Docente --[inheritance]--> MiembroUniversitario\n"
            "  - MiembroUniversitario --[association]--> Prestamo [1:0..*] (rol: 'solicita')\n"
            "  - Prestamo --[association]--> Ejemplar [0..*:1] (rol: 'involucra')\n"
            "  - Libro --[composition]--> Ejemplar [1:1..*] (rol: 'ejemplares')"
        ),
        "user_message": "¿El diagrama de la biblioteca cumple los estándares para generar el código?",
        "ground_truth": {
            "verdict": "APROBADO",
            "total_score": 94.0,
            "passing_score": 70.0,
            "summary": "Excelente jerarquía polimórfica (LSP respetado) y separación clara entre el catálogo (Libro) y las copias físicas (Ejemplar) con composición 1..*.",
            "criteria_scores": [
                {
                    "criterion_code": "arquitectura_diagrama_uml",
                    "name": "Arquitectura y Diagrama de Clases UML",
                    "weight": 25.0,
                    "score": 96.0,
                    "strengths": [
                        "Clase abstracta polimórfica con método abstracto bien implementado en subclases.",
                        "Separación conceptual limpia de Libro (metadatos) vs Ejemplar (inventario físico).",
                        "Asociación y multiplicidad exacta en préstamos."
                    ],
                    "weaknesses": []
                },
                {
                    "criterion_code": "modelo_persistencia_datos",
                    "name": "Modelo de Persistencia y Base de Datos",
                    "weight": 15.0,
                    "score": 93.0,
                    "strengths": ["Esquema herencial con SINGLE_TABLE o JOINED perfectamente mapeable en JPA/SQLAlchemy."],
                    "weaknesses": []
                }
            ],
            "technical_specification": {
                "title": "Especificación Técnica - Sistema de Préstamos Bibliotecarios",
                "overview": "Backend REST en FastAPI/Spring Boot con persistencia relacional PostgreSQL y autenticación SSO institucional.",
                "functional_scope": ["Gestión de catálogo bibliográfico", "Control de préstamos y devoluciones", "Cálculo de penalizaciones"],
                "system_architecture": "Arquitectura en 3 Capas (Controlador, Servicio de Dominio, Repositorio JPA/SQLAlchemy).",
                "components": [
                    {"name": "CatalogService", "role": "Gestión de libros y copias", "technology": "FastAPI", "description": "CRUD de libros e inventario de ejemplares."},
                    {"name": "LoanService", "role": "Motor de préstamos", "technology": "FastAPI", "description": "Aplica reglas de negocio por tipo de miembro."}
                ],
                "api_endpoints": [
                    {"method": "GET", "path": "/api/v1/books", "description": "Búsqueda y disponibilidad de libros por ISBN o título."},
                    {"method": "POST", "path": "/api/v1/loans", "description": "Registra el préstamo de un ejemplar a un miembro."},
                    {"method": "PUT", "path": "/api/v1/loans/{id}/return", "description": "Procesa la devolución del libro y calcula mora si aplica."}
                ],
                "data_model": [
                    {"name": "members", "attributes": ["id BIGSERIAL PK", "matricula VARCHAR(32) UNIQUE", "name VARCHAR(120)", "member_type VARCHAR(20)"], "relationships": []},
                    {"name": "books", "attributes": ["id BIGSERIAL PK", "isbn VARCHAR(20) UNIQUE", "title VARCHAR(255)", "author VARCHAR(150)"], "relationships": []},
                    {"name": "copies", "attributes": ["id BIGSERIAL PK", "book_id BIGINT NOT NULL", "barcode VARCHAR(50) UNIQUE", "available BOOLEAN DEFAULT TRUE"], "relationships": ["FK book_id -> books(id) ON DELETE CASCADE"]},
                    {"name": "loans", "attributes": ["id BIGSERIAL PK", "member_id BIGINT NOT NULL", "copy_id BIGINT NOT NULL", "loan_date DATE", "due_date DATE", "status VARCHAR(20)"], "relationships": ["FK member_id -> members(id)", "FK copy_id -> copies(id)"]}
                ],
                "non_functional_requirements": ["Búsqueda de ejemplares < 50ms", "Concurrencia con bloqueo pesimista en copias"],
                "deployment_and_security": ["Docker, Nginx Reverse Proxy, RBAC para bibliotecarios y estudiantes"]
            },
            "required_improvements": []
        }
    },

    # ── RECHAZADO 2: God Class y Violación SRP ───────────────────────────────
    {
        "id": "proj-uml-04-god-class-monolito",
        "title": "Sistema Monolítico de Facturación e Inventario",
        "diagram_summary": (
            "DIAGRAMA UML: Core ERP\n"
            "CLASES:\n"
            "  CLASE: SistemaERP (entity) [id: Long, nombreEmpresa: String, rfc: String, listaUsuarios: List, saldoCaja: Decimal, conexionBD: String, tokenSeguridad: String, hostSmtp: String, puertoSmtp: Integer, listaProductos: List, listaFacturas: List, templateFacturaPdf: String]\n"
            "    Métodos: + autenticarUsuario(): Boolean, + calcularImpuestos(): Decimal, + enviarCorreoFactura(): Boolean, + conectarBaseDatos(): void, + guardarEnDisco(): void, + imprimirTicket(): void, + registrarEntradaStock(): void, + backupBaseDatos(): void\n"
            "RELACIONES:\n"
            "  (Sin relaciones explícitas, toda la lógica y datos residen dentro de SistemaERP)"
        ),
        "user_message": "Verificar si la clase SistemaERP está lista para producción.",
        "ground_truth": {
            "verdict": "RECHAZADO",
            "total_score": 28.0,
            "passing_score": 70.0,
            "summary": "Rechazado categóricamente. Antipatrón 'God Class' severo que viola el Principio de Responsabilidad Única (SRP), mezclando persistencia, correo SMTP, autenticación y reglas de negocio en una sola clase.",
            "criteria_scores": [
                {
                    "criterion_code": "arquitectura_diagrama_uml",
                    "name": "Arquitectura y Diagrama de Clases UML",
                    "weight": 25.0,
                    "score": 20.0,
                    "strengths": [],
                    "weaknesses": [
                        "Antipatrón Clase Dios (God Class) con más de 20 responsabilidades disjuntas.",
                        "Ausencia total de desacoplamiento y relaciones UML entre entidades del dominio."
                    ]
                }
            ],
            "technical_specification": None,
            "required_improvements": [
                "Descomponer 'SistemaERP' aplicando SRP en clases especializadas: Usuario, Factura, Producto, EmailService y DatabaseConfig.",
                "Extraer las responsabilidades de infraestructura (SMTP, conexión a BD, copias de seguridad) fuera de las entidades de negocio.",
                "Establecer relaciones formales de asociación y agregación entre Factura, LineaFactura y Producto.",
                "Utilizar interfaces para desacoplar el envío de correos (ej. INotifierService) y persistencia (IRepository)."
            ]
        }
    }
]

def main():
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        for item in samples:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"[Dataset ML] Generado exitosamente en: {DATASET_PATH} con {len(samples)} muestras UML puras.")

if __name__ == "__main__":
    main()
