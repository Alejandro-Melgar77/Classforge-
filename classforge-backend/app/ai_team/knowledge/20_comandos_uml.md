# 20 — Comandos UML y Esquema de Respuestas de IA

ClassForge permite modificar el lienzo UML de forma automatizada mediante el esquema `UMLCommandResponse` definido en `app/modules/ai/schemas.py`.

## Esquema Pydantic (`app/modules/ai/schemas.py`)

```python
class UMLCommandResponse(BaseModel):
    action: str  # "generate_system" | "add_class" | "update_class" | "delete_element" | "add_relation" | "refactor"
    classes: List[UMLClassCommand] = []
    relations: List[UMLRelationCommand] = []
    deleted_elements: List[str] = []
    explanation: str
    source: str = "backend_ai"  # "gemini_ai" | "backend_ai"
```

## 8 Ejemplos Concretos de Comandos UML

### 1. Creación de una Nueva Clase (`add_class`)
```json
{
  "action": "add_class",
  "classes": [
    {
      "name": "Usuario",
      "stereotype": "entity",
      "attributes": [
        {"name": "id", "type": "Long", "visibility": "-"},
        {"name": "email", "type": "String", "visibility": "-"},
        {"name": "passwordHash", "type": "String", "visibility": "-"},
        {"name": "activo", "type": "Boolean", "visibility": "-"}
      ],
      "methods": [
        {"name": "autenticar", "params": "password: String", "return_type": "Boolean", "visibility": "+"},
        {"name": "desactivar", "params": "", "return_type": "void", "visibility": "+"}
      ]
    }
  ],
  "relations": [],
  "deleted_elements": [],
  "explanation": "Se crea la entidad Usuario con atributos esenciales de autenticación y encapsulamiento privado.",
  "source": "backend_ai"
}
```

### 2. Actualización de Clase Existente (`update_class`)
```json
{
  "action": "update_class",
  "classes": [
    {
      "name": "Pedido",
      "stereotype": "entity",
      "attributes": [
        {"name": "id", "type": "UUID", "visibility": "-"},
        {"name": "codigoSeguimiento", "type": "String", "visibility": "-"},
        {"name": "total", "type": "Double", "visibility": "-"},
        {"name": "estado", "type": "String", "visibility": "-"}
      ],
      "methods": [
        {"name": "calcularTotal", "params": "", "return_type": "Double", "visibility": "+"}
      ]
    }
  ],
  "relations": [],
  "deleted_elements": [],
  "explanation": "Se añade el atributo codigoSeguimiento y método calcularTotal a la clase Pedido.",
  "source": "backend_ai"
}
```

### 3. Generalización / Herencia (`add_relation`)
```json
{
  "action": "add_relation",
  "classes": [],
  "relations": [
    {
      "source": "Cliente",
      "target": "Persona",
      "type": "inheritance",
      "label": "extiende",
      "source_multiplicity": null,
      "target_multiplicity": null
    }
  ],
  "deleted_elements": [],
  "explanation": "Se establece relación de herencia: Cliente es una especialización de Persona.",
  "source": "backend_ai"
}
```

### 4. Composición Fuerte con Multiplicidades (`add_relation`)
```json
{
  "action": "add_relation",
  "classes": [],
  "relations": [
    {
      "source": "Pedido",
      "target": "LineaPedido",
      "type": "composition",
      "label": "contiene",
      "source_multiplicity": "1",
      "target_multiplicity": "1..*"
    }
  ],
  "deleted_elements": [],
  "explanation": "Composición: Las líneas de pedido no tienen existencia independiente fuera del ciclo de vida de Pedido.",
  "source": "backend_ai"
}
```

### 5. Agregación Débil Compartida (`add_relation`)
```json
{
  "action": "add_relation",
  "classes": [],
  "relations": [
    {
      "source": "Departamento",
      "target": "Profesor",
      "type": "aggregation",
      "label": "asigna",
      "source_multiplicity": "1",
      "target_multiplicity": "0..*"
    }
  ],
  "deleted_elements": [],
  "explanation": "Agregación: El profesor puede pertenecer a un departamento pero subsiste si este se disuelve.",
  "source": "backend_ai"
}
```

### 6. Relación N-a-N con Clase de Asociación Intermedia (`generate_system`)
```json
{
  "action": "generate_system",
  "classes": [
    {
      "name": "Estudiante",
      "attributes": [{"name": "id", "type": "Long", "visibility": "-"}, {"name": "nombre", "type": "String", "visibility": "-"}],
      "methods": []
    },
    {
      "name": "Curso",
      "attributes": [{"name": "id", "type": "Long", "visibility": "-"}, {"name": "titulo", "type": "String", "visibility": "-"}],
      "methods": []
    },
    {
      "name": "Matricula",
      "stereotype": "association_class",
      "attributes": [
        {"name": "id", "type": "Long", "visibility": "-"},
        {"name": "fecha", "type": "Date", "visibility": "-"},
        {"name": "calificacionFinal", "type": "Double", "visibility": "-"}
      ],
      "methods": []
    }
  ],
  "relations": [
    {
      "source": "Estudiante",
      "target": "Matricula",
      "type": "composition",
      "source_multiplicity": "1",
      "target_multiplicity": "0..*"
    },
    {
      "source": "Curso",
      "target": "Matricula",
      "type": "composition",
      "source_multiplicity": "1",
      "target_multiplicity": "0..*"
    }
  ],
  "deleted_elements": [],
  "explanation": "Se resuelve la relación N-a-N mediante la clase de asociación Matricula para alojar fecha y nota.",
  "source": "backend_ai"
}
```

### 7. Eliminación de Elemento Redundante (`delete_element`)
```json
{
  "action": "delete_element",
  "classes": [],
  "relations": [],
  "deleted_elements": ["TempSessionHelper", "edge_old_association_12"],
  "explanation": "Se eliminan clases y aristas temporales que violaban el principio de responsabilidad única.",
  "source": "backend_ai"
}
```

### 8. Refactorización para Desacoplamiento e Interfaz (`refactor`)
```json
{
  "action": "refactor",
  "classes": [
    {
      "name": "NotificadorService",
      "type": "interface",
      "stereotype": "service",
      "attributes": [],
      "methods": [
        {"name": "enviar", "params": "destinatario: String, mensaje: String", "return_type": "Boolean", "visibility": "+"}
      ]
    },
    {
      "name": "EmailNotificador",
      "attributes": [{"name": "servidorSmtp", "type": "String", "visibility": "-"}],
      "methods": [
        {"name": "enviar", "params": "destinatario: String, mensaje: String", "return_type": "Boolean", "visibility": "+"}
      ]
    }
  ],
  "relations": [
    {
      "source": "EmailNotificador",
      "target": "NotificadorService",
      "type": "realization",
      "label": "implementa",
      "source_multiplicity": null,
      "target_multiplicity": null
    }
  ],
  "deleted_elements": [],
  "explanation": "Se extrae la interfaz NotificadorService para cumplir el principio de inversión de dependencias (DIP).",
  "source": "backend_ai"
}
```
