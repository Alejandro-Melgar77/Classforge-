import {
  Component,
  Input,
  inject,
  signal,
  ChangeDetectionStrategy
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { AiTeamHeaderComponent } from '../ai-team-header/ai-team-header.component';
import { AiTeamStore } from '../../data-access/ai-team.store';
import { AI_TEAM_I18N } from '../../ai-team.constants';

export type AiTeamSubTab = 'chat' | 'history' | 'tasks';

@Component({
  selector: 'app-ai-team-panel',
  standalone: true,
  imports: [CommonModule, AiTeamHeaderComponent],
  templateUrl: './ai-team-panel.component.html',
  styleUrl: './ai-team-panel.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AiTeamPanelComponent {
  @Input() diagramId?: string;
  @Input() projectId?: string;

  public store = inject(AiTeamStore);
  public activeSubTab = signal<AiTeamSubTab>('chat');

  public readonly i18n = AI_TEAM_I18N;

  public selectSubTab(tab: AiTeamSubTab): void {
    this.activeSubTab.set(tab);
    if (tab === 'chat') {
      this.store.selectThread('personal');
    } else if (tab === 'history') {
      this.store.selectThread('project');
    }
  }
}
