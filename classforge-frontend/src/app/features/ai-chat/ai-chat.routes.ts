import { Routes } from '@angular/router';

/** Routes for the AI Chat feature module. */
export const AI_CHAT_ROUTES: Routes = [
  {
    path: ':projectId',
    loadComponent: () =>
      import('./components/ai-chat-panel/ai-chat-panel.component').then(
        m => m.AiChatPanelComponent
      ),
    title: 'Chat IA — ClassForge'
  }
];
