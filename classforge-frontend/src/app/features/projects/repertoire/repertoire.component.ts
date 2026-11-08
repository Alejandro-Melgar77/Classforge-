import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ProjectCardComponent } from './project-card.component';
import { ProjectsService, ProjectFilters, CreateProjectDto } from '../services/projects.service';
import { FoldersService } from '../services/folders.service';
import { TeamsService } from '../services/teams.service';
import { Project } from '../models/project.model';
import { Folder } from '../models/folder.model';
import { Team } from '../models/team.model';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-repertoire',
  standalone: true,
  imports: [CommonModule, FormsModule, ProjectCardComponent],
  templateUrl: './repertoire.component.html'
})
export class RepertoireComponent implements OnInit {
  private projectsService = inject(ProjectsService);
  private foldersService = inject(FoldersService);
  private teamsService = inject(TeamsService);
  private authService = inject(AuthService);
  private toastService = inject(ToastService);
  private router = inject(Router);

  projects: Project[] = [];
  folders: Folder[] = [];
  teams: Team[] = [];
  
  loadingProjects = true;
  loadingFolders = true;
  loadingTeams = false;

  activeFolderId: string | null = null;
  searchQuery = '';
  statusFilter = '';

  user$ = this.authService.currentUser$;

  // Modal Crear Proyecto
  isCreateModalOpen = false;
  isCreating = false;
  newProjectName = '';
  newProjectDesc = '';
  newProjectType: 'personal' | 'team' = 'personal';
  newProjectTeamId = '';
  newProjectColor = '#3b82f6';
  newProjectTags = '';

  colorOptions = [
    { label: 'Azul', value: '#3b82f6' },
    { label: 'Púrpura', value: '#8b5cf6' },
    { label: 'Verde', value: '#10b981' },
    { label: 'Ámbar', value: '#f59e0b' },
    { label: 'Rojo', value: '#ef4444' },
    { label: 'Cian', value: '#06b6d4' }
  ];

  ngOnInit() {
    this.loadFolders();
    this.loadProjects();
  }

  canCreateProject(role?: string): boolean {
    return role === 'admin' || role === 'scrum_master';
  }

  loadFolders() {
    this.loadingFolders = true;
    this.foldersService.getFolderTree().subscribe({
      next: (res) => {
        this.folders = res.data || [];
        this.loadingFolders = false;
      },
      error: () => {
        this.loadingFolders = false;
      }
    });
  }

  loadProjects() {
    this.loadingProjects = true;
    const filters: ProjectFilters = {};
    if (this.activeFolderId) filters.folder_id = this.activeFolderId;
    if (this.searchQuery) filters.search = this.searchQuery;
    if (this.statusFilter) filters.status = this.statusFilter;

    this.projectsService.getProjects(filters).subscribe({
      next: (res: any) => {
        this.projects = res.data?.items || res.data || [];
        this.loadingProjects = false;
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || err.message || 'Error cargando proyectos');
        this.loadingProjects = false;
      }
    });
  }

  openCreateModal() {
    this.newProjectName = '';
    this.newProjectDesc = '';
    this.newProjectType = 'personal';
    this.newProjectTeamId = '';
    this.newProjectColor = '#3b82f6';
    this.newProjectTags = '';
    this.isCreateModalOpen = true;

    this.loadingTeams = true;
    this.teamsService.getTeams().subscribe({
      next: (res) => {
        this.teams = res.data || [];
        if (this.teams.length > 0 && !this.newProjectTeamId) {
          this.newProjectTeamId = this.teams[0].id;
        }
        this.loadingTeams = false;
      },
      error: () => {
        this.loadingTeams = false;
      }
    });
  }

  closeCreateModal() {
    this.isCreateModalOpen = false;
  }

  setColor(color: string) {
    this.newProjectColor = color;
  }

  submitCreateProject() {
    const name = this.newProjectName.trim();
    if (!name) {
      this.toastService.error('El nombre del proyecto es obligatorio');
      return;
    }

    if (this.newProjectType === 'team' && !this.newProjectTeamId) {
      this.toastService.error('Debes seleccionar un equipo para el proyecto de equipo');
      return;
    }

    this.isCreating = true;
    const tags = this.newProjectTags
      ? this.newProjectTags.split(',').map(t => t.trim()).filter(Boolean)
      : [];

    const payload: CreateProjectDto = {
      name,
      description: this.newProjectDesc.trim(),
      type: this.newProjectType,
      team_id: this.newProjectType === 'team' ? this.newProjectTeamId : undefined,
      color_tag: this.newProjectColor,
      tags
    };

    this.projectsService.createProject(payload).subscribe({
      next: (res) => {
        this.isCreating = false;
        this.isCreateModalOpen = false;
        this.toastService.success('Proyecto creado exitosamente');
        this.loadProjects();
      },
      error: (err) => {
        this.isCreating = false;
        this.toastService.error(err.error?.detail || err.message || 'Error al crear el proyecto');
      }
    });
  }

  selectFolder(folderId: string | null) {
    this.activeFolderId = folderId;
    this.loadProjects();
  }

  onSearch() {
    this.loadProjects();
  }

  onFilterChange() {
    this.loadProjects();
  }

  viewProject(project: Project) {
    this.router.navigate(['/projects', project.id]);
  }

  editProject(project: Project) {
    this.router.navigate(['/projects', project.id, 'resumen']);
  }
}
