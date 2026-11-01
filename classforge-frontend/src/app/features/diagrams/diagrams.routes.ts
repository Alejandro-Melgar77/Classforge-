import { Routes } from '@angular/router';
import { DiagramListComponent } from './list/diagram-list.component';

export const DIAGRAMS_ROUTES: Routes = [
  { path: '', component: DiagramListComponent, data: { breadcrumb: 'Diagramas' } },
  {
    path: ':id',
    loadComponent: () => import('./canvas/diagram-canvas.component').then((m) => m.DiagramCanvasComponent),
    data: { breadcrumb: 'Lienzo UML' }
  }
];
