import { TestBed } from '@angular/core/testing';
import { AiRolesRegistryService, LOCAL_ROLES_FALLBACK } from './ai-roles.registry';
import { AiRole } from './ai-team.models';

describe('AiRolesRegistryService', () => {
  let service: AiRolesRegistryService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AiRolesRegistryService]
    });
    service = TestBed.inject(AiRolesRegistryService);
    service.resetToDefault();
  });

  it('should initialize with 7 canonical roles', () => {
    const roles = service.allRoles();
    expect(roles.length).toBe(7);

    const ids = roles.map(r => r.role_id);
    expect(ids).toContain('architect');
    expect(ids).toContain('qa');
    expect(ids).toContain('tech_lead');
    expect(ids).toContain('mentor');
    expect(ids).toContain('dba');
    expect(ids).toContain('security');
    expect(ids).toContain('analyst');
  });

  it('should return correct role and skin for architect', () => {
    const architect = service.getRole('architect');
    expect(architect).toBeDefined();
    expect(architect.label).toBe('Arquitecto de Software');
    expect(architect.emoji).toBe('🏛️');
    expect(architect.skin?.accent).toBe('#3B82F6');
    expect(architect.triggers).toContain('arquitectura');
  });

  it('should provide a sensible fallback for an unknown role', () => {
    const unknown = service.getRole('devops');
    expect(unknown).toBeDefined();
    expect(unknown.role_id).toBe('devops');
    expect(unknown.label).toBe('Devops');
    expect(unknown.emoji).toBe('🤖');
    expect(unknown.skin?.icon).toBe('bot');
  });

  it('should merge dynamic roles from backend while preserving defaults', () => {
    const backendRoles: AiRole[] = [
      {
        role_id: 'architect',
        label: 'Lead Solution Architect',
        emoji: '🏗️',
        description: 'Updated architecture lead description',
        is_active: true
      },
      {
        role_id: 'product_owner',
        label: 'Product Owner',
        emoji: '📋',
        description: 'PO persona',
        is_active: true
      }
    ];

    service.registerRoles(backendRoles);

    const architect = service.getRole('architect');
    expect(architect.label).toBe('Lead Solution Architect');
    expect(architect.emoji).toBe('🏗️');
    // Skin preserved from fallback
    expect(architect.skin?.accent).toBe('#3B82F6');

    const po = service.getRole('product_owner');
    expect(po.label).toBe('Product Owner');
    expect(po.skin).toBeDefined();
  });
});
