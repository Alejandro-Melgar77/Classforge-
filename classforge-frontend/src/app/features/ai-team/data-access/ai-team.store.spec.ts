import { TestBed, fakeAsync, tick, discardPeriodicTasks } from '@angular/core/testing';
import { Subject, of, throwError } from 'rxjs';
import { AiRolesRegistryService } from './ai-roles.registry';
import { AiTeamApiService } from './ai-team.api';
import { AiTeamStore } from './ai-team.store';
import { CommandBridgeService } from './command-bridge';
import {
  AiMessage,
  AiProjectState,
  AiRole,
  AiSendMessageResponse,
  ConnectionStatus,
  WsServerEvent
} from './ai-team.models';

describe('AiTeamStore', () => {
  let store: AiTeamStore;
  let apiSpy: jasmine.SpyObj<AiTeamApiService>;
  let commandBridgeSpy: jasmine.SpyObj<CommandBridgeService>;

  let mockSocketStatus$: Subject<ConnectionStatus>;
  let mockSocketEvents$: Subject<WsServerEvent>;
  let mockSocketResume$: Subject<string | null>;
  let mockSocketService: any;

  const mockProjectState: AiProjectState = {
    project_id: 'proj-1',
    participative: { enabled: false },
    roles: [
      { role_id: 'architect', enabled: true, autonomy: 'suggest' },
      { role_id: 'qa', enabled: true, autonomy: 'suggest' }
    ],
    digest: { text: 'Resumen inicial', tokens: 100 }
  };

  const mockInitialRoles: AiRole[] = [
    {
      role_id: 'architect',
      label: 'Arquitecto',
      emoji: '🏛️',
      description: 'Arqui',
      is_active: true,
      autonomy: 'suggest'
    },
    {
      role_id: 'qa',
      label: 'QA',
      emoji: '🧪',
      description: 'QA',
      is_active: true,
      autonomy: 'suggest'
    }
  ];

  beforeEach(() => {
    mockSocketStatus$ = new Subject<ConnectionStatus>();
    mockSocketEvents$ = new Subject<WsServerEvent>();
    mockSocketResume$ = new Subject<string | null>();

    mockSocketService = {
      status$: mockSocketStatus$.asObservable(),
      events$: mockSocketEvents$.asObservable(),
      resume$: mockSocketResume$.asObservable(),
      connect: jasmine.createSpy('connect'),
      disconnect: jasmine.createSpy('disconnect'),
      sendTyping: jasmine.createSpy('sendTyping')
    };

    apiSpy = jasmine.createSpyObj('AiTeamApiService', [
      'getState',
      'getRoles',
      'getHistory',
      'listTasks',
      'getAiHealth',
      'sendMessage',
      'updateState',
      'setRole',
      'createTask',
      'executeTask',
      'updateTask',
      'deleteTask'
    ]);

    commandBridgeSpy = jasmine.createSpyObj('CommandBridgeService', [
      'applyProposal',
      'dismissProposal'
    ]);

    apiSpy.getState.and.returnValue(of(mockProjectState));
    apiSpy.getRoles.and.returnValue(of(mockInitialRoles));
    apiSpy.getHistory.and.returnValue(
      of({
        project_id: 'proj-1',
        messages: [
          {
            id: 'msg-seed-1',
            thread: 'personal',
            author_type: 'user',
            author_name: 'Ana',
            content: 'Mensaje existente',
            created_at: '2026-11-01T10:00:00Z',
            status: 'ok'
          }
        ],
        total: 1,
        next_cursor: 'cursor-seed'
      })
    );
    apiSpy.listTasks.and.returnValue(of({ project_id: 'proj-1', tasks: [], total: 0 }));
    apiSpy.getAiHealth.and.returnValue(
      of({
        provider: 'gemini',
        models: ['gemini-3.8-flash', 'gemini-2.5-flash'],
        has_server_key: true,
        ollama_available: false,
        model: 'gemini-3.8-flash'
      })
    );

    TestBed.configureTestingModule({
      providers: [
        AiTeamStore,
        AiRolesRegistryService,
        { provide: AiTeamApiService, useValue: apiSpy },
        { provide: CommandBridgeService, useValue: commandBridgeSpy }
      ]
    });

    store = TestBed.inject(AiTeamStore);
  });

  afterEach(() => {
    store.destroy();
  });

  it('should initialize and load state, roles, health, and initial history', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    expect(apiSpy.getState).toHaveBeenCalledWith('proj-1');
    expect(apiSpy.getRoles).toHaveBeenCalledWith('proj-1');
    expect(apiSpy.getHistory).toHaveBeenCalledWith('proj-1', { limit: 50 });
    expect(mockSocketService.connect).toHaveBeenCalledWith('proj-1');

    expect(store.state()?.project_id).toBe('proj-1');
    expect(store.messages().length).toBe(1);
    expect(store.messages()[0].content).toBe('Mensaje existente');
    expect(store.availableModels()).toContain('gemini-3.8-flash');
  }));

  it('should perform optimistic sending, generate unique client_id, and confirm via server response', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    let capturedClientId: string = '';
    apiSpy.sendMessage.and.callFake((pid, body) => {
      capturedClientId = body.client_id;
      const resp: AiSendMessageResponse = {
        message: {
          id: 'server-msg-123',
          project_id: pid,
          thread: 'personal',
          author_type: 'user',
          author_name: 'Ana',
          content: body.content,
          client_id: body.client_id,
          status: 'ok',
          created_at: '2026-11-01T12:00:00Z'
        },
        ai_pending: [{ role: 'architect', message_id: 'pending-ai-1' }]
      };
      return of(resp);
    });

    store.sendMessage('¿Cómo modularizamos el dominio?');

    // While request is in-flight, optimistic message exists with status sending
    const inFlightMsgs = store.messages();
    const optimistic = inFlightMsgs.find(m => m.content === '¿Cómo modularizamos el dominio?');
    expect(optimistic).toBeDefined();
    expect(optimistic?.status).toBe('sending');
    expect(optimistic?.client_id).toBeTruthy();

    tick();

    // After resolution, optimistic message replaced by confirmed server message
    const msgs = store.messages();
    const confirmed = msgs.find(m => m.client_id === capturedClientId);
    expect(confirmed).toBeDefined();
    expect(confirmed?.id).toBe('server-msg-123');
    expect(confirmed?.status).toBe('ok');
    expect(store.pendingRoles().length).toBe(1);
    expect(store.pendingRoles()[0].role).toBe('architect');
  }));

  it('should mark message as failed on error and allow retry with identical client_id', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    let callCount = 0;
    const clientIdsUsed: string[] = [];

    apiSpy.sendMessage.and.callFake((pid, body) => {
      callCount++;
      clientIdsUsed.push(body.client_id);
      if (callCount === 1) {
        return throwError(() => ({ status: 500, message: 'Server down' }));
      }
      return of({
        message: {
          id: 'server-msg-retry',
          project_id: pid,
          thread: 'personal',
          author_type: 'user',
          author_name: 'Ana',
          content: body.content,
          client_id: body.client_id,
          status: 'ok',
          created_at: '2026-11-01T12:05:00Z'
        },
        ai_pending: []
      });
    });

    store.sendMessage('Mensaje que fallará inicialmente');
    tick();

    const failedMsg = store.messages().find(m => m.content === 'Mensaje que fallará inicialmente');
    expect(failedMsg).toBeDefined();
    expect(failedMsg?.status).toBe('failed');
    expect(store.errorMessage()).toContain('Reintentar');

    // Retry sending message
    store.retrySendMessage(failedMsg!.client_id!);
    tick();

    expect(callCount).toBe(2);
    // Crucial requirement: EXACT same client_id passed on retry for idempotency
    expect(clientIdsUsed[0]).toBe(clientIdsUsed[1]);

    const resolved = store.messages().find(m => m.content === 'Mensaje que fallará inicialmente');
    expect(resolved?.status).toBe('ok');
  }));

  it('should deduplicate messages strictly by id and client_id', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    const initialLength = store.messages().length;

    // Simulate WS emitting an AI_MESSAGE_CREATED for a message that has the same id
    mockSocketEvents$.next({
      type: 'AI_MESSAGE_CREATED',
      message: {
        id: 'msg-seed-1',
        thread: 'personal',
        author_type: 'user',
        author_name: 'Ana',
        content: 'Mensaje existente con contenido actualizado',
        created_at: '2026-11-01T10:00:00Z',
        status: 'ok'
      }
    });

    expect(store.messages().length).toBe(initialLength);
    expect(store.messages()[0].content).toBe('Mensaje existente con contenido actualizado');
  }));

  it('should resume history (?after=) when reconnection event arrives', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    apiSpy.getHistory.and.returnValue(
      of({
        project_id: 'proj-1',
        messages: [
          {
            id: 'msg-reconnected-1',
            thread: 'personal',
            author_type: 'ai',
            author_name: 'Arquitecto',
            ai_role: 'architect',
            content: 'Respuesta durante desconexión',
            created_at: '2026-11-01T10:30:00Z',
            status: 'ok'
          }
        ],
        total: 1,
        next_cursor: 'cursor-seed'
      })
    );

    mockSocketResume$.next('2026-11-01T10:00:00Z');
    tick();

    expect(apiSpy.getHistory).toHaveBeenCalledWith('proj-1', {
      after: '2026-11-01T10:00:00Z',
      limit: 100
    });
    expect(store.messages().some(m => m.id === 'msg-reconnected-1')).toBeTrue();
  }));

  it('should fallback to polling when socket enters polling_fallback with backoff', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    apiSpy.getHistory.calls.reset();
    apiSpy.getState.calls.reset();

    mockSocketStatus$.next('polling_fallback');
    expect(store.connectionStatus()).toBe('polling_fallback');

    // First polling tick (5s)
    tick(5100);
    expect(apiSpy.getHistory).toHaveBeenCalled();
    expect(apiSpy.getState).toHaveBeenCalled();

    // Next polling tick with backoff (5s * 1.5 = 7.5s)
    apiSpy.getHistory.calls.reset();
    tick(7600);
    expect(apiSpy.getHistory).toHaveBeenCalled();

    store.destroy();
    discardPeriodicTasks();
  }));

  it('should update state and sync roles when AI_STATE_CHANGED is received', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    const newState: AiProjectState = {
      project_id: 'proj-1',
      participative: { enabled: true, updated_by: 'usr-admin' },
      roles: [
        { role_id: 'architect', enabled: true, autonomy: 'apply' },
        { role_id: 'qa', enabled: false, autonomy: 'off' }
      ],
      digest: { text: 'Nuevo digest auditado', tokens: 240 }
    };

    mockSocketEvents$.next({
      type: 'AI_STATE_CHANGED',
      state: newState
    });

    expect(store.isParticipativeEnabled()).toBeTrue();
    expect(store.currentDigest()?.text).toBe('Nuevo digest auditado');

    const architectRole = store.roles().find(r => r.role_id === 'architect');
    expect(architectRole?.autonomy).toBe('apply');
    expect(architectRole?.is_active).toBeTrue();

    const qaRole = store.roles().find(r => r.role_id === 'qa');
    expect(qaRole?.autonomy).toBe('off');
    expect(qaRole?.is_active).toBeFalse();
  }));

  it('should paginate older messages using loadMore cursor', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    apiSpy.getHistory.and.returnValue(
      of({
        project_id: 'proj-1',
        messages: [
          {
            id: 'msg-older-0',
            thread: 'personal',
            author_type: 'user',
            author_name: 'Ana',
            content: 'Mensaje anterior más viejo',
            created_at: '2026-11-01T09:00:00Z',
            status: 'ok'
          }
        ],
        total: 2,
        next_cursor: 'cursor-abc'
      })
    );

    store.loadMore();
    tick();

    expect(apiSpy.getHistory).toHaveBeenCalledWith('proj-1', {
      before: '2026-11-01T10:00:00Z',
      limit: 30,
      member: undefined,
      role: undefined
    });
    expect(store.messages().length).toBe(2);
    // Older message prepended
    expect(store.messages()[0].id).toBe('msg-older-0');
  }));

  it('should filter messages by thread, member, role and onlyProposals', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    // Add diverse test messages via socket events
    const msgs: AiMessage[] = [
      {
        id: 'm1',
        thread: 'personal',
        author_type: 'user',
        author_name: 'Ana',
        content: 'Hola personal',
        created_at: '2026-11-01T10:00:00Z',
        status: 'ok'
      },
      {
        id: 'm2',
        thread: 'project',
        author_type: 'user',
        author_name: 'Carlos',
        content: 'Hola grupo',
        created_at: '2026-11-01T10:01:00Z',
        status: 'ok'
      },
      {
        id: 'm3',
        thread: 'personal',
        author_type: 'ai',
        author_name: 'Arquitecto',
        ai_role: 'architect',
        content: 'Propuesta arquitectónica',
        proposals: [{ id: 'p1', kind: 'uml_command', title: 'Crear Clase', rationale: 'r', severity: 'info' }],
        created_at: '2026-11-01T10:02:00Z',
        status: 'ok'
      },
      {
        id: 'm4',
        thread: 'personal',
        author_type: 'ai',
        author_name: 'QA',
        ai_role: 'qa',
        content: 'Reporte de QA',
        created_at: '2026-11-01T10:03:00Z',
        status: 'ok'
      }
    ];

    for (const m of msgs) {
      mockSocketEvents$.next({ type: 'AI_MESSAGE_CREATED', message: m });
    }

    // Default thread is 'personal'
    store.selectThread('personal');
    expect(store.filteredMessages().some(m => m.id === 'm2')).toBeFalse();

    // Switch to project thread
    store.selectThread('project');
    expect(store.filteredMessages().every(m => m.thread === 'project')).toBeTrue();

    // Switch back to personal and apply role filter
    store.selectThread('personal');
    store.setFilters({ role: 'architect' });
    expect(store.filteredMessages().length).toBe(1);
    expect(store.filteredMessages()[0].ai_role).toBe('architect');

    // Apply onlyProposals filter
    store.setFilters({ onlyProposals: true });
    expect(store.filteredMessages().length).toBe(1);
    expect(store.filteredMessages()[0].proposals?.length).toBe(1);
  }));

  it('should handle 429 rate limit with cooldown', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    apiSpy.sendMessage.and.returnValue(throwError(() => ({ status: 429, message: 'Too many requests' })));
    store.sendMessage('Mensaje que chocará con 429');
    tick();

    expect(store.coolingDownUntil()).toBeGreaterThan(Date.now());
    expect(store.isCoolingDown()).toBeTrue();
    expect(store.errorMessage()).toContain('429');
  }));

  it('should handle 403 forbidden expulsion', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    apiSpy.sendMessage.and.returnValue(throwError(() => ({ status: 403, message: 'Forbidden' })));
    store.sendMessage('Mensaje que chocará con 403');
    tick();

    expect(store.forbidden()).toBeTrue();
    expect(store.errorMessage()).toContain('403');
  }));

  it('should track unread counters per thread', fakeAsync(() => {
    store.setSocketService(mockSocketService);
    store.init('proj-1', 'usr-1', 'Ana');
    tick();

    store.selectThread('personal');

    // Incoming message in project thread while personal thread is active
    mockSocketEvents$.next({
      type: 'AI_MESSAGE_CREATED',
      message: {
        id: 'msg-proj-unread',
        thread: 'project',
        author_type: 'user',
        author_name: 'Carlos',
        content: 'Noticia grupal',
        created_at: '2026-11-01T11:00:00Z',
        status: 'ok'
      }
    });

    expect(store.unreadCount().project).toBe(1);
    expect(store.unreadCount().personal).toBe(0);

    // Switching to project resets its unread counter
    store.selectThread('project');
    expect(store.unreadCount().project).toBe(0);
  }));
});
