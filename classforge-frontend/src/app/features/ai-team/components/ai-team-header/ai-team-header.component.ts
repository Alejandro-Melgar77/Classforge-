import {
  Component,
  inject,
  computed,
  signal,
  ChangeDetectionStrategy
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiTeamStore } from '../../data-access/ai-team.store';
import { AuthService } from '../../../../core/services/auth.service';
import { AiRole, AiRoleAutonomy, ConnectionStatus } from '../../data-access/ai-team.models';
import { AI_TEAM_I18N } from '../../ai-team.constants';

@Component({
  selector: 'app-ai-team-header',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ai-team-header.component.html',
  styleUrl: './ai-team-header.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AiTeamHeaderComponent {
  public store = inject(AiTeamStore);
  public authService = inject(AuthService);

  public readonly i18n = AI_TEAM_I18N.header;
  public showRolesExpanded = signal<boolean>(false);

  // Permission check: Dev role cannot set autonomy to 'apply'
  public canApplyAutonomy = computed<boolean>(() => {
    const user = this.authService.getCurrentUser();
    if (!user) return false;
    // admin and scrum_master have permission
    return user.role === 'admin' || user.role === 'scrum_master';
  });

  // Current connection status string
  public connectionLabel = computed<string>(() => {
    const status: ConnectionStatus = this.store.connectionStatus();
    return this.i18n.connection[status] || this.i18n.connection.disconnected;
  });

  // Daily consumption formatted string
  public consumptionText = computed<string>(() => {
    const digest = this.store.currentDigest();
    const tokens = digest?.tokens ?? 0;
    return tokens > 0 ? this.i18n.consumption.formatTokens(tokens) : this.i18n.consumption.noUsage;
  });

  // Audit information for participative mode
  public participativeAuditText = computed<string>(() => {
    const state = this.store.state();
    if (!state?.participative?.updated_by) {
      return this.i18n.participativeDefaultAudit;
    }
    const user = state.participative.updated_by;
    const time = this.formatDate(state.participative.updated_at);
    return this.i18n.participativeChangedBy(user, time);
  });

  public toggleRolesAccordion(): void {
    this.showRolesExpanded.update(v => !v);
  }

  public async onToggleParticipative(): Promise<void> {
    await this.store.toggleParticipative();
  }

  public async onToggleLocalOnly(): Promise<void> {
    await this.store.toggleLocalOnly();
  }

  public async onToggleRoleActive(role: AiRole, event: Event): Promise<void> {
    event.stopPropagation();
    await this.store.setRoleEnabled(role.role_id, !role.is_active);
  }

  public async onChangeAutonomy(role: AiRole, autonomy: AiRoleAutonomy): Promise<void> {
    if (autonomy === 'apply' && !this.canApplyAutonomy()) {
      return;
    }
    await this.store.setAutonomy(role.role_id, autonomy);
  }

  public formatDate(val?: string | null): string {
    if (!val) return 'reciente';
    try {
      const d = new Date(val);
      if (isNaN(d.getTime())) return 'reciente';
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return 'reciente';
    }
  }
}
