import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AiMessage, AI_ROLE_THEMES, AiRoleId } from '../../models/ai-conversation.model';
import { AiRoleAvatarComponent } from '../ai-role-avatar/ai-role-avatar.component';

@Component({
  selector: 'app-ai-message-bubble',
  standalone: true,
  imports: [CommonModule, AiRoleAvatarComponent],
  template: `
    <div class="message-wrapper" [class.is-ai]="message.author_type === 'ai'" [class.is-user]="message.author_type === 'user'">
      <!-- AI Avatar -->
      <app-ai-role-avatar
        *ngIf="message.author_type === 'ai' && message.ai_role"
        [role]="message.ai_role as AiRoleId"
        class="avatar"
      ></app-ai-role-avatar>

      <!-- User Avatar -->
      <div *ngIf="message.author_type === 'user'" class="user-avatar">
        {{ message.author_name.charAt(0).toUpperCase() }}
      </div>

      <div class="bubble-content">
        <div class="bubble-header">
          <span class="author-name" [style.color]="getAuthorColor()">
            {{ message.author_name }}
          </span>
          <span class="timestamp">{{ message.timestamp | date:'HH:mm' }}</span>
        </div>

        <div
          class="bubble"
          [class.ai-bubble]="message.author_type === 'ai'"
          [class.user-bubble]="message.author_type === 'user'"
          [style.border-color]="message.author_type === 'ai' ? getRoleTheme()?.borderColor : ''"
        >
          <p class="content" [innerHTML]="formatContent(message.content)"></p>
        </div>

        <!-- Apply to Diagram button (shown when AI proposes diagram changes) -->
        <div *ngIf="message.has_diagram_changes" class="diagram-action-bar">
          <span class="hint">💡 La IA propone cambios al diagrama</span>
          <button class="btn-apply" (click)="applyToDiagram.emit(message)">
            ✅ Aplicar al Diagrama
          </button>
          <button class="btn-ignore" (click)="ignoreDiagramChanges.emit(message)">
            ✗ Ignorar
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .message-wrapper {
      display: flex;
      gap: 10px;
      margin-bottom: 16px;
      align-items: flex-start;
    }
    .is-user { flex-direction: row-reverse; }
    .avatar { flex-shrink: 0; }
    .user-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: #374151;
      color: #9CA3AF;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 14px;
      flex-shrink: 0;
    }
    .bubble-content { flex: 1; max-width: 75%; }
    .is-user .bubble-content { display: flex; flex-direction: column; align-items: flex-end; }
    .bubble-header {
      display: flex;
      gap: 8px;
      align-items: baseline;
      margin-bottom: 4px;
    }
    .is-user .bubble-header { flex-direction: row-reverse; }
    .author-name { font-size: 12px; font-weight: 600; }
    .timestamp { font-size: 11px; color: #6B7280; }
    .bubble {
      padding: 10px 14px;
      border-radius: 12px;
      border: 1px solid transparent;
      line-height: 1.5;
    }
    .ai-bubble {
      background: rgba(255,255,255,0.05);
      border-radius: 4px 12px 12px 12px;
    }
    .user-bubble {
      background: rgba(59, 130, 246, 0.15);
      border-color: rgba(59, 130, 246, 0.3);
      border-radius: 12px 4px 12px 12px;
    }
    .content { margin: 0; white-space: pre-wrap; font-size: 13px; color: #E5E7EB; }
    .diagram-action-bar {
      display: flex;
      gap: 8px;
      align-items: center;
      margin-top: 8px;
      padding: 8px;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      border-radius: 8px;
      flex-wrap: wrap;
    }
    .hint { font-size: 12px; color: #6EE7B7; flex: 1; }
    .btn-apply {
      padding: 4px 12px;
      background: #059669;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
    }
    .btn-apply:hover { background: #047857; }
    .btn-ignore {
      padding: 4px 12px;
      background: transparent;
      color: #6B7280;
      border: 1px solid #374151;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
    }
    .btn-ignore:hover { color: #EF4444; border-color: #EF4444; }
  `]
})
export class AiMessageBubbleComponent {
  @Input() message!: AiMessage;
  @Output() applyToDiagram = new EventEmitter<AiMessage>();
  @Output() ignoreDiagramChanges = new EventEmitter<AiMessage>();

  getAuthorColor(): string {
    if (this.message.author_type === 'user') return '#93C5FD';
    const theme = this.getRoleTheme();
    return theme?.textColor ?? '#A78BFA';
  }

  getRoleTheme() {
    if (!this.message.ai_role) return null;
    return AI_ROLE_THEMES[this.message.ai_role as AiRoleId] ?? null;
  }

  formatContent(content: string): string {
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  }
}
