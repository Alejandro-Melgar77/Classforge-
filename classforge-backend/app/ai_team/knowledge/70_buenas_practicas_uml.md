# 70 — Buenas Prácticas de Modelado UML y Principios SOLID

Este documento establece los estándares de calidad arquitectural que los roles de IA promueven y que el linter determinista (`app/ai_team/domain/lint.py`) audita en ClassForge.

## 1. Principios SOLID Aplicados al Diagrama de Clases

1. **Principio de Responsabilidad Única (SRP)**:
   - Cada clase debe tener una sola razón para cambiar y una responsabilidad bien delimitada.
   - *Antipatrón*: **Clase Dios (God Class)** con más de 15 miembros (atributos + métodos) o que mezcla persistencia, presentación y reglas de negocio.
   - *Solución*: Descomponer en clases cohesivas especializadas (ej. separar `Usuario` de `UsuarioNotifier` y `UsuarioRepository`).

2. **Principio de Abierto/Cerrado (OCP)**:
   - Las entidades deben estar abiertas a la extensión pero cerradas a la modificación.
   - *Buenas prácticas*: Utilizar interfaces o clases abstractas polimórficas (ej. `EstrategiaDescuento`) para permitir nuevos comportamientos sin modificar el cliente que los consume.

3. **Principio de Sustitución de Liskov (LSP)**:
   - Las subclases deben poder sustituir a su superclase sin alterar la corrección del programa.
   - Evitar heredar de una clase concreta únicamente para reutilizar código si no existe una relación semántica estricta "es-un".

4. **Principio de Segregación de Interfaces (ISP)**:
   - Los clientes no deben verse forzados a depender de interfaces con métodos que no utilizan.
   - Favorecer interfaces reducidas y específicas sobre interfaces monolíticas y sobrecargadas.

5. **Principio de Inversión de Dependencias (DIP)**:
   - Los módulos de alto nivel no deben depender de módulos de bajo nivel; ambos deben depender de abstracciones (interfaces).
   - En ClassForge, los controladores y servicios deben asociarse a interfaces mediante relaciones de realización (`realization`) o dependencia (`dependency`).

## 2. Composición sobre Herencia

- **Herencia**: Crea un fuerte acoplamiento en tiempo de compilación. No debe usarse herencia múltiple de clases concretas (incompatible con Java/Spring Boot y generadora del problema del diamante).
- **Composición**: Proporciona flexibilidad en tiempo de ejecución ("tiene-un"). Si el objeto parte tiene un ciclo de vida propio que trasciende al contenedor, modelar como **agregación**; si desaparece junto con el contenedor, modelar como **composición**.

## 3. Resolución de Asociaciones N-a-N (Muchos a Muchos)

- Las asociaciones directas `*` a `*` (o `0..*` a `0..*`) son ambiguas cuando la relación requiere almacenar atributos propios (como fecha de vinculación, estado, rol o puntuación).
- **Regla de Oro**: Descomponer la asociación N-a-N creando una **Clase de Asociación intermedia** conectada con relaciones 1..* hacia ambos extremos (ej. `Estudiante` 1 -- * `Matricula` * -- 1 `Curso`).
- Facilita la generación directa y limpia de tablas intermedias en JPA (`@JoinTable`) y SQLAlchemy (`Table` asociativa).

## 4. Convenciones de Nombres y Encapsulamiento

- **Nombres de Clases**: Siempre en `PascalCase`, sustantivos en singular (ej. `Factura`, `DetalleEnvio`).
- **Nombres de Atributos**: Siempre en `camelCase` (ej. `precioUnitario`, `fechaVencimiento`).
- **Encapsulamiento**: Todo atributo de entidad persistible debe declararse con visibilidad privada (`-`) o protegida (`#`), exponiendo comportamiento mediante métodos públicos (`+`).
- **Claves Primarias**: Toda clase persistible debe contener un atributo identificador (`id`: `Long`, `UUID` o `Integer`) para posibilitar la generación ORM sin ambigüedades.
