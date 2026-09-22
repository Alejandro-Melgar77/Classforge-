import { Routes } from '@angular/router';
import { DiagramListComponent } from './list/diagram-list.component';
import { DiagramCanvasComponent } from './canvas/diagram-canvas.component';

export const DIAGRAMS_ROUTES: Routes = [
  { path: '', component: DiagramListComponent },
  { path: ':id', component: DiagramCanvasComponent }
];
