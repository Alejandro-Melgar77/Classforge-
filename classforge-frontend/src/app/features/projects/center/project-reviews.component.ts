import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { ProjectReviewsService } from '../services/project-reviews.service';
import { ProjectReview, ReviewDocument, VerdictType } from '../models/review.model';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-project-reviews',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="h-full flex flex-col gap-6 text-[var(--text-primary)]">
      
      <!-- Top Header & Upload Section -->
      <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-6 shadow-sm">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <span>📑</span>
              <span>Evaluador Inteligente Local de Proyectos</span>
            </h2>
            <p class="text-xs text-[var(--text-secondary)] mt-1 max-w-2xl">
              Analiza la documentación PDF de tu proyecto de software mediante IA local y rúbrica técnica formal (CF-SE-2026.1).
              Emite dictámenes verificables, detección de alucinaciones y pliegos de especificaciones.
            </p>
          </div>
          <div class="flex items-center gap-2">
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Motor Local Activo
            </span>
          </div>
        </div>

        <!-- Upload Drag & Drop Area -->
        <div
          class="border-2 border-dashed border-[var(--border)] hover:border-primary/60 rounded-xl p-6 text-center transition-colors bg-[var(--surface-3)]/40 flex flex-col items-center justify-center gap-3 cursor-pointer"
          (click)="fileInput.click()"
        >
          <input
            #fileInput
            type="file"
            accept=".pdf,application/pdf"
            class="hidden"
            (change)="onFileSelected($event)"
          />
          <div class="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xl">
            📄
          </div>
          <div>
            <p class="text-sm font-semibold text-white">
              {{ selectedFile() ? selectedFile()!.name : 'Haz clic para seleccionar o arrastra un documento PDF' }}
            </p>
            <p class="text-xs text-[var(--text-secondary)] mt-0.5">
              Tamaño máximo 25 MB • Hasta 300 páginas • Compatible con especificaciones y tesis
            </p>
          </div>

          <div *ngIf="selectedFile()" class="flex items-center gap-3 mt-2" (click)="$event.stopPropagation()">
            <span class="text-xs text-[var(--text-secondary)]">
              ({{ (selectedFile()!.size / (1024 * 1024)).toFixed(2) }} MB)
            </span>
            <button
              type="button"
              [disabled]="isEvaluating()"
              (click)="evaluateSelectedFile()"
              class="px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-bold rounded-xl shadow transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              <span *ngIf="isEvaluating()" class="w-3 h-3 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
              <span>{{ isEvaluating() ? 'Evaluando documento...' : 'Ejecutar Evaluación Técnica' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Reviews History Section -->
      <div class="flex-1 flex flex-col gap-4">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-white flex items-center gap-2">
            <span>📋</span>
            <span>Historial de Evaluaciones Técnicas ({{ reviews().length }})</span>
          </h3>
          <button
            type="button"
            (click)="loadReviews()"
            class="text-xs text-[var(--text-secondary)] hover:text-white px-2.5 py-1 rounded-lg bg-[var(--surface-3)] transition-colors cursor-pointer"
          >
            🔄 Actualizar
          </button>
        </div>

        <!-- Empty State -->
        <div
          *ngIf="reviews().length === 0 && !isLoading()"
          class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-12 text-center"
        >
          <div class="text-4xl mb-3">📂</div>
          <h4 class="text-sm font-bold text-white">Aún no hay evaluaciones registradas</h4>
          <p class="text-xs text-[var(--text-secondary)] mt-1 max-w-md mx-auto">
            Sube el primer documento PDF de especificación técnica o arquitectura de tu proyecto para recibir un dictamen inteligente.
          </p>
        </div>

        <!-- Reviews List -->
        <div *ngFor="let rev of reviews()" class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl overflow-hidden transition-all shadow-sm">
          
          <!-- Review Summary Row -->
          <div class="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[var(--surface-3)]/30">
            <div class="flex items-center gap-4">
              <div class="w-10 h-10 rounded-xl bg-[var(--surface-4)] border border-[var(--border)] flex items-center justify-center font-bold text-sm text-white shrink-0">
                #{{ rev.review_number }}
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2.5 flex-wrap">
                  <h4 class="text-sm font-bold text-white truncate max-w-md">
                    {{ rev.document_filename }}
                  </h4>
                  <span
                    class="px-2.5 py-0.5 rounded-full text-xs font-bold border"
                    [ngClass]="{
                      'bg-emerald-500/10 text-emerald-400 border-emerald-500/20': rev.verdict === 'APROBADO',
                      'bg-rose-500/10 text-rose-400 border-rose-500/20': rev.verdict === 'RECHAZADO',
                      'bg-amber-500/10 text-amber-400 border-amber-500/20': rev.verdict === 'INFORMACION_INSUFICIENTE'
                    }"
                  >
                    {{ rev.verdict || rev.status }}
                  </span>
                </div>
                <div class="flex items-center gap-3 text-xs text-[var(--text-secondary)] mt-1">
                  <span>📅 {{ rev.created_at | date:'yyyy-MM-dd HH:mm' }}</span>
                  <span>•</span>
                  <span>🤖 {{ rev.evaluated_by_model || 'Local Heuristic' }}</span>
                  <span *ngIf="rev.total_score !== null && rev.total_score !== undefined">•</span>
                  <span *ngIf="rev.total_score !== null && rev.total_score !== undefined" class="font-bold text-white">
                    Puntaje: {{ rev.total_score }} / 100
                  </span>
                </div>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="flex items-center gap-2 shrink-0">
              <button
                type="button"
                (click)="toggleExpand(rev.id)"
                class="px-3 py-1.5 rounded-xl bg-[var(--surface-4)] hover:bg-[var(--surface-4)]/80 text-xs text-white font-semibold transition-colors cursor-pointer"
              >
                {{ expandedReviewId() === rev.id ? 'Ocultar Detalle' : 'Ver Detalle' }}
              </button>

              <button
                *ngIf="rev.status === 'COMPLETED'"
                type="button"
                (click)="downloadReport(rev.id)"
                class="px-3 py-1.5 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                title="Descargar dictamen oficial en PDF"
              >
                <span>📥</span>
                <span>Dictamen PDF</span>
              </button>

              <button
                *ngIf="rev.verdict === 'APROBADO'"
                type="button"
                (click)="downloadSpecification(rev.id)"
                class="px-3 py-1.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                title="Descargar pliego de especificaciones técnicas"
              >
                <span>📐</span>
                <span>Pliego PDF</span>
              </button>
            </div>
          </div>

          <!-- Expanded Review Content -->
          <div *ngIf="expandedReviewId() === rev.id" class="p-6 border-t border-[var(--border)] flex flex-col gap-6 bg-[var(--surface-2)]">
            
            <!-- Summary Card -->
            <div
              *ngIf="rev.summary"
              class="p-4 rounded-xl border"
              [ngClass]="{
                'bg-emerald-500/5 border-emerald-500/20 text-emerald-200': rev.verdict === 'APROBADO',
                'bg-rose-500/5 border-rose-500/20 text-rose-200': rev.verdict === 'RECHAZADO',
                'bg-amber-500/5 border-amber-500/20 text-amber-200': rev.verdict === 'INFORMACION_INSUFICIENTE'
              }"
            >
              <h5 class="text-xs font-bold uppercase tracking-wider mb-1">Fundamentación del Dictamen</h5>
              <p class="text-xs leading-relaxed">{{ rev.summary }}</p>
            </div>

            <!-- Criteria Scores Grid -->
            <div>
              <h5 class="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-3">
                Desglose por Criterios de la Rúbrica
              </h5>
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                <div
                  *ngFor="let crit of rev.criteria_scores"
                  class="bg-[var(--surface-3)] border border-[var(--border)] rounded-xl p-4 flex flex-col justify-between"
                >
                  <div>
                    <div class="flex items-center justify-between mb-1.5">
                      <span class="text-xs font-bold text-white">{{ crit.name }}</span>
                      <span class="text-xs font-bold text-primary">{{ crit.score }} / 100</span>
                    </div>
                    <p class="text-[11px] text-[var(--text-secondary)] line-clamp-2">
                      {{ crit.observations || 'Sin observaciones adicionales.' }}
                    </p>
                  </div>
                  <div class="mt-3 pt-2 border-t border-[var(--border)]/50 flex items-center justify-between text-[10px] text-[var(--text-secondary)]">
                    <span>Peso: {{ crit.weight }}%</span>
                    <span *ngIf="crit.citations.length > 0">Págs: {{ crit.citations.join(', ') }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Recommendations Section -->
            <div *ngIf="rev.recommendations && rev.recommendations.length > 0">
              <h5 class="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-3">
                Recomendaciones Priorizadas
              </h5>
              <div class="flex flex-col gap-2">
                <div
                  *ngFor="let rec of rev.recommendations"
                  class="p-3.5 rounded-xl border bg-[var(--surface-3)] flex flex-col md:flex-row md:items-start justify-between gap-3"
                >
                  <div>
                    <div class="flex items-center gap-2">
                      <span
                        class="px-2 py-0.5 rounded text-[10px] font-bold"
                        [ngClass]="{
                          'bg-rose-500/20 text-rose-300': rec.priority === 'HIGH',
                          'bg-amber-500/20 text-amber-300': rec.priority === 'MEDIUM',
                          'bg-blue-500/20 text-blue-300': rec.priority === 'LOW'
                        }"
                      >
                        {{ rec.priority }}
                      </span>
                      <span class="text-xs font-bold text-white">{{ rec.title }}</span>
                    </div>
                    <p class="text-xs text-[var(--text-secondary)] mt-1">{{ rec.description }}</p>
                    <p class="text-xs text-primary/90 mt-1 font-medium">Plan sugerido: {{ rec.action_plan }}</p>
                  </div>
                </div>
              </div>
            </div>

          </div>

        </div>

      </div>

    </div>
  `
})
export class ProjectReviewsComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private reviewService = inject(ProjectReviewsService);
  private toast = inject(ToastService);

  projectId = signal<string>('');
  reviews = signal<ProjectReview[]>([]);
  isLoading = signal<boolean>(false);
  isEvaluating = signal<boolean>(false);
  selectedFile = signal<File | null>(null);
  expandedReviewId = signal<string | null>(null);

  ngOnInit(): void {
    // Retrieve projectId from parent route
    this.route.parent?.paramMap.subscribe(params => {
      const pid = params.get('projectId');
      if (pid) {
        this.projectId.set(pid);
        this.loadReviews();
      }
    });
  }

  loadReviews(): void {
    const pid = this.projectId();
    if (!pid) return;

    this.isLoading.set(true);
    this.reviewService.listReviews(pid).subscribe({
      next: res => {
        this.reviews.set(res.data?.items || []);
        this.isLoading.set(false);
      },
      error: err => {
        this.isLoading.set(false);
        this.toast.error('Error al cargar historial de evaluaciones');
      }
    });
  }

  onFileSelected(event: any): void {
    const file = event.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        this.toast.error('Solo se admiten documentos en formato PDF');
        return;
      }
      if (file.size > 25 * 1024 * 1024) {
        this.toast.error('El archivo excede el límite máximo de 25 MB');
        return;
      }
      this.selectedFile.set(file);
    }
  }

  evaluateSelectedFile(): void {
    const file = this.selectedFile();
    const pid = this.projectId();
    if (!file || !pid) return;

    this.isEvaluating.set(true);
    this.toast.info('Subiendo y extrayendo estructura del documento...');

    this.reviewService.uploadDocument(pid, file).subscribe({
      next: docRes => {
        const docId = docRes.data.id;
        this.toast.info('Ejecutando evaluación técnica inteligente con rúbrica...');
        this.reviewService.createReview(pid, docId).subscribe({
          next: revRes => {
            this.isEvaluating.set(false);
            this.selectedFile.set(null);
            this.toast.success(`Evaluación completada. Dictamen: ${revRes.data.verdict}`);
            this.loadReviews();
            this.expandedReviewId.set(revRes.data.id);
          },
          error: err => {
            this.isEvaluating.set(false);
            this.toast.error('Error durante la evaluación del documento');
          }
        });
      },
      error: err => {
        this.isEvaluating.set(false);
        this.toast.error('Error al subir el documento PDF');
      }
    });
  }

  toggleExpand(reviewId: string): void {
    if (this.expandedReviewId() === reviewId) {
      this.expandedReviewId.set(null);
    } else {
      this.expandedReviewId.set(reviewId);
    }
  }

  downloadReport(reviewId: string): void {
    const pid = this.projectId();
    if (!pid) return;

    this.toast.info('Descargando dictamen oficial en PDF...');
    this.reviewService.downloadReportPdf(pid, reviewId).subscribe({
      next: blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dictamen_evaluacion_${reviewId.substring(0, 8)}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: err => {
        this.toast.error('No se pudo descargar el informe PDF');
      }
    });
  }

  downloadSpecification(reviewId: string): void {
    const pid = this.projectId();
    if (!pid) return;

    this.toast.info('Descargando pliego de especificaciones técnicas...');
    this.reviewService.downloadSpecificationPdf(pid, reviewId).subscribe({
      next: blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pliego_especificaciones_${reviewId.substring(0, 8)}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: err => {
        this.toast.error('No se pudo descargar el pliego de especificaciones');
      }
    });
  }
}
