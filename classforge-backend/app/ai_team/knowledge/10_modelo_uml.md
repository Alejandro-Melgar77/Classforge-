# 10 — Modelo UML Canónico de ClassForge

Este documento define la representación interna formal de diagramas de clases en ClassForge y resuelve la discrepancia histórica entre variantes de serialización.

## Esquema Canónico (`app/ai_team/domain/diagram_model.py`)

Un diagrama canónico se compone de una colección de nodos (`nodes`) y aristas (`edges`):

### 1. Nodos (`Node`)
Representan clasificadores UML en el lienzo:
- `id: str`: Identificador único (UUID v4 o id alfanumérico de AntV X6).
- `name: str`: Nombre del clasificador (ej. `Usuario`, `OrdenCompra`). Debe seguir PascalCase.
- `type: str`: Tipo de clasificador. Valores soportados:
  - `class`: Clase concreta estándar.
  - `interface`: Interfaz formal de operaciones abstractas.
  - `abstract`: Clase abstracta que no puede instanciarse directamente.
  - `enum`: Enumeración de literales constantes.
  - `note`: Nota explicativa textual.
  - `package`: Contenedor modular de agrupación lógica.
- `stereotype: Optional[str]`: Anotación UML opcional (ej. `<<entity>>`, `<<service>>`, `<<repository>>`, `<<value_object>>`).
- `attributes: List[Attribute]`:
  - `name: str`: Identificador en camelCase (ej. `fechaCreacion`).
  - `type: str`: Tipo de dato abstracto o concreto (ej. `String`, `Integer`, `Double`, `Boolean`, `DateTime`, `UUID`).
  - `visibility: str`: Uno de `+` (público), `-` (privado), `#` (protegido), `~` (paquete).
- `methods: List[Method]`:
  - `name: str`: Nombre de operación en camelCase (ej. `calcularTotal`).
  - `params: str`: Lista de parámetros (ej. `monto: Double, tasa: Float`).
  - `return_type: str`: Tipo devuelto (ej. `void`, `Boolean`, `List[Item]`).
  - `visibility: str`: Uno de `+`, `-`, `#`, `~`.
- `position: Dict[str, float]`: Coordenadas `{ "x": float, "y": float }`.
- `size: Dict[str, float]`: Dimensiones `{ "width": float, "height": float }`.
- `notes: Optional[str]`: Comentarios descriptivos o documentación.
- `enum_values: List[str]`: Literales de enumeración (cuando `type == "enum"`).

### 2. Aristas (`Edge`)
Representan relaciones estructurales y de comportamiento entre clasificadores:
- `id: str`: Identificador único de la arista.
- `type: str`: Semántica de relación UML:
  - `association`: Asociación bidireccional o no dirigida básica.
  - `inheritance`: Generalización/herencia (subclase hacia superclase).
  - `composition`: Composición existencial fuerte (el ciclo de vida del hijo depende del padre, diamante relleno).
  - `aggregation`: Agregación compartida débil (el hijo existe independientemente, diamante hueco).
  - `dependency`: Dependencia de uso o invocación transitoria (flecha punteada).
  - `realization`: Implementación de interfaz por una clase (flecha punteada con triángulo cerrado).
- `source: str`: ID del nodo origen.
- `target: str`: ID del nodo destino.
- `label: Optional[str]`: Rol o nombre descriptivo de la relación (ej. `gestiona`, `contiene`).
- `source_multiplicity: Optional[str]`: Cardinalidad en el extremo origen (ej. `1`, `0..1`, `*`, `1..*`).
- `target_multiplicity: Optional[str]`: Cardinalidad en el extremo destino.

## Resolución de la Discrepancia de Serialización (Frontend vs Backend)

Al revisar `classforge-frontend/src/app/features/diagrams/services/canvas.service.ts` (`toGraphData()`):
- **Estructura real emitida por `canvas.service.toGraphData()`**:
  Las aristas se emiten con **campos planos en snake_case**:
  `{ id, type, source, target, label, source_multiplicity, target_multiplicity }`.
- **Estructura alternativa (legacy / WebSocket / DTOs antiguos)**:
  Algunos payloads ubicaban estos campos anidados en `edge.data`:
  `{ id, source, target, data: { type, sourceMultiplicity, targetMultiplicity } }`.

**Regla Canónica de ClassForge:**
El adaptador `from_graph_data` en `app/ai_team/domain/diagram_model.py` inspecciona y tolera ambas estructuras automáticamente:
1. Si existen campos planos (`source_multiplicity`, `target_multiplicity`, `type`), los adopta directamente.
2. Si los campos vienen en camelCase dentro de `edge["data"]` (`sourceMultiplicity`, `targetMultiplicity`), los extrae y normaliza a snake_case canónico.
3. El backend y los roles de IA trabajan **exclusivamente** sobre el esquema canónico unificado.
