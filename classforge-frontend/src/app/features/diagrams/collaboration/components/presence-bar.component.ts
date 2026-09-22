import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CollaborationService } from '../services/collaboration.service';

@Component({
  selector: 'app-presence-bar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="presence-bar">
      <div class="status-indicator">
        <span class="dot" [ngClass]="status()"></span>
        <span class="count">{{ activeCount() }} colaborando</span>
      </div>
      <div class="avatars">
        <div *ngFor="let user of users()" 
             class="avatar-container"
             [title]="user.name + ' (' + user.role + ') - ' + user.status">
          <div class="avatar" [style.background-color]="user.color">
            {{ getInitials(user.name) }}
          </div>
          <div class="user-status-dot" [ngClass]="user.status"></div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .presence-bar {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 4px 10px;
      background: var(--surface-3);
      border: 1px solid var(--border);
      border-radius: 8px;
    }
    .status-indicator {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--text-secondary);
      font-weight: 500;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .dot.connected { background-color: var(--accent, #00C896); }
    .dot.connecting { background-color: var(--warning, #F5A623); }
    .dot.disconnected { background-color: var(--danger, #E74C3C); }
    .avatars {
      display: flex;
      align-items: center;
    }
    .avatar-container {
      position: relative;
      margin-left: -6px;
    }
    .avatar-container:first-child {
      margin-left: 0;
    }
    .avatar {
      width: 26px;
      height: 26px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: 11px;
      border: 2px solid var(--surface-2);
      cursor: pointer;
      box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }
    .user-status-dot {
      position: absolute;
      bottom: -1px;
      right: -1px;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      border: 1.5px solid var(--surface-2);
    }
    .user-status-dot.online { background-color: #22c55e; }
    .user-status-dot.away { background-color: #eab308; }
    .user-status-dot.busy { background-color: #ef4444; }
  `]
})
export class PresenceBarComponent {
  private colabService = inject(CollaborationService);
  
  status = this.colabService.connectionStatus;
  users = this.colabService.connectedUsers;
  activeCount = computed(() => this.users().length);

  getInitials(name: string): string {
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  }
}
