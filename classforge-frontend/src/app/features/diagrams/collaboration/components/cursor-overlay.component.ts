import { Component, inject, effect, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { CollaborationService } from '../services/collaboration.service';
import { CanvasService } from '../../services/canvas.service';
import { AuthService } from '../../../../core/services/auth.service';

interface Cursor {
  id: string;
  x: number;
  y: number;
  name: string;
  color: string;
  lastUpdate: number;
}

interface LockedElementBadge {
  id: string;
  x: number;
  y: number;
  userName: string;
  userColor: string;
  isMyLock: boolean;
}

interface AiFocusHighlight {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  role: string;
}

@Component({
  selector: 'app-cursor-overlay',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="cursor-overlay" aria-hidden="true">
      <!-- ═══ Remote Cursors ═══ -->
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

      <!-- ═══ Locked Elements Badges ═══ -->
      <div *ngFor="let lock of lockedBadges()"
           class="lock-badge"
           [class.my-lock]="lock.isMyLock"
           [style.left.px]="lock.x"
           [style.top.px]="lock.y"
           [style.border-color]="lock.userColor"
           [title]="lock.isMyLock ? 'Bloqueado por ti (editando)' : 'Bloqueado por ' + lock.userName + ' (edición bloqueada)'">
        <span class="lock-icon">🔒</span>
        <span class="lock-text font-bold" [style.color]="lock.userColor">
          {{ lock.isMyLock ? 'Editando tú' : lock.userName }}
        </span>
      </div>

      <!-- ═══ AI Focus Highlights (with prefers-reduced-motion) ═══ -->
      <div *ngFor="let focus of aiFocusHighlights()"
           class="ai-focus-box"
           [style.left.px]="focus.x"
           [style.top.px]="focus.y"
           [style.width.px]="focus.width"
           [style.height.px]="focus.height"
           [title]="'Foco de la IA (' + focus.role + ')'">
        <span class="ai-focus-label">🤖 {{ focus.role | uppercase }}</span>
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
      font-size: 11px;
      font-weight: 600;
      white-space: nowrap;
    }
    .lock-badge {
      position: absolute;
      transform: translateY(-100%);
      margin-top: -6px;
      display: flex;
      align-items: center;
      gap: 4px;
      background: rgba(15, 23, 42, 0.92);
      backdrop-filter: blur(4px);
      border: 1.5px solid;
      border-radius: 6px;
      padding: 2px 8px;
      font-size: 11px;
      pointer-events: auto;
      cursor: help;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
      z-index: 50;
      animation: fadeIn 150ms ease-out;
    }
    .lock-badge.my-lock {
      opacity: 0.8;
    }
    .lock-icon {
      font-size: 11px;
    }
    .ai-focus-box {
      position: absolute;
      border-radius: 8px;
      border: 2.5px solid #A855F7;
      background: rgba(168, 85, 247, 0.08);
      pointer-events: none;
      z-index: 40;
      animation: aiPulse 2s infinite ease-in-out;
      box-shadow: 0 0 16px rgba(168, 85, 247, 0.4);
    }
    .ai-focus-label {
      position: absolute;
      top: -22px;
      right: 4px;
      background: #7E22CE;
      color: white;
      font-size: 9px;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 4px;
      letter-spacing: 0.05em;
    }
    @keyframes aiPulse {
      0%, 100% {
        box-shadow: 0 0 0 0 rgba(168, 85, 247, 0.6);
        border-color: #C084FC;
      }
      50% {
        box-shadow: 0 0 0 10px rgba(168, 85, 247, 0);
        border-color: #9333EA;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .ai-focus-box {
        animation: none !important;
        border: 3px solid #C084FC !important;
        box-shadow: 0 0 8px rgba(168, 85, 247, 0.6) !important;
      }
      .cursor {
        transition: none !important;
      }
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-90%); }
      to { opacity: 1; transform: translateY(-100%); }
    }
  `]
})
export class CursorOverlayComponent implements OnDestroy {
  private colabService = inject(CollaborationService);
  private canvasService = inject(CanvasService);
  private authService = inject(AuthService);

  private cleanupTimer: any;
  private badgeUpdateTimer: any;
  private focusTimeout: any;
  private subs = new Subscription();

  public activeCursors = signal<Cursor[]>([]);
  public lockedBadges = signal<LockedElementBadge[]>([]);
  public aiFocusHighlights = signal<AiFocusHighlight[]>([]);

  constructor() {
    effect(() => {
      const map = this.colabService.remoteCursors();
      const now = Date.now();
      const cursors: Cursor[] = [];

      map.forEach((data, id) => {
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

    // Actualización de badges de locks
    effect(() => {
      const lockedMap = this.colabService.lockedElements();
      const users = this.colabService.connectedUsers();
      this.updateLockedBadges(lockedMap, users);
    }, { allowSignalWrites: true });

    // Listener para eventos AI_FOCUS
    this.subs.add(
      this.colabService.aiFocus$.subscribe(({ element_ids, role }) => {
        this.applyAiFocus(element_ids, role || 'IA');
      })
    );

    // Limpieza de cursores inactivos cada 1s
    this.cleanupTimer = setInterval(() => {
      const now = Date.now();
      const current = this.activeCursors();
      const filtered = current.filter(c => now - c.lastUpdate < 5000);
      if (filtered.length !== current.length) {
        this.activeCursors.set(filtered);
      }
    }, 1000);

    // Reubicar badges si el viewport hace pan/zoom
    this.badgeUpdateTimer = setInterval(() => {
      const lockedMap = this.colabService.lockedElements();
      if (lockedMap.size > 0) {
        this.updateLockedBadges(lockedMap, this.colabService.connectedUsers());
      }
    }, 500);
  }

  private updateLockedBadges(lockedMap: Map<string, string>, users: any[]) {
    const graph = this.canvasService.getGraph();
    if (!graph) {
      this.lockedBadges.set([]);
      return;
    }

    const currentUserId = this.authService.getCurrentUser()?.id;
    const badges: LockedElementBadge[] = [];

    lockedMap.forEach((lockedByUserId, elementId) => {
      const cell = graph.getCellById(elementId);
      if (cell && cell.isNode()) {
        const node = cell as any;
        const pos = node.position();
        const clientPt = graph.localToClient(pos);
        const container = (graph as any).container;
        if (!container) return;

        const containerRect = container.getBoundingClientRect();
        const x = clientPt.x - containerRect.left;
        const y = clientPt.y - containerRect.top;

        const user = users.find(u => u.user_id === lockedByUserId);
        const userName = user ? user.name : 'Colaborador';
        const userColor = user ? user.color : '#E11D48';
        const isMyLock = lockedByUserId === currentUserId;

        badges.push({
          id: elementId,
          x: Math.max(8, x),
          y: Math.max(20, y),
          userName,
          userColor,
          isMyLock
        });
      }
    });

    this.lockedBadges.set(badges);
  }

  private applyAiFocus(elementIds: string[], role: string) {
    const graph = this.canvasService.getGraph();
    if (!graph || !elementIds || elementIds.length === 0) return;

    const highlights: AiFocusHighlight[] = [];
    const container = (graph as any).container;
    if (!container) return;
    const containerRect = container.getBoundingClientRect();

    elementIds.forEach(id => {
      const cell = graph.getCellById(id);
      if (cell && cell.isNode()) {
        const node = cell as any;
        const pos = node.position();
        const size = node.size();
        const clientPt = graph.localToClient(pos);
        const zoom = graph.zoom();

        highlights.push({
          id,
          x: clientPt.x - containerRect.left - 4,
          y: clientPt.y - containerRect.top - 4,
          width: size.width * zoom + 8,
          height: size.height * zoom + 8,
          role
        });
      }
    });

    this.aiFocusHighlights.set(highlights);

    // Desvanecer foco tras 5 segundos
    clearTimeout(this.focusTimeout);
    this.focusTimeout = setTimeout(() => {
      this.aiFocusHighlights.set([]);
    }, 5000);
  }

  ngOnDestroy(): void {
    clearInterval(this.cleanupTimer);
    clearInterval(this.badgeUpdateTimer);
    clearTimeout(this.focusTimeout);
    this.subs.unsubscribe();
  }
}
