# Contrato propuesto del núcleo UML

El aplicador recibe una copia del grafo y una lista ordenada de operaciones. No tiene acceso a MongoDB, transporte ni identidad. Una lista completa se valida antes de devolver un resultado; un fallo no modifica el grafo original. Cada operación utiliza `type`, el identificador del elemento y, según corresponda, `data` o `patch`.

Los parches mezclan objetos recursivamente; las listas suministradas se reemplazan explícitamente y las omitidas se conservan. `null` establece el valor nulo: no elimina una clave. Los identificadores no pueden cambiarse mediante un parche. `remove_node` elimina también las relaciones que lo referencian, incluidos extremos X6 `{cell: ...}`. Los campos y metadatos desconocidos se conservan.

La persistencia sigue siendo responsabilidad del repositorio. Para proteger contra solicitudes atrasadas el cliente debe aportar su revisión observada; un compare-and-set confirma como máximo un cambio sobre esa revisión. Este contrato aún no certifica la integración completa de todas las vías, idempotencia durable ni recuperación distribuida; véase el informe de estado de la fase.
