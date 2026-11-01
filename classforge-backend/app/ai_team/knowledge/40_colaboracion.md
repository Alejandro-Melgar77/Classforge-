# 40 — Colaboración en Tiempo Real y Concurrencia

ClassForge soporta modelado multiusuario concurrente sobre WebSockets con persistencia atómica y exclusión mutua pesimista por elemento.

## Conexión y Autenticación (`app/modules/collaboration/router.py`)

1. **Token de un solo uso**:
   - Antes de conectar al WebSocket, el cliente solicita un token temporal en `GET /api/v1/diagrams/{id}/ws-token`.
   - Al conectar a `/ws/diagrams/{id}?token={ws_token}`, el backend verifica y consume el token atómicamente (`find_one_and_delete`). Un token consumido o expirado provoca cierre inmediato con código `4001`.
2. **Límites de Seguridad y Protección contra Abusos**:
   - Tamaño máximo por mensaje: **64 KB** (`MAX_MESSAGE_BYTES = 65536`).
   - Tasa máxima de envío: **60 mensajes/segundo** (`MAX_BURST_PER_SECOND = 60`).
   - Si se supera cualquiera de estos límites, el socket se termina con código `4008 (Policy Violation)`.

## Protocolo de Bloqueos (Locks) y Mensajes (`docs/ws-protocol.md`)

Para evitar condiciones de carrera y sobrescrituras destructivas en el canvas:
- **Bloqueo de Elemento**:
  - `NODE_LOCK` / `EDGE_LOCK`: Un usuario toma posesión temporal de un nodo o arista mientras lo arrastra o edita.
  - El backend almacena el lock en memoria (`active_locks: Dict[element_id, user_id]`).
- **Rechazo Concurrente (`OP_REJECTED`)**:
  - Si un usuario `B` intenta emitir `NODE_OPERATION` o `EDGE_OPERATION` sobre un elemento bloqueado por el usuario `A`, el backend **no persiste el cambio ni lo retransmite** a los demás.
  - El backend responde inmediatamente al usuario `B`:
    ```json
    { "type": "OP_REJECTED", "element_id": "node_123", "reason": "locked" }
    ```
  - El frontend del usuario `B` debe revertir la posición o estado del elemento a la última confirmada.
- **Liberación**:
  - `NODE_UNLOCK` / `EDGE_UNLOCK` o desconexión del cliente liberan automáticamente todos los locks del usuario.

## Persistencia Atómica en MongoDB (`app/modules/collaboration/service.py`)

El backend no utiliza Read-Modify-Write (que provocaría pérdida de datos en operaciones concurrentes), sino operadores atómicos directos:
1. **Adición (`add`)**: `$push` en `graph_data.nodes` o `graph_data.edges`.
2. **Eliminación (`delete`)**: `$pull` atómico del nodo y `$pull` simultáneo de todas las aristas que referencien su ID como `source` o `target` (limpieza de huérfanos).
3. **Modificación / Movimiento (`move`, `update`)**: `$set` atómico con `arrayFilters` posicionales para actualizar coordenadas o atributos en el documento de MongoDB sin lecturas previas.
