import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AiDrawerComponent } from './ai-drawer.component';
import { AiTeamStore } from '../../../ai-team/data-access/ai-team.store';
import { AiTeamSocketService } from '../../../ai-team/data-access/ai-team.socket';
import { AuthService } from '../../../../core/services/auth.service';
import { VoiceRecognitionService } from '../services/voice-recognition.service';
import { AiService } from '../services/ai.service';
import { CommandExecutorService } from '../services/command-executor.service';
import { AiHistoryService } from '../services/ai-history.service';
import { signal, computed } from '@angular/core';
import { of } from 'rxjs';

describe('AiDrawerComponent', () => {
  let component: AiDrawerComponent;
  let fixture: ComponentFixture<AiDrawerComponent>;

  let mockStore: any;
  let mockSocket: any;
  let mockAuth: any;
  let mockVoice: any;
  let mockAi: any;
  let mockExecutor: any;
  let mockHistory: any;

  beforeEach(async () => {
    mockStore = {
      init: jasmine.createSpy(),
      destroy: jasmine.createSpy(),
      setSocketService: jasmine.createSpy(),
      unreadCount: signal({ personal: 0, project: 0 }),
      tasks: signal([]),
      roles: signal([]),
      activeRoles: computed(() => []),
      connectionStatus: signal('connected'),
      currentDigest: signal(null),
      state: signal(null),
      isParticipativeEnabled: signal(false),
      isLocalOnly: signal(false),
      toggleLocalOnly: jasmine.createSpy().and.returnValue(Promise.resolve())
    };

    mockSocket = {
      connect: jasmine.createSpy(),
      disconnect: jasmine.createSpy()
    };

    mockAuth = {
      getCurrentUser: jasmine.createSpy().and.returnValue({
        id: 'u-1',
        name: 'Maria Developer',
        role: 'dev'
      })
    };

    mockVoice = {
      isListening: signal(false),
      transcript: signal(''),
      interimTranscript: signal(''),
      audioLevel: signal(0),
      getBestTranscript: jasmine.createSpy().and.returnValue('')
    };

    mockAi = {
      processInput: jasmine.createSpy().and.returnValue(of(null)),
      checkHealth: jasmine.createSpy().and.returnValue(of({ local_available: false, local_model: 'qwen2.5:1.5b' }))
    };

    mockExecutor = {
      execute: jasmine.createSpy()
    };

    mockHistory = {
      reloadHistory: jasmine.createSpy(),
      history: signal([]),
      addEntry: jasmine.createSpy(),
      clearUserHistory: jasmine.createSpy()
    };

    await TestBed.configureTestingModule({
      imports: [AiDrawerComponent],
      providers: [
        { provide: AiTeamStore, useValue: mockStore },
        { provide: AiTeamSocketService, useValue: mockSocket },
        { provide: AuthService, useValue: mockAuth },
        { provide: VoiceRecognitionService, useValue: mockVoice },
        { provide: AiService, useValue: mockAi },
        { provide: CommandExecutorService, useValue: mockExecutor },
        { provide: AiHistoryService, useValue: mockHistory }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AiDrawerComponent);
    component = fixture.componentInstance;
    component.projectId = 'proj-123';
    component.diagramId = 'diag-456';
    fixture.detectChanges();
  });

  it('should create and initialize the thin host', () => {
    expect(component).toBeTruthy();
    expect(component.mainTab()).toBe('commands');
    expect(mockStore.setSocketService).toHaveBeenCalledWith(mockSocket);
    expect(mockStore.init).toHaveBeenCalledWith('proj-123', 'u-1', 'Maria Developer');
  });

  it('should switch between commands and ai-team tabs', () => {
    component.setTab('ai-team');
    expect(component.mainTab()).toBe('ai-team');

    component.setTab('commands');
    expect(component.mainTab()).toBe('commands');
  });

  it('should change drawer width on preset button clicks', () => {
    component.setDrawerWidth(400);
    expect(component.drawerWidth).toBe(400);

    component.setDrawerWidth(760);
    expect(component.drawerWidth).toBe(760);
  });

  it('should emit close on Escape keydown when drawer is open', () => {
    spyOn(component.close, 'emit');
    component.isOpen = true;

    component.onEscape();
    expect(component.close.emit).toHaveBeenCalled();
  });

  it('should clean up store on component destroy', () => {
    component.ngOnDestroy();
    expect(mockStore.destroy).toHaveBeenCalled();
  });
});
