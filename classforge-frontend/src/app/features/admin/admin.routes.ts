import { Routes } from '@angular/router';
import { AdminShellComponent } from './admin-shell.component';
import { UserListComponent } from './users/user-list.component';
import { TeamListComponent } from './teams/team-list.component';
import { GlobalConfigComponent } from './config/global-config.component';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    component: AdminShellComponent,
    children: [
      { path: '', redirectTo: 'users', pathMatch: 'full' },
      { path: 'users', component: UserListComponent },
      { path: 'teams', component: TeamListComponent },
      { path: 'config', component: GlobalConfigComponent }
    ]
  }
];

