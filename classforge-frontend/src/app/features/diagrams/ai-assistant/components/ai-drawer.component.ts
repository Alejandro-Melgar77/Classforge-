import {
  Component,
  Input,
  Output,
  EventEmitter,
  inject,
  signal,
  OnInit,
  OnDestroy,
  OnChanges,
  SimpleChanges,
  HostListener,
  ChangeDetectionStrategy
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../../core/services/auth.service';
import { AiTeamStore } from '../../../ai-team/data-access/ai-team.store';
import { AiTeamSocketService } from '../../../ai-team/data-access/ai-team.socket';
import { CommandConsoleComponent } from './command-console/command-console.component';
import { AiTeamPanelComponent } from '../../../ai-team/components/ai-team-panel/ai-team-panel.component';
import { AI_TEAM_I18N } from '../../../ai-team/ai-team.constants';

export type MainDrawerTab = 'commands' | 'ai-team';

@Component({
  selector: 'app-ai-drawer',
  standalone: true,
  imports: [CommonModule, CommandConsoleComponent, AiTeamPanelComponent],
  templateUrl: './ai-drawer.component.html',
  styleUrl: './ai-drawer.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AiDrawerComponent implements OnInit, OnDestroy, OnChanges {
  @Input() isOpen = false;
  @Input() diagramId?: string;
  @Input() projectId?: string;
  @Output() close = new EventEmitter<void>();

  public store = inject(AiTeamStore);
  public socketService = inject(AiTeamSocketService);
  public authService = inject(AuthService);

  public readonly i18n = AI_TEAM_I18N;
  public mainTab = signal<MainDrawerTab>('commands');
  public drawerWidth = 520;
  private isResizing = false;

  ngOnInit(): void {
    if (typeof localStorage !== 'undefined') {
      const savedWidth = localStorage.getItem('cf_ai_drawer_width');
      if (savedWidth) {
        const w = parseInt(savedWidth, 10);
        if (w >= 360 && w <= 960) this.drawerWidth = w;
      }
    }
    this.syncTeamSession();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['projectId'] && !changes['projectId'].firstChange) {
      this.syncTeamSession();
    }
  }

  ngOnDestroy(): void {
    this.store.destroy();
  }

  private syncTeamSession(): void {
    if (this.projectId) {
      const user = this.authService.getCurrentUser();
      this.store.setSocketService(this.socketService);
      this.store.init(this.projectId, user?.id, user?.name);
    }
  }

  public setTab(tab: MainDrawerTab): void {
    this.mainTab.set(tab);
  }

  public setDrawerWidth(width: number): void {
    this.drawerWidth = width;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('cf_ai_drawer_width', width.toString());
    }
  }

  public startResize(event: MouseEvent): void {
    event.preventDefault();
    this.isResizing = true;
  }

  @HostListener('window:mousemove', ['$event'])
  public onMouseMove(event: MouseEvent): void {
    if (!this.isResizing) return;
    const newWidth = window.innerWidth - event.clientX;
    if (newWidth >= 360 && newWidth <= 960) {
      this.drawerWidth = newWidth;
    }
  }

  @HostListener('window:mouseup')
  public onMouseUp(): void {
    if (this.isResizing) {
      this.isResizing = false;
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('cf_ai_drawer_width', this.drawerWidth.toString());
      }
    }
  }

  @HostListener('window:keydown.escape')
  public onEscape(): void {
    if (this.isOpen) {
      this.close.emit();
    }
  }
}
