# Fase 3: estado técnico

**FASE 3 INCOMPLETA.** El motor de revisión de la Fase 2 y la autorización de la Fase 1 continúan incompletos. El sistema no garantiza convergencia, entrega durable ni edición concurrente segura.

Rama `main`, commit inicial `26af799`; el árbol ya contenía cambios sin confirmar de fases anteriores. Se conservaron. No se agregaron dependencias ni se hizo commit, push o despliegue.

| Área | Estado inicial | Cambio | Estado |
|---|---|---|---|
| H06 / SYNC-01 | No había outbox ni difusión común para todos los guardados. | Sin cambio. | Bloqueante: no hay entrega durable ni dispatcher. |
| SYNC-02 / SYNC-03 | Sin protocolo completo de ACK, idempotencia ni recuperación por revisión. | Sin cambio. | Bloqueante. |
| H11 / COLLAB-01 | Una conexión por usuario reemplazaba la anterior. | El gestor mantiene varias conexiones, presencia agregada y desconexión independiente; las operaciones llegan a otras pestañas del mismo usuario. | Parcial: probado en memoria, no en varios procesos o navegadores. |
| COLLAB-02 | Una desconexión liberaba bloqueos aunque hubiera otra pestaña; un usuario podía generar evento de liberación sin ser propietario. | Los bloqueos se conservan hasta la última conexión; solo su propietario puede liberarlos. | Parcial: falta titularidad por conexión, caducidad y coordinación distribuida. |
| COLLAB-03 | Salas y bloqueos locales al proceso; difusión secuencial sin límite. | Envíos concurrentes con timeout y limpieza de conexiones fallidas. | Parcial: falta bus compartido, backpressure completo y prueba de carga. |
| WEB-01 / AI-01 | Autoguardado y WebSocket tienen recorridos separados; las propuestas no usan un flujo durable. | Sin integración nueva en Angular ni IA. | Bloqueante. |
| SEC-01 | La autorización se revalidaba al recibir mensajes, pero no antes de enviar a conexiones pasivas; mensajes personales se difundían al proyecto completo. | Se verifica acceso antes de entregar y se restringen mensajes personales de IA al propietario. | Parcial: falta vincular tokens WS a sesiones revocables y demostrar aislamiento completo. |

## Implementación

`connection_manager.py` almacena un identificador aleatorio y una referencia por conexión dentro de cada usuario de sala. `router.py` desconecta la referencia concreta, comunica salida solo al cerrar la última conexión y excluye únicamente la conexión emisora de operaciones. Cada entrega consulta la autorización vigente y tiene límite de espera; al fallar se cierra y limpia la conexión. Los eventos de mensajes personales con `thread=personal` se restringen a `owner_id` y se descartan si carecen de propietario.

Este gestor sigue siendo memoria local de un proceso. No hay garantías de entrega ni orden entre procesos; los bloqueos siguen asociados al usuario, no a pestañas individuales. Las comprobaciones de permisos no sustituyen la revocación de sesión y todavía existe una ventana entre la comprobación y la entrega.

## Verificación y pendientes

La batería inicial pasó 314 pruebas con MongoDB simulado. La suite final obtuvo 320 aprobadas, cero fallidas, cero omitidas y 13 advertencias. Las seis pruebas nuevas cubren dos y tres conexiones, cierre independiente, fallo de envío, revocación previa a difusión, privacidad de mensajes personales y propiedad de bloqueos. No se utilizaron datos de producción.

El servidor Docker no estaba disponible y no se encontró `mongod`; por ello no se ejecutaron pruebas con MongoDB real, dos procesos, bus, reinicio de dispatcher, navegadores o mediciones de latencia y carga. No se afirma soporte Flutter ni preparación para producción. La sincronización de las escrituras WS existentes, outbox, protocolo ACK/NACK, recuperación de clientes y autorización por sesión deben completarse antes de cerrar esta fase.
