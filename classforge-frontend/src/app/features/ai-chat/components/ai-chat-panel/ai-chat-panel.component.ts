import { Component, Input, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';

import { AiChatService } from '../../services/ai-chat.service';
import { AiMessage, AiRoleId, AiRoleStatus } from '../../models/ai-conversation.model';
import { AiTask, AiTaskCreate } from '../../models/ai-task.model';
import { AiRoleSelectorComponent } from '../ai-role-selector/ai-role-selector.component';
import { AiMessageBubbleComponent } from '../ai-message-bubble/ai-message-bubble.component';
import { AiTaskPanelComponent } from '../ai-task-panel/ai-task-panel.component';

type ChatTab = 'my-chat' | 'group-history' | 'tasks';

@Component({
  selector: 'app-ai-chat-panel',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    AiRoleSelectorComponent,
    AiMessageBubbleComponent,
    AiTaskPanelComponent,
  ],
  template: `
    <div class="ai-chat-panel">
      <!-- Header -->
      <div class="panel-header">
        <h3 class="panel-title">💬 Chat IA del Proyecto</h3>
        <p class="panel-subtitle">{{ projectName }}</p>
      </div>

      <!-- Role Selector -->
      <app-ai-role-selector
        [roles]="roles"
        [selectedRole]="activeRole"
        [participativeActive]="participativeActive"
        (roleChange)="onRoleChange($event)"
        (participativeChange)="onParticipativeChange($event)"
      ></app-ai-role-selector>

      <!-- Tabs -->
      <div class="tabs">
        <button class="tab" [class.active]="activeTab === 'my-chat'" (click)="switchTab('my-chat')">
          💬 Mi Chat
        </button>
        <button class="tab" [class.active]="activeTab === 'group-history'" (click)="switchTab('group-history')">
          👥 Historial del Grupo
        </button>
        <button class="tab" [class.active]="activeTab === 'tasks'" (click)="switchTab('tasks')">
          📋 Tareas IA
          <span class="badge" *ngIf="pendingTaskCount > 0">{{ pendingTaskCount }}</span>
        </button>
      </div>

      <!-- Messages Area -->
      <div class="messages-area" #messagesContainer *ngIf="activeTab !== 'tasks'">
        <div *ngIf="isLoading" class="loading-state">
          <span>Cargando conversación...</span>
        </div>
        <div *ngIf="!isLoading && currentMessages.length === 0" class="empty-state">
          <p>No hay mensajes aún. ¡Inicia la conversación!</p>
          <p *ngIf="participativeActive" class="hint">La IA está activa como {{ activeRole }} y responderá automáticamente.</p>
        </div>
        <app-ai-message-bubble
          *ngFor="let msg of currentMessages; trackBy: trackByMsgId"
          [message]="msg"
          (applyToDiagram)="onApplyToDiagram($event)"
          (ignoreDiagramChanges)="onIgnoreDiagramChanges($event)"
        ></app-ai-message-bubble>
      </div>

      <!-- Tasks Panel -->
      <app-ai-task-panel
        *ngIf="activeTab === 'tasks'"
        [tasks]="tasks"
        (createTask)="onCreateTask($event)"
        (executeTask)="onExecuteTask($event)"
        class="tasks-panel"
      ></app-ai-task-panel>

      <!-- Input Area -->
      <div class="input-area" *ngIf="activeTab !== 'tasks'">
        <div *ngIf="error" class="error-bar">{{ error }}</div>
        <div class="input-row">
          <textarea
            class="message-input"
            [(ngModel)]="messageText"
            placeholder="Escribe tu mensaje..."
            rows="2"
            (keydown.enter)="onEnterKey($event)"
            [disabled]="!participativeActive || isSending"
          ></textarea>
          <button
            class="send-button"
            (click)="sendMessage()"
            [disabled]="!participativeActive || !messageText.trim() || isSending"
          >
            {{ isSending ? '...' : 'Enviar' }}
          </button>
        </div>
        <p class="input-hint" *ngIf="!participativeActive">
          Activa la IA Participativa para enviar mensajes.
        </p>
      </div>
    </div>
  `,
  styles: [`
    .ai-chat-panel {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #111827;
      color: #E5E7EB;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    .panel-header {
      padding: 16px 16px 8px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .panel-title { margin: 0; font-size: 15px; font-weight: 600; }
    .panel-subtitle { margin: 2px 0 0; font-size: 12px; color: #6B7280; }
    .tabs {
      display: flex;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .tab {
      flex: 1;
      padding: 10px 6px;
      background: transparent;
      border: none;
      border-bottom: 2px solid transparent;
      color: #6B7280;
      cursor: pointer;
      font-size: 12px;
      transition: all 0.2s;
      position: relative;
    }
    .tab.active {
      color: #60A5FA;
      border-bottom-color: #60A5FA;
    }
    .tab:hover:not(.active) { color: #9CA3AF; }
    .badge {
      position: absolute;
      top: 4px;
      right: 4px;
      background: #F59E0B;
      color: #111;
      border-radius: 50%;
      width: 16px;
      height: 16px;
      font-size: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
    }
    .messages-area {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
    }
    .tasks-panel { flex: 1; overflow-y: auto; }
    .loading-state, .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #6B7280;
      font-size: 13px;
      gap: 8px;
    }
    .hint { font-size: 12px; color: #10B981; }
    .input-area {
      padding: 12px;
      border-top: 1px solid rgba(255,255,255,0.06);
    }
    .error-bar {
      padding: 6px 10px;
      background: rgba(239,68,68,0.15);
      border: 1px solid rgba(239,68,68,0.3);
      border-radius: 6px;
      color: #FCA5A5;
      font-size: 12px;
      margin-bottom: 8px;
    }
    .input-row { display: flex; gap: 8px; }
    .message-input {
      flex: 1;
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 8px;
      color: #E5E7EB;
      padding: 8px 10px;
      font-size: 13px;
      resize: none;
      font-family: inherit;
    }
    .message-input:focus { outline: none; border-color: rgba(96,165,250,0.5); }
    .message-input:disabled { opacity: 0.5; cursor: not-allowed; }
    .send-button {
      padding: 8px 16px;
      background: #2563EB;
      color: white;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      align-self: flex-end;
      transition: background 0.2s;
    }
    .send-button:hover:not(:disabled) { background: #1D4ED8; }
    .send-button:disabled { opacity: 0.5; cursor: not-allowed; }
    .input-hint { margin: 6px 0 0; font-size: 11px; color: #6B7280; text-align: center; }
  `]
})
export class AiChatPanelComponent implements OnInit, OnDestroy, AfterViewChecked {
  @Input() projectId!: string;
  @Input() projectName = 'Proyecto';
  @Input() diagramId?: string;

