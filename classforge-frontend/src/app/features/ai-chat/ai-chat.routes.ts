import { Routes } from '@angular/router';

/**
 * AI Chat routes.
 * As part of P6b / P7a architecture, direct /ai-chat/:projectId routes
 * redirect to the project hub center (/projects).
 */
export const AI_CHAT_ROUTES: Routes = [
  {
    path: ':projectId',
    redirectTo: '/projects/:projectId/equipo-ia',
    pathMatch: 'full'
  },
  {
    path: '',
    redirectTo: '/projects',
    pathMatch: 'full'
  }
];
