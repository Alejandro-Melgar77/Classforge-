# 60 — Glosario Formal de Modelado UML y Software (Español)

Este glosario unifica la terminología utilizada por todos los roles de IA en ClassForge (`app/ai_team/domain/roles.py`).

## Clasificadores UML

- **Clase**: Plantilla que define el estado (atributos) y comportamiento (métodos) de objetos del dominio del problema.
- **Clase Abstracta**: Clase que no puede instanciarse directamente y sirve como base genérica para subclases que completan su implementación.
- **Interfaz**: Contrato formal que especifica un conjunto de operaciones que una clase debe implementar, sin alojar lógica ni atributos de instancia.
- **Enumeración (`enum`)**: Tipo de dato discreto que define un conjunto fijo de constantes simbólicas legibles.
- **Nota**: Elemento visual informativo para documentar decisiones de diseño sin impacto estructural en el código.
- **Paquete**: Mecanismo de agrupación modular de clasificadores relacionados para delimitar subsistemas o bounded contexts.

## Visibilidad y Miembros

- **Público (`+`)**: Accesible desde cualquier clasificador externo.
- **Privado (`-`)**: Accesible exclusivamente dentro del clasificador que lo declara (base del encapsulamiento).
- **Protegido (`#`)**: Accesible dentro del clasificador y en todas sus subclases derivadas.
- **Paquete (`~`)**: Accesible por cualquier clasificador que resida en el mismo paquete o módulo.

## Relaciones entre Clasificadores

- **Generalización / Herencia**: Relación taxonómica donde una subclase hereda atributos y operaciones de una superclase ("es-un"). Representada por una flecha continua con triángulo hueco cerrado hacia la superclase.
- **Realización**: Relación donde una clase concreta implementa las operaciones abstractas definidas por una interfaz. Representada por una flecha discontinua con triángulo hueco.
- **Asociación**: Conexión estructural entre dos clasificadores que indica navegación o colaboración. Puede poseer nombre y cardinalidades en ambos extremos.
- **Agregación**: Relación débil "todo-parte" donde el objeto parte puede existir independientemente del objeto contenedor (diamante hueco en el contenedor).
- **Composición**: Relación fuerte "todo-parte" o existencial, donde el ciclo de vida del objeto parte está atado estrictamente al contenedor (diamante relleno).
- **Dependencia**: Relación transitoria donde un clasificador utiliza a otro temporalmente (ej. parámetro de método o tipo local). Representada por flecha discontinua abierta.
- **Clase de Asociación**: Clasificador que modela y aloja propiedades y comportamiento propios de una relación (típicamente N a N) entre otros dos clasificadores.

## Métricas y Principios de Diseño

- **Clase Dios (God Class)**: Antipatrón donde una sola clase acumula más de 15 atributos/métodos y concentra la lógica de múltiples dominios, violando el principio de responsabilidad única.
- **Linter Determinista**: Analizador puramente algorítmico (`app/ai_team/domain/lint.py`) que valida reglas estructurales y de nomenclatura sobre el grafo sin requerir inferencia de modelos LLM.
- **Cohesión**: Grado en que los elementos internos de una clase pertenecen juntos y sirven a un propósito conceptual único.
- **Acoplamiento**: Grado de interdependencia entre módulos; el buen diseño persigue bajo acoplamiento y alta cohesión.
