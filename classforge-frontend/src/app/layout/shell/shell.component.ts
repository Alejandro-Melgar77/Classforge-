import { Component, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { Subscription, filter } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { InactivityService } from '../../core/services/inactivity.service';
import { UserRole } from '../../core/models/user.model';

export interface NavItem {
  icon: string;
  label: string;
  route?: string;
  children?: NavItem[];
  roles?: UserRole[];
  expanded?: boolean;
}

import { TourOverlayComponent } from '../../features/support/components/tour-overlay/tour-overlay.component';
import { SupportAssistantComponent } from '../../features/support/components/support-assistant/support-assistant.component';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive, TourOverlayComponent, SupportAssistantComponent],
  templateUrl: './shell.component.html'
})
export class ShellComponent implements OnInit, OnDestroy {
  private authService = inject(AuthService);
  private inactivityService = inject(InactivityService);
  private router = inject(Router);
  private routerSub: Subscription | null = null;

  user$ = this.authService.currentUser$;
  isSidebarExpanded = true;
  isMobileOpen = false;
  isFullscreenMode = false;

  navItems: NavItem[] = [
    { icon: 'home', label: 'Dashboard', route: '/dashboard' },
    {
      icon: 'folder',
      label: 'Repertorio',
      expanded: false,
      children: [
        { icon: 'folder-open', label: 'Mis Proyectos', route: '/projects/mine' },
        { icon: 'users', label: 'Equipos', route: '/projects/teams' }
      ]
    },
    { icon: 'layout', label: 'Diagramas', route: '/diagrams' },
    {
      icon: 'settings',
      label: 'Administración',
      roles: ['admin'],
      expanded: false,
      children: [
        { icon: 'user', label: 'Usuarios', route: '/admin/users' },
        { icon: 'users', label: 'Equipos', route: '/admin/teams' },
        { icon: 'sliders', label: 'Configuración', route: '/admin/config' }
      ]
    }
  ];

  ngOnInit() {
    this.checkFullscreenMode(this.router.url);

    this.routerSub = this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd)
    ).subscribe(event => {
      this.checkFullscreenMode(event.urlAfterRedirects || event.url);
    });
  }

  ngOnDestroy() {
    this.routerSub?.unsubscribe();
  }

  private checkFullscreenMode(url: string) {
    // Auto-collapse sidebar when editing a specific diagram (/diagrams/:id)
    const isDiagramEditor = /\/diagrams\/[a-f0-9]+/.test(url);
    this.isFullscreenMode = isDiagramEditor;
    if (isDiagramEditor) {
      this.isSidebarExpanded = false;
    }
  }

  logout() {
    this.authService.logout();
  }

  toggleSidebar() {
    this.isSidebarExpanded = !this.isSidebarExpanded;
  }

  toggleMobileMenu() {
    this.isMobileOpen = !this.isMobileOpen;
  }

  isMenuItemVisible(item: NavItem): boolean {
    if (!item.roles || item.roles.length === 0) {
      return true;
    }
    return this.authService.hasAnyRole(item.roles);
  }

  getInitials(name: string): string {
    if (!name) return '';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  }

  getRoleLabel(role: string): string {
    const labels: Record<string, string> = {
      'admin': 'Administrador',
      'scrum_master': 'Scrum Master',
      'dev': 'Desarrollador'
    };
    return labels[role] || role;
  }
}
