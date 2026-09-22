import { Component, inject, ViewChild, ElementRef, AfterViewChecked, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CollaborationService } from '../services/collaboration.service';

@Component({
  selector: 'app-collaborators-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="h-full w-80 bg-[var(--surface-2)] border-l border-[var(--border)] flex flex-col shadow-xl absolute right-0 top-0 z-50 transition-transform duration-300"
         [class.translate-x-full]="!isOpen"
         [class.translate-x-0]="isOpen">
         
      <!-- Header -->
      <div class="h-12 border-b border-[var(--border)] flex items-center justify-between px-4 shrink-0 bg-[var(--surface-2)]">
        <h3 class="font-bold text-[var(--text-primary)]">Colaboradores & Chat</h3>
        <button (click)="close.emit()" class="text-[var(--text-secondary)] hover:text-white transition-colors">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"></path></svg>
        </button>
      </div>

      <!-- Tabs -->
      <div class="flex border-b border-[var(--border)] shrink-0">
        <button class="flex-1 py-2 text-sm text-center border-b-2 transition-colors"
                [class.border-[var(--primary)]]="activeTab === 'collaborators'"
                [class.text-[var(--primary)]]="activeTab === 'collaborators'"
                [class.border-transparent]="activeTab !== 'collaborators'"
                [class.text-[var(--text-secondary)]]="activeTab !== 'collaborators'"
                (click)="activeTab = 'collaborators'">
          Colaboradores ({{ colabService.connectedUsers().length }})
        </button>
        <button class="flex-1 py-2 text-sm text-center border-b-2 transition-colors"
                [class.border-[var(--primary)]]="activeTab === 'chat'"
                [class.text-[var(--primary)]]="activeTab === 'chat'"
                [class.border-transparent]="activeTab !== 'chat'"
                [class.text-[var(--text-secondary)]]="activeTab !== 'chat'"
                (click)="activeTab = 'chat'">
          Chat en vivo
        </button>
      </div>

      <!-- Tab Content: Collaborators -->
      <div class="flex-1 overflow-y-auto p-4" *ngIf="activeTab === 'collaborators'">
        <!-- My Status Selector -->
        <div class="mb-6 bg-[var(--surface-3)] p-3 rounded-lg border border-[var(--border)]">
          <label class="text-xs text-[var(--text-secondary)] uppercase font-bold mb-2 block">Mi estado</label>
          <select [ngModel]="colabService.myPresenceStatus()" 
                  (ngModelChange)="onStatusChange($event)"
                  class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded px-2 py-1 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--primary)]">
            <option value="online">🟢 Online</option>
            <option value="away">🟡 Ausente</option>
            <option value="busy">🔴 Ocupado</option>
          </select>
        </div>

        <div class="space-y-4">
          <label class="text-xs text-[var(--text-secondary)] uppercase font-bold">Activos</label>
          
          <div *ngFor="let user of colabService.connectedUsers()" class="flex items-start gap-3">
            <div class="relative">
              <div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm"
                   [style.background-color]="user.color">
                {{ getInitials(user.name) }}
              </div>
              <div class="absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-2 border-[var(--surface-2)]"
                   [ngClass]="getStatusColor(user.status)">
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between">
                <span class="font-medium text-sm text-[var(--text-primary)] truncate">{{ user.name }}</span>
                <span class="text-[10px] uppercase bg-[var(--surface-3)] text-[var(--text-secondary)] px-1.5 py-0.5 rounded">{{ user.role }}</span>
              </div>
              
              <!-- Check if editing -->
              <div *ngIf="getLockedElementInfo(user.user_id)" class="text-xs text-yellow-500 flex items-center gap-1 mt-1">
                <span>✏️</span> <span class="truncate">Editando...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab Content: Chat -->
      <div class="flex flex-col h-full" *ngIf="activeTab === 'chat'">
        <div class="flex-1 overflow-y-auto p-4 space-y-4" #chatContainer>
          <div *ngFor="let msg of colabService.chatMessages()" class="flex flex-col">
            <div class="flex items-center gap-2 mb-1">
              <span class="font-bold text-xs" [style.color]="msg.user_color">{{ msg.user_name }}</span>
              <span class="text-[10px] text-[var(--text-secondary)]">{{ formatTime(msg.timestamp) }}</span>
            </div>
            <div class="bg-[var(--surface-3)] text-[var(--text-primary)] text-sm rounded-lg rounded-tl-none p-2 w-fit max-w-[90%] border border-[var(--border)]">
              {{ msg.content }}
            </div>
          </div>
          <div *ngIf="colabService.chatMessages().length === 0" class="text-center text-[var(--text-secondary)] text-sm mt-10">
            No hay mensajes aún. ¡Escribe el primero!
          </div>
        </div>
        
        <div class="p-3 bg-[var(--surface-3)] border-t border-[var(--border)] shrink-0">
          <form (submit)="sendMessage($event)" class="flex gap-2">
            <input type="text" [(ngModel)]="newMessage" name="newMessage" 
                   placeholder="Escribe un mensaje..."
                   class="flex-1 bg-[var(--surface-1)] border border-[var(--border)] rounded px-3 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--primary)]"
                   autocomplete="off">
            <button type="submit" [disabled]="!newMessage.trim()"
                    class="bg-[var(--primary)] text-white px-3 py-1.5 rounded disabled:opacity-50 transition-colors">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"></path></svg>
            </button>
          </form>
        </div>
      </div>
    </div>
  `
})
export class CollaboratorsPanelComponent implements AfterViewChecked {
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();

  @ViewChild('chatContainer') private chatContainer!: ElementRef;

  public colabService = inject(CollaborationService);
  public activeTab: 'collaborators' | 'chat' = 'collaborators';
  public newMessage = '';

  private shouldScrollToBottom = true;

  ngAfterViewChecked() {
    if (this.activeTab === 'chat' && this.shouldScrollToBottom) {
      this.scrollToBottom();
    }
  }

  scrollToBottom(): void {
    if (this.chatContainer) {
      this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
      this.shouldScrollToBottom = false;
    }
  }

  sendMessage(e: Event) {
    e.preventDefault();
    if (this.newMessage.trim()) {
      this.colabService.sendChatMessage(this.newMessage.trim());
      this.newMessage = '';
      this.shouldScrollToBottom = true;
    }
  }

  onStatusChange(status: 'online' | 'away' | 'busy') {
    this.colabService.setPresenceStatus(status);
  }

  getInitials(name: string): string {
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'online': return 'bg-green-500';
      case 'away': return 'bg-yellow-500';
      case 'busy': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  }

  getLockedElementInfo(userId: string): boolean {
    const lockedMap = this.colabService.lockedElements();
    for (const [elementId, lockerId] of lockedMap.entries()) {
      if (lockerId === userId) return true;
    }
    return false;
  }

  formatTime(timestamp: string): string {
    try {
      const d = new Date(timestamp);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  }
}
