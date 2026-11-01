import { Injectable, signal, computed } from '@angular/core';
import { AiRole, RoleSkin } from './ai-team.models';

export const LOCAL_ROLES_FALLBACK: Record<string, AiRole> = {
  architect: {
    role_id: 'architect',
    label: 'Arquitecto de Software',
    emoji: '🏛️',
    description: 'Topología de clasificadores, cohesión, modularidad y límites arquitecturales.',
    is_active: true,
    autonomy: 'suggest',
    skin: {
      accent: '#3B82F6',
      bg: '#0F172A',
      border: '#2563EB',
      text: '#93C5FD',
      icon: 'landmark',
      bubble_shape: 'bubble-rounded-bl',
      typing_text: 'El Arquitecto está evaluando la arquitectura...',
      avatar_style: 'avatar-blueprint'
    },
    triggers: [
      'arquitectura', 'patrón', 'diseño', 'estructura', 'módulo', 'responsabilidad',
      'srp', 'ocp', 'acoplamiento', 'cohesión', 'subclase', 'herencia vs composición'
    ]
  },
  qa: {
    role_id: 'qa',
    label: 'Ingeniero de Calidad (QA)',
    emoji: '🧪',
    description: 'Consistencia de cardinalidades, casos de borde, validación de multiplicidades.',
    is_active: true,
    autonomy: 'suggest',
    skin: {
      accent: '#10B981',
      bg: '#064E3B',
      border: '#059669',
      text: '#A7F3D0',
      icon: 'check-circle-2',
      bubble_shape: 'bubble-rounded-tl',
      typing_text: 'QA está verificando la calidad del modelo...',
      avatar_style: 'avatar-matrix'
    },
    triggers: [
      'qa', 'test', 'prueba', 'calidad', 'cardinalidad', 'multiplicidad',
      'validación', 'caso de borde', 'inconsistencia', 'nulo', 'linter'
    ]
  },
  tech_lead: {
    role_id: 'tech_lead',
    label: 'Líder Técnico',
    emoji: '⚡',
    description: 'Factibilidad técnica, balance de deuda, estándares y convención de nombres.',
    is_active: true,
    autonomy: 'suggest',
    skin: {
      accent: '#F59E0B',
      bg: '#451A03',
      border: '#D97706',
      text: '#FDE68A',
      icon: 'shield-alert',
      bubble_shape: 'bubble-sharp-r',
      typing_text: 'El Tech Lead está revisando la viabilidad técnica...',
      avatar_style: 'avatar-tactical'
    },
    triggers: [
      'lead', 'tech lead', 'viabilidad', 'complejidad', 'deuda técnica',
      'convención', 'estándar', 'naming', 'refactor', 'bloqueo'
    ]
  },
  mentor: {
    role_id: 'mentor',
    label: 'Mentor Pedagógico',
    emoji: '🎓',
    description: 'Explicaciones conceptuales, guías de modelado y pedagogía de patrones.',
    is_active: true,
    autonomy: 'suggest',
    skin: {
      accent: '#8B5CF6',
      bg: '#2E1065',
      border: '#7C3AED',
      text: '#DDD6FE',
      icon: 'sparkles',
      bubble_shape: 'bubble-soft-all',
      typing_text: 'El Mentor está preparando una explicación pedagógica...',
      avatar_style: 'avatar-scholar'
    },
    triggers: [
      'mentor', 'aprender', 'por qué', 'concepto', 'explicar', 'ayuda',
      'cómo funciona', 'ejemplo', 'duda', 'principio'
    ]
  },
  dba: {
    role_id: 'dba',
    label: 'Administrador de Datos (DBA)',
    emoji: '🗄️',
    description: 'Modelado relacional, normalización, tipos de datos y persistencia.',
    is_active: true,
    autonomy: 'suggest',
    skin: {
      accent: '#06B6D4',
      bg: '#083344',
      border: '#0891B2',
      text: '#A5F3FC',
      icon: 'database',
      bubble_shape: 'bubble-rounded-br',
      typing_text: 'El DBA está evaluando la estructura de persistencia...',
      avatar_style: 'avatar-db'
    },
    triggers: [
      'dba', 'base de datos', 'bd', 'tabla', 'columna', 'primary key', 'pk',
      'foreign key', 'fk', 'normalización', 'índice', 'persistencia'
    ]
  },
  security: {
    role_id: 'security',
    label: 'Especialista en Seguridad',
    emoji: '🛡️',
    description: 'Auditoría de datos sensibles, control de acceso y amenazas de diseño.',
    is_active: true,
    autonomy: 'suggest',
    skin: {
      accent: '#EF4444',
      bg: '#450A0A',
      border: '#DC2626',
      text: '#FECACA',
      icon: 'shield-check',
      bubble_shape: 'bubble-sharp-l',
      typing_text: 'Seguridad está analizando vulnerabilidades...',
      avatar_style: 'avatar-sec'
    },
    triggers: [
      'seguridad', 'security', 'auth', 'autorización', 'token', 'contraseña',
      'password', 'encriptación', 'vulnerabilidad', 'permiso', 'rol'
    ]
  },
  analyst: {
    role_id: 'analyst',
    label: 'Analista de Negocio',
    emoji: '📊',
    description: 'Alineación de requisitos de dominio, reglas de negocio y casos de uso.',
    is_active: true,
    autonomy: 'suggest',
    skin: {
      accent: '#EC4899',
      bg: '#500724',
      border: '#DB2777',
      text: '#FBCFE8',
      icon: 'briefcase',
      bubble_shape: 'bubble-rounded-tr',
      typing_text: 'El Analista está verificando las reglas de negocio...',
      avatar_style: 'avatar-business'
    },
    triggers: [
      'negocio', 'requisito', 'requerimiento', 'dominio', 'flujo', 'caso de uso',
      'cliente', 'regla de negocio', 'alcance', 'funcionalidad'
    ]
  }
};

