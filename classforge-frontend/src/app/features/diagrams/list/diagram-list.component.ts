import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { DiagramService } from '../services/diagram.service';
import { TeamsService } from '../../projects/services/teams.service';
import { AuthService } from '../../../core/services/auth.service';
import { Diagram, ParticipantItem, DiagramParticipantsResponse } from '../models/diagram.model';
import { Team } from '../../projects/models/team.model';
import { FormsModule } from '@angular/forms';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmDialogService } from '../../../core/services/confirm-dialog.service';

@Component({
  selector: 'diagram-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './diagram-list.component.html',
})
export class DiagramListComponent implements OnInit {
  private diagramService = inject(DiagramService);
  private teamsService = inject(TeamsService);
  public authService = inject(AuthService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmDialogService);
  private router = inject(Router);

  diagrams: Diagram[] = [];
  teams: Team[] = [];
  
  statusFilter = '';
  searchQuery = '';
  isLoading = false;
  isSaving = false;
  errorMessage = '';

  // ═══ Create / Edit Modal State ═══
  isDiagramModalOpen = false;
  isEditMode = false;
  editingDiagramId: string | null = null;
  
  diagramForm = {
    name: '',
    description: '',
    image_url: '' as string | null,
    team_id: '' as string | null,
    member_ids: [] as string[]
  };
  logoPreview: string | null = null;
  selectedTeamMembers: ParticipantItem[] = [];

  // ═══ Participants Modal State ═══
  isParticipantsModalOpen = false;
  activeDiagramForParticipants: Diagram | null = null;
  participantsLoading = false;
  participantsData: DiagramParticipantsResponse | null = null;
  selectedParticipantIds = new Set<string>();

  get currentUser() {
    return this.authService.getCurrentUser();
  }

  get isAdmin(): boolean {
    return this.authService.hasRole('admin');
  }

  get isScrumMaster(): boolean {
    return this.authService.hasRole('scrum_master');
  }

  get canCreateOrManage(): boolean {
    return this.isAdmin || this.isScrumMaster;
  }

  ngOnInit() {
    this.loadDiagrams();
    this.loadTeams();
  }

