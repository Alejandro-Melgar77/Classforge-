import { Injectable, OnDestroy, computed, inject, signal } from '@angular/core';
import { Subscription, firstValueFrom } from 'rxjs';
import { AiRolesRegistryService } from './ai-roles.registry';
import { AiTeamApiService, GEMINI_BYOK_STORAGE_KEY } from './ai-team.api';
import {
  AiMessage,
  AiPendingRole,
  AiProjectState,
  AiRole,
  AiRoleAutonomy,
  AiTask,
  ConnectionStatus,
  HistoryFilters,
  Proposal,
  TaskStatus,
  WsPresenceMember,
  WsServerEvent,
  WsTypingEvent
} from './ai-team.models';
import { ApplyProposalResult, CommandBridgeService } from './command-bridge';

function generateClientId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `client-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

@Injectable({
  providedIn: 'root'
})
export class AiTeamStore implements OnDestroy {
  private api = inject(AiTeamApiService);
  private rolesRegistry = inject(AiRolesRegistryService);
  private commandBridge = inject(CommandBridgeService);

  // Injected dynamically or set via setter
  private socketService: any = null;

  // ── Private State Signals ──────────────────────────────────────────────────
  private _projectId = signal<string | null>(null);
  private _currentUserId = signal<string | null>(null);
  private _currentUserName = signal<string>('Usuario');

  private _state = signal<AiProjectState | null>(null);
  private _roles = signal<AiRole[]>(this.rolesRegistry.allRoles());
  private _activeThread = signal<'personal' | 'project'>('personal');
  private _messages = signal<AiMessage[]>([]);
  private _tasks = signal<AiTask[]>([]);
  private _presence = signal<WsPresenceMember[]>([]);
  private _connectionStatus = signal<ConnectionStatus>('disconnected');
  private _typingUsers = signal<WsTypingEvent[]>([]);
  private _pendingRoles = signal<AiPendingRole[]>([]);

  private _unreadPersonal = signal<number>(0);
  private _unreadProject = signal<number>(0);

  private _filters = signal<HistoryFilters>({});
  private _hasMoreHistory = signal<boolean>(true);
  private _nextCursor = signal<string | null>(null);

  private _isLoading = signal<boolean>(false);
  private _isLoadingMore = signal<boolean>(false);
  private _isSending = signal<boolean>(false);

  private _coolingDownUntil = signal<number | null>(null);
  private _forbidden = signal<boolean>(false);
  private _errorMessage = signal<string | null>(null);

  private _availableModels = signal<string[]>(['gemini-3.8-flash']);
  private _activeModel = signal<string>('gemini-3.8-flash');

  // Polling fallback state
  private pollingTimer: any = null;
  private pollingIntervalMs = 5000;
  private maxPollingIntervalMs = 30000;

  // Subscriptions
  private subscriptions: Subscription[] = [];
  private typingTimeoutMap = new Map<string, any>();

  // ── Public Readonly Signals & Computed ─────────────────────────────────────
  public projectId = this._projectId.asReadonly();
  public state = this._state.asReadonly();
  public roles = this._roles.asReadonly();
  public activeThread = this._activeThread.asReadonly();
  public messages = this._messages.asReadonly();
  public tasks = this._tasks.asReadonly();
  public presence = this._presence.asReadonly();
  public connectionStatus = this._connectionStatus.asReadonly();
  public typingUsers = this._typingUsers.asReadonly();
  public pendingRoles = this._pendingRoles.asReadonly();

  public unreadCount = computed(() => ({
    personal: this._unreadPersonal(),
    project: this._unreadProject()
  }));

  public filters = this._filters.asReadonly();
  public hasMoreHistory = this._hasMoreHistory.asReadonly();
  public nextCursor = this._nextCursor.asReadonly();

  public isLoading = this._isLoading.asReadonly();
  public isLoadingMore = this._isLoadingMore.asReadonly();
  public isSending = this._isSending.asReadonly();

  public coolingDownUntil = this._coolingDownUntil.asReadonly();
  public forbidden = this._forbidden.asReadonly();
  public errorMessage = this._errorMessage.asReadonly();

  public availableModels = this._availableModels.asReadonly();
  public activeModel = this._activeModel.asReadonly();

  public isParticipativeEnabled = computed(() => this._state()?.participative?.enabled ?? false);
  public isLocalOnly = computed(() => this._state()?.local_only ?? false);

  public activeRoles = computed(() => this._roles().filter((r) => r.is_active));

  public currentDigest = computed(() => this._state()?.digest ?? null);

  public isCoolingDown = computed(() => {
    const until = this._coolingDownUntil();
    return until !== null && Date.now() < until;
  });

  public cooldownSecondsLeft = computed(() => {
    const until = this._coolingDownUntil();
    if (!until) return 0;
    const diff = Math.ceil((until - Date.now()) / 1000);
    return diff > 0 ? diff : 0;
  });

  public filteredMessages = computed(() => {
    const all = this._messages();
    const thread = this._activeThread();
    const filter = this._filters();

    return all.filter((msg) => {
      // 1. Thread isolation:
      // 'personal' thread displays personal messages of current user + project publications
      // 'project' thread displays project announcements & group chat
      if (thread === 'personal') {
        if (msg.thread !== 'personal') return false;
      } else if (thread === 'project') {
        if (msg.thread !== 'project') return false;
      }

      // 2. Member filter
      if (filter.member) {
        const memNorm = filter.member.toLowerCase().trim();
        const matchesAuthor = msg.author_name.toLowerCase().includes(memNorm);
        const matchesId = msg.author_id === filter.member;
        if (!matchesAuthor && !matchesId) return false;
      }

      // 3. AI Role filter
      if (filter.role) {
        if (msg.ai_role !== filter.role) return false;
      }

      // 4. Proposals only filter
      if (filter.onlyProposals) {
        if (!msg.proposals || msg.proposals.length === 0) return false;
      }

      return true;
    });
  });

  public proposals = computed<Array<{ messageId: string; proposal: Proposal }>>(() => {
    const res: Array<{ messageId: string; proposal: Proposal }> = [];
    for (const msg of this._messages()) {
      if (msg.proposals && msg.proposals.length > 0) {
        for (const p of msg.proposals) {
          res.push({ messageId: msg.id, proposal: p });
        }
      }
    }
    return res;
  });

  public setSocketService(socket: any): void {
    this.socketService = socket;
    this.setupSocketSubscriptions();
  }

  // ── Initialization & Cleanup ───────────────────────────────────────────────
  public init(projectId: string, currentUserId?: string, currentUserName?: string): void {
    if (!projectId) return;

    this.destroy();
    this._projectId.set(projectId);
    if (currentUserId) this._currentUserId.set(currentUserId);
    if (currentUserName) this._currentUserName.set(currentUserName);

    this._isLoading.set(true);
    this._forbidden.set(false);
    this._errorMessage.set(null);

    // 1. Load shared project state
    this.api.getState(projectId).subscribe({
      next: (state) => {
        this._state.set(state);
        this.syncRolesWithState(state);
      },
      error: (err) => {
        if (err?.status === 403) {
          this._forbidden.set(true);
          this._errorMessage.set('No tienes permisos para acceder al equipo de IA de este proyecto.');
        }
      }
    });

    // 2. Load roles catalog and skins
    this.api.getRoles(projectId).subscribe({
      next: (roles) => {
        this.rolesRegistry.registerRoles(roles);
        this._roles.set(this.rolesRegistry.allRoles());
        if (this._state()) {
          this.syncRolesWithState(this._state()!);
        }
      },
      error: () => {
        // Fallback already active
      }
    });

    // 3. Load initial history
    this.loadInitialHistory(projectId);

    // 4. Load tasks
    this.api.listTasks(projectId).subscribe({
      next: (res) => {
        this._tasks.set(res.tasks || []);
      },
      error: () => {}
    });

    // 5. Load model availability from /ai/health
    this.api.getAiHealth().subscribe({
      next: (health) => {
        if (health?.models && health.models.length > 0) {
          const list = health.models.filter((m) => m && m.trim());
          if (!list.includes('gemini-3.8-flash')) {
            list.unshift('gemini-3.8-flash');
          }
          this._availableModels.set(list);
        }
      },
      error: () => {
        this._availableModels.set(['gemini-3.8-flash']);
      }
    });

    // 6. Connect socket if available
    if (this.socketService) {
      this.setupSocketSubscriptions();
      this.socketService.connect(projectId);
    }
  }

  private loadInitialHistory(projectId: string): void {
    this.api.getHistory(projectId, { limit: 50 }).subscribe({
      next: (res) => {
        this._messages.set(res.messages || []);
        this._hasMoreHistory.set((res.messages || []).length >= 50 || !!res.next_cursor);
        this._nextCursor.set(res.next_cursor || null);
        this._isLoading.set(false);
      },
      error: (err) => {
        this._isLoading.set(false);
        if (err?.status === 403) {
          this._forbidden.set(true);
          this._errorMessage.set('Acceso no autorizado al historial del proyecto.');
        }
      }
    });
  }

  private syncRolesWithState(state: AiProjectState): void {
    if (!state?.roles) return;
    const rolesMap = new Map(state.roles.map((r) => [r.role_id, r]));

    this._roles.update((current) =>
      current.map((r) => {
        const stateCfg = rolesMap.get(r.role_id);
        if (stateCfg) {
          return {
            ...r,
            is_active: stateCfg.enabled,
            autonomy: stateCfg.autonomy
          };
        }
        return r;
      })
    );
  }

  private setupSocketSubscriptions(): void {
    if (!this.socketService) return;

    for (const sub of this.subscriptions) {
      sub.unsubscribe();
    }
    this.subscriptions = [];

    // Status
    this.subscriptions.push(
      this.socketService.status$.subscribe((status: ConnectionStatus) => {
        this._connectionStatus.set(status);
        if (status === 'polling_fallback') {
          this.startPollingFallback();
        } else if (status === 'connected') {
          this.stopPollingFallback();
        }
      })
    );

    // Events
    this.subscriptions.push(
      this.socketService.events$.subscribe((event: WsServerEvent) => {
        this.handleWsEvent(event);
      })
    );

    // Resume after reconnect (?after=)
    this.subscriptions.push(
      this.socketService.resume$.subscribe((lastTimestamp: string | null) => {
        this.resumeHistory(lastTimestamp);
      })
    );
  }

  // ── Real-Time Event Handling & Deduplication ───────────────────────────────
  public handleWsEvent(event: WsServerEvent): void {
    switch (event.type) {
      case 'AI_MESSAGE_CREATED': {
        this.upsertMessage(event.message);
        // Remove answering role from pending if matching
        if (event.message.ai_role) {
          this._pendingRoles.update((pending) =>
            pending.filter((p) => p.role !== event.message.ai_role)
          );
        }
        // Increment unread count if message belongs to a non-active thread
        if (event.message.thread !== this._activeThread()) {
          if (event.message.thread === 'personal') {
            this._unreadPersonal.update((c) => c + 1);
          } else {
            this._unreadProject.update((c) => c + 1);
          }
        }
        break;
      }
      case 'AI_MESSAGE_UPDATED': {
        this.updateMessageInPlace(event.message);
        break;
      }
      case 'AI_TYPING': {
        this.handleTypingEvent(event);
        break;
      }
      case 'AI_STATE_CHANGED': {
        this._state.set(event.state);
        this.syncRolesWithState(event.state);
        break;
      }
      case 'AI_TASK_UPDATED': {
        this.upsertTask(event.task);
        break;
      }
      case 'PRESENCE': {
        this._presence.set(event.members || []);
        break;
      }
    }
  }

  private handleTypingEvent(event: WsTypingEvent): void {
    const roleKey = `${event.role}_${event.user_name || ''}`;

    if (event.state === 'start') {
      this._typingUsers.update((current) => {
        const without = current.filter((u) => u.role !== event.role);
        return [...without, event];
      });

      // Auto-clear typing indicator after 8 seconds of silence
      if (this.typingTimeoutMap.has(roleKey)) {
        clearTimeout(this.typingTimeoutMap.get(roleKey));
      }
      const t = setTimeout(() => {
        this._typingUsers.update((cur) => cur.filter((u) => u.role !== event.role));
      }, 8000);
      this.typingTimeoutMap.set(roleKey, t);
    } else {
      if (this.typingTimeoutMap.has(roleKey)) {
        clearTimeout(this.typingTimeoutMap.get(roleKey));
        this.typingTimeoutMap.delete(roleKey);
      }
      this._typingUsers.update((current) => current.filter((u) => u.role !== event.role));
    }
  }

  private upsertMessage(newMsg: AiMessage): void {
    this._messages.update((current) => {
      // 1. Check if matching by client_id (e.g. replacing optimistic user message)
      if (newMsg.client_id) {
        const clientIdx = current.findIndex((m) => m.client_id === newMsg.client_id);
        if (clientIdx !== -1) {
          const updated = [...current];
          updated[clientIdx] = { ...current[clientIdx], ...newMsg, status: 'ok' };
          return updated;
        }
      }

      // 2. Check if matching by ID
      const idIdx = current.findIndex((m) => m.id === newMsg.id);
      if (idIdx !== -1) {
        const updated = [...current];
        updated[idIdx] = { ...current[idIdx], ...newMsg };
        return updated;
      }

      // 3. New message: insert preserving chronological order
      const newTime = new Date(newMsg.created_at || newMsg.timestamp || 0).getTime();
      const insertIdx = current.findIndex((m) => {
        const mTime = new Date(m.created_at || m.timestamp || 0).getTime();
        return mTime > newTime;
      });

      if (insertIdx === -1) {
        return [...current, newMsg];
      }
      const copy = [...current];
      copy.splice(insertIdx, 0, newMsg);
      return copy;
    });
  }

  private updateMessageInPlace(updatedMsg: AiMessage): void {
    this._messages.update((current) => {
      const idx = current.findIndex(
        (m) => m.id === updatedMsg.id || (updatedMsg.client_id && m.client_id === updatedMsg.client_id)
      );
      if (idx === -1) {
        return [...current, updatedMsg];
      }
      const copy = [...current];
      copy[idx] = { ...copy[idx], ...updatedMsg };
      return copy;
    });
  }

  private upsertTask(task: AiTask): void {
    if (task.status === 'deleted') {
      this._tasks.update((tasks) => tasks.filter((t) => t.id !== task.id));
      return;
    }
    this._tasks.update((tasks) => {
      const idx = tasks.findIndex((t) => t.id === task.id);
      if (idx !== -1) {
        const updated = [...tasks];
        updated[idx] = { ...updated[idx], ...task };
        return updated;
      }
      return [...tasks, task];
    });
  }

  // ── Reconnection Resume (?after=) ──────────────────────────────────────────
  public resumeHistory(afterTimestamp: string | null): void {
    const pid = this._projectId();
    if (!pid) return;

    // Use either the provided timestamp or the newest message in store
    let after = afterTimestamp;
    if (!after && this._messages().length > 0) {
      const last = this._messages()[this._messages().length - 1];
      after = last.created_at || last.timestamp || null;
    }

    if (!after) return;

    this.api.getHistory(pid, { after, limit: 100 }).subscribe({
      next: (res) => {
        if (res.messages && res.messages.length > 0) {
          for (const msg of res.messages) {
            this.upsertMessage(msg);
          }
        }
      },
      error: () => {}
    });
  }

  // ── Polling Fallback Mechanism ─────────────────────────────────────────────
  private startPollingFallback(): void {
    this.stopPollingFallback();
    this.pollingIntervalMs = 5000;

    const poll = () => {
      const pid = this._projectId();
      if (!pid) return;

      const last = this._messages()[this._messages().length - 1];
      const after = last?.created_at || last?.timestamp;

      this.api.getHistory(pid, { after, limit: 50 }).subscribe({
        next: (res) => {
          if (res.messages && res.messages.length > 0) {
            for (const m of res.messages) {
              this.upsertMessage(m);
            }
          }
        },
        error: () => {}
      });

      this.api.getState(pid).subscribe({
        next: (state) => {
          this._state.set(state);
          this.syncRolesWithState(state);
        },
        error: () => {}
      });

      // Exponential backoff up to maxPollingIntervalMs (30s)
      this.pollingIntervalMs = Math.min(this.pollingIntervalMs * 1.5, this.maxPollingIntervalMs);
      this.pollingTimer = setTimeout(poll, this.pollingIntervalMs);
    };

    this.pollingTimer = setTimeout(poll, this.pollingIntervalMs);
  }

  private stopPollingFallback(): void {
    if (this.pollingTimer) {
      clearTimeout(this.pollingTimer);
      this.pollingTimer = null;
    }
  }

  // ── Optimistic Sending with Idempotency ────────────────────────────────────
  public async sendMessage(
    content: string,
    options?: {
      aiRole?: string;
      diagramId?: string;
      replyTo?: string;
    }
  ): Promise<void> {
    const trimmed = content.trim();
    const pid = this._projectId();
    if (!trimmed || !pid) return;

    // Check rate limit cooldown
    if (this.isCoolingDown()) {
      this._errorMessage.set(
        `Debes esperar ${this.cooldownSecondsLeft()} segundos antes de enviar otro mensaje.`
      );
      return;
    }

    const clientId = generateClientId();
    const nowIso = new Date().toISOString();

    // 1. Create optimistic local message
    const optimisticMsg: AiMessage = {
      id: clientId,
      client_id: clientId,
      project_id: pid,
      thread: this._activeThread(),
      author_type: 'user',
      author_id: this._currentUserId(),
      author_name: this._currentUserName(),
      content: trimmed,
      status: 'sending',
      timestamp: nowIso,
      created_at: nowIso,
      reply_to: options?.replyTo || null,
      ai_role: options?.aiRole || null
    };

    this.upsertMessage(optimisticMsg);
    this._isSending.set(true);
    this._errorMessage.set(null);

    // Stop client typing indicator if any
    this.setTyping(false);

    try {
      const response = await firstValueFrom(
        this.api.sendMessage(pid, {
          content: trimmed,
          client_id: clientId,
          ai_role: options?.aiRole,
          diagram_id: options?.diagramId,
          reply_to: options?.replyTo,
          model: this._activeModel()
        })
      );

      this._isSending.set(false);

      // Replace optimistic message with confirmed server message
      if (response.message) {
        this.upsertMessage({
          ...response.message,
          client_id: clientId,
          status: 'ok'
        });
      }

      // Add background tasks to pending roles
      if (response.ai_pending && response.ai_pending.length > 0) {
        this._pendingRoles.update((cur) => [...cur, ...response.ai_pending]);
      }

      // If response includes immediate AI message (backward compatibility)
      if (response.ai_message) {
        this.upsertMessage(response.ai_message);
      }
    } catch (err: any) {
      this._isSending.set(false);
      this.handleSendError(clientId, err);
    }
  }

  public async retrySendMessage(clientIdOrId: string): Promise<void> {
    const msg = this._messages().find(
      (m) => m.client_id === clientIdOrId || m.id === clientIdOrId
    );
    if (!msg || msg.status !== 'failed') return;

    // Reset status to sending
    this.updateMessageInPlace({ ...msg, status: 'sending' });

    const pid = this._projectId();
    if (!pid) return;

    try {
      const response = await firstValueFrom(
        this.api.sendMessage(pid, {
          content: msg.content,
          client_id: msg.client_id || msg.id,
          ai_role: msg.ai_role || undefined,
          reply_to: msg.reply_to || undefined,
          model: this._activeModel()
        })
      );

      if (response.message) {
        this.upsertMessage({
          ...response.message,
          client_id: msg.client_id,
          status: 'ok'
        });
      }
      if (response.ai_pending && response.ai_pending.length > 0) {
        this._pendingRoles.update((cur) => [...cur, ...response.ai_pending]);
      }
    } catch (err: any) {
      this.handleSendError(msg.client_id || msg.id, err);
    }
  }

  private handleSendError(clientId: string, err: any): void {
    const msg = this._messages().find((m) => m.client_id === clientId || m.id === clientId);
    if (msg) {
      this.updateMessageInPlace({ ...msg, status: 'failed' });
    }

    if (err?.status === 429) {
      // Cooldown 30s
      this._coolingDownUntil.set(Date.now() + 30000);
      this._errorMessage.set(
        'Límite de solicitudes alcanzado (429). Por favor, espera antes de continuar.'
      );
    } else if (err?.status === 403) {
      this._forbidden.set(true);
      this._errorMessage.set(
        'Acceso no autorizado (403): No perteneces a este proyecto o tu rol no tiene permisos.'
      );
    } else {
      this._errorMessage.set(
        'No se pudo entregar el mensaje. Puedes pulsar en "Reintentar".'
      );
    }
  }

  // ── Cursor Pagination (loadMore) ──────────────────────────────────────────
  public async loadMore(): Promise<void> {
    const pid = this._projectId();
    if (!pid || !this._hasMoreHistory() || this._isLoadingMore()) return;

    const msgs = this._messages();
    if (msgs.length === 0) return;

    // Oldest message is at index 0
    const oldest = msgs[0];
    const beforeCursor = oldest.created_at || oldest.timestamp;
    if (!beforeCursor) return;

    this._isLoadingMore.set(true);

    try {
      const res = await firstValueFrom(
        this.api.getHistory(pid, {
          before: beforeCursor,
          limit: 30,
          member: this._filters().member,
          role: this._filters().role
        })
      );

      this._isLoadingMore.set(false);

      if (!res.messages || res.messages.length === 0) {
        this._hasMoreHistory.set(false);
        return;
      }

      this._hasMoreHistory.set(res.messages.length >= 30);
      this._nextCursor.set(res.next_cursor || null);

      // Prepend older messages avoiding duplicates
      for (const m of res.messages) {
        this.upsertMessage(m);
      }
    } catch {
      this._isLoadingMore.set(false);
      this._errorMessage.set('Error al cargar mensajes anteriores.');
    }
  }

  // ── Filters & Thread Selection ────────────────────────────────────────────
  public selectThread(thread: 'personal' | 'project'): void {
    this._activeThread.set(thread);
    if (thread === 'personal') {
      this._unreadPersonal.set(0);
    } else {
      this._unreadProject.set(0);
    }
  }

  public setFilters(filters: HistoryFilters): void {
    this._filters.set({ ...filters });
  }

  public clearFilters(): void {
    this._filters.set({});
  }

  // ── Project State Actions ──────────────────────────────────────────────────
  public async toggleParticipative(): Promise<void> {
    const pid = this._projectId();
    const curState = this._state();
    if (!pid || !curState) return;

    const newEnabled = !curState.participative.enabled;

    // Optimistic update
    this._state.set({
      ...curState,
      participative: {
        ...curState.participative,
        enabled: newEnabled
      }
    });

    try {
      const updated = await firstValueFrom(
        this.api.updateState(pid, {
          participative: { enabled: newEnabled }
        })
      );
      this._state.set(updated);
      this.syncRolesWithState(updated);
    } catch {
      // Revert optimistic update
      this._state.set(curState);
      this._errorMessage.set('Error al actualizar el modo participativo en el servidor.');
    }
  }

  public async toggleLocalOnly(): Promise<void> {
    const pid = this._projectId();
    const curState = this._state();
    if (!pid || !curState) return;

    const newLocalOnly = !curState.local_only;

    // Optimistic update
    this._state.set({
      ...curState,
      local_only: newLocalOnly
    });

    try {
      const updated = await firstValueFrom(
        this.api.updateState(pid, {
          local_only: newLocalOnly
        })
      );
      this._state.set(updated);
      this.syncRolesWithState(updated);
    } catch {
      // Revert optimistic update
      this._state.set(curState);
      this._errorMessage.set('Error al actualizar el modo de privacidad (local_only) en el servidor.');
    }
  }

  public async setRoleEnabled(roleId: string, enabled: boolean): Promise<void> {
    const pid = this._projectId();
    if (!pid) return;

    // Optimistic
    this._roles.update((roles) =>
      roles.map((r) => (r.role_id === roleId ? { ...r, is_active: enabled } : r))
    );

    try {
      await firstValueFrom(this.api.setRole(pid, roleId, enabled));
    } catch {
      this._errorMessage.set(`Error al cambiar el estado del rol ${roleId}.`);
    }
  }

  public async setAutonomy(roleId: string, autonomy: AiRoleAutonomy): Promise<void> {
    const pid = this._projectId();
    if (!pid) return;

    // Optimistic
    this._roles.update((roles) =>
      roles.map((r) => (r.role_id === roleId ? { ...r, autonomy } : r))
    );

    try {
      const updated = await firstValueFrom(
        this.api.updateState(pid, {
          roles: [{ role_id: roleId, autonomy }]
        })
      );
      this._state.set(updated);
      this.syncRolesWithState(updated);
    } catch (err: any) {
      if (err?.status === 403) {
        this._errorMessage.set(
          "Solo Scrum Master, Owner o Admin pueden configurar autonomía 'apply'."
        );
      } else {
        this._errorMessage.set('Error al actualizar la autonomía del rol.');
      }
    }
  }

  // ── Proposal Actions (via CommandBridge) ───────────────────────────────────
  public async applyProposal(
    messageId: string,
    proposal: Proposal,
    currentDiagramId?: string,
    proposalDiagramId?: string
  ): Promise<ApplyProposalResult> {
    const pid = this._projectId();
    if (!pid) {
      return { success: false, message: 'Proyecto no seleccionado.' };
    }

    const result = await this.commandBridge.applyProposal(
      pid,
      messageId,
      proposal,
      currentDiagramId,
      proposalDiagramId
    );

    if (result.success) {
      // Mark proposal in local store immediately
      this.updateProposalLocalState(messageId, proposal.id, 'applied');
    }

    return result;
  }

  public async dismissProposal(messageId: string, proposalId: string): Promise<void> {
    const pid = this._projectId();
    if (!pid) return;

    const res = await this.commandBridge.dismissProposal(pid, messageId, proposalId);
    if (res.success) {
      this.updateProposalLocalState(messageId, proposalId, 'dismissed');
    }
  }

  private updateProposalLocalState(
    messageId: string,
    proposalId: string,
    status: 'applied' | 'dismissed'
  ): void {
    this._messages.update((msgs) =>
      msgs.map((m) => {
        if (m.id === messageId) {
          return {
            ...m,
            proposal_state: {
              ...(m.proposal_state || {}),
              [proposalId]: {
                status,
                by: this._currentUserId() || undefined,
                at: new Date().toISOString()
              }
            }
          };
        }
        return m;
      })
    );
  }

  // ── Tasks Operations ──────────────────────────────────────────────────────
  public async createTask(
    title: string,
    description: string,
    aiRole: string,
    diagramId?: string
  ): Promise<void> {
    const pid = this._projectId();
    if (!pid) return;

    try {
      const res = await firstValueFrom(
        this.api.createTask(pid, {
          title,
          description,
          ai_role: aiRole,
          diagram_id: diagramId
        })
      );

      const newTask: AiTask = {
        id: res.task_id,
        project_id: pid,
        title,
        description,
        ai_role: aiRole,
        assignee_type: 'ai_role',
        status: 'pending',
        diagram_id: diagramId,
        created_at: new Date().toISOString()
      };
      this.upsertTask(newTask);
    } catch {
      this._errorMessage.set('Error al crear la tarea de IA.');
    }
  }

  public async executeTask(taskId: string): Promise<void> {
    const pid = this._projectId();
    if (!pid) return;

    try {
      await firstValueFrom(this.api.executeTask(pid, taskId));
      this._tasks.update((tasks) =>
        tasks.map((t) => (t.id === taskId ? { ...t, status: 'in_progress' } : t))
      );
    } catch {
      this._errorMessage.set('Error al ejecutar la tarea.');
    }
  }

  public async updateTask(
    taskId: string,
    updates: Partial<{ title: string; description: string; status: TaskStatus }>
  ): Promise<void> {
    const pid = this._projectId();
    if (!pid) return;

    try {
      const updated = await firstValueFrom(this.api.updateTask(pid, taskId, updates));
      this.upsertTask(updated);
    } catch {
      this._errorMessage.set('Error al modificar la tarea.');
    }
  }

  public async deleteTask(taskId: string): Promise<void> {
    const pid = this._projectId();
    if (!pid) return;

    try {
      await firstValueFrom(this.api.deleteTask(pid, taskId));
      this._tasks.update((tasks) => tasks.filter((t) => t.id !== taskId));
    } catch {
      this._errorMessage.set('Error al eliminar la tarea.');
    }
  }

  // ── Secret / Model Management ──────────────────────────────────────────────
  public setCustomGeminiApiKey(key: string): void {
    if (typeof sessionStorage === 'undefined') return;
    const trimmed = key.trim();
    if (trimmed) {
      sessionStorage.setItem(GEMINI_BYOK_STORAGE_KEY, trimmed);
    } else {
      sessionStorage.removeItem(GEMINI_BYOK_STORAGE_KEY);
    }
  }

  public hasCustomApiKey(): boolean {
    if (typeof sessionStorage === 'undefined') return false;
    return !!sessionStorage.getItem(GEMINI_BYOK_STORAGE_KEY);
  }

  public setActiveModel(model: string): void {
    this._activeModel.set(model);
  }

  public setTyping(isTyping: boolean): void {
    if (this.socketService) {
      this.socketService.sendTyping(isTyping);
    }
  }

  public clearError(): void {
    this._errorMessage.set(null);
  }

  // ── Destroy ────────────────────────────────────────────────────────────────
  public destroy(): void {
    this.stopPollingFallback();
    for (const sub of this.subscriptions) {
      sub.unsubscribe();
    }
    this.subscriptions = [];

    for (const timer of this.typingTimeoutMap.values()) {
      clearTimeout(timer);
    }
    this.typingTimeoutMap.clear();

    if (this.socketService) {
      this.socketService.disconnect();
    }

    this._messages.set([]);
    this._tasks.set([]);
    this._presence.set([]);
    this._typingUsers.set([]);
    this._pendingRoles.set([]);
    this._unreadPersonal.set(0);
    this._unreadProject.set(0);
    this._filters.set({});
    this._hasMoreHistory.set(true);
    this._nextCursor.set(null);
    this._errorMessage.set(null);
    this._forbidden.set(false);
  }

  ngOnDestroy(): void {
    this.destroy();
  }
}
