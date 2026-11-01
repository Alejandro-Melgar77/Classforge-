# Handoff P6a — Frontend "Equipo IA": Capa de Datos, WebSocket y Estado

**Fecha:** 1 de noviembre de 2026  
**Módulo:** `src/app/features/ai-team/data-access/`  
**Objetivo alcanzado:** Cimientos tipados, reactivos y exhaustivamente probados del nuevo panel de "Equipo IA". Incluye modelo de datos estricto sin `any`, cliente HTTP tipado para todos los contratos de P4/P5, cliente WebSocket con reconexión exponencial y token único por intento, bus de eventos reactivo con reanudación `?after=`, fallback a sondeo (polling), puente de comandos UML hacia el lienzo con `CommandExecutorService`, erradicación de secretos y estado de equipo de `localStorage`, e interceptor HTTP para BYOK Gemini vía `sessionStorage`.

---

## 1. Estructura de Archivos (`src/app/features/ai-team/`)

Diseñada bajo el principio *Clean Architecture* / *Feature-First*:

```
src/app/features/ai-team/
├── index.ts                           # Barrel export público del subsistema
└── data-access/
    ├── ai-team.models.ts              # Tipos estrictos sin any (Proposal, AiRole, AiMessage, AiTask, AiProjectState, etc.)
    ├── ai-roles.registry.ts           # Catálogo canónico local de los 7 roles y sincronización dinámica
    ├── ai-roles.registry.spec.ts      # Suite de pruebas del catálogo de roles
    ├── ai-team.api.ts                 # Cliente HTTP tipado (rutas REST /ai-chat de P4)
    ├── ai-team.socket.ts              # Cliente WebSocket nativo con heartbeat, backoff y resume
    ├── ai-team.socket.spec.ts         # Suite de pruebas unitarias del WebSocket
    ├── command-bridge.ts              # Puente Proposal(uml_command) -> CommandExecutorService sin re-invocación a /ai/generate
    ├── command-bridge.spec.ts         # Pruebas del puente de comandos y chequeo de diagrama activo
    ├── ai-team.store.ts               # Signals Store (Angular 17 signals & computed)
    └── ai-team.store.spec.ts          # Pruebas de integración del store (optimista, idempotencia, filtros, etc.)
```

---

## 2. API Pública de `AiTeamStore` (Contrato para P6b)

`AiTeamStore` es un servicio `@Injectable({ providedIn: 'root' })` que encapsula todo el estado y la lógica reactiva del equipo de IA. Los componentes de la interfaz de usuario (P6b) deben consumirlo en modo `ChangeDetectionStrategy.OnPush`.

### 2.1. Signals de Lectura y `computed()`

