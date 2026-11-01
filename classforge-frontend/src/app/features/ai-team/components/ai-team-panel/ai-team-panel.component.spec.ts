import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AiTeamPanelComponent } from './ai-team-panel.component';
import { AiTeamStore } from '../../data-access/ai-team.store';
import { AuthService } from '../../../../core/services/auth.service';
import { signal, computed } from '@angular/core';

describe('AiTeamPanelComponent', () => {
  let component: AiTeamPanelComponent;
  let fixture: ComponentFixture<AiTeamPanelComponent>;
  let mockStore: any;
  let mockAuthService: any;

  beforeEach(async () => {
    mockStore = {
      isParticipativeEnabled: signal(false),
      state: signal(null),
      roles: signal([]),
      activeRoles: computed(() => []),
      connectionStatus: signal('connected'),
      currentDigest: signal(null),
      unreadCount: signal({ personal: 2, project: 5 }),
      isLocalOnly: signal(false),
      toggleLocalOnly: jasmine.createSpy().and.returnValue(Promise.resolve()),
      tasks: signal([]),
      selectThread: jasmine.createSpy(),
      toggleParticipative: jasmine.createSpy().and.returnValue(Promise.resolve()),
      setRoleEnabled: jasmine.createSpy().and.returnValue(Promise.resolve()),
      setAutonomy: jasmine.createSpy().and.returnValue(Promise.resolve())
    };

    mockAuthService = {
      getCurrentUser: jasmine.createSpy().and.returnValue({
        id: 'u-1',
        name: 'Tester',
        role: 'dev'
      })
    };

    await TestBed.configureTestingModule({
      imports: [AiTeamPanelComponent],
      providers: [
        { provide: AiTeamStore, useValue: mockStore },
        { provide: AuthService, useValue: mockAuthService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AiTeamPanelComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create and default to chat subtab', () => {
    expect(component).toBeTruthy();
    expect(component.activeSubTab()).toBe('chat');
  });

  it('should switch subtab to history and select project thread', () => {
    component.selectSubTab('history');
    expect(component.activeSubTab()).toBe('history');
    expect(mockStore.selectThread).toHaveBeenCalledWith('project');
  });

  it('should switch subtab to tasks', () => {
    component.selectSubTab('tasks');
    expect(component.activeSubTab()).toBe('tasks');
  });

  it('should switch back to chat and select personal thread', () => {
    component.selectSubTab('history');
    component.selectSubTab('chat');
    expect(component.activeSubTab()).toBe('chat');
    expect(mockStore.selectThread).toHaveBeenCalledWith('personal');
  });
});