  loadDiagrams() {
    this.isLoading = true;
    this.diagramService.getDiagrams(this.statusFilter ? { status: this.statusFilter } : {}).subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.success && res.data) {
          const items = Array.isArray(res.data) ? res.data : ((res.data as any).items || []);
          this.diagrams = items;
        } else {
          this.diagrams = [];
        }
      },
      error: (err) => {
        this.isLoading = false;
        console.error('Error al cargar diagramas:', err);
        this.diagrams = [];
      }
    });
  }

  loadTeams() {
    if (!this.canCreateOrManage) return;
    this.teamsService.getTeams().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.teams = res.data;
        }
      },
      error: (err) => console.error('Error al cargar equipos:', err)
    });
  }

  get filteredDiagrams(): Diagram[] {
    let list = this.diagrams;
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase().trim();
      list = list.filter(d => 
        (d.name && d.name.toLowerCase().includes(q)) ||
        (d.description && d.description.toLowerCase().includes(q)) ||
        (d.team_name && d.team_name.toLowerCase().includes(q))
      );
    }
    return list;
  }

  // ═══ Modal: Create & Edit Diagram ═══

  openCreateModal() {
    this.isEditMode = false;
    this.editingDiagramId = null;
    const count = this.diagrams.length + 1;
    this.diagramForm = {
      name: `Proyecto ${count} - Empresa`,
      description: 'Lienzo de modelado conceptual UML para arquitectura de software',
      image_url: null,
      team_id: this.teams.length > 0 ? this.teams[0].id : null,
      member_ids: []
    };
    this.logoPreview = null;
    this.selectedTeamMembers = [];
    this.isDiagramModalOpen = true;
    this.onTeamSelected();
  }

  openEditModal(diagram: Diagram, event?: Event) {
    if (event) event.stopPropagation();
    this.isEditMode = true;
    this.editingDiagramId = diagram.id;
    this.diagramForm = {
      name: diagram.name || '',
      description: diagram.description || '',
      image_url: diagram.image_url || null,
      team_id: diagram.team_id || null,
      member_ids: diagram.member_ids ? [...diagram.member_ids] : []
    };
    this.logoPreview = diagram.image_url || null;
    this.isDiagramModalOpen = true;
    this.loadTeamMembersForDiagram(diagram.id);
  }

  closeDiagramModal() {
    this.isDiagramModalOpen = false;
    this.isEditMode = false;
    this.editingDiagramId = null;
    this.logoPreview = null;
  }

  onLogoFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file = input.files[0];
      if (file.size > 3 * 1024 * 1024) {
        alert('La imagen seleccionada no debe superar los 3MB.');
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result as string;
        this.diagramForm.image_url = base64;
        this.logoPreview = base64;
      };
      reader.readAsDataURL(file);
    }
  }

  removeLogo() {
    this.diagramForm.image_url = null;
    this.logoPreview = null;
  }

  onTeamSelected() {
    if (!this.diagramForm.team_id) {
      this.selectedTeamMembers = [];
      return;
    }
    // We can load participants for the selected team
    // Or if creating, we can initialize selected member_ids
  }

  loadTeamMembersForDiagram(diagramId: string) {
    this.diagramService.getParticipants(diagramId).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.selectedTeamMembers = res.data.available_members || [];
        }
      }
    });
  }

  saveDiagramModal() {
    if (!this.diagramForm.name.trim()) {
      this.toastService.error('Por favor ingrese un nombre para el diagrama');
      return;
    }

    this.isSaving = true;

    if (this.isEditMode && this.editingDiagramId) {
      this.diagramService.updateDiagram(this.editingDiagramId, {
        name: this.diagramForm.name.trim(),
        description: this.diagramForm.description?.trim(),
        image_url: this.diagramForm.image_url,
        team_id: this.diagramForm.team_id || null
      }).subscribe({
        next: (res) => {
          this.isSaving = false;
          if (res.success) {
            this.toastService.success('Diagrama actualizado');
            this.closeDiagramModal();
            this.loadDiagrams();
          } else {
            this.toastService.error(res.message || 'Error al actualizar diagrama');
          }
        },
        error: (err) => {
          this.isSaving = false;
          this.toastService.error(err.error?.detail || err.message || 'Error al actualizar diagrama');
        }
      });
    } else {
      this.diagramService.createDiagram({
        name: this.diagramForm.name.trim(),
        description: this.diagramForm.description?.trim(),
        image_url: this.diagramForm.image_url,
        team_id: this.diagramForm.team_id || null,
        member_ids: this.diagramForm.member_ids
      }).subscribe({
        next: (res) => {
          this.isSaving = false;
          if (res.success && res.data) {
            this.toastService.success('Diagrama creado exitosamente');
            this.closeDiagramModal();
            const newId = res.data.id || (res.data as any)._id;
            this.router.navigate(['/diagrams', newId]);
          } else {
            this.toastService.error(res.message || 'Error al crear diagrama');
            this.loadDiagrams();
          }
        },
        error: (err) => {
          this.isSaving = false;
          this.toastService.error(err.error?.detail || err.message || 'Error al crear diagrama');
        }
      });
    }
  }

  // ═══ Modal: Manage Participants ═══

  openParticipantsModal(diagram: Diagram, event?: Event) {
    if (event) event.stopPropagation();
    this.activeDiagramForParticipants = diagram;
    this.isParticipantsModalOpen = true;
    this.participantsLoading = true;
    this.selectedParticipantIds.clear();

    this.diagramService.getParticipants(diagram.id).subscribe({
      next: (res) => {
        this.participantsLoading = false;
        if (res.success && res.data) {
          this.participantsData = res.data;
          const assigned = res.data.assigned_member_ids || [];
          this.selectedParticipantIds = new Set(assigned);
        }
      },
      error: (err) => {
        this.participantsLoading = false;
        this.toastService.error(err.error?.detail || err.message || 'Error al obtener participantes');
      }
    });
  }

  closeParticipantsModal() {
    this.isParticipantsModalOpen = false;
    this.activeDiagramForParticipants = null;
    this.participantsData = null;
    this.selectedParticipantIds.clear();
  }

  toggleParticipant(memberId: string) {
    if (this.selectedParticipantIds.has(memberId)) {
      this.selectedParticipantIds.delete(memberId);
    } else {
      this.selectedParticipantIds.add(memberId);
    }
  }

  saveParticipants() {
    if (!this.activeDiagramForParticipants) return;
    this.isSaving = true;
    const memberIds = Array.from(this.selectedParticipantIds);

    this.diagramService.updateParticipants(this.activeDiagramForParticipants.id, memberIds).subscribe({
      next: (res) => {
        this.isSaving = false;
        if (res.success) {
          this.toastService.success('Participantes actualizados');
          this.closeParticipantsModal();
          this.loadDiagrams();
        } else {
          this.toastService.error(res.message || 'Error al actualizar participantes');
        }
      },
      error: (err) => {
        this.isSaving = false;
        this.toastService.error(err.error?.detail || err.message || 'Error al guardar participantes');
      }
    });
  }

  // ═══ Actions ═══

  async deleteDiagram(diagram: Diagram, event?: Event) {
    if (event) event.stopPropagation();
    const confirmed = await this.confirmService.confirm({
      title: '¿Eliminar diagrama?',
      message: `¿Está seguro de que desea eliminar el diagrama "${diagram.name}"? Esta acción no se puede deshacer.`,
      confirmText: 'Eliminar Diagrama',
      danger: true
    });
    if (!confirmed) return;

    this.diagramService.deleteDiagram(diagram.id).subscribe({
      next: (res) => {
        if (res.success) {
          this.toastService.success('Diagrama eliminado');
          this.loadDiagrams();
        } else {
          this.toastService.error(res.message || 'Error al eliminar diagrama');
        }
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || err.message || 'Error al eliminar diagrama');
      }
    });
  }

  openDiagram(diagramId: string) {
    if (diagramId) {
      this.router.navigate(['/diagrams', diagramId]);
    }
  }
}
