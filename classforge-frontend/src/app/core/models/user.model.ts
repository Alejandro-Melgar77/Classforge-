import { UserProfile } from './api-response.model';

/** Re-export UserProfile as User for convenience across the app */
export type User = UserProfile;

export type UserRole = 'admin' | 'scrum_master' | 'dev';

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrador',
  scrum_master: 'Scrum Master',
  dev: 'Equipo de Desarrollo',
};