const DEFAULT_FALLBACK_SKIN: RoleSkin = {
  accent: '#64748B',
  bg: '#1E293B',
  border: '#475569',
  text: '#E2E8F0',
  icon: 'bot',
  bubble_shape: 'bubble-soft-all',
  typing_text: 'La IA está escribiendo...',
  avatar_style: 'avatar-default'
};

@Injectable({
  providedIn: 'root'
})
export class AiRolesRegistryService {
  private rolesMap = signal<Record<string, AiRole>>({ ...LOCAL_ROLES_FALLBACK });

  public allRoles = computed<AiRole[]>(() => Object.values(this.rolesMap()));

  public getRole(roleId: string): AiRole {
    const existing = this.rolesMap()[roleId];
    if (existing) return existing;

    // Fallback if role is unknown
    return {
      role_id: roleId,
      label: roleId.charAt(0).toUpperCase() + roleId.slice(1),
      emoji: '🤖',
      description: 'Rol de IA del equipo.',
      is_active: true,
      autonomy: 'suggest',
      skin: DEFAULT_FALLBACK_SKIN,
      triggers: []
    };
  }

  public getSkin(roleId: string): RoleSkin {
    const role = this.getRole(roleId);
    return role.skin || DEFAULT_FALLBACK_SKIN;
  }

  public registerRoles(roles: AiRole[]): void {
    if (!roles || roles.length === 0) return;

    this.rolesMap.update(current => {
      const updated = { ...current };
      for (const r of roles) {
        const fallback = current[r.role_id] || LOCAL_ROLES_FALLBACK[r.role_id];
        updated[r.role_id] = {
          ...fallback,
          ...r,
          skin: r.skin || fallback?.skin || DEFAULT_FALLBACK_SKIN,
          triggers: r.triggers && r.triggers.length > 0 ? r.triggers : fallback?.triggers || []
        };
      }
      return updated;
    });
  }

  public resetToDefault(): void {
    this.rolesMap.set({ ...LOCAL_ROLES_FALLBACK });
  }
}
