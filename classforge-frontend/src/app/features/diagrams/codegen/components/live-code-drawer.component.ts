import { Component, Input, Output, EventEmitter, inject, HostListener, OnInit, OnChanges, SimpleChanges, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CodegenService } from '../services/codegen.service';
import { FileTreeComponent } from './file-tree.component';
import { ActivatedRoute } from '@angular/router';
import { CodegenEngine } from '../models/codegen.model';

@Component({
  selector: 'app-live-code-drawer',
  standalone: true,
  imports: [CommonModule, FormsModule, FileTreeComponent],
  template: `
    <div 
      class="fixed inset-y-0 right-0 z-50 bg-[var(--surface-1)] border-l border-[var(--border)] shadow-2xl flex flex-col transition-all select-none"
      [class.translate-x-0]="isOpen"
      [class.translate-x-full]="!isOpen"
      [style.width]="isMaximized ? '100vw' : drawerWidth + 'px'"
      [style.minWidth]="isMaximized ? '100vw' : '520px'">
      
      <!-- ═══ DRAWER RESIZE HANDLE (Left Edge) ═══ -->
      <div 
        *ngIf="!isMaximized"
        (mousedown)="startDrawerResize($event)"
        class="absolute -left-1.5 inset-y-0 w-3 cursor-ew-resize hover:bg-blue-500/50 active:bg-blue-600 transition-colors z-50 flex items-center justify-center group"
        title="Arrastra para cambiar el ancho del panel">
        <div class="w-1 h-8 rounded-full bg-slate-500/40 group-hover:bg-blue-400 group-active:bg-white transition-colors"></div>
      </div>

      <!-- ═══ HEADER BAR ═══ -->
      <div class="h-14 border-b border-[var(--border)] bg-[var(--surface-2)] flex items-center justify-between px-4 shrink-0 gap-3">
        
        <!-- Left Title & Badges -->
        <div class="flex items-center gap-2.5 overflow-hidden">
          <div class="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-base shrink-0">
            💻
          </div>

          <div class="flex flex-col overflow-hidden">
            <div class="flex items-center gap-2">
              <h2 class="text-sm font-bold text-[var(--text-primary)] truncate">
                Código Spring Boot 3 en Vivo
              </h2>
              
              <!-- Sync Indicator -->
              <span *ngIf="!codegen.isLoading()" class="px-2 py-0.5 text-[10px] font-semibold tracking-wide rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1 shrink-0">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Sincronizado
              </span>
              
              <span *ngIf="codegen.isLoading()" class="px-2 py-0.5 text-[10px] font-semibold tracking-wide rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1 shrink-0 animate-pulse">
                <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping"></span>
                Generando...
              </span>
            </div>

            <!-- Meta subtext -->
            <div class="flex items-center gap-2 text-[10px] text-slate-400">
              <span>Java 17 · Spring Boot 3.3.3 · Clean Architecture</span>
              <span>•</span>
              <span class="font-mono text-emerald-400">{{ filePaths.length }} archivos generados</span>
            </div>
          </div>
        </div>

        <!-- Right Header Actions -->
        <div class="flex items-center gap-2 shrink-0">
          
          <!-- Download ZIP Button -->
          <button 
            (click)="downloadProject()"
            [disabled]="isDownloadingZip || filePaths.length === 0"
            class="px-3.5 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-md hover:shadow-lg transition-all flex items-center gap-1.5 cursor-pointer">
            <span *ngIf="!isDownloadingZip">⬇️ Descargar (.ZIP)</span>
            <span *ngIf="isDownloadingZip" class="flex items-center gap-1">
              <span class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              Comprimiendo...
            </span>
          </button>

          <!-- Maximize / Restore Toggle -->
          <button 
            (click)="toggleMaximize()" 
            class="p-2 text-slate-400 hover:text-white hover:bg-[var(--surface-3)] rounded-lg transition-colors text-xs"
            [title]="isMaximized ? 'Restaurar tamaño' : 'Pantalla completa'">
            {{ isMaximized ? '🗗' : '🗖' }}
          </button>
          
          <!-- Close Button -->
          <button 
            (click)="close.emit()" 
            class="p-2 text-slate-400 hover:text-white hover:bg-[var(--surface-3)] rounded-lg transition-colors text-sm"
            title="Cerrar panel de código">
            ✕
          </button>
        </div>

      </div>

      <!-- ═══ SUB-HEADER: ENGINE CONTROLS & AI SETTINGS ═══ -->
      <div class="px-4 py-2 bg-[var(--surface-1)] border-b border-[var(--border)] flex flex-wrap items-center justify-between gap-3 text-xs shrink-0">
        
        <!-- Left: Engine Selector Toggle -->
        <div class="flex items-center gap-2">
          <span class="text-[11px] font-semibold text-slate-400">Motor de Generación:</span>
          <div class="flex items-center bg-[var(--surface-2)] p-0.5 rounded-lg border border-[var(--border)]">
            <button 
              (click)="setEngine('gemini')"
              class="px-2.5 py-1 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 cursor-pointer"
              [ngClass]="codegen.activeEngine() === 'gemini' ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-xs' : 'text-slate-400 hover:text-white'">
              <span>🧠</span>
              <span>IA Gemini Pro</span>
              <span class="text-[9px] px-1 py-0.2 bg-purple-900/60 text-purple-200 rounded-full font-mono">Semántico</span>
            </button>
            
            <button 
              (click)="setEngine('deterministic')"
              class="px-2.5 py-1 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 cursor-pointer"
              [ngClass]="codegen.activeEngine() === 'deterministic' ? 'bg-blue-600 text-white shadow-xs' : 'text-slate-400 hover:text-white'">
              <span>⚡</span>
              <span>Determinista</span>
              <span class="text-[9px] px-1 py-0.2 bg-blue-900/60 text-blue-200 rounded-full font-mono">Rápido</span>
            </button>
          </div>
          
          <!-- Gemini Settings Button -->
          <button 
            *ngIf="codegen.activeEngine() === 'gemini'"
            (click)="openSettingsModal()"
            class="px-2 py-1 bg-[var(--surface-2)] hover:bg-[var(--surface-3)] text-slate-300 hover:text-white rounded-lg border border-[var(--border)] transition-colors cursor-pointer flex items-center gap-1.5"
            title="Configurar clave de API y modelo de Gemini">
            <span>⚙️</span>
            <span class="text-[10px] font-mono text-purple-300">{{ codegen.geminiModel() }}</span>
          </button>
        </div>

        <!-- Right: Active Engine Badge & Regenerate Button -->
        <div class="flex items-center gap-2">
          <!-- Active Engine Badge -->
          <span class="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
            <span class="w-1.5 h-1.5 rounded-full" [ngClass]="codegen.activeEngine() === 'gemini' ? 'bg-purple-400 animate-pulse' : 'bg-blue-400'"></span>
            {{ codegen.engineUsed() }}
          </span>

          <button 
            (click)="regenerate()"
            [disabled]="codegen.isLoading()"
            class="px-3 py-1 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow transition-all flex items-center gap-1 cursor-pointer">
            <span *ngIf="!codegen.isLoading()">🔄 Regenerar</span>
            <span *ngIf="codegen.isLoading()" class="flex items-center gap-1">
              <span class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              Generando...
            </span>
          </button>
        </div>

      </div>

      <!-- ═══ BODY (SPLIT VIEW) ═══ -->
      <div class="flex-1 flex overflow-hidden relative">
        
        <!-- Left Pane: File Tree -->
        <div 
          class="shrink-0 bg-[var(--surface-2)] overflow-hidden flex flex-col p-2.5"
          [style.width]="treeWidth + 'px'">
          <app-file-tree 
            [paths]="filePaths" 
            [selectedPath]="codegen.selectedFilePath()"
            (fileSelected)="onFileSelected($event)">
          </app-file-tree>
        </div>

        <!-- ═══ SPLITTER RESIZE HANDLE (Between Tree & Code) ═══ -->
        <div 
          (mousedown)="startTreeResize($event)"
          class="w-1.5 bg-[var(--border)] hover:bg-blue-500 active:bg-blue-600 cursor-col-resize shrink-0 transition-colors z-20 flex items-center justify-center"
          title="Arrastra para cambiar el ancho del árbol de archivos">
        </div>

        <!-- Right Pane: Code Viewer -->
        <div class="flex-1 flex flex-col bg-[#141416] overflow-hidden select-text">
          
          <!-- Top Editor Controls Bar -->
          <div class="h-10 bg-[#1e1e22] border-b border-[#2d2d34] flex items-center justify-between px-3 shrink-0 gap-2">
            
            <!-- Breadcrumb Navigation -->
            <div class="flex items-center gap-1 text-[11px] font-mono text-slate-400 overflow-hidden truncate">
              <span class="text-slate-500 text-xs shrink-0">📄</span>
              <div class="flex items-center gap-1 overflow-hidden truncate">
                <span *ngFor="let part of breadcrumbs; let last = last; let i = index" class="flex items-center gap-1">
                  <span [class.text-blue-300]="last" [class.font-semibold]="last" [class.text-slate-400]="!last">
                    {{ part }}
                  </span>
                  <span *ngIf="!last" class="text-slate-600">/</span>
                </span>
              </div>
            </div>

            <!-- Editor Action Buttons -->
            <div class="flex items-center gap-1.5 shrink-0 text-xs">
              
              <!-- Font Size Controls -->
              <div class="flex items-center bg-[#282830] rounded border border-[#3c3c46] overflow-hidden text-[10px]">
                <button (click)="changeFontSize(-1)" class="px-1.5 py-0.5 text-slate-300 hover:text-white hover:bg-[#383844]" title="Reducir fuente">A−</button>
                <span class="px-1 text-slate-400 font-mono">{{ fontSize }}px</span>
                <button (click)="changeFontSize(1)" class="px-1.5 py-0.5 text-slate-300 hover:text-white hover:bg-[#383844]" title="Aumentar fuente">A+</button>
              </div>

              <!-- Word Wrap Toggle -->
              <button 
                (click)="toggleWordWrap()"
                class="px-2 py-1 rounded text-[11px] font-medium border transition-colors flex items-center gap-1"
                [ngClass]="wordWrap ? 'bg-blue-600/30 text-blue-300 border-blue-500/40' : 'bg-[#282830] text-slate-400 border-[#3c3c46] hover:text-white'"
                title="Ajustar líneas al ancho">
                <span>🔤</span> Wrap
              </button>

              <!-- Download Single File -->
              <button 
                (click)="downloadCurrentFile()"
                class="px-2.5 py-1 rounded text-[11px] font-medium bg-[#282830] hover:bg-[#383844] text-slate-300 hover:text-white border border-[#3c3c46] transition-colors flex items-center gap-1 cursor-pointer"
                title="Descargar este archivo individual">
                <span>💾</span> Guardar
              </button>

              <!-- Copy Code Button -->
              <button 
                (click)="copyCode()"
                class="px-3 py-1 rounded text-[11px] font-semibold transition-all flex items-center gap-1 border shadow-xs cursor-pointer"
                [ngClass]="copied ? 'bg-emerald-600 text-white border-emerald-500' : 'bg-blue-600 hover:bg-blue-500 text-white border-blue-500'">
                <span *ngIf="!copied">📋 Copiar</span>
                <span *ngIf="copied" class="flex items-center gap-1">✓ Copiado</span>
              </button>

            </div>

          </div>

          <!-- Architecture Insight Banner if Gemini generated -->
          <div *ngIf="codegen.engineSummary()" class="px-3 py-1.5 bg-gradient-to-r from-purple-950/70 to-indigo-950/50 border-b border-purple-500/20 flex items-center justify-between text-[11px] text-purple-200 shrink-0">
            <div class="flex items-center gap-2 overflow-hidden truncate">
              <span class="text-xs shrink-0">💡</span>
              <span class="truncate font-sans"><strong class="text-purple-300">Semántica IA:</strong> {{ codegen.engineSummary() }}</span>
            </div>
          </div>

          <!-- Code Content Area (with Line Numbers Column) -->
          <div class="flex-1 overflow-auto custom-scrollbar flex bg-[#141416] font-mono leading-relaxed" [style.fontSize.px]="fontSize">
            
            <!-- Line Numbers Gutter -->
            <div class="py-4 px-3 bg-[#18181c] border-r border-[#26262e] text-slate-600 text-right select-none shrink-0 font-mono text-[11px] leading-relaxed" style="min-width: 44px;">
              <div *ngFor="let num of lineNumbers">{{ num }}</div>
            </div>

            <!-- Code Body -->
            <div 
              class="flex-1 p-4 font-mono leading-relaxed text-[#d4d4d4]" 
              [class.whitespace-pre]="!wordWrap"
              [class.whitespace-pre-wrap]="wordWrap"
              style="font-family: 'JetBrains Mono', Consolas, 'Fira Code', monospace;">
              <pre class="m-0 p-0 font-inherit bg-transparent"><code [innerHTML]="highlightedCode"></code></pre>
            </div>

          </div>

          <!-- Footer Status Bar -->
          <div class="h-6 bg-[#18181c] border-t border-[#26262e] px-3 flex items-center justify-between text-[10px] text-slate-500 font-mono select-none">
            <div class="flex items-center gap-3">
              <span>{{ activeFileLanguage }}</span>
              <span>•</span>
              <span>{{ lineNumbers.length }} líneas</span>
              <span>•</span>
              <span>{{ activeFileSizeBytes }} bytes</span>
            </div>

            <div class="flex items-center gap-2 text-slate-400">
              <span class="hover:text-white cursor-pointer" (click)="copyFilePath()" title="Copiar ruta del archivo">
                {{ codegen.selectedFilePath() }} 📋
              </span>
            </div>
          </div>

        </div>

      </div>

      <!-- ═══ GEMINI SETTINGS MODAL ═══ -->
      <div *ngIf="isSettingsOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs animate-fadeIn select-text">
        <div class="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden text-[var(--text-primary)]">
          <div class="px-5 py-4 border-b border-[var(--border)] bg-[var(--surface-1)] flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-xl">⚙️</span>
              <h3 class="text-sm font-bold">Configuración de Google Gemini API</h3>
            </div>
            <button (click)="closeSettingsModal()" class="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-[var(--surface-3)]">✕</button>
          </div>
          
          <div class="p-5 flex flex-col gap-4 text-xs">
            <!-- API Key Field -->
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-300">Clave de API de Gemini:</label>
              <div class="relative flex items-center">
                <input 
                  [type]="showApiKey ? 'text' : 'password'"
                  [(ngModel)]="tempApiKey"
                  placeholder="AQ... o AIzaSy..."
                  class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg px-3 py-2 pr-10 text-xs font-mono text-white placeholder-slate-500 outline-none focus:border-purple-400">
                <button 
                  type="button"
                  (click)="showApiKey = !showApiKey"
                  class="absolute right-2 text-slate-400 hover:text-white text-xs p-1"
                  title="Mostrar u ocultar clave">
                  {{ showApiKey ? '🙈' : '👁️' }}
                </button>
              </div>
              <span class="text-[10px] text-slate-400">Tu clave se guarda de forma segura en tu navegador y en el backend local.</span>
            </div>

            <!-- Model Selector -->
            <div class="flex flex-col gap-1.5">
              <label class="font-semibold text-slate-300">Modelo de Gemini:</label>
              <select 
                [(ngModel)]="tempModel"
                class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded-lg px-3 py-2 text-xs font-mono text-white outline-none focus:border-purple-400">
                <option value="gemini-3.8-flash">gemini-3.8-flash (Recomendado - Razonamiento profundo y alta velocidad)</option>
                <option value="gemini-flash-latest">gemini-flash-latest (Alta velocidad)</option>
                <option value="gemini-3.5-flash">gemini-3.5-flash (Flash multimodal)</option>
                <option value="gemini-3.7-flash">gemini-3.7-flash (Flash híbrido)</option>
                <option value="gemini-pro-latest">gemini-pro-latest (Pro - Requiere facturación en Google Cloud)</option>
              </select>
            </div>

            <div class="p-3 bg-purple-500/10 border border-purple-500/20 rounded-xl text-purple-300 text-[11px] leading-relaxed">
              ✨ <strong>Generación Semántica Activa:</strong> Gemini analiza las clases UML, relaciones (ManyToOne, OneToMany), validaciones y genera la lógica de negocio real en los servicios Spring Boot 3.
            </div>

          </div>

          <div class="px-5 py-3 border-t border-[var(--border)] bg-[var(--surface-1)] flex items-center justify-end gap-2">
            <button (click)="closeSettingsModal()" class="px-3 py-1.5 text-xs text-slate-400 hover:text-white rounded-lg">Cancelar</button>
            <button (click)="saveSettingsAndRegenerate()" class="px-4 py-1.5 text-xs font-bold bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white rounded-lg shadow-md cursor-pointer">
              Guardar y Regenerar
            </button>
          </div>
        </div>
      </div>

    </div>
  `
})
export class LiveCodeDrawerComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() diagramId = '';
  @Input() graphData: any = null;
  @Output() close = new EventEmitter<void>();

  public codegen = inject(CodegenService);
  private route = inject(ActivatedRoute);
  private cdr = inject(ChangeDetectorRef);

  copied = false;
  isMaximized = false;
  isDownloadingZip = false;
  wordWrap = false;
  fontSize = 12;

  // Gemini Settings state
  isSettingsOpen = false;
  tempApiKey = '';
  tempModel = 'gemini-3.8-flash';
  showApiKey = false;
  
  // Resizable state
  drawerWidth = Math.max(620, Math.min(window.innerWidth * 0.58, 980));
  treeWidth = 240;
  
  private isResizingDrawer = false;
  private isResizingTree = false;
  private resizeStartX = 0;
  private startDrawerWidth = 0;
  private startTreeWidth = 0;

  ngOnInit() {
    this.ensureSelectedFile();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['isOpen'] && this.isOpen) {
      this.ensureSelectedFile();
      this.cdr.markForCheck();
      this.cdr.detectChanges();
    }
  }

  ensureSelectedFile() {
    const current = this.codegen.selectedFilePath();
    const files = this.codegen.generatedFiles() || {};
    const paths = Object.keys(files);
    if (!current || !files[current]) {
      if (files['pom.xml']) {
        this.codegen.selectedFilePath.set('pom.xml');
      } else if (paths.length > 0) {
        this.codegen.selectedFilePath.set(paths[0]);
      }
    }
  }

  get filePaths(): string[] {
    return Object.keys(this.codegen.generatedFiles() || {});
  }

  get breadcrumbs(): string[] {
    const path = this.codegen.selectedFilePath();
    return path ? path.split('/') : [];
  }

  get activeContent(): string {
    return this.codegen.selectedFileContent() || '// Selecciona un archivo en el explorador izquierdo...';
  }

  get lineNumbers(): number[] {
    const count = this.activeContent.split('\n').length;
    return Array.from({ length: count }, (_, i) => i + 1);
  }

  get activeFileSizeBytes(): number {
    return new Blob([this.activeContent]).size;
  }

  get activeFileLanguage(): string {
    const path = (this.codegen.selectedFilePath() || '').toLowerCase();
    if (path.endsWith('.java')) return 'Java (Spring Boot 3)';
    if (path.endsWith('.xml')) return 'Maven POM XML';
    if (path.endsWith('.yml') || path.endsWith('.yaml')) return 'YAML Config';
    if (path.endsWith('.md')) return 'Markdown Documentation';
    if (path.endsWith('.bat')) return 'Windows Batch Script';
    if (path.endsWith('.sh')) return 'Shell Script';
    if (path.endsWith('.json')) return 'JSON Config';
    return 'Plain Text';
  }

  private escapeHtml(str: string): string {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  get highlightedCode(): string {
    const code = this.activeContent;
    const filePath = this.codegen.selectedFilePath();
    if (!code) return '';

    const ext = (filePath || '').split('.').pop()?.toLowerCase() || '';
    if (ext === 'md' || ext === 'txt') {
      return this.escapeHtml(code);
    }

    // Single-pass tokenizer: matches strings, comments, annotations, xml tags, keywords, types, numbers
    const tokenRegex = /(\/\/[^\n]*|\/\*[\s\S]*?\*\/|<!--[\s\S]*?-->|^\s*#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|@[A-Za-z0-9_]+|<\/?[a-zA-Z0-9_:-]+|\b(?:package|import|public|private|protected|class|interface|enum|extends|implements|return|if|else|for|while|new|this|super|static|final|void|default|throw|throws|try|catch|finally|boolean|int|long|double|float|char|byte|short|record|sealed|permits|var|yield)\b|\b(?:String|Integer|Long|Boolean|Double|Float|List|Set|Map|Optional|ResponseEntity|HttpStatus|LocalDateTime|LocalDate|LocalTime|Object|System|Exception|RuntimeException|BigDecimal)\b|\b\d+(?:\.\d+)?\b)/gm;

    let lastIndex = 0;
    let result = '';
    let match: RegExpExecArray | null;

    while ((match = tokenRegex.exec(code)) !== null) {
      if (match.index > lastIndex) {
        result += this.escapeHtml(code.slice(lastIndex, match.index));
      }
      
      const token = match[0];
      const escaped = this.escapeHtml(token);

      if (token.startsWith('//') || token.startsWith('/*') || token.startsWith('<!--') || token.trim().startsWith('#')) {
        result += `<span class="text-[#6a9955] italic">${escaped}</span>`;
      } else if ((token.startsWith('"') && token.endsWith('"')) || (token.startsWith("'") && token.endsWith("'"))) {
        result += `<span class="text-[#ce9178]">${escaped}</span>`;
      } else if (token.startsWith('@')) {
        result += `<span class="text-[#dcdcaa] font-semibold">${escaped}</span>`;
      } else if (token.startsWith('<')) {
        result += `<span class="text-[#569cd6]">${escaped}</span>`;
      } else if (/^\d+(?:\.\d+)?$/.test(token)) {
        result += `<span class="text-[#b5cea8]">${escaped}</span>`;
      } else if (/^(package|import|public|private|protected|class|interface|enum|extends|implements|return|if|else|for|while|new|this|super|static|final|void|default|throw|throws|try|catch|finally|boolean|int|long|double|float|char|byte|short|record|sealed|permits|var|yield)$/.test(token)) {
        result += `<span class="text-[#569cd6] font-semibold">${escaped}</span>`;
      } else if (/^(String|Integer|Long|Boolean|Double|Float|List|Set|Map|Optional|ResponseEntity|HttpStatus|LocalDateTime|LocalDate|LocalTime|Object|System|Exception|RuntimeException|BigDecimal)$/.test(token)) {
        result += `<span class="text-[#4ec9b0] font-semibold">${escaped}</span>`;
      } else {
        result += escaped;
      }

      lastIndex = tokenRegex.lastIndex;
    }

    if (lastIndex < code.length) {
      result += this.escapeHtml(code.slice(lastIndex));
    }

    return result;
  }

  onFileSelected(path: string) {
    this.codegen.selectedFilePath.set(path);
    this.cdr.markForCheck();
    this.cdr.detectChanges();
  }

  toggleMaximize() {
    this.isMaximized = !this.isMaximized;
  }

  toggleWordWrap() {
    this.wordWrap = !this.wordWrap;
  }

  changeFontSize(delta: number) {
    this.fontSize = Math.max(10, Math.min(20, this.fontSize + delta));
  }

  // ─── Resizing Handlers ─────────────────────────────────────────

  startDrawerResize(event: MouseEvent) {
    event.preventDefault();
    this.isResizingDrawer = true;
    this.resizeStartX = event.clientX;
    this.startDrawerWidth = this.drawerWidth;
  }

  startTreeResize(event: MouseEvent) {
    event.preventDefault();
    this.isResizingTree = true;
    this.resizeStartX = event.clientX;
    this.startTreeWidth = this.treeWidth;
  }

  @HostListener('document:mousemove', ['$event'])
  onMouseMove(event: MouseEvent) {
    if (this.isResizingDrawer) {
      const delta = this.resizeStartX - event.clientX;
      this.drawerWidth = Math.max(480, Math.min(window.innerWidth * 0.95, this.startDrawerWidth + delta));
    } else if (this.isResizingTree) {
      const delta = event.clientX - this.resizeStartX;
      this.treeWidth = Math.max(160, Math.min(460, this.startTreeWidth + delta));
    }
  }

  @HostListener('document:mouseup')
  onMouseUp() {
    this.isResizingDrawer = false;
    this.isResizingTree = false;
  }

  // ─── Actions ───────────────────────────────────────────────────

  downloadProject() {
    const diagramId = this.diagramId || this.route.snapshot.paramMap.get('id');
    if (diagramId) {
      this.isDownloadingZip = true;
      this.codegen.downloadZip(diagramId, 'classforge-springboot-backend.zip');
      setTimeout(() => this.isDownloadingZip = false, 1500);
    }
  }

  downloadCurrentFile() {
    const path = this.codegen.selectedFilePath();
    const content = this.codegen.selectedFileContent();
    if (!path || !content) return;

    const fileName = path.split('/').pop() || 'file.txt';
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  copyCode() {
    const code = this.codegen.selectedFileContent();
    if (code) {
      navigator.clipboard.writeText(code).then(() => {
        this.copied = true;
        this.cdr.markForCheck();
        setTimeout(() => {
          this.copied = false;
          this.cdr.markForCheck();
        }, 2000);
      });
    }
  }

  copyFilePath() {
    const path = this.codegen.selectedFilePath();
    if (path) {
      navigator.clipboard.writeText(path);
    }
  }

  // ─── Gemini Engine & Settings ──────────────────────────────────

  setEngine(engine: CodegenEngine) {
    this.codegen.setEngine(engine);
    this.cdr.markForCheck();
    this.regenerate();
  }

  openSettingsModal() {
    this.tempApiKey = this.codegen.geminiApiKey();
    this.tempModel = this.codegen.geminiModel();
    this.isSettingsOpen = true;
    this.cdr.markForCheck();
  }

  closeSettingsModal() {
    this.isSettingsOpen = false;
    this.cdr.markForCheck();
  }

  saveSettingsAndRegenerate() {
    this.codegen.setGeminiApiKey(this.tempApiKey.trim());
    this.codegen.setGeminiModel(this.tempModel);
    this.isSettingsOpen = false;
    this.cdr.markForCheck();
    this.regenerate();
  }

  regenerate() {
    const targetId = this.diagramId || this.route.snapshot.paramMap.get('id');
    if (!targetId) return;

    this.codegen.isLoading.set(true);
    this.cdr.markForCheck();
    this.codegen.getPreview(targetId, this.graphData).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.codegen.generatedFiles.set(res.data.files);
          this.ensureSelectedFile();
        }
        this.codegen.isLoading.set(false);
        this.cdr.markForCheck();
        this.cdr.detectChanges();
      },
      error: () => {
        this.codegen.isLoading.set(false);
        this.cdr.markForCheck();
      }
    });
  }
}


