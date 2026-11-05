# Fase 1: avance y riesgos de seguridad

Estado: incompleta. Base `26af799`, rama `main`. Este documento no certifica seguridad ni disponibilidad para producción.

## Cambios y decisiones

- H01: el constructor del chat ya filtraba por proyecto; se añadieron filtros de proyecto y borrado a las consultas de diagramas de revisión, tareas y disparadores. Los hallazgos de revisión también se restringen al proyecto y diagrama. Falta demostrar integralmente autorización individual, snapshots y prompts mediante pruebas HTTP con proveedor espía.
- H02: las propuestas personales ahora exigen propietario; la escritura comprueba proyecto y pertenencia de la propuesta. Se rechaza `applied` hasta que una aplicación real pueda confirmarse. El cliente puede seguir enviando `dismissed`; `applied` devuelve error 400. Las pruebas anteriores que aceptaban una aplicación ficticia se actualizaron.
- H03: además de los bloqueos existentes de Gemini, se rechazan proveedores globales desconocidos y destinos Ollama que no sean loopback en modo local. Es una decisión restrictiva: un túnel o servidor Ollama remoto requiere desactivar el modo exclusivamente local. Falta una prueba integral de todas las modalidades y evitar todas las respuestas simuladas de fallback.
- H09: los trabajos nuevos rechazan campos de credenciales conocidos, y el chat diferido rechaza claves por petición antes de crear mensajes. Debe configurarse la credencial del proveedor en el servidor. Los trabajos antiguos no reutilizan `payload.api_key`, pero sus documentos no han sido migrados ni borrados: necesitan inventario y migración con respaldo. La nueva clave activa tiene índice único por proyecto y tipo de trabajo; documentos antiguos sin esa clave no quedan cubiertos por el índice. La finalización y fallo exigen worker, generación de intento y lease vigente. Falta renovación, autorización diferida, coherencia completa de estados y protección de efectos durante o después de perder el lease; el control de finalización no proporciona ejecución exactamente una vez.
- H10: los mensajes WebSocket revalidan usuario, proyecto y membresía en la base de datos; al perder acceso se cierra la conexión. El documento de equipo prevalece sobre `user.team_ids`. La revocación no se propaga a una conexión que solo recibe eventos, y los tokens WS no están vinculados a una sesión revocable. No se han establecido permisos diferenciados de lectura y escritura.

## Verificación y riesgos

La suite inicial ejecutó 299 pruebas con MongoDB simulado. Las regresiones añadidas cubren propuestas, credenciales, reservas, deduplicación simulada, destino Ollama y retirada de membresía. Las pruebas simuladas no demuestran atomicidad de MongoDB ni comportamiento multiproceso. No se usaron datos de producción ni proveedores externos; MongoDB real y compatibilidad integral de clientes permanecen pendientes.

La validación semántica completa y la aplicación transaccional de propuestas pertenecen al motor de mutaciones de la Fase 2. Los problemas de autorización diferida, revocación WebSocket, privacidad de mensajes y efectos duplicados son bloqueantes de la Fase 1 y requieren resolución antes de declararla terminada.
