import { Component, inject, OnInit, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { Subscription, filter } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { InactivityService } from '../../core/services/inactivity.service';
import { NotificationService } from '../../core/services/notification.service';
import { BreadcrumbService } from '../../core/services/breadcrumb.service';
import { UserRole } from '../../core/models/user.model';

import { BreadcrumbsComponent } from '../../shared/components/breadcrumbs/breadcrumbs.component';
import { ToastContainerComponent } from '../../shared/components/toast-container/toast-container.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { SessionExpiredModalComponent } from '../../shared/components/session-expired-modal/session-expired-modal.component';
import { UserMenuModalComponent } from './user-menu-modal/user-menu-modal.component';
import { ShortcutsDialogComponent } from './shortcuts-dialog/shortcuts-dialog.component';
import { NotificationsPanelComponent } from './notifications-panel/notifications-panel.component';
import { TourOverlayComponent } from '../../features/support/components/tour-overlay/tour-overlay.component';
import { SupportAssistantComponent } from '../../features/support/components/support-assistant/support-assistant.component';

export interface ShellNavItem {
  icon: string;
  label: string;
  route?: string;
  action?: 'notifications' | 'profile';
  children?: ShellNavItem[];
  roles?: UserRole[];
  expanded?: boolean;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    BreadcrumbsComponent,
    ToastContainerComponent,
    ConfirmDialogComponent,
    SessionExpiredModalComponent,
    UserMenuModalComponent,
    ShortcutsDialogComponent,
    NotificationsPanelComponent,
    TourOverlayComponent,
    SupportAssistantComponent
  ],
  templateUrl: './shell.component.html'
})
export class ShellComponent implements OnInit, OnDestroy {
  private authService = inject(AuthService);
  private inactivityService = inject(InactivityService);
  private notificationService = inject(NotificationService);
  private breadcrumbService = inject(BreadcrumbService);
  private router = inject(Router);
  private routerSub: Subscription | null = null;

  user$ = this.authService.currentUser$;
  isSidebarExpanded = true;
  isMobileOpen = false;
  isFullscreenMode = false;

  isNotificationsOpen = false;
  isUserModalOpen = false;
  isShortcutsOpen = false;

  unreadCount = this.notificationService.unreadCount;

  navItems: ShellNavItem[] = [
    { icon: '🏠', label: 'Inicio', route: '/dashboard' },
    { icon: '📁', label: 'Proyectos', route: '/projects' },
    { icon: '📊', label: 'Diagramas', route: '/diagrams' },
    { icon: '👥', label: 'Mis Equipos', route: '/projects/teams' },
    { icon: '🔔', label: 'Notificaciones', action: 'notifications' },
    { icon: '👤', label: 'Perfil', action: 'profile' },
    {
      icon: '🛡️',
      label: 'Administración',
      roles: ['admin'],
      expanded: false,
      children: [
        { icon: '👤', label: 'Usuarios', route: '/admin/users' },
        { icon: '👥', label: 'Equipos', route: '/admin/teams' },
        { icon: '⚙️', label: 'Configuración', route: '/admin/config' }
      ]
    }
  ];

  @HostListener('window:keydown', ['$event'])
  handleGlobalShortcuts(event: KeyboardEvent): void {
    if (event.key === '?' && !this.isInputElement(event.target)) {
      event.preventDefault();
      this.isShortcutsOpen = !this.isShortcutsOpen;
      return;
    }
    if (event.key === 'Escape') {
      if (this.isShortcutsOpen) { this.isShortcutsOpen = false; return; }
      if (this.isNotificationsOpen) { this.isNotificationsOpen = false; return; }
      if (this.isUserModalOpen) { this.isUserModalOpen = false; return; }
    }
    if (event.altKey && !event.ctrlKey && !event.shiftKey) {
      if (event.key.toLowerCase() === 'd') {
        event.preventDefault();
        this.router.navigate(['/dashboard']);
      } else if (event.key.toLowerCase() === 'p') {
        event.preventDefault();
        this.router.navigate(['/projects']);
      } else if (event.key.toLowerCase() === 'u') {
        event.preventDefault();
        this.router.navigate(['/diagrams']);
      }
    }
  }

  private isInputElement(target: EventTarget | null): boolean {
    if (!target) return false;
    const el = target as HTMLElement;
    return el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable;
  }

  ngOnInit(): void {
    this.checkFullscreenMode(this.router.url);

    this.routerSub = this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd)
    ).subscribe(event => {
      this.checkFullscreenMode(event.urlAfterRedirects || event.url);
      this.isMobileOpen = false;
      this.isNotificationsOpen = false;
    });

    this.notificationService.loadNotifications().subscribe();
  }

  ngOnDestroy(): void {
    this.routerSub?.unsubscribe();
  }

  private checkFullscreenMode(url: string): void {
    const isDiagramEditor = /\/diagrams\/[a-f0-9]+/.test(url);
    this.isFullscreenMode = isDiagramEditor;
    if (isDiagramEditor) {
      this.isSidebarExpanded = false;
    }
  }

  onNavItemClick(item: ShellNavItem): void {
    if (item.action === 'notifications') {
      this.isNotificationsOpen = !this.isNotificationsOpen;
    } else if (item.action === 'profile') {
      this.isUserModalOpen = true;
    }
  }

  toggleSidebar(): void {
    this.isSidebarExpanded = !this.isSidebarExpanded;
  }

  toggleMobileMenu(): void {
    this.isMobileOpen = !this.isMobileOpen;
  }

  toggleNotifications(): void {
    this.isNotificationsOpen = !this.isNotificationsOpen;
  }

  openUserModal(): void {
    this.isUserModalOpen = true;
  }

  openShortcuts(): void {
    this.isShortcutsOpen = true;
  }

  isMenuItemVisible(item: ShellNavItem): boolean {
    if (!item.roles || item.roles.length === 0) {
      return true;
    }
    return this.authService.hasAnyRole(item.roles);
  }

  getInitials(name: string): string {
    if (!name) return 'U';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  }

  getRoleLabel(role: string): string {
    const labels: Record<string, string> = {
      'admin': 'Admin',
      'scrum_master': 'Scrum Master',
      'dev': 'Dev'
    };
    return labels[role] || role;
  }
}