| Propiedad | Tipo | Descripción |
|---|---|---|
| `projectId` | `Signal<string \| null>` | ID del proyecto activo. |
| `state` | `Signal<AiProjectState \| null>` | Estado compartido auditado (`participative`, `roles`, `digest`). |
| `isParticipativeEnabled` | `Signal<boolean>` | `computed()`: Si el modo participativo está activado en el proyecto. |
| `roles` | `Signal<AiRole[]>` | Lista de roles con skins UI, estado activo y autonomía configurada. |
| `activeRoles` | `Signal<AiRole[]>` | `computed()`: Roles actualmente activados para el proyecto. |
| `currentDigest` | `Signal<ProjectDigest \| null>` | `computed()`: Memoria ejecutiva compartida actual. |
| `activeThread` | `Signal<'personal' \| 'project'>` | Hilo seleccionado ('personal': chat propio; 'project': grupo). |
| `messages` | `Signal<AiMessage[]>` | Todos los mensajes cargados cronológicamente sin duplicados. |
| `filteredMessages` | `Signal<AiMessage[]>` | `computed()`: Mensajes filtrados por hilo activo, miembro, rol y `onlyProposals`. |
| `proposals` | `Signal<{messageId, proposal}[]>` | `computed()`: Todas las propuestas estructuradas extraídas de los mensajes. |
| `tasks` | `Signal<AiTask[]>` | Tareas asignadas a la IA en el proyecto. |
| `presence` | `Signal<WsPresenceMember[]>` | Miembros del equipo conectados en vivo al WebSocket de proyecto. |
| `connectionStatus` | `Signal<ConnectionStatus>` | Estado de conexión: `'disconnected' \| 'connecting' \| 'connected' \| 'reconnecting' \| 'polling_fallback'`. |
| `typingUsers` | `Signal<WsTypingEvent[]>` | Indicadores en vivo de integrantes o roles de IA escribiendo. |
| `pendingRoles` | `Signal<AiPendingRole[]>` | Roles de IA que están procesando respuestas en segundo plano. |
| `unreadCount` | `Signal<{ personal: number, project: number }>` | `computed()`: Contadores de mensajes no leídos por hilo/pestaña. |
| `hasMoreHistory` | `Signal<boolean>` | Indica si existen más mensajes antiguos disponibles en el servidor. |
| `isLoading` | `Signal<boolean>` | Carga inicial del proyecto en progreso. |
| `isLoadingMore` | `Signal<boolean>` | Paginación de historial hacia atrás en progreso. |
| `isSending` | `Signal<boolean>` | Envío de mensaje en curso. |
| `isCoolingDown` | `Signal<boolean>` | `computed()`: Si está activo el enfriamiento por límite de tasa (429). |
| `cooldownSecondsLeft`| `Signal<number>` | `computed()`: Segundos restantes de enfriamiento tras 429. |
| `forbidden` | `Signal<boolean>` | `true` si el usuario no tiene acceso al proyecto (403). |
| `errorMessage` | `Signal<string \| null>` | Mensaje descriptivo de error para el usuario (sin `console.error`). |
| `availableModels` | `Signal<string[]>` | Modelos obtenidos dinámicamente de `GET /ai/health` (incluye `gemini-3.8-flash`). |
| `activeModel` | `Signal<string>` | Modelo LLM seleccionado por el usuario para su sesión. |

---

### 2.2. Métodos Públicos (Acciones del Store)

#### Inicialización y Ciclo de Vida
- `init(projectId: string, currentUserId?: string, currentUserName?: string): void`  
  Carga el estado del proyecto, roles, salud de modelos, historial inicial, tareas y abre la conexión WebSocket de proyecto.
- `setSocketService(socket: AiTeamSocketService): void`  
  Vincula el cliente WebSocket y configura la suscripción reactiva bidireccional.
- `destroy(): void`  
  Limpia suscripciones, temporizadores de polling, indicadores de escritura y cierra el WebSocket.

#### Mensajería e Idempotencia
- `sendMessage(content: string, options?: { aiRole?: string, diagramId?: string, replyTo?: string }): Promise<void>`  
  Genera un `client_id` (UUID v4), crea un mensaje optimista con estado `'sending'`, y envía la petición al backend. Al recibir respuesta, reemplaza el mensaje por `client_id` con estado `'ok'`. Si falla, marca el mensaje como `'failed'`.
- `retrySendMessage(clientIdOrId: string): Promise<void>`  
  Reintenta el envío de un mensaje fallido manteniendo **el mismo `client_id`**, garantizando idempotencia estricta en el servidor MongoDB.
- `setTyping(isTyping: boolean): void`  
  Transmite el evento `TYPING` al equipo vía WebSocket.

#### Pestañas, Filtros y Paginación
- `selectThread(thread: 'personal' | 'project'): void`  
  Cambia la vista entre hilo personal y publicaciones de proyecto, reseteando el contador de no leídos de la pestaña elegida.
- `setFilters(filters: HistoryFilters): void`  
  Aplica filtros de historial (`member`, `role`, `onlyProposals`).
- `clearFilters(): void`  
  Restablece los filtros de historial.
