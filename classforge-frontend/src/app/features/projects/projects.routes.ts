import { Routes } from '@angular/router';
import { RepertoireComponent } from './repertoire/repertoire.component';

export const PROJECTS_ROUTES: Routes = [
  {
    path: '',
    redirectTo: 'mine',
    pathMatch: 'full'
  },
  {
    path: 'mine',
    component: RepertoireComponent
  },
  {
    path: 'teams',
    component: RepertoireComponent // Reuse for now, we can pass data or use distinct component later
  }
];
