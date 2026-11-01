# Protocolo de Colaboración en Tiempo Real (WebSocket)

**Documento:** `docs/ws-protocol.md`  
**Módulo:** `app/modules/collaboration`  
**Endpoint:** `/api/v1/ws/diagrams/{diagram_id}`  

---

## 1. Conexión y Autenticación

1. **Obtención del Token:**
   El cliente debe solicitar un token temporal de un solo uso mediante:
   ```http
   GET /api/v1/diagrams/{diagram_id}/ws-token
   Authorization: Bearer <access_token>
   ```
   **Respuesta:**
   ```json
   {
     "success": true,
     "message": "Token generated",
     "data": {
       "token": "a1b2c3d4e5...",
       "expires_at": "2026-10-31T12:00:00Z"
     }
   }
   ```

2. **Apertura del WebSocket:**
   ```
   ws://<host>:<port>/api/v1/ws/diagrams/{diagram_id}?token={ws_token}
   ```
   - **Token de un solo uso:** Se consume en la apertura (`find_one_and_delete`). Cualquier intento de reutilizar el token es rechazado con código de cierre `4001`.
   - **Reconexión:** En cada desconexión o reconexión, el cliente debe obtener un token fresco vía `GET /api/v1/diagrams/{diagram_id}/ws-token`.

3. **Límites de Conexión:**
   - **Tamaño máximo de mensaje:** 64 KB (65.536 bytes). Superar este límite desconecta inmediatamente con código `4008`.
   - **Ráfaga máxima (Burst):** 60 mensajes por segundo. Si se excede, el servidor cierra la conexión con código `4008`.

---

## 2. Mensajes del Cliente al Servidor (Client -> Server)

| Tipo (`type`) | Carga Útil (`payload`) | Descripción |
|---|---|---|
| `JOIN` | `{}` | Handshake inicial. Solicita sincronización de estado de la sala. |
| `CURSOR_MOVE` | `{"x": float, "y": float}` | Coordenadas del puntero del usuario en el lienzo. |
| `NODE_OPERATION` | `{"op": "add"\|"move"\|"update"\|"delete", "node_id": str, "data": {...}}` | Operación sobre un nodo UML. |
| `EDGE_OPERATION` | `{"op": "add"\|"update"\|"delete", "edge_id": str, "data": {...}}` | Operación sobre una arista/relación. |
| `LOCK_ACQUIRE` | `{"element_id": str}` | Solicita el bloqueo exclusivo de un nodo o arista. |
| `LOCK_RELEASE` | `{"element_id": str}` | Libera el bloqueo de un nodo o arista. |
| `PING` | `{}` | Keepalive periódico para mantener la conexión activa. |
| `CHAT_MESSAGE` | `{"content": str}` | Mensaje en el chat colaborativo del diagrama. |
| `PRESENCE_STATUS` | `{"status": "online"\|"away"\|"busy"}` | Cambio de estado de presencia del usuario. |

---

## 3. Mensajes del Servidor al Cliente (Server -> Client)

| Tipo (`type`) | Carga Útil (`payload`) | Descripción |
|---|---|---|
| `ROOM_STATE` | `{"users": [...], "chat_history": [...]}` | Estado inicial al unirse: usuarios conectados y chat previo. |
| `USER_JOINED` | `{"user_id": str, "user_name": str, "user_color": str, "role": str, "status": "online"}` | Notifica la conexión de un nuevo colaborador. |
| `USER_LEFT` | `{"user_id": str}` | Notifica la desconexión de un colaborador. |
| `CURSOR_UPDATE` | `{"user_id": str, "x": float, "y": float, "user_name": str, "user_color": str}` | Transmisión del cursor remoto de otro usuario. |
| `NODE_OPERATION` | `{"op": str, "node_id": str, "data": {...}, "user_id": str}` | Reenvío de operación de nodo aprobada. |
| `EDGE_OPERATION` | `{"op": str, "edge_id": str, "data": {...}, "user_id": str}` | Reenvío de operación de arista aprobada. |
| `LOCK_GRANTED` | `{"element_id": str, "user_id": str}` | Notifica a todos que el lock fue otorgado al usuario. |
| `LOCK_REJECTED` | `{"element_id": str}` | Enviado al solicitante si el elemento ya está bloqueado. |
| `LOCK_RELEASED` | `{"element_id": str, "user_id": str}` | Notifica la liberación de un lock. |
| `OP_REJECTED` | `{"element_id": str, "reason": "locked"}` | **Nuevo en P1:** Enviado al emisor si intenta mover, actualizar o borrar un elemento bloqueado por otro usuario. No se persiste ni se retransmite. |
| `PONG` | `{}` | Respuesta a mensaje `PING`. |
| `CHAT_MESSAGE` | `{"type": "CHAT_MESSAGE", "content": str, "user_id": str, "user_name": str, "user_color": str, "timestamp": str}` | Difusión de mensaje de chat. |
| `USER_PRESENCE_UPDATED` | `{"user_id": str, "status": str}` | Difusión de cambio de estado de presencia. |

---

## 4. Política de Concurrencia y Locks

