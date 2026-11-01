import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { SessionStateService } from './session-state.service';

describe('SessionStateService', () => {
  let service: SessionStateService;
  let mockRouter: jasmine.SpyObj<Router>;

  beforeEach(() => {
    mockRouter = jasmine.createSpyObj('Router', ['navigate'], { url: '/projects/p123' });

    TestBed.configureTestingModule({
      providers: [
        SessionStateService,
        { provide: Router, useValue: mockRouter }
      ]
    });
    service = TestBed.inject(SessionStateService);
  });

  it('should start with isExpired false and returnUrl /', () => {
    expect(service.isExpired()).toBeFalse();
    expect(service.returnUrl()).toBe('/');
  });

  it('should mark session as expired and preserve url', () => {
    service.handleSessionExpired('/projects/42');
    expect(service.isExpired()).toBeTrue();
    expect(service.returnUrl()).toBe('/projects/42');
  });

  it('should redirect to login with returnUrl on dismissAndRedirect', () => {
    service.handleSessionExpired('/projects/42');
    service.dismissAndRedirect();
    expect(service.isExpired()).toBeFalse();
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/auth/login'], {
      queryParams: { returnUrl: '/projects/42' }
    });
  });
});
