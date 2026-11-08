import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ProjectReviewsService } from '../services/project-reviews.service';
import { DiagramService } from '../../diagrams/services/diagram.service';
import { Diagram } from '../../diagrams/models/diagram.model';
import { ToastService } from '../../../core/services/toast.service';
import {
  ProjectReview,
  LocalAiStatus,
  LocalAiChatMessage,
  LocalAiChatRequest,
  LocalAiChatResponse,
  LocalAiUiMessage,
} from '../models/review.model';

@Component({
  selector: 'app-project-reviews',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="h-full flex flex-col gap-5 text-[var(--text-primary)]">
      
      <!-- Top Header & Local Node Connection Bar -->
      <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-5 shadow-sm space-y-4">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <span class="text-xl">🤖</span>
              <span>Consola Inteligente de Arquitectura UML & IA Local</span>
            </h2>
            <p class="text-xs text-[var(--text-secondary)] mt-1 max-w-2xl">
              Motor de evaluación interactivo basado en <strong>Liquid AI LFM 1.7B</strong> sobre Ollama.
              Audita directamente los diagramas de clases UML 2.5+, valida restricciones formales (rúbrica CF-SE-2026.1) y emite pliegos técnicos sin requerir documentos PDF.
            </p>
          </div>

          <!-- Live Status Badge -->
          <div class="flex items-center gap-2">
            @if (localStatus()?.status === 'connected' || localStatus()?.online) {
              <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 shadow-sm">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>🟢 PC Local Conectada (Liquid LFM 1.7B Activo)</span>
                @if (localStatus()?.latency_ms !== undefined) {
                  <span class="text-[10px] bg-emerald-500/20 px-1.5 py-0.5 rounded text-emerald-300 font-mono">
                    {{ localStatus()?.latency_ms }} ms
                  </span>
                }
              </div>
            } @else {
              <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/25 shadow-sm">
                <span class="w-2 h-2 rounded-full bg-rose-400"></span>
                <span>🔴 PC Local Apagada / Túnel Desconectado</span>
              </div>
            }
          </div>
        </div>

        <!-- Connection Input Bar (Cloudflare / ngrok / localhost) -->
        <div class="pt-3 border-t border-[var(--border)]/70 flex flex-col sm:flex-row sm:items-center gap-3">
          <div class="flex items-center gap-2 text-xs font-medium text-[var(--text-secondary)] shrink-0">
            <span>🌐 URL del Nodo / Túnel:</span>
          </div>

          <div class="flex-1 flex items-center gap-2">
            <input
              type="text"
              [ngModel]="tunnelUrl()"
              (ngModelChange)="onTunnelUrlChange($event)"
              placeholder="http://localhost:11434 o https://tu-tunel.trycloudflare.com"
              class="flex-1 bg-[var(--surface-3)] border border-[var(--border)] focus:border-primary rounded-xl px-3.5 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none transition-colors"
            />
            <button
              type="button"
              [disabled]="isCheckingStatus()"
              (click)="testConnection()"
              class="px-4 py-2 bg-[var(--surface-4)] hover:bg-primary text-white text-xs font-semibold rounded-xl border border-[var(--border)] hover:border-primary transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50 shrink-0"
              title="Comprobar conectividad con Ollama y el modelo local"
            >
              @if (isCheckingStatus()) {
                <span class="w-3 h-3 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
                <span>Probando...</span>
              } @else {
                <span>⚡ Probar Conexión</span>
              }
            </button>
          </div>
        </div>

        @if (localStatus() && !localStatus()?.online) {
          <div class="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300 flex items-start gap-2">
            <span class="text-sm">⚠️</span>
            <div class="space-y-0.5">
              <p class="font-semibold">El nodo local de Ollama no responde en la URL indicada.</p>
              <p class="text-[11px] text-amber-300/80">
                Asegúrate de ejecutar <code>start_local_ai_tunnel.bat</code> en la PC de escritorio o iniciar Ollama con <code>ollama serve</code> y el modelo <code>classforge-local-1.7b</code>.
              </p>
            </div>
          </div>
        }
      </div>

      <!-- Action & Diagram Selector Toolbar -->
      <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex flex-col sm:flex-row sm:items-center gap-3 flex-1">
          <label class="text-xs font-semibold text-white flex items-center gap-1.5 shrink-0">
            <span>📐 Diagrama a Evaluar:</span>
          </label>
          <select
            [ngModel]="selectedDiagramId()"
            (ngModelChange)="selectedDiagramId.set($event)"
            class="bg-[var(--surface-3)] border border-[var(--border)] focus:border-primary text-xs text-white rounded-xl px-3 py-2 focus:outline-none max-w-md w-full"
          >
            <option value="all">📐 Todos los diagramas del proyecto (Esquema Completo)</option>
            @for (diag of diagrams(); track diag.id) {
              <option [value]="diag.id">
                📐 {{ diag.name }} (v{{ diag.version }} - {{ diag.status }})
              </option>
            }
          </select>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <button
            type="button"
            [disabled]="isEvaluating()"
            (click)="requestEvaluation()"
            class="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold rounded-xl shadow-md shadow-emerald-900/30 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            @if (isEvaluating()) {
              <span class="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
              <span>Analizando Arquitectura...</span>
            } @else {
              <span>⚡ Solicitar Evaluación y Visto Bueno</span>
            }
          </button>

          <button
            type="button"
            (click)="resetConversation()"
            class="px-3 py-2.5 bg-[var(--surface-3)] hover:bg-[var(--surface-4)] text-[var(--text-secondary)] hover:text-white rounded-xl text-xs font-medium border border-[var(--border)] transition-colors cursor-pointer"
            title="Reiniciar historial de la consola interactiva"
          >
            🔄 Limpiar Chat
          </button>
        </div>
      </div>

      <!-- Quick Action Prompt Suggestions -->
      <div class="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span class="text-[var(--text-muted)] text-[11px] uppercase tracking-wider font-bold shrink-0">Atajos rápidos:</span>
        <button
          type="button"
          (click)="sendQuickPrompt('Audita exhaustivamente las relaciones UML (asociación, agregación, composición, herencia) y verifica si existen relaciones muchos-a-muchos sin clase intermedia.')"
          class="px-3 py-1 rounded-lg bg-[var(--surface-3)] hover:bg-primary/20 hover:border-primary/40 text-[var(--text-secondary)] hover:text-white border border-[var(--border)] transition-all cursor-pointer whitespace-nowrap"
        >
          🔍 Auditar Relaciones y Multiplicidades
        </button>
        <button
          type="button"
          (click)="sendQuickPrompt('Genera el pliego de entidades relacionales de PostgreSQL con llaves primarias, foráneas e índices sugeridos según las clases del diagrama.')"
          class="px-3 py-1 rounded-lg bg-[var(--surface-3)] hover:bg-primary/20 hover:border-primary/40 text-[var(--text-secondary)] hover:text-white border border-[var(--border)] transition-all cursor-pointer whitespace-nowrap"
        >
          🗄️ Esquema SQL e Índices
        </button>
        <button
          type="button"
          (click)="sendQuickPrompt('Revisa los estereotipos de interfaz y métodos en los diagramas. ¿Se cumple el Principio de Segregación de Interfaces (ISP) e Inversión de Dependencias (DIP)?')"
          class="px-3 py-1 rounded-lg bg-[var(--surface-3)] hover:bg-primary/20 hover:border-primary/40 text-[var(--text-secondary)] hover:text-white border border-[var(--border)] transition-all cursor-pointer whitespace-nowrap"
        >
          🛡️ Principios SOLID y Cohesión
        </button>
      </div>

      <!-- Interactive Console & Chat Container -->
      <div class="flex-1 min-h-[460px] bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl flex flex-col overflow-hidden shadow-sm">
        
        <!-- Messages Scroll Area -->
        <div #scrollArea class="flex-1 p-6 overflow-y-auto space-y-6">
          
          @for (msg of messages(); track msg.id) {
            <!-- User Message -->
            @if (msg.role === 'user') {
              <div class="flex justify-end gap-3">
                <div class="max-w-2xl bg-primary/20 border border-primary/30 rounded-2xl rounded-tr-sm p-4 text-white text-xs leading-relaxed shadow-sm">
                  <div class="flex items-center justify-between gap-4 mb-1 text-[10px] text-primary-light">
                    <span class="font-bold">Tú</span>
                    <span>{{ msg.timestamp | date:'HH:mm:ss' }}</span>
                  </div>
                  <div class="whitespace-pre-wrap">{{ msg.content }}</div>
                </div>
                <div class="w-8 h-8 rounded-full bg-primary/30 border border-primary/50 text-white flex items-center justify-center font-bold text-xs shrink-0">
                  U
                </div>
              </div>
            }

            <!-- Assistant / Evaluation Message -->
            @if (msg.role === 'assistant') {
              <div class="flex justify-start gap-3">
                <div class="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 flex items-center justify-center font-bold text-xs shrink-0 mt-1">
                  🤖
                </div>
                
                <div class="max-w-3xl flex-1 bg-[var(--surface-3)]/80 border border-[var(--border)] rounded-2xl rounded-tl-sm p-5 space-y-4 text-white text-xs leading-relaxed shadow-sm">
                  
                  <div class="flex items-center justify-between text-[11px] border-b border-[var(--border)]/60 pb-2">
                    <div class="flex items-center gap-2">
                      <span class="font-bold text-emerald-400">ClassForge Local AI</span>
                      <span class="text-[10px] text-[var(--text-muted)] bg-[var(--surface-4)] px-2 py-0.5 rounded">Liquid LFM 1.7B</span>
                      @if (msg.evaluation?.latency_ms) {
                        <span class="text-[10px] text-[var(--text-muted)] font-mono">{{ msg.evaluation?.latency_ms }}ms</span>
                      }
                    </div>
                    <span class="text-[10px] text-[var(--text-muted)]">{{ msg.timestamp | date:'HH:mm:ss' }}</span>
                  </div>

                  <!-- Structured Evaluation Verdict Banner (if evaluation present) -->
                  @if (msg.evaluation) {
                    <div
                      class="p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-inner"
                      [ngClass]="{
                        'bg-emerald-500/15 border-emerald-500/40 text-emerald-200': msg.evaluation.verdict === 'APROBADO',
                        'bg-rose-500/15 border-rose-500/40 text-rose-200': msg.evaluation.verdict === 'RECHAZADO',
                        'bg-amber-500/15 border-amber-500/40 text-amber-200': msg.evaluation.verdict === 'INFORMACION_INSUFICIENTE'
                      }"
                    >
                      <div class="space-y-1">
                        <div class="flex items-center gap-2">
                          <span class="text-base">
                            {{ msg.evaluation.verdict === 'APROBADO' ? '✅' : (msg.evaluation.verdict === 'RECHAZADO' ? '❌' : '⚠️') }}
                          </span>
                          <span class="text-sm font-extrabold tracking-wide uppercase">
                            DICTAMEN: {{ msg.evaluation.verdict }}
                          </span>
                        </div>
                        <p class="text-[11px] opacity-90">
                          Rúbrica: CF-SE-2026.1 • Umbral de Aprobación: {{ msg.evaluation.passing_score }}/100
                        </p>
                      </div>

                      <div class="flex items-center gap-3">
                        <div class="text-right">
                          <div class="text-2xl font-black">
                            {{ msg.evaluation.total_score }} <span class="text-xs font-normal opacity-70">/ 100</span>
                          </div>
                          <div class="text-[10px] font-semibold uppercase tracking-wider">
                            Puntaje Final
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- Summary Statement -->
                    @if (msg.evaluation.summary) {
                      <div class="p-3.5 bg-[var(--surface-4)]/60 border border-[var(--border)] rounded-xl">
                        <div class="text-[10px] uppercase font-bold text-[var(--text-secondary)] mb-1">Fundamentación Técnica</div>
                        <p class="text-xs text-zinc-200 leading-relaxed">{{ msg.evaluation.summary }}</p>
                      </div>
                    }

                    <!-- Criteria Breakdown Grid -->
                    @if (msg.evaluation.criteria_scores && msg.evaluation.criteria_scores.length > 0) {
                      <div>
                        <div class="text-[10px] uppercase font-bold text-[var(--text-secondary)] mb-2">Desglose de Rúbrica Formal</div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                          @for (crit of msg.evaluation.criteria_scores; track crit.criterion_code) {
                            <div class="p-3 bg-[var(--surface-2)]/80 border border-[var(--border)]/80 rounded-xl space-y-1">
                              <div class="flex items-center justify-between text-xs font-semibold">
                                <span class="text-white truncate">{{ crit.name }}</span>
                                <span
                                  class="font-mono text-[11px] font-bold px-1.5 py-0.5 rounded"
                                  [ngClass]="crit.score >= 70 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'"
                                >
                                  {{ crit.score }}/100
                                </span>
                              </div>
                              <p class="text-[11px] text-[var(--text-secondary)] line-clamp-2">
                                {{ crit.observations || 'Evaluado satisfactoriamente sin observaciones críticas.' }}
                              </p>
                            </div>
                          }
                        </div>
                      </div>
                    }

                    <!-- RECHAZADO: Required Improvements Checklist -->
                    @if (msg.evaluation.verdict === 'RECHAZADO' && msg.evaluation.required_improvements.length > 0) {
                      <div class="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl space-y-2">
                        <div class="flex items-center gap-2 text-rose-400 font-bold text-xs uppercase tracking-wider">
                          <span>⚠️</span>
                          <span>Mejoras Necesarias para Obtener Aprobación</span>
                        </div>
                        <ul class="space-y-1.5 list-disc list-inside text-xs text-rose-200/90 pl-1">
                          @for (imp of msg.evaluation.required_improvements; track $index) {
                            <li class="leading-relaxed">{{ imp }}</li>
                          }
                        </ul>
                      </div>
                    }

                    <!-- APROBADO: Technical Specifications Accordion -->
                    @if (msg.evaluation.verdict === 'APROBADO' && msg.evaluation.technical_specification) {
                      <div class="border border-emerald-500/30 rounded-xl overflow-hidden bg-emerald-500/5">
                        <button
                          type="button"
                          (click)="toggleSpecs(msg.id)"
                          class="w-full p-3.5 flex items-center justify-between text-left text-xs font-bold text-emerald-300 hover:bg-emerald-500/10 transition-colors cursor-pointer"
                        >
                          <span class="flex items-center gap-2">
                            <span>📐</span>
                            <span>Especificaciones Técnicas Recomendadas (Pliego de Arquitectura & Base de Datos)</span>
                          </span>
                          <span class="text-xs">{{ isSpecsExpanded(msg.id) ? '▲ Ocultar' : '▼ Expandir Pliego' }}</span>
                        </button>

                        @if (isSpecsExpanded(msg.id)) {
                          <div class="p-4 border-t border-emerald-500/20 space-y-4 text-xs bg-[var(--surface-2)]/90">
                            
                            @if (msg.evaluation.technical_specification.system_architecture) {
                              <div>
                                <span class="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block mb-1">Arquitectura Recomendada</span>
                                <p class="text-zinc-300 leading-relaxed">{{ msg.evaluation.technical_specification.system_architecture }}</p>
                              </div>
                            }

                            <!-- REST Endpoints -->
                            @if (msg.evaluation.technical_specification.api_endpoints && msg.evaluation.technical_specification.api_endpoints.length > 0) {
                              <div>
                                <span class="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block mb-2">Contratos de Endpoints REST</span>
                                <div class="space-y-2">
                                  @for (ep of msg.evaluation.technical_specification.api_endpoints; track $index) {
                                    <div class="p-2.5 bg-[var(--surface-3)] border border-[var(--border)] rounded-lg font-mono text-[11px] flex flex-col gap-1">
                                      <div class="flex items-center gap-2">
                                        <span class="px-2 py-0.5 rounded font-bold text-[10px]"
                                          [ngClass]="{
                                            'bg-emerald-600/30 text-emerald-400': ep.method === 'GET',
                                            'bg-blue-600/30 text-blue-400': ep.method === 'POST',
                                            'bg-amber-600/30 text-amber-400': ep.method === 'PUT',
                                            'bg-rose-600/30 text-rose-400': ep.method === 'DELETE'
                                          }"
                                        >{{ ep.method }}</span>
                                        <span class="text-white">{{ ep.path }}</span>
                                      </div>
                                      <div class="text-[10px] text-[var(--text-secondary)] font-sans mt-0.5">
                                        {{ ep.description }}
                                      </div>
                                    </div>
                                  }
                                </div>
                              </div>
                            }

                            <!-- Database Entities / Data Model -->
                            @if (msg.evaluation.technical_specification.data_model && msg.evaluation.technical_specification.data_model.length > 0) {
                              <div>
                                <span class="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block mb-2">Entidades Relacionales e Índices</span>
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                                  @for (ent of msg.evaluation.technical_specification.data_model; track $index) {
                                    <div class="p-3 bg-[var(--surface-3)] border border-[var(--border)] rounded-xl space-y-1.5 font-mono text-[11px]">
                                      <div class="text-xs font-bold text-primary-light flex items-center justify-between">
                                        <span>📊 {{ ent.name }}</span>
                                      </div>
                                      <div class="text-[10px] text-zinc-300 font-sans">
                                        Atributos: {{ ent.attributes.join(', ') }}
                                      </div>
                                      @if (ent.relationships && ent.relationships.length > 0) {
                                        <div class="text-[10px] text-amber-300/80 font-mono">
                                          Relaciones: {{ ent.relationships.join(', ') }}
                                        </div>
                                      }
                                    </div>
                                  }
                                </div>
                              </div>
                            }

                          </div>
                        }
                      </div>
                    }

                  }

                  <!-- Conversational Assistant Message Body -->
                  @if (msg.content) {
                    <div class="text-xs text-zinc-200 whitespace-pre-wrap leading-relaxed">
                      {{ msg.content }}
                    </div>
                  }

                </div>
              </div>
            }
          }

          <!-- Thinking Spinner / Loading State -->
          @if (isEvaluating()) {
            <div class="flex justify-start gap-3 animate-fade-in">
              <div class="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 flex items-center justify-center font-bold text-xs shrink-0">
                🤖
              </div>
              <div class="bg-[var(--surface-3)]/80 border border-[var(--border)] rounded-2xl rounded-tl-sm p-4 text-xs text-zinc-300 flex items-center gap-3">
                <span class="w-4 h-4 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin"></span>
                <span class="font-medium">
                  Liquid AI LFM 1.7B está analizando la topología UML y ejecutando la rúbrica CF-SE-2026.1...
                </span>
              </div>
            </div>
          }

        </div>

        <!-- Chat Input Footer -->
        <div class="p-4 bg-[var(--surface-3)]/40 border-t border-[var(--border)] flex flex-col gap-2">
          <div class="flex items-end gap-3">
            <textarea
              rows="2"
              [ngModel]="inputMessage()"
              (ngModelChange)="inputMessage.set($event)"
              (keydown.enter)="$event.preventDefault(); sendMessage()"
              placeholder="Haz una consulta a la IA local sobre el diseño UML, pide aclaraciones o solicita cambios de arquitectura (Presiona Enter para enviar)..."
              class="flex-1 bg-[var(--surface-2)] border border-[var(--border)] focus:border-primary rounded-xl p-3 text-xs text-white placeholder-zinc-500 focus:outline-none resize-none transition-colors"
            ></textarea>

            <button
              type="button"
              [disabled]="isEvaluating() || !inputMessage().trim()"
              (click)="sendMessage()"
              class="px-5 py-3 bg-primary hover:bg-primary-hover text-white text-xs font-bold rounded-xl shadow-md transition-all flex items-center gap-2 cursor-pointer disabled:opacity-40 h-[46px] shrink-0"
            >
              @if (isEvaluating()) {
                <span class="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
              } @else {
                <span>Enviar</span>
                <span>➤</span>
              }
            </button>
          </div>
          <div class="flex items-center justify-between text-[10px] text-[var(--text-muted)] px-1">
            <span>Usa <strong>Shift + Enter</strong> para salto de línea.</span>
            <span>Nodo: Liquid AI LFM 1.7B GGUF • Ollama Local/Túnel</span>
          </div>
        </div>

      </div>

    </div>
  `
})
export class ProjectReviewsComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private reviewService = inject(ProjectReviewsService);
  private diagramService = inject(DiagramService);
  private toast = inject(ToastService);

  projectId = signal<string>('');
  diagrams = signal<Diagram[]>([]);
  selectedDiagramId = signal<string>('all');
  tunnelUrl = signal<string>(localStorage.getItem('classforge_local_ai_url') || 'https://repackage-remarry-reviving.ngrok-free.dev');
  
  localStatus = signal<LocalAiStatus | null>(null);
  isCheckingStatus = signal<boolean>(false);
  isEvaluating = signal<boolean>(false);
  
  inputMessage = signal<string>('');
  messages = signal<LocalAiUiMessage[]>([]);
  expandedSpecs = signal<{ [msgId: string]: boolean }>({});

  ngOnInit(): void {
    this.route.parent?.paramMap.subscribe(params => {
      const pid = params.get('projectId');
      if (pid) {
        this.projectId.set(pid);
        this.loadProjectDiagrams(pid);
      }
    });

    // Check status on startup
    this.testConnection();

    // Initial greeting from Local AI
    this.messages.set([
      {
        id: 'msg-welcome',
        role: 'assistant',
        content: '👋 ¡Hola! Soy el Gestor y Aprobador Inteligente de Arquitectura UML impulsado por Liquid AI LFM 1.7B en tu nodo local.\n\nAudito directamente la topología de tus diagramas UML 2.5+ (clases, interfaces, atributos tipados, métodos, relaciones y multiplicidades) contra la rúbrica técnica formal CF-SE-2026.1, emito dictámenes de APROBADO/RECHAZADO con pliegos de arquitectura o mejoras requeridas, y respondo tus preguntas técnicas interactivamente.\n\nSelecciona un diagrama o el esquema completo arriba y haz clic en "⚡ Solicitar Evaluación y Visto Bueno" para iniciar.',
        timestamp: new Date(),
      }
    ]);
  }

  onTunnelUrlChange(newUrl: string): void {
    this.tunnelUrl.set(newUrl);
    localStorage.setItem('classforge_local_ai_url', newUrl);
  }

  loadProjectDiagrams(pid: string): void {
    this.diagramService.getDiagrams({ project_id: pid }).subscribe({
      next: res => {
        this.diagrams.set(res.data || []);
      },
      error: () => {
        this.toast.error('No se pudieron cargar los diagramas del proyecto');
      }
    });
  }

  testConnection(): void {
    const url = this.tunnelUrl().trim();
    this.isCheckingStatus.set(true);

    this.reviewService.checkLocalStatus(url).subscribe({
      next: status => {
        this.localStatus.set(status);
        this.isCheckingStatus.set(false);
        if (status.online) {
          this.toast.success(`Nodo local en línea (${status.model}) • ${status.latency_ms ?? 0} ms`);
        } else {
          this.toast.warning('Nodo local desconectado o no accesible en la URL indicada');
        }
      },
      error: err => {
        this.isCheckingStatus.set(false);
        this.localStatus.set({
          online: false,
          model: 'classforge-local-1.7b',
          installed_models: [],
          is_classforge_local_active: false,
          url: url,
          status: 'disconnected',
          error: err?.message || 'Error de conexión',
        });
        this.toast.error('No se pudo verificar el estado del nodo local');
      }
    });
  }

  requestEvaluation(): void {
    const prompt = 'Por favor evalúa la arquitectura UML 2.5+ del proyecto según la rúbrica técnica formal CF-SE-2026.1 y emite tu veredicto (APROBADO o RECHAZADO) con especificaciones técnicas o mejoras requeridas.';
    this.executeEvaluationAndChat(prompt);
  }

  sendQuickPrompt(promptText: string): void {
    this.executeEvaluationAndChat(promptText);
  }

  sendMessage(): void {
    const text = this.inputMessage().trim();
    if (!text || this.isEvaluating()) return;
    this.inputMessage.set('');
    this.executeEvaluationAndChat(text);
  }

  private executeEvaluationAndChat(userText: string): void {
    const pid = this.projectId();
    if (!pid) {
      this.toast.error('ID del proyecto no encontrado');
      return;
    }

    const userMsg: LocalAiUiMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userText,
      timestamp: new Date(),
    };

    this.messages.update(msgs => [...msgs, userMsg]);
    this.isEvaluating.set(true);

    const history: LocalAiChatMessage[] = this.messages()
      .filter(m => m.id !== 'msg-welcome')
      .map(m => ({
        role: m.role,
        content: m.content,
      }));

    const diagId = this.selectedDiagramId();
    const req: LocalAiChatRequest = {
      diagram_id: diagId !== 'all' ? diagId : undefined,
      message: userText,
      session_history: history,
      tunnel_url: this.tunnelUrl().trim() || undefined,
    };

    this.reviewService.evaluateAndChat(pid, req, this.tunnelUrl().trim()).subscribe({
      next: res => {
        this.isEvaluating.set(false);
        const evalData = res.data;

        const assistantMsg: LocalAiUiMessage = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: evalData.assistant_message || '',
          timestamp: new Date(),
          evaluation: evalData,
        };

        this.messages.update(msgs => [...msgs, assistantMsg]);

        // Auto-expand specs if approved
        if (evalData.verdict === 'APROBADO') {
          this.expandedSpecs.update(s => ({ ...s, [assistantMsg.id]: true }));
          this.toast.success(`¡Proyecto APROBADO con puntuación ${evalData.total_score}/100!`);
        } else if (evalData.verdict === 'RECHAZADO') {
          this.toast.warning(`Proyecto RECHAZADO (${evalData.total_score}/100). Revisa las mejoras requeridas.`);
        } else {
          this.toast.info('Evaluación procesada por el modelo local');
        }
      },
      error: err => {
        this.isEvaluating.set(false);
        const errDetail = err?.error?.detail || err?.message || 'Error al comunicarse con la IA local';
        this.toast.error(`Error: ${errDetail}`);

        const errorMsg: LocalAiUiMessage = {
          id: `asst-err-${Date.now()}`,
          role: 'assistant',
          content: `❌ Hubo un error al procesar la solicitud con el modelo local: ${errDetail}\n\nVerifica que Ollama esté corriendo con \`classforge-local-1.7b\` y que la URL del nodo sea correcta.`,
          timestamp: new Date(),
        };
        this.messages.update(msgs => [...msgs, errorMsg]);
      }
    });
  }

  toggleSpecs(msgId: string): void {
    this.expandedSpecs.update(s => ({ ...s, [msgId]: !s[msgId] }));
  }

  isSpecsExpanded(msgId: string): boolean {
    return !!this.expandedSpecs()[msgId];
  }

  resetConversation(): void {
    this.messages.set([
      {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: 'Conversación reiniciada. ¿En qué aspecto de los diagramas o la arquitectura te gustaría trabajar ahora?',
        timestamp: new Date(),
      }
    ]);
    this.toast.info('Historial de conversación reiniciado');
  }
}
