import { Component, Input, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AiRoleId, AI_ROLE_THEMES, AiRoleTheme } from '../../models/ai-conversation.model';

@Component({
  selector: 'app-ai-role-avatar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="role-avatar"
      [style.background-color]="theme.bgColor"
      [style.border-color]="theme.borderColor"
      [style.color]="theme.textColor"
      [title]="theme.label"
    >
      <span class="emoji" role="img" [attr.aria-label]="theme.label">{{ theme.emoji }}</span>
    </div>
  `,
  styles: [`
    .role-avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      border: 2px solid;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      font-size: 18px;
      transition: transform 0.2s ease;
    }
    .role-avatar:hover {
      transform: scale(1.1);
    }
    .emoji {
      line-height: 1;
    }
  `]
})
export class AiRoleAvatarComponent implements OnChanges {
  /** The AI role to display. Defaults to architect. */
  @Input() role: AiRoleId | null = 'architect';

  theme!: AiRoleTheme;

  ngOnChanges(): void {
    this.theme = (this.role ? AI_ROLE_THEMES[this.role] : null) ?? AI_ROLE_THEMES['architect'];
  }
}
