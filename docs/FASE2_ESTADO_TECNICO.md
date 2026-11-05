# Fase 2: estado técnico

**FASE 2 INCOMPLETA.** Este avance no garantiza que las vías existentes de edición sean seguras para colaboración concurrente. Rama `main`, base `26af799`; había cambios locales de Fase 1 y anteriores al inicio, que se conservaron. No se hizo commit ni despliegue.

| Área | Estado inicial | Avance | Evidencia y estado |
|---|---|---|---|
| H04 | El editor IA hacía round-trip por un modelo que descartaba extensiones. | Aplicador puro de operaciones en `operations.py`; el editor IA traduce su simulación a parches sobre el documento original. | Pruebas de preservación y lotes; parcial: no todos los adaptadores lo utilizan. |
| H05 | REST tenía CAS y `base_version` opcional; WS no avanzaba versión. | Endpoint de operaciones requiere revisión; restauración, XMI e imagen usan la revisión observada por el servidor al iniciar. | Prueba HTTP de conflicto con MongoDB simulado; incompleto: REST legado y WS eluden revisión conocida del cliente, falta idempotencia. |
| H10 | Existía validación estructural parcial. | El motor valida entrada y resultado; se validan también dimensiones finitas y positivas. | Pruebas puras; incompleto: faltan tipos, multiplicidades y otras reglas UML e integración de WS. |
| Persistencia | Existía recuperación de snapshots posteriores; creación podía quedar sin snapshot y se descartaba historia embebida y snapshots antiguos. | La creación guarda snapshot pendiente en el documento; se verifica el grafo al materializar, se conserva historia embebida y se elimina la poda automática. | Pruebas con fallos simulados y recuperación; sin MongoDB real ni prueba de todos los puntos de fallo. |
| Migración | Script previo y estructuras mixtas. | Se preservan campos desconocidos e historia embebida durante guardados; el adaptador IA conserva miembros de nivel superior. | Falta inventario completo, migración con respaldo y dry-run verificados. |
| Integración | Varias rutas independientes, incluido WS directo. | Endpoint `POST /diagrams/{id}/operations`; editor IA usa el aplicador. | Incompleta: WS, Angular, cliente móvil y propuestas no están integrados con un protocolo común. |

## Contrato y arquitectura

El contrato y la semántica de parches se describen en `FASE2_CONTRATO_OPERACIONES.md`. El aplicador opera sobre una copia, procesa secuencias completas, mantiene campos desconocidos y valida el resultado. No escribe en MongoDB. El endpoint REST autoriza con el servicio de diagramas y persiste con la revisión suministrada; no implementa aún `operation_id` ni respuestas idempotentes. El editor IA conserva el grafo original y aplica las diferencias identificadas por el comando; las listas suministradas por un parche se reemplazan expresamente.

El repositorio conserva el mecanismo anterior: una actualización condicional escribe el grafo y `_pending_snapshot` en un documento, y después materializa el snapshot. La creación ahora utiliza el mismo patrón. La recuperación aún depende de una lectura o escritura posterior; hay que resolver el límite BSON, fallos de auditoría posteriores al commit y garantías distribuidas. El índice único de revisiones requiere una base MongoDB configurada correctamente.

## Verificación

La suite de referencia tuvo 307 pruebas aprobadas. La suite final tuvo 314 aprobadas, cero fallidas, cero omitidas y 13 advertencias. Las nuevas pruebas cubren parches, fallos de lote, preservación de datos del editor IA, compatibilidad de miembros legados, preservación de historia embebida, recuperación del snapshot inicial y conflicto HTTP. Se ejecutaron también regresiones existentes de XMI, generadores, autenticación y Fase 1 como parte de la suite.

Se usó `mongomock-motor` forzando una dirección local inaccesible; no se usaron datos reales. Docker Desktop no tenía servidor disponible y no se encontró `mongod`, por lo que no se ejecutaron las pruebas obligatorias con MongoDB real o múltiples procesos. Las pruebas simuladas no demuestran atomicidad real. Tampoco se ejecutaron pruebas Angular, móvil ni proveedores de IA.

## Bloqueantes

- Integrar WebSocket y todos los escritores con revisión del cliente y el motor; el recorrido WS todavía escribe directamente en MongoDB y puede eludir el versionado.
- Establecer `operation_id` durable e idempotente, respuesta tras pérdida de conexión y prueba real de concurrencia/recuperación.
- Completar validación UML, adaptación de datos existentes, migración verificable y límites de documento.
- Integrar y probar clientes Angular, operaciones de propuestas e IA, y resolver conflictos sin descartar ediciones locales.
- Resolver las dependencias pendientes de autorización y estados de la Fase 1 descritas en `FASE1_SEGURIDAD_ESTADO.md`.

La distribución durable de eventos, presencia distribuida y recuperación integral de clientes corresponden a la Fase 3; no están implementadas aquí.