  @ViewChild('messagesContainer') private messagesContainer?: ElementRef;

  activeTab: ChatTab = 'my-chat';
  activeRole: AiRoleId = 'architect';
  participativeActive = false;
  messageText = '';
  isSending = false;
  isLoading = false;
  error: string | null = null;

  myMessages: AiMessage[] = [];
  groupMessages: AiMessage[] = [];
  tasks: AiTask[] = [];
  roles: AiRoleStatus[] = [];

  private readonly destroy$ = new Subject<void>();
  private shouldScrollToBottom = false;

  constructor(private readonly aiChatService: AiChatService) {}

  get currentMessages(): AiMessage[] {
    return this.activeTab === 'group-history' ? this.groupMessages : this.myMessages;
  }

  get pendingTaskCount(): number {
    return this.tasks.filter(t => t.status === 'pending').length;
  }

  ngOnInit(): void {
    if (this.projectId) {
      this.loadRoles();
      this.loadMyMessages();
    }
  }

  ngAfterViewChecked(): void {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  switchTab(tab: ChatTab): void {
    this.activeTab = tab;
    if (tab === 'group-history' && this.groupMessages.length === 0) {
      this.loadGroupHistory();
    }
    if (tab === 'tasks' && this.tasks.length === 0) {
      this.loadTasks();
    }
  }

  onRoleChange(role: AiRoleId): void {
    this.activeRole = role;
  }

  onParticipativeChange(active: boolean): void {
    this.participativeActive = active;
    if (active && this.projectId) {
      this.aiChatService.setRole(this.projectId, this.activeRole, true)
        .pipe(takeUntil(this.destroy$))
        .subscribe({ error: (e) => console.error('Error activating role:', e) });
    }
  }

  onEnterKey(event: Event): void {
    const ke = event as KeyboardEvent;
    if (!ke.shiftKey) {
      ke.preventDefault();
      this.sendMessage();
    }
  }

  sendMessage(): void {
    if (!this.messageText.trim() || !this.participativeActive || this.isSending) return;
    this.isSending = true;
    this.error = null;

    this.aiChatService.sendMessage(this.projectId, this.messageText, this.activeRole, this.diagramId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res) => {
          this.myMessages.push(res.ai_message);
          if (res.ai_message) {
            const userMsg: AiMessage = {
              id: Date.now().toString(),
              author_type: 'user',
              author_name: 'Tú',
              author_role_label: 'dev',
              content: this.messageText,
              timestamp: new Date().toISOString(),
              visible_to_all: true,
            };
            this.myMessages.splice(this.myMessages.length - 1, 0, userMsg);
          }
          this.messageText = '';
          this.isSending = false;
          this.shouldScrollToBottom = true;
        },
        error: (err) => {
          this.error = 'Error al enviar el mensaje. Intenta de nuevo.';
          this.isSending = false;
          console.error('Send message error:', err);
        }
      });
  }

  onApplyToDiagram(message: AiMessage): void {
    console.log('[AiChatPanel] Apply to diagram:', message);
  }

  onIgnoreDiagramChanges(message: AiMessage): void {
    const idx = this.myMessages.findIndex(m => m.id === message.id);
    if (idx >= 0) {
      this.myMessages[idx] = { ...message, has_diagram_changes: false };
    }
  }

  onCreateTask(task: AiTaskCreate): void {
    this.aiChatService.createTask(this.projectId, task)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => this.loadTasks(),
        error: (e) => console.error('Create task error:', e)
      });
  }

  onExecuteTask(task: AiTask): void {
    if (!task.id) return;
    this.aiChatService.executeTask(this.projectId, task.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => this.loadTasks(),
        error: (e) => console.error('Execute task error:', e)
      });
  }

  trackByMsgId(_: number, msg: AiMessage): string {
    return msg.id;
  }

  private loadRoles(): void {
    this.aiChatService.getRoles(this.projectId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (roles) => { this.roles = roles; },
        error: (e) => console.error('Load roles error:', e)
      });
  }

  private loadMyMessages(): void {
    this.isLoading = true;
    this.aiChatService.getMyHistory(this.projectId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res) => {
          this.myMessages = res.messages as AiMessage[];
          this.isLoading = false;
          this.shouldScrollToBottom = true;
        },
        error: () => { this.isLoading = false; }
      });
  }

  private loadGroupHistory(): void {
    this.isLoading = true;
    this.aiChatService.getGroupHistory(this.projectId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res) => {
          this.groupMessages = res.messages as AiMessage[];
          this.isLoading = false;
        },
        error: () => { this.isLoading = false; }
      });
  }

  private loadTasks(): void {
    this.aiChatService.listTasks(this.projectId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res) => { this.tasks = res.tasks; },
        error: (e) => console.error('Load tasks error:', e)
      });
  }

  private scrollToBottom(): void {
    if (this.messagesContainer?.nativeElement) {
      const el = this.messagesContainer.nativeElement;
      el.scrollTop = el.scrollHeight;
    }
  }
}
