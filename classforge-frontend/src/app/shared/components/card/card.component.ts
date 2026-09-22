import { Component } from '@angular/core';

@Component({
  selector: 'app-card',
  standalone: true,
  template: `
    <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-xl p-6 shadow-lg">
      <ng-content></ng-content>
    </div>
  `
})
export class CardComponent {}
