import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { SupportTourService } from './support-tour.service';
import { AuthService } from '../../../core/services/auth.service';
import { User, UserRole } from '../../../core/models/user.model';

describe('SupportTourService', () => {
  let service: SupportTourService;
  let mockAuthService: { getCurrentUser: jasmine.Spy };
  let mockRouter: { navigate: jasmine.Spy };

  const createUser = (role: UserRole): User => ({
    id: 'user-123',
    name: 'Test User',
    email: 'test@example.com',
    role: role
  });

  beforeEach(() => {
    mockAuthService = {
      getCurrentUser: jasmine.createSpy('getCurrentUser').and.returnValue(createUser('dev'))
    };

    mockRouter = {
      navigate: jasmine.createSpy('navigate').and.returnValue(Promise.resolve(true))
    };

    TestBed.configureTestingModule({
      providers: [
        SupportTourService,
        { provide: AuthService, useValue: mockAuthService },
        { provide: Router, useValue: mockRouter }
      ]
    });

    service = TestBed.inject(SupportTourService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should return all registered tours with getAllTours()', () => {
    const allTours = service.getAllTours();
    expect(allTours.length).toBe(10);
    expect(allTours.map(t => t.id)).toContain('tour-auth-navigation');
    expect(allTours.map(t => t.id)).toContain('tour-project-evaluator');
    expect(allTours.map(t => t.id)).toContain('tour-teams-roles');
  });

  it('should filter out admin/scrum_master tours for dev role', () => {
    mockAuthService.getCurrentUser.and.returnValue(createUser('dev'));
    const tours = service.getAvailableTours();
    const ids = tours.map(t => t.id);

    expect(ids).not.toContain('tour-teams-roles');
    expect(ids).toContain('tour-auth-navigation');
    expect(ids).toContain('tour-uml-modeling');
    expect(ids).toContain('tour-project-evaluator');
  });

  it('should allow teams-roles tours for scrum_master role', () => {
    mockAuthService.getCurrentUser.and.returnValue(createUser('scrum_master'));
    const tours = service.getAvailableTours();
    const ids = tours.map(t => t.id);

    expect(ids).toContain('tour-teams-roles');
    expect(ids).toContain('tour-uml-modeling');
  });

  it('should allow all tours for admin role', () => {
    mockAuthService.getCurrentUser.and.returnValue(createUser('admin'));
    const tours = service.getAvailableTours();
    expect(tours.length).toBe(10);
  });

  it('should manage tour progress lifecycle', () => {
    expect(service.isTourActive()).toBeFalse();
    expect(service.currentStep()).toBeNull();

    service.startTour('tour-create-diagram');
    expect(service.isTourActive()).toBeTrue();
    expect(service.currentStepIndex()).toBe(0);
    expect(service.currentStep()?.id).toBe('step-nav-diagrams');
    expect(service.progressPercentage()).toBeGreaterThan(0);

    service.nextStep();
    expect(service.currentStepIndex()).toBe(1);
    expect(service.currentStep()?.id).toBe('step-new-diagram-btn');

    service.previousStep();
    expect(service.currentStepIndex()).toBe(0);

    service.endTour();
    expect(service.isTourActive()).toBeFalse();
    expect(service.activeTour()).toBeNull();
  });
});
