import { Injectable, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { Router, NavigationEnd, ActivatedRoute, ActivatedRouteSnapshot } from '@angular/router';
import { filter } from 'rxjs';

export interface Breadcrumb {
  label: string;
  url: string;
}

@Injectable({
  providedIn: 'root'
})
export class BreadcrumbService {
  private router = inject(Router);
  private activatedRoute = inject(ActivatedRoute);
  private titleService = inject(Title);

  private breadcrumbsSignal = signal<Breadcrumb[]>([]);
  public breadcrumbs = this.breadcrumbsSignal.asReadonly();

  // Dynamic overrides map, e.g. { ':projectId': 'Sistema de Facturación' }
  private dynamicOverrides = new Map<string, string>();

  constructor() {
    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe(() => {
        this.recomputeBreadcrumbs();
      });
  }

  setDynamicLabel(key: string, label: string): void {
    this.dynamicOverrides.set(key, label);
    this.recomputeBreadcrumbs();
  }

  clearDynamicLabels(): void {
    this.dynamicOverrides.clear();
    this.recomputeBreadcrumbs();
  }

  private recomputeBreadcrumbs(): void {
    const root = this.router.routerState.snapshot.root;
    const breadcrumbs: Breadcrumb[] = [];
    this.buildBreadcrumbs(root, '', breadcrumbs);

    this.breadcrumbsSignal.set(breadcrumbs);

    // Update document title
    if (breadcrumbs.length > 0) {
      const pageTitle = breadcrumbs[breadcrumbs.length - 1].label;
      this.titleService.setTitle(`${pageTitle} | ClassForge`);
    } else {
      this.titleService.setTitle('ClassForge | Modelado UML Colaborativo');
    }
  }

  private buildBreadcrumbs(route: ActivatedRouteSnapshot, accumulatedUrl: string, breadcrumbs: Breadcrumb[]): void {
    const routeURL: string = route.url.map(segment => segment.path).join('/');
    const nextUrl = routeURL ? `${accumulatedUrl}/${routeURL}` : accumulatedUrl;

    if (route.data && route.data['breadcrumb']) {
      let label = route.data['breadcrumb'] as string;

      // Check if any route parameter has a dynamic override
      for (const [paramName, overrideValue] of this.dynamicOverrides.entries()) {
        if (route.params[paramName] || routeURL.includes(paramName)) {
          label = overrideValue;
        }
      }

      // Avoid consecutive duplicate labels
      const last = breadcrumbs[breadcrumbs.length - 1];
      if (!last || last.label !== label) {
        breadcrumbs.push({
          label,
          url: nextUrl || '/'
        });
      }
    }

    for (const child of route.children) {
      this.buildBreadcrumbs(child, nextUrl, breadcrumbs);
    }
  }
}
