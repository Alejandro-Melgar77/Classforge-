import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AiTeamHeaderComponent } from './ai-team-header.component';
import { AiTeamStore } from '../../data-access/ai-team.store';
import { AuthService } from '../../../../core/services/auth.service';
import { signal, computed } from '@angular/core';
import { AiRole, ConnectionStatus } from '../../data-access/ai-team.models';

describe('AiTeamHeaderComponent', () => {
  let component: AiTeamHeaderComponent;
  let fixture: ComponentFixture<AiTeamHeaderComponent>;

  let mockStore: any;
  let mockAuthService: any;

  const mockRoles: AiRole[] = [
    {
      role_id: 'architect',
      label: 'Arquitecto',
      emoji: '🏛️',
      description: 'Topología de clases',
      is_active: true,
      autonomy: 'suggest'
    },
    {
      role_id: 'qa',
      label: 'QA Engineer',
      emoji: '🧪',
      description: 'Validación de modelos',
      is_active: false,
      autonomy: 'suggest'
    }
  ];

  beforeEach(async () => {
    mockStore = {
      isParticipativeEnabled: signal(true),
      isLocalOnly: signal(false),
      state: signal({
        project_id: 'p-1',
        participative: {
          enabled: true,
          updated_by: 'Ana Gómez',
          updated_at: '2026-11-01T14:30:00Z'
        },
        roles: [],
        digest: { text: '', tokens: 1450 },
        local_only: false
      }),
      roles: signal(mockRoles),
      activeRoles: computed(() => mockRoles.filter(r => r.is_active)),
      connectionStatus: signal<ConnectionStatus>('connected'),
      currentDigest: signal({ text: '', tokens: 1450 }),
      toggleParticipative: jasmine.createSpy().and.returnValue(Promise.resolve()),
      toggleLocalOnly: jasmine.createSpy().and.returnValue(Promise.resolve()),
      setRoleEnabled: jasmine.createSpy().and.returnValue(Promise.resolve()),
      setAutonomy: jasmine.createSpy().and.returnValue(Promise.resolve())
    };

    mockAuthService = {
      getCurrentUser: jasmine.createSpy().and.returnValue({
        id: 'u-1',
        name: 'Carlos Dev',
        email: 'carlos@test.com',
        role: 'dev'
      })
    };

    await TestBed.configureTestingModule({
      imports: [AiTeamHeaderComponent],
      providers: [
        { provide: AiTeamStore, useValue: mockStore },
        { provide: AuthService, useValue: mockAuthService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AiTeamHeaderComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create and render model and connection status', () => {
    expect(component).toBeTruthy();
    expect(component.connectionLabel()).toBe('En vivo');
    expect(component.consumptionText()).toMatch(/1,?450 tokens/);
    expect(component.participativeAuditText()).toContain('Ana Gómez');
  });

  it('should toggle participative AI mode on click', async () => {
    await component.onToggleParticipative();
    expect(mockStore.toggleParticipative).toHaveBeenCalled();
  });

  it('should toggle role activation status', async () => {
    const fakeEvent = new Event('click');
    spyOn(fakeEvent, 'stopPropagation');

    await component.onToggleRoleActive(mockRoles[0], fakeEvent);
    expect(fakeEvent.stopPropagation).toHaveBeenCalled();
    expect(mockStore.setRoleEnabled).toHaveBeenCalledWith('architect', false);
  });

  it('should prevent setting apply autonomy for user with dev role', async () => {
    expect(component.canApplyAutonomy()).toBeFalse();

    await component.onChangeAutonomy(mockRoles[0], 'apply');
    expect(mockStore.setAutonomy).not.toHaveBeenCalled();
  });

  it('should allow setting apply autonomy for user with admin or scrum_master role', async () => {
    mockAuthService.getCurrentUser.and.returnValue({
      id: 'u-2',
      name: 'Admin Boss',
      email: 'admin@test.com',
      role: 'admin'
    });

    expect(component.canApplyAutonomy()).toBeTrue();

    await component.onChangeAutonomy(mockRoles[0], 'apply');
    expect(mockStore.setAutonomy).toHaveBeenCalledWith('architect', 'apply');
  });

  it('should expand and collapse roles accordion', () => {
    expect(component.showRolesExpanded()).toBeFalse();
    component.toggleRolesAccordion();
    expect(component.showRolesExpanded()).toBeTrue();
    component.toggleRolesAccordion();
    expect(component.showRolesExpanded()).toBeFalse();
  });
});
