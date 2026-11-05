import json
from pathlib import Path

DATASET_PATH = Path("ml/data/reviews_dataset.jsonl")

# Sample project definitions
samples = [
    # ── APROBADO (1-8) ────────────────────────────────────────────────────────
    {
        "id": "proj-01-ecommerce-microservices",
        "title": "Plataforma de Comercio Electrónico Distribuida Basada en Microservicios",
        "page_count": 8,
        "document_text": (
            "[Página 1]\n"
            "DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
            "1.1 Planteamiento del Problema\n"
            "El crecimiento del comercio digital demanda alta disponibilidad y escalabilidad elástica. "
            "Este proyecto desarrolla una plataforma de comercio electrónico orientada a microservicios. "
            "Objetivo general: Implementar un sistema distribuido tolerante a fallos para transacciones online.\n"
            "Objetivos específicos: Desacoplar el catálogo de la pasarela de pagos; garantizar latencia menor a 200ms.\n"
            "Alcance del proyecto: Gestión de catálogo, procesamiento de órdenes, pagos y envíos. Fuera de alcance: logística de almacenes físicos.\n\n"
            "[Página 2]\n"
            "ESPECIFICACIÓN DE REQUISITOS\n"
            "2.1 Requisitos Funcionales\n"
            "RF-01: El sistema debe permitir el registro y autenticación de clientes.\n"
            "RF-02: El cliente puede buscar productos por categoría, precio y fabricante.\n"
            "RF-03: El sistema debe procesar órdenes de compra con tarjeta de crédito o débito.\n"
            "RF-04: El administrador puede actualizar el stock y precios en tiempo real.\n"
            "2.2 Requisitos No Funcionales\n"
            "RNF-01 (Rendimiento): Tiempo de respuesta del catálogo < 150 ms para el percentil 95.\n"
            "RNF-02 (Disponibilidad): Disponibilidad del sistema del 99.9% anual.\n"
            "RNF-03 (Seguridad): Cifrado de datos en reposo y en tránsito mediante TLS 1.3.\n"
            "Casos de uso: CU-01 Crear Orden, CU-02 Pagar Carrito.\n\n"
            "[Página 3]\n"
            "ARQUITECTURA DEL SISTEMA Y DIAGRAMA DE CLASES UML\n"
            "3.1 Diseño Arquitectónico\n"
            "Arquitectura hexagonal con microservicios comunicados vía REST y Apache Kafka para mensajería asíncrona.\n"
            "3.2 Diagrama de Clases UML\n"
            "Se modelan las entidades principales y sus relaciones:\n"
            "class Usuario { +id: Long, +email: String, +passwordHash: String, +rol: Rol, +autenticar(): Boolean }\n"
            "class Orden { +id: Long, +codigo: String, +fecha: Date, +total: Decimal, +calcularTotal(): Decimal }\n"
            "class LineaItem { +id: Long, +cantidad: Integer, +precioUnitario: Decimal }\n"
            "class Producto { +id: Long, +nombre: String, +precio: Decimal, +stock: Integer, +reducirStock(): Boolean }\n"
            "class Pago { +id: Long, +monto: Decimal, +estado: EstadoPago, +procesar(): Boolean }\n"
            "Relaciones: Orden *-- LineaItem (composición 1 a N). LineaItem --> Producto (asociación). Orden o-- Pago (agregación).\n"
            "Usuario 1 -- * Orden. Se implementa el patrón Repository y Factory.\n\n"
            "[Página 4]\n"
            "MODELO DE PERSISTENCIA Y BASE DE DATOS\n"
            "4.1 Esquema de Base de Datos\n"
            "Persistencia políglota: PostgreSQL para órdenes y pagos (ACID); MongoDB para catálogo de productos.\n"
            "Tablas relacionales: users (id PK, email UK, password_hash, role_id FK), orders (id PK, user_id FK, status, total),\n"
            "order_items (id PK, order_id FK, product_id, quantity, unit_price).\n"
            "Diccionario de datos con índices B-Tree en email, user_id y fecha de creación.\n\n"
            "[Página 5]\n"
            "PLAN DE PRUEBAS Y ASEGURAMIENTO DE CALIDAD\n"
            "5.1 Estrategia de Pruebas\n"
            "Pirámide de pruebas: 70% pruebas unitarias con JUnit 5 y Mockito, 20% pruebas de integración con Testcontainers,\n"
            "10% pruebas end-to-end con Cypress.\n"
            "Casos de prueba: CP-01 Creación de orden exitosa con stock suficiente; CP-02 Rechazo por stock agotado;\n"
            "CP-03 Validación de token JWT expirado.\n"
            "Criterios de aceptación: Cobertura mínima de código del 80% verificada mediante SonarQube.\n\n"
            "[Página 6]\n"
            "SEGURIDAD Y GESTIÓN DE RIESGOS\n"
            "6.1 Mecanismos de Seguridad\n"
            "Autenticación stateless basada en JSON Web Tokens (JWT) con rotación de claves RSA-256.\n"
            "Control de accesos basado en roles (RBAC): CLIENTE, ADMINISTRADOR, VENDEDOR.\n"
            "6.2 Matriz de Riesgos\n"
            "Riesgo 1: Caída de la pasarela de pagos. Impacto: Alto. Mitigación: Circuit breaker con Resilience4j y cola de reintentos.\n"
            "Riesgo 2: Inyección SQL y XSS. Mitigación: Consultas parametrizadas y Content Security Policy (CSP).\n"
        ),
        "ground_truth": {
            "verdict": "APROBADO",
            "total_score": 88.0,
            "has_sufficient_text": True,
            "detected_sections": [
                "definicion_problema_alcance",
                "especificacion_requisitos",
                "arquitectura_diagrama_uml",
                "modelo_persistencia_datos",
                "plan_pruebas_qa",
                "seguridad_riesgos",
            ],
        },
    },
    {
        "id": "proj-02-hospital-clinical-records",
        "title": "Sistema Hospitalario de Historia Clínica Electrónica",
        "page_count": 7,
        "document_text": (
            "[Página 1]\n"
            "DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
            "El registro manual de historias clínicas genera fragmentación y demoras diagnósticas. "
            "Este proyecto implementa un Sistema de Historia Clínica Electrónica (HCE) interoperable bajo estándar HL7 FHIR. "
            "Objetivo general: Centralizar y securizar el historial médico de pacientes hospitalarios. "
            "Objetivos específicos: Digitalizar recetas médicas; proveer firma digital; interoperar con laboratorio.\n"
            "Alcance del proyecto: Pacientes ambulatorios y hospitalización general.\n\n"
            "[Página 2]\n"
            "ESPECIFICACIÓN DE REQUISITOS\n"
            "Requisitos Funcionales:\n"
            "RF-01: Registro de filiación del paciente con validación de identidad.\n"
            "RF-02: Creación de consulta médica con anamnesis, exploración y diagnóstico CIE-11.\n"
            "RF-03: Emisión de recetas médicas electrónicas con firma digital PKI.\n"
            "RF-04: Visualización de resultados de laboratorio e imágenes DICOM.\n"
            "Requisitos No Funcionales:\n"
            "RNF-01 (Seguridad): Cumplimiento estricto de confidencialidad médica HIPAA y RGPD.\n"
            "RNF-02 (Auditoría): Registro inmutable de cada lectura o modificación de historias clínicas.\n"
            "Casos de uso: CU-10 Apertura de Consulta, CU-11 Prescribir Medicamento.\n\n"
            "[Página 3]\n"
            "ARQUITECTURA Y DIAGRAMA DE CLASES UML\n"
            "Arquitectura en capas (Clean Architecture): Dominio, Casos de Uso, Adaptadores e Infraestructura.\n"
            "Diagrama de Clases UML:\n"
            "class Paciente { +id: UUID, +dni: String, +nombreCompleto: String, +fechaNacimiento: Date }\n"
            "class Medico { +id: UUID, +colegiatura: String, +especialidad: String, +firmar(): Boolean }\n"
            "class HistoriaClinica { +id: UUID, +numeroExpediente: String, +agregarEntrada(): Void }\n"
            "class EpisodioClinico { +id: UUID, +fecha: DateTime, +motivo: String, +diagnostico: String }\n"
            "class RecetaMedica { +id: UUID, +medicamentos: List, +firmaDigital: String }\n"
            "Relaciones: Paciente 1 -- 1 HistoriaClinica (composición). HistoriaClinica 1 *-- EpisodioClinico.\n"
            "EpisodioClinico --> Medico (asociación). EpisodioClinico 1 -- 0..1 RecetaMedica.\n\n"
            "[Página 4]\n"
            "MODELO DE PERSISTENCIA Y BASE DE DATOS\n"
            "Base de datos relacional PostgreSQL con particionamiento por año de atención.\n"
            "Tablas: pacientes, medicos, historias_clinicas, episodios_clinicos, recetas_medicas.\n"
            "Claves foráneas con integridad referencial restrictiva. Diccionario de datos documentado.\n\n"
            "[Página 5]\n"
            "PLAN DE PRUEBAS Y ASEGURAMIENTO DE CALIDAD\n"
            "Pruebas unitarias con pytest para lógica de diagnóstico y reglas de dosificación.\n"
            "Pruebas de integración para persistencia y validación de esquemas JSON FHIR.\n"
            "Casos de prueba: CP-01 Acceso no autorizado a historia clínica ajena (esperado: 403 Forbidden);\n"
            "CP-02 Verificación criptográfica de firma digital de receta.\n"
            "Criterios de aceptación: Cobertura de pruebas unitarias superior al 85%.\n\n"
            "[Página 6]\n"
            "SEGURIDAD Y GESTIÓN DE RIESGOS\n"
            "Mecanismos de seguridad: Autenticación multifactor (MFA), cifrado de columnas sensibles con pgcrypto,\n"
            "control de acceso basado en atributos y roles (ABAC/RBAC).\n"
            "Matriz de riesgos: Riesgo de fuga de datos clínicos mitigado por canal seguro TLS y token temporal de sesión.\n"
        ),
        "ground_truth": {
            "verdict": "APROBADO",
            "total_score": 92.5,
            "has_sufficient_text": True,
            "detected_sections": [
                "definicion_problema_alcance",
                "especificacion_requisitos",
                "arquitectura_diagrama_uml",
                "modelo_persistencia_datos",
                "plan_pruebas_qa",
                "seguridad_riesgos",
            ],
        },
    },
    {
        "id": "proj-03-logistics-tracking",
        "title": "Sistema de Trazabilidad Logística y Monitoreo Vehicular en Tiempo Real",
        "page_count": 6,
        "document_text": (
            "[Página 1]\n"
            "DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
            "La distribución de carga terrestre experimenta pérdidas por falta de telemetría continua.\n"
            "Este proyecto diseña un sistema de telemetría IoT y rastreo GPS en tiempo real.\n"
            "Objetivo general: Proporcionar visibilidad continua de rutas y alertas de desvío vehicular.\n"
            "Alcance del proyecto: Monitoreo de flotas, geocercas, telemetría de combustible y estado de entregas.\n\n"
            "[Página 2]\n"
            "ESPECIFICACIÓN DE REQUISITOS\n"
            "Requisitos Funcionales:\n"
            "RF-01: Recepción de coordenadas GPS cada 10 segundos por vehículo.\n"
            "RF-02: Generación automática de alerta ante salida de geocerca programada.\n"
            "RF-03: Registro de conductores y asignación de hojas de ruta.\n"
            "Requisitos No Funcionales:\n"
            "RNF-01: Ingesta de 5,000 eventos por segundo con latencia de procesamiento < 500 ms.\n"
            "RNF-02: Interfaz web responsiva con actualización vía WebSockets.\n\n"
            "[Página 3]\n"
            "ARQUITECTURA Y DIAGRAMA DE CLASES UML\n"
            "Arquitectura basada en eventos con Apache Kafka, FastAPI y MongoDB.\n"
            "Diagrama de Clases UML:\n"
            "class Vehiculo { +placa: String, +modelo: String, +capacidadKg: Double }\n"
            "class DispositivoGPS { +imei: String, +estado: String, +enviarPosicion(): Void }\n"
            "class PosicionGPS { +latitud: Double, +longitud: Double, +velocidad: Double, +timestamp: DateTime }\n"
            "class HojaRuta { +id: Long, +origen: String, +destino: String, +estado: EstadoRuta }\n"
            "Vehiculo 1 -- 1 DispositivoGPS (agregación). DispositivoGPS 1 *-- PosicionGPS (composición). Vehiculo 1 -- * HojaRuta.\n\n"
            "[Página 4]\n"
            "MODELO DE PERSISTENCIA Y BASE DE DATOS\n"
            "Base de datos NoSQL MongoDB con índices geoespaciales 2dsphere para consultas geográficas eficientes.\n"
            "Colecciones: vehiculos, dispositivos, posiciones_geo, rutas.\n\n"
            "[Página 5]\n"
            "PLAN DE PRUEBAS Y ASEGURAMIENTO DE CALIDAD\n"
            "Estrategia de pruebas con pytest para los cálculos de distancias Haversine.\n"
            "Pruebas de carga con Locust simulando 1,000 dispositivos GPS concurrentes.\n"
            "Casos de prueba: CP-01 Inserción de coordenada válida; CP-02 Detección de salto anómalo de velocidad.\n\n"
            "[Página 6]\n"
            "SEGURIDAD Y GESTIÓN DE RIESGOS\n"
            "Seguridad en dispositivos mediante certificados de cliente mTLS y autenticación por API Key.\n"
            "Matriz de riesgos: Pérdida de conectividad celular mitigada por almacenamiento local en buffer del hardware GPS.\n"
        ),
        "ground_truth": {
            "verdict": "APROBADO",
            "total_score": 85.0,
            "has_sufficient_text": True,
            "detected_sections": [
                "definicion_problema_alcance",
                "especificacion_requisitos",
                "arquitectura_diagrama_uml",
                "modelo_persistencia_datos",
                "plan_pruebas_qa",
                "seguridad_riesgos",
            ],
        },
    },
    {
        "id": "proj-04-academic-management",
        "title": "Portal Integral de Gestión Académica y Matrícula Universitaria",
        "page_count": 5,
        "document_text": (
            "[Página 1]\n"
            "INTRODUCCIÓN, DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
            "El proceso de matrícula presenta cuellos de botella durante períodos de alta concurrencia.\n"
            "Objetivo general: Optimizar la asignación de cupos y horarios para estudiantes universitarios.\n"
            "Alcance del proyecto: Prematrícula, matrícula ordinaria, registro de calificaciones y convalidaciones.\n\n"
            "[Página 2]\n"
            "ESPECIFICACIÓN DE REQUISITOS\n"
            "Requisitos Funcionales:\n"
            "RF-01: El estudiante puede seleccionar materias según su plan de estudios y prerrequisitos cumplidos.\n"
            "RF-02: El docente registra notas parciales y finales con ponderaciones configurables.\n"
            "RF-03: Generación del consolidado de notas y certificado de estudios en PDF.\n"
            "Requisitos No Funcionales:\n"
            "RNF-01: Concurrencia de hasta 2,000 matrículas simultáneas.\n\n"
            "[Página 3]\n"
            "ARQUITECTURA Y DIAGRAMA DE CLASES UML\n"
            "Arquitectura Modelo-Vista-Controlador (MVC) con backend en Spring Boot y base de datos relacional MySQL.\n"
            "Diagrama de Clases UML:\n"
            "class Estudiante { +codigo: String, +promedioPonderado: Double, +matricular(): Boolean }\n"
            "class Asignatura { +sigla: String, +nombre: String, +creditos: Integer }\n"
            "class Grupo { +numero: Integer, +cupoMaximo: Integer, +cuposDisponibles: Integer }\n"
            "class Matricula { +fecha: DateTime, +semestre: String, +calcularCreditos(): Integer }\n"
            "Estudiante 1 -- * Matricula. Matricula *-- Grupo. Grupo --> Asignatura.\n\n"
            "[Página 4]\n"
            "MODELO DE PERSISTENCIA Y PLAN DE PRUEBAS\n"
            "Modelo relacional con tablas estudiantes, asignaturas, grupos, matriculas con claves foráneas.\n"
            "Plan de pruebas: Pruebas unitarias con JUnit 5 para validación de prerrequisitos.\n"
            "Casos de prueba para matricula con cruce de horario y matrícula sin cupos.\n\n"
            "[Página 5]\n"
            "SEGURIDAD Y RIESGOS\n"
            "Autenticación centralizada LDAP/OAuth2 institucional. Roles de Alumno, Docente y Director de Carrera.\n"
            "Riesgos de sobrecarga de servidor mitigados con cola Redis y escalado horizontal.\n"
        ),
        "ground_truth": {
            "verdict": "APROBADO",
            "total_score": 78.5,
            "has_sufficient_text": True,
            "detected_sections": [
                "definicion_problema_alcance",
                "especificacion_requisitos",
                "arquitectura_diagrama_uml",
                "modelo_persistencia_datos",
                "plan_pruebas_qa",
                "seguridad_riesgos",
            ],
        },
    },
    {
        "id": "proj-05-iot-telemetry-dashboard",
        "title": "Panel de Telemetría y Mantenimiento Predictivo para Maquinaria Industrial",
        "page_count": 6,
        "document_text": (
            "[Página 1]\n"
            "DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
            "Las fallas imprevistas en líneas de manufactura ocasionan pérdidas económicas millonarias.\n"
            "Objetivo general: Desarrollar un sistema de telemetría IoT y detección temprana de anomalías.\n"
            "Alcance del proyecto: Monitoreo de vibración, temperatura y consumo eléctrico de motores industriales.\n\n"
            "[Página 2]\n"
            "REQUISITOS FUNCIONALES Y NO FUNCIONALES\n"
            "RF-01: Ingesta continua de métricas mediante protocolo MQTT.\n"
            "RF-02: Visualización en tiempo real mediante dashboard interactivo.\n"
            "RF-03: Alertas automáticas vía SMS y correo ante superación de umbrales críticos.\n"
            "RNF-01: Latencia de procesamiento de alertas menor a 1 segundo.\n\n"
            "[Página 3]\n"
            "ARQUITECTURA DEL SISTEMA Y DIAGRAMA DE CLASES UML\n"
            "Arquitectura basada en microservicios con bróker MQTT (Mosquitto), TimescaleDB y FastAPI.\n"
            "Diagrama de Clases UML:\n"
            "class Sensor { +id: String, +tipo: String, +frecuenciaHz: Integer, +calibrar(): Void }\n"
            "class Maquina { +codigo: String, +lineaProduccion: String, +estado: EstadoOperativo }\n"
            "class Lectura { +timestamp: DateTime, +valor: Double, +unidad: String }\n"
            "class Alerta { +nivel: String, +mensaje: String, +resuelta: Boolean }\n"
            "Maquina 1 *-- Sensor (composición). Sensor 1 -- * Lectura. Sensor 1 -- * Alerta.\n\n"
            "[Página 4]\n"
            "MODELO DE DATOS Y PERSISTENCIA\n"
            "Base de datos de series temporales TimescaleDB sobre PostgreSQL, con políticas de compresión de datos antiguos.\n"
            "Tablas e hipertablas: maquinarias, sensores, lecturas_sensor.\n\n"
            "[Página 5]\n"
            "PLAN DE PRUEBAS QA Y SEGURIDAD\n"
            "Pruebas unitarias para algoritmos de detección de umbrales. Pruebas de integración de protocolo MQTT.\n"
            "Seguridad: Cifrado TLS en el bróker MQTT y tokens JWT para la API REST del dashboard.\n"
        ),
        "ground_truth": {
            "verdict": "APROBADO",
            "total_score": 82.0,
            "has_sufficient_text": True,
            "detected_sections": [
                "definicion_problema_alcance",
                "especificacion_requisitos",
                "arquitectura_diagrama_uml",
                "modelo_persistencia_datos",
                "plan_pruebas_qa",
                "seguridad_riesgos",
            ],
        },
    },
    {
        "id": "proj-06-financial-expense-tracker",
        "title": "Sistema de Gestión Financiera y Control de Presupuestos Empresariales",
        "page_count": 5,
        "document_text": (
            "[Página 1]\n"
            "DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
            "Las PyMEs carecen de visibilidad ágil sobre flujos de caja y gastos por centros de costos.\n"
            "Objetivo general: Proporcionar un sistema de presupuesto y conciliación bancaria automatizada.\n"
            "Alcance del proyecto: Presupuestos anuales, aprobación de gastos y reportes contables.\n\n"
            "[Página 2]\n"
            "ESPECIFICACIÓN DE REQUISITOS\n"
            "RF-01: Creación de presupuestos por centro de costos y cuenta contable.\n"
            "RF-02: Solicitud de rendición de gastos con carga de factura electrónica.\n"
            "RF-03: Flujo de aprobación multinivel según monto del gasto.\n"
            "RNF-01: Cifrado de información financiera con AES-256.\n\n"
            "[Página 3]\n"
            "ARQUITECTURA Y DIAGRAMA DE CLASES UML\n"
            "Arquitectura en capas Clean Architecture en Python/FastAPI.\n"
            "Diagrama de Clases UML:\n"
            "class CentroCosto { +codigo: String, +nombre: String, +presupuestoAsignado: Decimal }\n"
            "class SolicitudGasto { +id: Long, +monto: Decimal, +estado: EstadoSolicitud, +aprobar(): Void }\n"
            "class Comprobante { +folio: String, +emisor: String, +validar(): Boolean }\n"
            "CentroCosto 1 -- * SolicitudGasto. SolicitudGasto 1 *-- Comprobante.\n\n"
            "[Página 4]\n"
            "BASE DE DATOS Y PLAN DE PRUEBAS\n"
            "Base de datos PostgreSQL con esquema normalizado en 3FN. Pruebas unitarias con pytest y cobertura del 75%.\n"
            "Casos de prueba para flujo de aprobación y rechazo por exceso de presupuesto.\n\n"
            "[Página 5]\n"
            "SEGURIDAD Y RIESGOS\n"
            "Autenticación con JWT, roles de Solicitante, Aprobador y Auditor Financiero.\n"
            "Mitigación de riesgos de fraude mediante pistas de auditoría inmutables.\n"
        ),
        "ground_truth": {
            "verdict": "APROBADO",
            "total_score": 75.0,
            "has_sufficient_text": True,
            "detected_sections": [
                "definicion_problema_alcance",
                "especificacion_requisitos",
                "arquitectura_diagrama_uml",
                "modelo_persistencia_datos",
                "plan_pruebas_qa",
                "seguridad_riesgos",
            ],
        },
    },
    {
        "id": "proj-07-mobile-food-delivery",
        "title": "Plataforma de Despacho Gastronómico y Envíos a Domicilio",
        "page_count": 6,
        "document_text": (
            "[Página 1]\n"
            "PLANTEAMIENTO DEL PROBLEMA Y ALCANCE\n"
            "Optimizar la conexión entre restaurantes locales y repartidores independientes.\n"
            "Objetivo general: Reducir los tiempos de entrega de pedidos de comida a domicilio.\n"
            "Alcance del proyecto: Aplicación cliente, aplicación repartidor y portal restaurante.\n\n"
            "[Página 2]\n"
            "REQUISITOS FUNCIONALES Y NO FUNCIONALES\n"
            "RF-01: Exploración de menús y personalización de platillos.\n"
            "RF-02: Asignación algorítmica de repartidor por cercanía geográfica.\n"
            "RF-03: Pago online con tarjeta y confirmación en tiempo real.\n"
            "RNF-01: Soporte para 10,000 usuarios activos simultáneos.\n\n"
            "[Página 3]\n"
            "ARQUITECTURA DEL SISTEMA Y DIAGRAMA DE CLASES UML\n"
            "Microservicios con Spring Boot, Node.js y Redis para almacenamiento en caché.\n"
            "Diagrama de Clases UML:\n"
            "class Restaurante { +id: Long, +nombre: String, +direccion: String, +abierto: Boolean }\n"
            "class Plato { +id: Long, +nombre: String, +precio: Decimal }\n"
            "class PedidoDelivery { +id: Long, +estado: String, +tiempoEstimadoMin: Integer }\n"
            "class Repartidor { +id: Long, +latitud: Double, +longitud: Double, +activo: Boolean }\n"
            "Restaurante 1 *-- Plato. PedidoDelivery --> Restaurante. PedidoDelivery --> Repartidor.\n\n"
            "[Página 4]\n"
            "PERSISTENCIA Y PRUEBAS QA\n"
            "Base de datos PostgreSQL con extensión PostGIS para cálculo de rutas. Redis para caché de menús.\n"
            "Estrategia de pruebas con Mockito y Jest. Pruebas de integración de la pasarela de pagos.\n\n"
            "[Página 5]\n"
            "SEGURIDAD Y RIESGOS\n"
            "Autenticación OAuth2 con Google y Apple Sign-In. Protección contra ataques DDoS con Cloudflare.\n"
        ),
        "ground_truth": {
            "verdict": "APROBADO",
            "total_score": 80.0,
            "has_sufficient_text": True,
            "detected_sections": [
                "definicion_problema_alcance",
                "especificacion_requisitos",
                "arquitectura_diagrama_uml",
                "modelo_persistencia_datos",
                "plan_pruebas_qa",
                "seguridad_riesgos",
            ],
        },
    },
    {
        "id": "proj-08-hotel-booking",
        "title": "Sistema de Reservas Hoteleras y Gestión de Habitaciones",
        "page_count": 5,
        "document_text": (
            "[Página 1]\n"
            "DEFINICIÓN DEL PROBLEMA Y ALCANCE\n"
            "La gestión manual de reservas hoteleras genera sobreventa (overbooking) e inconsistencias de inventario.\n"
            "Objetivo general: Automatizar la disponibilidad de habitaciones y reservas online.\n"
            "Alcance del proyecto: Habitaciones, tarifas por temporada y pagos de estadía.\n\n"
            "[Página 2]\n"
            "REQUISITOS FUNCIONALES Y NO FUNCIONALES\n"
            "RF-01: Consulta de disponibilidad por rango de fechas y tipo de habitación.\n"
            "RF-02: Bloqueo transaccional de habitación durante el proceso de reserva.\n"
            "RF-03: Check-in y check-out digital de huéspedes.\n"
            "RNF-01: Consistencia transaccional estricta (prevención de overbooking).\n\n"
            "[Página 3]\n"
            "ARQUITECTURA Y DIAGRAMA DE CLASES UML\n"
            "Arquitectura Hexagonal con backend en FastAPI y persistencia relacional.\n"
            "Diagrama de Clases UML:\n"
            "class Habitacion { +numero: Integer, +tipo: TipoHabitacion, +precioNoche: Decimal }\n"
            "class Reserva { +codigo: String, +fechaInicio: Date, +fechaFin: Date, +confirmar(): Boolean }\n"
            "class Huesped { +documento: String, +nombre: String, +telefono: String }\n"
            "Reserva --> Habitacion. Reserva --> Huesped. Relación de asociación formal.\n\n"
            "[Página 4]\n"
            "PERSISTENCIA Y PLAN DE PRUEBAS\n"
            "Base de datos MySQL con aislamiento Serializable para evitar reservas simultáneas de la misma habitación.\n"
            "Pruebas de concurrencia con pytest-asyncio y pruebas unitarias de cálculo de tarifas.\n\n"
            "[Página 5]\n"
            "SEGURIDAD Y RIESGOS\n"
            "Autenticación con JWT, cifrado de tarjetas de crédito cumpliendo normativa PCI-DSS.\n"
            "Riesgos de cancelaciones masivas mitigados con política de depósitos no reembolsables.\n"
        ),
        "ground_truth": {
            "verdict": "APROBADO",
            "total_score": 73.5,
            "has_sufficient_text": True,
            "detected_sections": [
                "definicion_problema_alcance",
                "especificacion_requisitos",
                "arquitectura_diagrama_uml",
                "modelo_persistencia_datos",
                "plan_pruebas_qa",
                "seguridad_riesgos",
            ],
        },
    },

    # ── RECHAZADO (9-16) ──────────────────────────────────────────────────────
    {
        "id": "proj-09-incomplete-chat-app",
        "title": "Borrador de Aplicación de Chat Instantáneo",
        "page_count": 3,
        "document_text": (
            "[Página 1]\n"
            "Queremos hacer una aplicación de chat parecida a WhatsApp para amigos de la universidad.\n"
            "Básicamente servirá para mandar mensajes de texto y fotos.\n"
            "Los usuarios se registran y crean grupos para hablar.\n\n"
            "[Página 2]\n"
            "La idea es usar React Native para el celular y Node.js en el backend.\n"
            "Todavía no tenemos claro cómo guardar los mensajes, tal vez en Firebase o en un archivo.\n"
            "No hemos hecho pruebas unitarias porque el código está cambiando mucho.\n\n"
            "[Página 3]\n"
            "Sobre la seguridad, pensamos poner una contraseña simple para que nadie entre sin permiso.\n"
            "Más adelante veremos lo de encriptar mensajes si da tiempo.\n"
        ),
        "ground_truth": {
            "verdict": "RECHAZADO",
            "total_score": 42.0,
            "has_sufficient_text": True,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-10-library-catalog-draft",
        "title": "Documento Preliminar para Catálogo de Libros",
        "page_count": 2,
        "document_text": (
            "[Página 1]\n"
            "SISTEMA DE BIBLIOTECA\n"
            "Este documento describe una página web para buscar libros en la biblioteca del colegio.\n"
            "Los alumnos podrán ver qué libros están prestados y cuáles están libres.\n"
            "Habrá una lista con el título del libro y el autor.\n\n"
            "[Página 2]\n"
            "El sistema se va a programar en PHP clásico con HTML básico.\n"
            "No se ha diseñado diagrama de clases UML ni arquitectura de capas.\n"
            "No se han definido casos de prueba ni plan de aseguramiento de calidad.\n"
        ),
        "ground_truth": {
            "verdict": "RECHAZADO",
            "total_score": 35.0,
            "has_sufficient_text": True,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-11-crypto-portfolio-tracker",
        "title": "Monitor de Criptomonedas Personal",
        "page_count": 3,
        "document_text": (
            "[Página 1]\n"
            "DEFINICIÓN DEL PROYECTO\n"
            "Una app para ver el precio del Bitcoin y Ethereum usando una API pública de CoinGecko.\n"
            "El usuario ingresa qué monedas compró y a qué precio para ver su ganancia o pérdida.\n\n"
            "[Página 2]\n"
            "Funcionalidades: Conectarse a la API cada 5 minutos y refrescar la pantalla.\n"
            "No hay arquitectura formal, solo una vista en Flutter y un script en Python.\n"
            "Faltan diagramas UML, no hay modelo de base de datos relacional.\n\n"
            "[Página 3]\n"
            "No se cuenta con plan de pruebas ni matriz de riesgos técnicos.\n"
        ),
        "ground_truth": {
            "verdict": "RECHAZADO",
            "total_score": 40.0,
            "has_sufficient_text": True,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-12-social-network-prototype",
        "title": "Prototipo de Red Social Universitaria",
        "page_count": 3,
        "document_text": (
            "[Página 1]\n"
            "Red social para estudiantes donde cada uno sube fotos y da me gusta.\n"
            "Los requisitos no están numerados ni estructurados formalmente.\n\n"
            "[Página 2]\n"
            "Se pensó en usar MongoDB pero no hay diagrama de clases ni esquema de datos definido.\n"
            "No se especifica control de accesos ni roles.\n\n"
            "[Página 3]\n"
            "No hay plan de pruebas QA ni métricas de calidad de software.\n"
        ),
        "ground_truth": {
            "verdict": "RECHAZADO",
            "total_score": 32.0,
            "has_sufficient_text": True,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-13-smart-home-controller",
        "title": "Controlador Domótico Casero",
        "page_count": 3,
        "document_text": (
            "[Página 1]\n"
            "Sistema casero para encender luces con una placa Arduino conectada por Bluetooth.\n"
            "La descripción es informal y no delimita el alcance técnico del software.\n\n"
            "[Página 2]\n"
            "Código simple en C++ para el microcontrolador. No existe arquitectura de software formal.\n"
            "Sin diagrama de clases UML ni especificación de requisitos funcionales y no funcionales.\n\n"
            "[Página 3]\n"
            "No se contemplan pruebas de software ni mecanismos de seguridad en la transmisión Bluetooth.\n"
        ),
        "ground_truth": {
            "verdict": "RECHAZADO",
            "total_score": 38.0,
            "has_sufficient_text": True,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-14-gym-member-manager",
        "title": "Sistema de Control de Socios de Gimnasio",
        "page_count": 3,
        "document_text": (
            "[Página 1]\n"
            "Gestor de socios de gimnasio para registrar pagos mensuales en un archivo Excel.\n"
            "Objetivos vagos y sin métricas cuantitativas de éxito.\n\n"
            "[Página 2]\n"
            "Script en Python con interfaz gráfica Tkinter básica. No hay arquitectura desacoplada.\n"
            "No hay diagrama de clases UML ni persistencia en base de datos formal.\n\n"
            "[Página 3]\n"
            "No tiene pruebas automatizadas ni análisis de riesgos o seguridad.\n"
        ),
        "ground_truth": {
            "verdict": "RECHAZADO",
            "total_score": 36.0,
            "has_sufficient_text": True,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-15-car-rental-prototype",
        "title": "Propuesta de Alquiler de Vehículos",
        "page_count": 2,
        "document_text": (
            "[Página 1]\n"
            "Propuesta para arrendar autos por internet con tarjeta.\n"
            "Faltan requisitos funcionales estructurados y no funcionales.\n\n"
            "[Página 2]\n"
            "Sin arquitectura de software, sin diagrama de clases y sin plan de pruebas.\n"
        ),
        "ground_truth": {
            "verdict": "RECHAZADO",
            "total_score": 28.0,
            "has_sufficient_text": True,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-16-job-board-concept",
        "title": "Bolsa de Trabajo para Egresados",
        "page_count": 3,
        "document_text": (
            "[Página 1]\n"
            "Portal donde las empresas publican ofertas laborales para recién graduados.\n"
            "El alcance es impreciso y no cuenta con delimitación de límites del sistema.\n\n"
            "[Página 2]\n"
            "Mención superficial de tecnologías sin arquitectura de componentes ni diagrama UML.\n"
            "Persistencia no especificada y sin diseño de base de datos.\n\n"
            "[Página 3]\n"
            "Ausencia total de plan de pruebas y análisis de seguridad de datos de postulantes.\n"
        ),
        "ground_truth": {
            "verdict": "RECHAZADO",
            "total_score": 34.0,
            "has_sufficient_text": True,
            "detected_sections": [],
        },
    },

    # ── INFORMACION_INSUFICIENTE (17-22) ──────────────────────────────────────
    {
        "id": "proj-17-scanned-document-receipts",
        "title": "Documento Escaneado de Facturas",
        "page_count": 2,
        "document_text": "[Página 1]\n[IMAGEN ESCANEADA SIN TEXTO OCR]\n\n[Página 2]\n[IMAGEN ESCANEADA]",
        "ground_truth": {
            "verdict": "INFORMACION_INSUFICIENTE",
            "total_score": 0.0,
            "has_sufficient_text": False,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-18-empty-placeholder",
        "title": "Documento en Blanco Placeholder",
        "page_count": 1,
        "document_text": "[Página 1]\nDocumento preliminar de proyecto de software sin redactar.",
        "ground_truth": {
            "verdict": "INFORMACION_INSUFICIENTE",
            "total_score": 0.0,
            "has_sufficient_text": False,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-19-single-page-memo",
        "title": "Memorando Corto de Asignación",
        "page_count": 1,
        "document_text": (
            "[Página 1]\n"
            "Estimado equipo, por favor iniciar el desarrollo del nuevo módulo de facturación la próxima semana. "
            "Reunión de coordinación el lunes a primera hora en sala de conferencias."
        ),
        "ground_truth": {
            "verdict": "INFORMACION_INSUFICIENTE",
            "total_score": 0.0,
            "has_sufficient_text": False,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-20-blank-template",
        "title": "Plantilla Vacía",
        "page_count": 1,
        "document_text": "",
        "ground_truth": {
            "verdict": "INFORMACION_INSUFICIENTE",
            "total_score": 0.0,
            "has_sufficient_text": False,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-21-corrupted-ocr",
        "title": "PDF Corrupto o Ilegible",
        "page_count": 2,
        "document_text": "[Página 1]\n#@! ?? ~~ ??? ---\n[Página 2]\n=== /// ...",
        "ground_truth": {
            "verdict": "INFORMACION_INSUFICIENTE",
            "total_score": 0.0,
            "has_sufficient_text": False,
            "detected_sections": [],
        },
    },
    {
        "id": "proj-22-adhoc-notes",
        "title": "Apuntes Sueltos de Brainstorming",
        "page_count": 1,
        "document_text": "[Página 1]\nNotas: hablar con Juan sobre base de datos. Comprar servidor. Ver colores de botones.",
        "ground_truth": {
            "verdict": "INFORMACION_INSUFICIENTE",
            "total_score": 0.0,
            "has_sufficient_text": False,
            "detected_sections": [],
        },
    },
]

DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(DATASET_PATH, "w", encoding="utf-8") as f:
    for item in samples:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"Dataset generated at {DATASET_PATH} with {len(samples)} samples.")
