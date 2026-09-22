import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-button',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button [class]="getClasses()" [disabled]="disabled" (click)="onClick()">
      <ng-content></ng-content>
    </button>
  `
})
export class ButtonComponent {
  @Input() variant: 'primary' | 'danger' | 'ghost' = 'primary';
  @Input() disabled = false;
  
  getClasses(): string {
    const base = 'rounded-lg px-6 py-2.5 font-medium transition-colors duration-200';
    if (this.variant === 'primary') return `${base} bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-white`;
    if (this.variant === 'danger') return `${base} bg-[var(--danger)] hover:bg-red-700 text-white`;
    if (this.variant === 'ghost') return `${base} bg-transparent border border-[var(--border)] hover:bg-[var(--surface-3)] text-white`;
    return base;
  }

  onClick() {}
}
