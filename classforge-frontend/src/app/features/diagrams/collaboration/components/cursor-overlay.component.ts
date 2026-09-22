import { Component, inject, effect, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CollaborationService } from '../services/collaboration.service';

interface Cursor {
  id: string;
  x: number;
  y: number;
  name: string;
  color: string;
  lastUpdate: number;
}

@Component({
  selector: 'app-cursor-overlay',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="cursor-overlay">
      <div *ngFor="let cursor of activeCursors()"
           class="cursor"
           [style.transform]="'translate(' + cursor.x + 'px, ' + cursor.y + 'px)'">
        <svg width="16" height="20" viewBox="0 0 16 20" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M0 0L16 11.2308L9.08377 12.3923L0 20V0Z" [attr.fill]="cursor.color"/>
        </svg>
        <div class="cursor-name" [style.background-color]="cursor.color">
          {{ cursor.name }}
        </div>
      </div>
    </div>
  `,
  styles: [`
    .cursor-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 9999;
      overflow: hidden;
    }
    .cursor {
      position: absolute;
      top: 0;
      left: 0;
      transition: transform 80ms ease-out;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
    }
    .cursor-name {
      margin-top: 4px;
      padding: 2px 8px;
      border-radius: 12px;
      color: white;
      font-size: 12px;
      font-weight: 500;
      white-space: nowrap;
    }
  `]
})
export class CursorOverlayComponent implements OnDestroy {
  private colabService = inject(CollaborationService);
  private cleanupTimer: any;
  
  public activeCursors = signal<Cursor[]>([]);

  constructor() {
    effect(() => {
      const map = this.colabService.remoteCursors();
      const now = Date.now();
      const cursors: Cursor[] = [];
      
      map.forEach((data, id) => {
        // Find existing to preserve lastUpdate if not updating it here, but actually
        // the effect runs when remoteCursors changes, meaning it was just updated.
        cursors.push({
          id,
          x: data.x,
          y: data.y,
          name: data.name,
          color: data.color,
          lastUpdate: now
        });
      });
      this.activeCursors.set(cursors);
    }, { allowSignalWrites: true });

    // Clean up inactive cursors (older than 5s)
    this.cleanupTimer = setInterval(() => {
      const now = Date.now();
      const current = this.activeCursors();
      const filtered = current.filter(c => now - c.lastUpdate < 5000);
      if (filtered.length !== current.length) {
        this.activeCursors.set(filtered);
      }
    }, 1000);
  }

  ngOnDestroy() {
    if (this.cleanupTimer) clearInterval(this.cleanupTimer);
  }
}
