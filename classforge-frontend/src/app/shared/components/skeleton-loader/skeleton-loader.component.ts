import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-skeleton-loader',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="skeleton-container" [attr.aria-busy]="true" [attr.aria-label]="'Cargando...'">
      <div
        *ngFor="let item of items"
        class="skeleton-item"
        [style.height]="height"
        [style.border-radius]="borderRadius"
      ></div>
    </div>
  `,
  styles: [`
    .skeleton-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding: 8px 0;
    }
    .skeleton-item {
      background: linear-gradient(
        90deg,
        rgba(255, 255, 255, 0.06) 25%,
        rgba(255, 255, 255, 0.12) 50%,
        rgba(255, 255, 255, 0.06) 75%
      );
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
      border-radius: 8px;
    }
    @keyframes shimmer {
      0% { background-position: -200% 0; }
      100% { background-position: 200% 0; }
    }
  `]
})
export class SkeletonLoaderComponent {
  /** Number of skeleton rows to display. */
  @Input() rows = 5;
  /** Height of each skeleton row. */
  @Input() height = '56px';
  /** Border radius of skeleton items. */
  @Input() borderRadius = '8px';

  get items(): number[] {
    return Array(this.rows).fill(0);
  }
}
