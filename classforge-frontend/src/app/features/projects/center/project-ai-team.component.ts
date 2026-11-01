import { Component, inject, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProjectCenterComponent } from './project-center.component';
import { AiTeamPanelComponent } from '../../ai-team/components/ai-team-panel/ai-team-panel.component';
import { AiTeamStore } from '../../ai-team/data-access/ai-team.store';

@Component({
  selector: 'app-project-ai-team',
  standalone: true,
  imports: [CommonModule, AiTeamPanelComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="h-full flex flex-col bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl overflow-hidden shadow-xl min-h-[600px]">
      
      <!-- Subheader info banner -->
      <div class="px-5 py-3 bg-[var(--surface-3)] border-b border-[var(--border)] flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-xl">🤖</span>
          <div>
            <h2 class="text-sm font-bold text-white">Centro de Colaboración: Equipo IA</h2>
            <p class="text-xs text-[var(--text-secondary)]">
              Interactúa con los 7 roles canónicos de IA para diseñar, analizar y auditar tu sistema.
            </p>
          </div>
        </div>
      </div>

      <!-- Full-screen AI Team Panel from P6b -->
      <div class="flex-1 overflow-hidden p-2 sm:p-4">
        <app-ai-team-panel
          class="w-full h-full block"
          [projectId]="center.project()?.id"
        ></app-ai-team-panel>
      </div>

    </div>
  `
})
export class ProjectAiTeamComponent implements OnInit {
  center = inject(ProjectCenterComponent);
  private store = inject(AiTeamStore);

  ngOnInit(): void {
    const proj = this.center.project();
    if (proj) {
      this.store.init(proj.id);
    }
  }
}