1. **Locks Exclusivos:**
   - Antes de modificar un elemento, un cliente puede enviar `LOCK_ACQUIRE`.
   - Si otro cliente intenta enviar `NODE_OPERATION` o `EDGE_OPERATION` sobre un elemento que posee lock activo de otro usuario, el backend responde con:
     ```json
     {
       "type": "OP_REJECTED",
       "element_id": "node_xyz",
       "reason": "locked"
     }
     ```
   - Al desconectarse un cliente, todos los locks retenidos por él se liberan automáticamente y se difunden con `LOCK_RELEASED`.

2. **Persistencia Atómica en Base de Datos:**
   - Las operaciones `NODE_OPERATION` y `EDGE_OPERATION` se persisten mediante operadores atómicos de MongoDB:
     - Inserción (`add`): `$push`
     - Eliminación (`delete`): `$pull` (incluyendo aristas huérfanas)
     - Modificación / Movimiento (`move`, `update`): `$set` con `arrayFilters` (y `$` posicional)
   - Esto previene pérdidas por condición de carrera (race conditions) bajo alta concurrencia.

---

## 5. Protocolo de WebSocket de Proyecto (P4 — Chat de Equipo y Estado IA)

**Endpoint:** `/api/v1/ws/projects/{project_id}?token={ws_token}`  
**Módulo:** `app/modules/collaboration` y `app/modules/ai_chat`  
**Sala en ConnectionManager:** `project:{project_id}`

### 5.1 Conexión y Autenticación de Proyecto
1. **Token de un solo uso:**
   El cliente solicita el token de WebSocket mediante:
   ```http
   GET /api/v1/ai-chat/projects/{project_id}/ws-token
   Authorization: Bearer <access_token>
   ```
   **Respuesta (200 OK):**
   ```json
   {
     "success": true,
     "message": "Token generated",
     "data": {
       "token": "7c48f8c0-...",
       "expires_at": "2026-11-01T12:05:00Z"
     }
   }
   ```
2. **Apertura:**
   ```
   ws://<host>:<port>/api/v1/ws/projects/{project_id}?token={token}
   ```
   - El token se consume inmediatamente en MongoDB (`ws_tokens.find_one_and_delete`). Reintentos o tokens expirados reciben cierre con código `4001`.
   - Se valida pertenencia al proyecto (`require_project_member` / `can_access_project`). Usuarios no miembros reciben cierre con código `4003`.
   - **Límites:** Tamaño máximo de mensaje 64 KB, ráfaga máxima 60 msg/s (código de cierre `4008`).

### 5.2 Mensajes Cliente -> Servidor (Client -> Server)
| Tipo (`type`) | Payload | Descripción |
|---|---|---|
| `PING` | `{}` | Keepalive. El servidor responde inmediatamente con `{"type": "PONG"}`. |
| `TYPING` | `{"is_typing": bool}` | Notifica al equipo si el usuario comenzó o detuvo su escritura en el chat. |

### 5.3 Mensajes Servidor -> Cliente (Server -> Client)
| Tipo (`type`) | Payload | Descripción |
|---|---|---|
| `PRESENCE` | `{"type": "PRESENCE", "members": [{"user_id": str, "user_name": str, "role": str, "status": "online"}, ...]}` | Lista en tiempo real de todos los integrantes conectados al proyecto. Se emite al conectar y desconectar. |
| `AI_TYPING` | `{"type": "AI_TYPING", "role": str, "state": "start"\|"stop", "user_name": Optional[str]}` | Notifica que un rol de IA (o usuario) está redactando una respuesta. Permite renderizar burbuja o indicador de escritura. |
| `AI_MESSAGE_CREATED` | `{"type": "AI_MESSAGE_CREATED", "message": {...}}` | Notifica la creación y guardado de un nuevo mensaje (`AiMessage`). |
| `AI_MESSAGE_UPDATED` | `{"type": "AI_MESSAGE_UPDATED", "message": {...}}` | Notifica la actualización de un mensaje (ej. resolución de status `ok`/`error`, actualización de `proposal_state`). |
| `AI_STATE_CHANGED` | `{"type": "AI_STATE_CHANGED", "state": {...}}` | Notifica cambios en el modo participativo o en la autonomía de roles (`AiProjectState`). |
| `AI_TASK_UPDATED` | `{"type": "AI_TASK_UPDATED", "task": {...}}` | Notifica cambios en el estado de una tarea (`in_progress`, `completed`, `failed`). |
| `PONG` | `{"type": "PONG"}` | Respuesta a keepalive `PING`. |

### 5.4 Estrategia de Reconexión
El WebSocket de proyecto es un flujo reactivo de eventos en vivo, **no la fuente de verdad persistente**.
Tras una desconexión o reconexión:
1. El cliente solicita un nuevo token vía `GET /api/v1/ai-chat/projects/{project_id}/ws-token`.
2. Reconecta el WebSocket.
3. El cliente consulta el historial faltante mediante:
   ```http
   GET /api/v1/ai-chat/projects/{project_id}/history?after={ultimo_created_at_o_id}
   ```
   garantizando consistencia absoluta sin pérdida de mensajes ni estados.
