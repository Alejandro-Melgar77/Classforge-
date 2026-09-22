import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProjectCardComponent } from './project-card.component';
import { ProjectsService, ProjectFilters } from '../services/projects.service';
import { FoldersService } from '../services/folders.service';
import { Project } from '../models/project.model';
import { Folder } from '../models/folder.model';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-repertoire',
  standalone: true,
  imports: [CommonModule, FormsModule, ProjectCardComponent],
  templateUrl: './repertoire.component.html'
})
export class RepertoireComponent implements OnInit {
  private projectsService = inject(ProjectsService);
  private foldersService = inject(FoldersService);
  private authService = inject(AuthService);

  projects: Project[] = [];
  folders: Folder[] = [];
  
  loadingProjects = true;
  loadingFolders = true;

  activeFolderId: string | null = null;
  searchQuery = '';
  statusFilter = '';

  user$ = this.authService.currentUser$;

  ngOnInit() {
    this.loadFolders();
    this.loadProjects();
  }

  loadFolders() {
    this.loadingFolders = true;
    this.foldersService.getFolderTree().subscribe({
      next: (res) => {
        this.folders = res.data || [];
        this.loadingFolders = false;
      },
      error: (err) => {
        console.error('Error loading folders', err);
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
      next: (res) => {
        this.projects = res.data || [];
        this.loadingProjects = false;
      },
      error: (err) => {
        console.error('Error loading projects', err);
        this.loadingProjects = false;
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
    // Navigate to UML canvas in future phase
    console.log('View project', project);
  }

  editProject(project: Project) {
    // Open edit modal
    console.log('Edit project', project);
  }
}
