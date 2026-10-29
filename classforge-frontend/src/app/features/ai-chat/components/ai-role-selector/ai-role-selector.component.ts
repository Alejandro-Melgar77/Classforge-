import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiRoleId, AiRoleStatus, AI_ROLE_THEMES } from '../../models/ai-conversation.model';

@Component({
  selector: 'app-ai-role-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="role-selector-container">
      <label class="participative-toggle">
        <input type="checkbox" [(ngModel)]="participativeActive" (change)="onToggleChange()" />
        <span class="toggle-label">
          <span class="dot" [class.active]="participativeActive"></span>
          IA Participativa {{ participativeActive ? 'Activa' : 'Inactiva' }}
        </span>
      </label>

      <div class="role-dropdown-wrapper" *ngIf="participativeActive">
        <label class="dropdown-label">Rol:</label>
        <div class="role-dropdown">
          <button
            class="dropdown-trigger"
            [style.border-color]="getTheme(selectedRole).borderColor"
            (click)="isOpen = !isOpen"
          >
            <span>{{ getTheme(selectedRole).emoji }} {{ getTheme(selectedRole).label }}</span>
            <span class="chevron">{{ isOpen ? '▲' : '▼' }}</span>
          </button>

          <div class="dropdown-menu" *ngIf="isOpen">
            <button
              *ngFor="let role of roles"
              class="dropdown-item"
              [class.active]="role.role_id === selectedRole"
              [style.border-left-color]="getTheme(role.role_id).borderColor"
              (click)="selectRole(role.role_id)"
            >
              <span class="role-emoji">{{ getTheme(role.role_id).emoji }}</span>
              <div class="role-info">
                <span class="role-label">{{ role.label }}</span>
                <span class="role-desc">{{ getTheme(role.role_id).description }}</span>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .role-selector-container {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 10px 16px;
      background: rgba(255,255,255,0.04);
      border-bottom: 1px solid rgba(255,255,255,0.08);
      flex-wrap: wrap;
    }
    .participative-toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      user-select: none;
    }
    .participative-toggle input { display: none; }
    .toggle-label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: #9CA3AF;
    }
    .dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      background: #374151;
      transition: background 0.2s;
    }
    .dot.active { background: #10B981; box-shadow: 0 0 6px #10B981; }
    .role-dropdown-wrapper {
      display: flex;
      align-items: center;
      gap: 8px;
      position: relative;
    }
    .dropdown-label { font-size: 12px; color: #6B7280; }
    .role-dropdown { position: relative; }
    .dropdown-trigger {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      background: rgba(255,255,255,0.06);
      border: 1px solid;
      border-radius: 8px;
      color: #E5E7EB;
      cursor: pointer;
      font-size: 13px;
      min-width: 160px;
      justify-content: space-between;
    }
    .dropdown-trigger:hover { background: rgba(255,255,255,0.1); }
    .chevron { font-size: 10px; color: #6B7280; }
    .dropdown-menu {
      position: absolute;
      top: calc(100% + 4px);
      left: 0;
      min-width: 240px;
      background: #1F2937;
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 10px;
      padding: 6px;
      z-index: 100;
      box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }
    .dropdown-item {
      display: flex;
      gap: 10px;
      align-items: center;
      padding: 8px 10px;
      border-radius: 8px;
      cursor: pointer;
      border: none;
      background: transparent;
      color: #E5E7EB;
      width: 100%;
      text-align: left;
      border-left: 3px solid transparent;
      transition: background 0.15s;
    }
    .dropdown-item:hover, .dropdown-item.active { background: rgba(255,255,255,0.08); }
    .role-emoji { font-size: 20px; }
    .role-info { display: flex; flex-direction: column; }
    .role-label { font-size: 13px; font-weight: 500; }
    .role-desc { font-size: 11px; color: #6B7280; }
  `]
})
export class AiRoleSelectorComponent implements OnInit {
  @Input() roles: AiRoleStatus[] = [];
  @Input() selectedRole: AiRoleId = 'architect';
  @Input() participativeActive = false;

  @Output() roleChange = new EventEmitter<AiRoleId>();
  @Output() participativeChange = new EventEmitter<boolean>();

  isOpen = false;

  ngOnInit(): void {
    if (!this.selectedRole && this.roles.length > 0) {
      this.selectedRole = this.roles[0].role_id as AiRoleId;
    }
  }

  getTheme(roleId: string) {
    return AI_ROLE_THEMES[roleId as AiRoleId] ?? AI_ROLE_THEMES['architect'];
  }

  selectRole(roleId: AiRoleId): void {
    this.selectedRole = roleId;
    this.isOpen = false;
    this.roleChange.emit(roleId);
  }

  onToggleChange(): void {
    this.participativeChange.emit(this.participativeActive);
  }
}
