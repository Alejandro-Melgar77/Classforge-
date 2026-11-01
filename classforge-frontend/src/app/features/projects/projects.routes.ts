import { Routes } from '@angular/router';
import { RepertoireComponent } from './repertoire/repertoire.component';
import { ProjectCenterComponent } from './center/project-center.component';
import { ProjectOverviewComponent } from './center/project-overview.component';
import { ProjectDiagramsComponent } from './center/project-diagrams.component';
import { ProjectAiTeamComponent } from './center/project-ai-team.component';
import { ProjectTasksComponent } from './center/project-tasks.component';
import { ProjectMembersComponent } from './center/project-members.component';

export const PROJECTS_ROUTES: Routes = [
  {
    path: '',
    redirectTo: 'mine',
    pathMatch: 'full'
  },
  {
    path: 'mine',
    component: RepertoireComponent,
    data: { breadcrumb: 'Mis Proyectos' }
  },
  {
    path: 'teams',
    component: RepertoireComponent,
    data: { breadcrumb: 'Equipos' }
  },
  {
    path: ':projectId',
    component: ProjectCenterComponent,
    data: { breadcrumb: 'Centro de Proyecto' },
    children: [
      { path: '', redirectTo: 'resumen', pathMatch: 'full' },
      { path: 'resumen', component: ProjectOverviewComponent, data: { breadcrumb: 'Resumen' } },
      { path: 'diagramas', component: ProjectDiagramsComponent, data: { breadcrumb: 'Diagramas' } },
      { path: 'equipo-ia', component: ProjectAiTeamComponent, data: { breadcrumb: 'Equipo IA' } },
      { path: 'tareas', component: ProjectTasksComponent, data: { breadcrumb: 'Tareas' } },
      { path: 'miembros', component: ProjectMembersComponent, data: { breadcrumb: 'Miembros' } }
    ]
  }
];
