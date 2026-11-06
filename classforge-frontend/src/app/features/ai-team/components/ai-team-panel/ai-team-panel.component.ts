import {
  Component,
  Input,
  inject,
  signal,
  computed,
  ChangeDetectionStrategy
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { AiTeamHeaderComponent } from '../ai-team-header/ai-team-header.component';
import { AiTeamStore } from '../../data-access/ai-team.store';
import { AI_TEAM_I18N } from '../../ai-team.constants';
import { AiTask, TaskStatus } from '../../data-access/ai-team.models';

export type AiTeamSubTab = 'chat' | 'history' | 'tasks';

const TASK_COLUMNS: TaskStatus[] = ['pending', 'in_progress', 'needs_input', 'completed', 'failed'];

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
  public readonly taskColumns = TASK_COLUMNS;

  public selectSubTab(tab: AiTeamSubTab): void {
    this.activeSubTab.set(tab);
    if (tab === 'chat') {
      this.store.selectThread('personal');
    } else if (tab === 'history') {
      this.store.selectThread('project');
    }
  }

  public getTasksByStatus(status: TaskStatus): AiTask[] {
    return this.store.tasks().filter(t => t.status === status);
  }

  public getColumnLabel(status: TaskStatus): string {
    return (this.i18n.tasks.columns as Record<string, string>)[status] ?? status;
  }

  public getColumnAccent(status: TaskStatus): string {
    const map: Record<string, string> = {
      pending: 'border-slate-600 text-slate-400',
      in_progress: 'border-blue-500 text-blue-400',
      needs_input: 'border-amber-500 text-amber-400',
      completed: 'border-emerald-500 text-emerald-400',
      failed: 'border-rose-500 text-rose-400'
    };
    return map[status] ?? 'border-slate-700 text-slate-400';
  }

  public getTaskBadgeClass(status: TaskStatus): string {
    const map: Record<string, string> = {
      pending: 'bg-slate-800 text-slate-300 border-slate-700',
      in_progress: 'bg-blue-900/60 text-blue-300 border-blue-700 animate-pulse',
      needs_input: 'bg-amber-900/50 text-amber-300 border-amber-700',
      completed: 'bg-emerald-900/50 text-emerald-300 border-emerald-700',
      failed: 'bg-rose-900/50 text-rose-300 border-rose-700'
    };
    return map[status] ?? 'bg-slate-800 text-slate-400 border-slate-700';
  }

  public getTaskStatusIcon(status: TaskStatus): string {
    const map: Record<string, string> = {
      pending: '⏳',
      in_progress: '⚡',
      needs_input: '❓',
      completed: '✅',
      failed: '❌'
    };
    return map[status] ?? '•';
  }

  public async onExecuteTask(task: AiTask): Promise<void> {
    await this.store.executeTask(task.id);
  }

  public async onDeleteTask(task: AiTask): Promise<void> {
    await this.store.deleteTask(task.id);
  }

  public formatRelativeTime(isoDate?: string | null): string {
    if (!isoDate) return '';
    try {
      const diff = Date.now() - new Date(isoDate).getTime();
      const mins = Math.floor(diff / 60000);
      if (mins < 1) return 'ahora';
      if (mins < 60) return `${mins}m`;
      const hrs = Math.floor(mins / 60);
      if (hrs < 24) return `${hrs}h`;
      return `${Math.floor(hrs / 24)}d`;
    } catch {
      return '';
    }
  }

  public getMessageTypeIcon(msg: any): string {
    if (msg.trigger === 'proactive_review') return '🔍';
    if (msg.trigger === 'task') return '📋';
    if (msg.author_type === 'ai') return '🤖';
    return '💬';
  }
}
