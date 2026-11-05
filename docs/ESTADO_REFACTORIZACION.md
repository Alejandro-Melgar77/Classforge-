# Estado verificable de la refactorización — 2026-11-04

## Implementado localmente en esta etapa

- El guardado completo admite base_version y rechaza versiones obsoletas con 409.
- La escritura del grafo compara versión y grafo observado para detectar cambios durante el guardado.
- Grafo y registro de recuperación del snapshot se escriben atómicamente en el mismo documento MongoDB.
- El snapshot pendiente se materializa de forma idempotente antes de otro guardado o al consultar el historial. La consulta directa de esa versión puede leer el registro pendiente.
- La respuesta de guardado corresponde al estado comprometido por esa operación, no a una lectura posterior que podría contener cambios de otro usuario.
- El editor de IA envía la versión del diagrama sobre la que preparó su propuesta.
- El cliente web recuerda la versión obtenida al cargar/guardar/restaurar/importar y la envía al guardar. El autoguardado no reintenta automáticamente un conflicto 409 y conserva el respaldo local.
- Validación no destructiva del snapshot: IDs, duplicados, extremos existentes, coordenadas finitas, límites de elementos y ciclos de herencia.
- Validación adicional del protocolo WS: objetos JSON y operaciones con datos no vacíos.

## Verificación

- Backend: 299 pruebas aprobadas, 13 advertencias, MongoDB simulado.
- Web: 92 pruebas aprobadas en ChromeHeadless durante esta etapa.
- Reproducciones nuevas: dos solicitudes con la misma versión base; fallo de escritura del historial con recuperación posterior; grafos estructuralmente inválidos.
- No se certificó MongoDB real, despliegue ni integración con proveedores externos.

## Límites del cambio de versionado

No constituye todavía un protocolo completo de concurrencia colaborativa. base_version sigue siendo opcional para clientes antiguos. Las operaciones WS aún modifican directamente el grafo sin avanzar esa versión. El chequeo del grafo cubre cambios entre lectura y escritura del repositorio, pero no todos los snapshots atrasados de clientes. La creación inicial, auditoría, difusión y migración requieren todavía la misma estrategia de recuperación. El registro pendiente duplica temporalmente el grafo dentro del documento: hace falta verificar límites de bytes BSON y migración antes del despliegue. No publicar esta etapa como cierre de los puntos 1–4.

## Pendientes de aceptación de los once puntos

1. Integrar revisión base obligatoria en todos los escritores, resolver conflictos del cliente sin pérdida, unificar revisión WS, creación inicial recuperable, auditoría atómica y migración con respaldo/dry-run.
2. Motor común de operaciones por ID para editor, REST, WS, imágenes e IA, preservación completa y reversión.
3. Tipos UML, multiplicidades, visibilidades, validación en WS, límites de bytes, compatibilidad de datos existentes y pruebas XMI con herramientas externas.
4. Evento durable posterior al commit en todas las vías, ACK/NACK, deduplicación, recuperación por revisión y política de fallo tras commit.
5. Conexión por pestaña, revocación activa, salas/locks entre procesos, expiración de locks y clientes lentos.
6. Flujos generativos web completos con preview/aplicación y errores reales de texto, voz e imágenes.
7. Tareas por rol con ejecución y entregables auditables, normalización y layout determinista seguro, estado applied respaldado por una revisión real.
8. Credenciales fuera del payload, deduplicación atómica, renovación de leases, fencing de complete/fail, efectos idempotentes y estados terminales coherentes.
9. Mensaje+job recuperables, pruebas de aislamiento de tareas/contextos restantes, filtros y multiusuario bajo fallos.
10. Tutoriales completos por rol y pantalla, avance por acción, espera cancelable, accesibilidad y adaptación.
11. MongoDB real, varias instancias y navegadores, proveedores externos, fallos/carga, documentación actualizada, compilación final y prueba del despliegue real.

Móvil e IA local permanecen excluidos. Los archivos de auditoría originales son una fotografía anterior; sus afirmaciones de estado no sustituyen este registro.