- `loadMore(): Promise<void>`  
  Paginación hacia atrás utilizando el cursor `before` del mensaje más antiguo cargado.

#### Estado Compartido del Proyecto
- `toggleParticipative(): Promise<void>`  
  Activa/desactiva el modo participativo de forma optimista y persiste vía `PUT /ai-chat/projects/{id}/state`.
- `setRoleEnabled(roleId: string, enabled: boolean): Promise<void>`  
  Habilita o deshabilita un rol para el proyecto.
- `setAutonomy(roleId: string, autonomy: 'off' | 'suggest' | 'apply'): Promise<void>`  
  Configura el nivel de autonomía. Si un usuario con rol 'dev' intenta configurar 'apply', captura el error 403 y notifica.

#### Ejecución de Propuestas (`command-bridge`)
- `applyProposal(messageId: string, proposal: Proposal, currentDiagramId?: string, proposalDiagramId?: string): Promise<ApplyProposalResult>`  
  Valida la propuesta, verifica coincidencia con el diagrama activo, ejecuta directamente sobre el lienzo mediante `CommandExecutorService` (**sin re-invocar `/ai/generate`**), y audita `status: 'applied'` en el backend.
- `dismissProposal(messageId: string, proposalId: string): Promise<void>`  
  Descarta la propuesta y audita `status: 'dismissed'` en el backend.

#### Gestión de Tareas de IA
- `createTask(title: string, description: string, aiRole: string, diagramId?: string): Promise<void>`
- `executeTask(taskId: string): Promise<void>`
- `updateTask(taskId: string, updates: Partial<{ title: string, description: string, status: TaskStatus }>): Promise<void>`
- `deleteTask(taskId: string): Promise<void>`

#### Configuración y Secretos
- `setCustomGeminiApiKey(key: string): void`  
  Guarda la clave BYOK exclusivamente en `sessionStorage` (`classforge_gemini_api_key`).
- `hasCustomApiKey(): boolean`
- `setActiveModel(model: string): void`
- `clearError(): void`

---

## 3. Cliente WebSocket y Protocolo en Vivo (`ai-team.socket.ts`)

- **Ruta de Conexión:** `/api/v1/ws/projects/{project_id}?token={ws_token}`
- **Token Único:** Por cada conexión o intento de reconexión, se invoca `GET /api/v1/ai-chat/projects/{project_id}/ws-token` para obtener un token nuevo de un solo uso.
- **Heartbeat:** Envío periódico de `{ type: 'PING' }` cada 25 segundos con temporizador de respuesta (10s) para detectar desconexiones silenciosas.
- **Backoff Exponencial:** Tras una desconexión no intencionada, se programa la reconexión con:
  $$\text{delay} = \min(1000 \times 2^{\text{intentos}}, 30000) + \text{jitter}$$
- **Reanudación Reactiva (`?after=`):** Al reconectar con éxito, emite a través de `resume$` el último timestamp registrado (`created_at`). El store consulta:
  ```http
  GET /api/v1/ai-chat/projects/{project_id}/history?after={ultimo_timestamp}
  ```
  asegurando cero pérdida de mensajes durante microcortes.
- **Fallback a Polling:** Si se superan 5 intentos fallidos consecutivos de conexión, la conexión transiciona a `'polling_fallback'`. El store arranca un bucle de sondeo periódico con backoff (5 s $\rightarrow$ 30 s) mostrando el banner `"Sin conexión en vivo (modo alternativo por sondeo)"`.

---

## 4. Puente de Comandos UML (`command-bridge.ts`)

- **Problema Previo:** Anteriormente `applyDiagramChangesFromMessage` tomaba el texto en lenguaje natural de la respuesta de la IA y volvía a llamar a `/ai/generate`, duplicando costos, agregando latencia y arriesgando no-determinismo.
- **Solución Implementada:** La propuesta `Proposal` con `kind: 'uml_command'` ya contiene el objeto estructurado `command: UMLCommandResponse` generado por el backend P4/P5. `CommandBridgeService` lo entrega directamente a:
  ```typescript
  this.commandExecutor.execute(proposal.command);
  ```
