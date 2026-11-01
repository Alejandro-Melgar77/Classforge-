import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { BreadcrumbService, Breadcrumb } from '../../../core/services/breadcrumb.service';

@Component({
  selector: 'app-breadcrumbs',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <nav
      *ngIf="breadcrumbs().length > 0"
      aria-label="Migas de pan"
      class="flex items-center text-xs text-[var(--text-secondary)] overflow-x-auto whitespace-nowrap scrollbar-none py-1"
    >
      <ol class="inline-flex items-center gap-1.5 list-none p-0 m-0">
        <li class="inline-flex items-center">
          <a
            routerLink="/dashboard"
            class="hover:text-white transition-colors flex items-center gap-1 text-[var(--text-secondary)] focus:outline-hidden focus:ring-1 focus:ring-primary rounded px-1"
            title="Ir a Inicio"
          >
            <span>🏠</span>
            <span class="sr-only">Inicio</span>
          </a>
        </li>

        <li *ngFor="let crumb of breadcrumbs(); let last = last; let i = index" class="inline-flex items-center gap-1.5">
          <span class="text-[var(--text-muted)] text-[10px]" aria-hidden="true">›</span>

          <a
            *ngIf="!last"
            [routerLink]="crumb.url"
            class="hover:text-white transition-colors text-[var(--text-secondary)] focus:outline-hidden focus:ring-1 focus:ring-primary rounded px-1"
          >
            {{ crumb.label }}
          </a>

          <span
            *ngIf="last"
            class="font-semibold text-white px-1 truncate max-w-[200px] md:max-w-xs"
            aria-current="page"
          >
            {{ crumb.label }}
          </span>
        </li>
      </ol>
    </nav>
  `
})
export class BreadcrumbsComponent {
  private breadcrumbService = inject(BreadcrumbService);
  breadcrumbs = this.breadcrumbService.breadcrumbs;
}
