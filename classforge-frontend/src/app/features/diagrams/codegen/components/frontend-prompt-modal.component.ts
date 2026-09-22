import { Component, Input, Output, EventEmitter, inject, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CodegenService } from '../services/codegen.service';
import { FrontendFramework, FrontendTheme } from '../models/codegen.model';

interface FrameworkOption {
  id: FrontendFramework;
  name: string;
  category: 'mobile' | 'web';
  icon: string;
  badge: string;
  description: string;
}

@Component({
  selector: 'app-frontend-prompt-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div *ngIf="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      
      <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden text-[var(--text-primary)]">
        
        <!-- Header -->
        <div class="px-6 py-4 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-1)]">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-blue-500/30 flex items-center justify-center text-xl shadow-inner">
              🤖
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-base font-bold">Generador de Prompt para Aplicaciones Móviles y Web con IA</h2>
                <span class="px-2 py-0.5 text-[10px] font-semibold tracking-wide rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  ⚡ Determinista (<5ms)
                </span>
              </div>
              <p class="text-xs text-[var(--text-secondary)]">
                Genera la especificación completa para que <strong>Claude, ChatGPT, Gemini o Cursor</strong> construyan la app móvil (Flutter / React Native) o frontend exacto para tu backend Spring Boot 3.
              </p>
            </div>
          </div>

          <button (click)="close.emit()" class="p-2 text-[var(--text-secondary)] hover:text-white hover:bg-[var(--surface-3)] rounded-lg transition-colors">
            ✕
          </button>
        </div>

        <!-- Controls Bar: Frameworks & Themes -->
        <div class="px-6 py-3 border-b border-[var(--border)] bg-[var(--surface-2)] flex flex-col gap-3 text-sm">
          
          <!-- Category 1: Mobile Frameworks (Flutter & React Native) -->
          <div class="flex flex-wrap items-center gap-3">
            <span class="text-xs font-bold uppercase tracking-wider text-purple-400 flex items-center gap-1 shrink-0">
              📱 Móvil:
            </span>
            <div class="flex flex-wrap items-center gap-2">
              <button 
                *ngFor="let fw of mobileFrameworks" 
                (click)="selectFramework(fw.id)"
                class="px-3 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center gap-2 border shadow-xs"
                [ngClass]="selectedFramework === fw.id ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white border-purple-400 shadow-md' : 'bg-slate-800/80 text-slate-300 border-slate-700 hover:border-purple-500/50 hover:bg-slate-800'">
                <span>{{ fw.icon }}</span>
                <span>{{ fw.name }}</span>
                <span class="text-[9px] px-1.5 py-0.2 rounded-full"
                      [ngClass]="selectedFramework === fw.id ? 'bg-purple-900/60 text-purple-200' : 'bg-slate-700/50 text-slate-400'">
                  {{ fw.badge }}
                </span>
              </button>
            </div>
          </div>

          <!-- Category 2: Web Frameworks & Theme Controls -->
          <div class="flex flex-wrap items-center justify-between gap-4 pt-1 border-t border-[var(--border)]/60">
            <div class="flex flex-wrap items-center gap-3">
              <span class="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1 shrink-0">
                🌐 Web SPA:
              </span>
              <div class="flex flex-wrap items-center gap-1.5">
                <button 
                  *ngFor="let fw of webFrameworks" 
                  (click)="selectFramework(fw.id)"
                  class="px-2.5 py-1 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 border"
                  [ngClass]="selectedFramework === fw.id ? 'bg-blue-600 text-white border-blue-400 shadow-xs' : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:text-white hover:border-slate-600'">
                  <span>{{ fw.icon }}</span>
                  <span>{{ fw.name }}</span>
                </button>
              </div>
            </div>

            <!-- Visual Theme Selector -->
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-[11px] font-semibold text-slate-400">Tema UI:</span>
              <div class="flex items-center bg-[var(--surface-1)] p-0.5 rounded-lg border border-[var(--border)] gap-1">
                <button 
                  (click)="selectTheme('dark')"
                  class="px-2 py-0.5 text-xs font-medium rounded transition-all flex items-center gap-1"
                  [ngClass]="selectedTheme === 'dark' ? 'bg-slate-700 text-white shadow-xs' : 'text-slate-400 hover:text-slate-200'">
                  <span>🌙</span> Dark
                </button>
                <button 
                  (click)="selectTheme('light')"
                  class="px-2 py-0.5 text-xs font-medium rounded transition-all flex items-center gap-1"
                  [ngClass]="selectedTheme === 'light' ? 'bg-slate-700 text-white shadow-xs' : 'text-slate-400 hover:text-slate-200'">
                  <span>☀️</span> Light
                </button>
              </div>
            </div>
          </div>

        </div>

        <!-- Prompt Preview Body -->
        <div class="flex-1 p-5 overflow-hidden flex flex-col">
          
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">
              VISTA PREVIA DEL META-PROMPT GENERADO (MARKDOWN):
            </span>
            
            <div class="flex items-center gap-3">
              <span *ngIf="isLoading" class="text-xs text-blue-400 animate-pulse flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping"></span>
                Sintetizando arquitectura móvil y contratos REST...
              </span>
              <span *ngIf="!isLoading && promptData" class="text-xs text-slate-400 font-mono">
                {{ promptData.character_count }} caracteres · ~{{ promptData.estimated_tokens }} tokens
              </span>
            </div>
          </div>

          <!-- Monospace Code / Markdown Area -->
          <div class="flex-1 bg-[#141416] border border-[#26262e] rounded-xl p-4 overflow-y-auto font-mono text-xs text-slate-300 leading-relaxed select-text custom-scrollbar" style="font-family: 'JetBrains Mono', Consolas, monospace;">
            <div *ngIf="isLoading" class="flex flex-col gap-2 py-12 items-center justify-center text-slate-500">
              <div class="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
              <span>Generando meta-prompt determinista para {{ selectedFrameworkName }}...</span>
            </div>
            
            <pre *ngIf="!isLoading && promptData" class="whitespace-pre-wrap font-inherit m-0">{{ promptData.prompt }}</pre>
            
            <div *ngIf="!isLoading && !promptData" class="text-center py-12 text-slate-500">
              Presiona el botón para generar el prompt.
            </div>
          </div>

          <!-- Model recommendations info banner -->
          <div class="mt-3 px-3.5 py-2.5 bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-500/20 rounded-xl flex items-center justify-between text-xs text-purple-200">
            <div class="flex items-center gap-2">
              <span class="text-base">💡</span>
              <span><strong>Modelos Recomendados para Móvil & Web:</strong> Pega este prompt en <strong>Claude 3.5 Sonnet</strong>, <strong>GPT-4o</strong>, <strong>Gemini 1.5 Pro</strong> o <strong>Cursor</strong> para obtener el código fuente completo listo para producción.</span>
            </div>
          </div>

        </div>

        <!-- Footer / Action Buttons -->
        <div class="px-6 py-4 border-t border-[var(--border)] bg-[var(--surface-1)] flex items-center justify-between">
          <button (click)="close.emit()" class="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white hover:bg-[var(--surface-3)] rounded-lg transition-colors cursor-pointer">
            Cerrar
          </button>

          <div class="flex items-center gap-3">
            
            <!-- Download Prompt as .MD File -->
            <button 
              (click)="downloadPromptFile()"
              [disabled]="isLoading || !promptData"
              class="px-4 py-2 text-xs font-semibold rounded-lg flex items-center gap-2 bg-[var(--surface-3)] hover:bg-[var(--surface-4)] text-slate-200 border border-[var(--border)] transition-colors cursor-pointer disabled:opacity-50">
              <span>💾</span> Descargar (.MD)
            </button>

            <!-- Copy Prompt Button -->
            <button 
              (click)="copyPrompt()"
              [disabled]="isLoading || !promptData"
              class="px-5 py-2 text-xs font-bold rounded-lg flex items-center gap-2 transition-all shadow-lg cursor-pointer disabled:opacity-50"
              [ngClass]="copied ? 'bg-emerald-600 text-white border border-emerald-500' : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white border border-purple-400'">
              <span *ngIf="!copied">📋 Copiar Prompt para IA</span>
              <span *ngIf="copied" class="flex items-center gap-1.5 animate-bounce">✓ ¡Copiado al Portapapeles!</span>
            </button>

          </div>
        </div>

      </div>

    </div>
  `
})
export class FrontendPromptModalComponent implements OnChanges {
  @Input() isOpen = false;
  @Input() diagramId = '';
  /** Graph data snapshot from the active canvas */
  @Input() graphData: any = null;
  @Output() close = new EventEmitter<void>();

  private codegen = inject(CodegenService);

  selectedFramework: FrontendFramework = 'flutter';
  selectedTheme: FrontendTheme = 'dark';
  isLoading = false;
  copied = false;
  promptData: { prompt: string; character_count: number; estimated_tokens: number } | null = null;

  frameworks: FrameworkOption[] = [
    { id: 'flutter', name: 'Flutter 3 (Dart)', category: 'mobile', icon: '📱', badge: 'Riverpod + Dio', description: 'App móvil multiplataforma Android/iOS' },
    { id: 'react-native', name: 'React Native', category: 'mobile', icon: '⚛️', badge: 'Expo + Query', description: 'App móvil nativa con TypeScript' },
    { id: 'react', name: 'React 18+', category: 'web', icon: '⚡', badge: 'Vite + Tailwind', description: 'Single Page App moderna' },
    { id: 'angular', name: 'Angular 17+', category: 'web', icon: '🅰️', badge: 'Signals + RxJS', description: 'Enterprise SPA' },
    { id: 'vue', name: 'Vue 3', category: 'web', icon: '🟢', badge: 'Pinia + Vite', description: 'Composition API' },
    { id: 'vanilla', name: 'Vanilla JS', category: 'web', icon: '🌐', badge: 'HTML5 ES6', description: 'Sin frameworks' }
  ];

  get mobileFrameworks(): FrameworkOption[] {
    return this.frameworks.filter(f => f.category === 'mobile');
  }

  get webFrameworks(): FrameworkOption[] {
    return this.frameworks.filter(f => f.category === 'web');
  }

  get selectedFrameworkName(): string {
    return this.frameworks.find(f => f.id === this.selectedFramework)?.name || 'Framework';
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['isOpen'] && this.isOpen) {
      this.fetchPrompt();
    }
  }

  selectFramework(fw: FrontendFramework) {
    this.selectedFramework = fw;
    this.fetchPrompt();
  }

  selectTheme(theme: FrontendTheme) {
    this.selectedTheme = theme;
    this.fetchPrompt();
  }

  fetchPrompt() {
    if (!this.diagramId && !this.graphData) return;
    this.isLoading = true;
    this.copied = false;

    this.codegen.getFrontendPrompt(this.diagramId, {
      target_framework: this.selectedFramework,
      theme: this.selectedTheme,
      graph_data: this.graphData
    }).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.promptData = res.data;
        }
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      }
    });
  }

  copyPrompt() {
    if (this.promptData?.prompt) {
      navigator.clipboard.writeText(this.promptData.prompt).then(() => {
        this.copied = true;
        setTimeout(() => this.copied = false, 2500);
      });
    }
  }

  downloadPromptFile() {
    if (!this.promptData?.prompt) return;
    const blob = new Blob([this.promptData.prompt], { type: 'text/markdown;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `classforge-${this.selectedFramework}-prompt.md`;
    a.click();
    window.URL.revokeObjectURL(url);
  }
}