- **Protección de Contexto:** Si la propuesta indica un `diagram_id` diferente al lienzo abierto actualmente en el frontend, no ejecuta el comando y notifica: `"El diagrama activo no coincide con el diagrama objetivo de la propuesta"`, ofreciendo abrir el diagrama correspondiente.
- **Auditoría:** Tras la ejecución exitosa en el lienzo, realiza `POST /api/v1/ai-chat/projects/{pid}/messages/{mid}/proposals/{prop_id}/state` con `{ "status": "applied" }`, lo cual difunde el cambio a todos los integrantes vía WebSocket.

---

## 5. Auditoría de Seguridad y Erradicación de `localStorage`

En cumplimiento de las políticas de seguridad R03 y los criterios de aceptación:
1. **BYOK Gemini Key:**
   - La clave personal del usuario pasa de `localStorage` a `sessionStorage` (`classforge_gemini_api_key`).
   - Se inyecta en peticiones HTTP salientes mediante el nuevo `geminiKeyInterceptor` en la cabecera `X-Gemini-Key`.
   - Se eliminaron todos los `setItem` / `getItem` de `classforge_gemini_api_key` en `localStorage` (solo se ejecuta `removeItem` para purgar posibles residuos en clientes viejos).
2. **Estado Compartido de Equipo:**
   - Se eliminaron por completo `cf_ai_participative` y `cf_active_ai_role` de `localStorage`.
   - El modo participativo y la asignación de roles se obtienen de `GET /projects/{id}/state` y se sincronizan reactivamente en tiempo real por el evento `AI_STATE_CHANGED`.
3. **Preferencias UI Permitidas:**
   - Solo se conservan en `localStorage` preferencias estrictamente de interfaz de usuario local: ancho del panel (`cf_ai_drawer_width`) y modelo seleccionado (`classforge_gemini_model`).

---

## 6. Resultados de la Verificación y Suite de Pruebas

### 6.1. Suite de Pruebas Unitarias (Karma + Chrome Headless)
```text
Chrome Headless 156.0.0.0 (Windows 10): Executed 43 of 43 SUCCESS (0.079 secs / 0.067 secs)
TOTAL: 43 SUCCESS
```
- Pruebas del Store: Envío optimista, confirmación, error y reintento con `client_id` idéntico, deduplicación, reanudación tras reconexión, fallback a sondeo, cambio de estado remoto (`AI_STATE_CHANGED`), paginación por cursor (`loadMore`), filtros por hilo/miembro/rol/propuestas, y contadores de no leídos.
- Pruebas del Socket: Solicitud de token fresco por intento, backoff exponencial, keepalive heartbeat (PING/PONG), reanudación con timestamp y manejo de 403.
- Pruebas del Bridge: Validación de comandos, prevención de ejecuciones cruzadas entre diagramas distintos, llamada a `CommandExecutorService` sin re-invocación a `/ai/generate`, y auditoría de propuestas aplicadas/descartadas.
- Pruebas del Interceptor: Inyección condicional de cabecera `X-Gemini-Key` desde `sessionStorage`.

### 6.2. Compilación de Producción
```text
npx ng build --configuration production
Application bundle generation complete. [12.033 seconds]
Exit code: 0
```
Sin errores de TypeScript ni discrepancias de esquema.

### 6.3. Verificación de `localStorage` (`grep`)
```powershell
Get-ChildItem -Path src -Recurse -File | Select-String -Pattern "localStorage\.(get|set)Item\s*\(\s*['""](classforge_gemini_api_key|cf_ai_participative|cf_active_ai_role)['""]"
# Salida: CERO coincidencias
```

La capa de datos y estado está lista para ser consumida por los componentes de UI en el hito **P6b**.
