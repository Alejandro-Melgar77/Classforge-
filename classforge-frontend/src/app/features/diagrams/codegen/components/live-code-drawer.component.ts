import { Component, Input, Output, EventEmitter, inject, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CodegenService } from '../services/codegen.service';
import { FileTreeComponent } from './file-tree.component';
import { ActivatedRoute } from '@angular/router';

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
              <span class="hover:text-white cursor-pointer" (click)="copyFilePath()" title="Copiar ruta absoluta del archivo">
                {{ codegen.selectedFilePath() }} 📋
              </span>
            </div>
          </div>

        </div>

      </div>

    </div>
  `
})
export class LiveCodeDrawerComponent {
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();

  public codegen = inject(CodegenService);
  private route = inject(ActivatedRoute);

  copied = false;
  isMaximized = false;
  isDownloadingZip = false;
  wordWrap = false;
  fontSize = 12;
  
  // Resizable state
  drawerWidth = Math.max(620, Math.min(window.innerWidth * 0.58, 980));
  treeWidth = 240;
  
  private isResizingDrawer = false;
  private isResizingTree = false;
  private resizeStartX = 0;
  private startDrawerWidth = 0;
  private startTreeWidth = 0;

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
    return 'Plain Text';
  }

  get highlightedCode(): string {
    const code = this.activeContent;
    const escaped = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    // Clean Code syntax highlighting
    return escaped
      .replace(/(\/\/[^\n]*)/g, '<span class="text-[#6a9955] italic">$1</span>') // Comments
      .replace(/\b(package|import|public|private|protected|class|interface|enum|extends|implements|return|if|else|for|while|new|this|super|static|final|void|default|throw|throws|try|catch|finally)\b/g, '<span class="text-[#569cd6] font-semibold">$1</span>')
      .replace(/\b(String|Integer|Long|Boolean|Double|Float|List|Set|Map|Optional|ResponseEntity|HttpStatus|LocalDateTime|LocalDate|LocalTime)\b/g, '<span class="text-[#4ec9b0]">$1</span>')
      .replace(/(@[A-Za-z0-9_]+)/g, '<span class="text-[#dcdcaa]">$1</span>') // Annotations
      .replace(/("[^"]*")/g, '<span class="text-[#ce9178]">$1</span>') // Strings
      .replace(/\b([0-9]+)\b/g, '<span class="text-[#b5cea8]">$1</span>'); // Numbers
  }

  onFileSelected(path: string) {
    this.codegen.selectedFilePath.set(path);
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
    const diagramId = this.route.snapshot.paramMap.get('id');
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
        setTimeout(() => this.copied = false, 2000);
      });
    }
  }

  copyFilePath() {
    const path = this.codegen.selectedFilePath();
    if (path) {
      navigator.clipboard.writeText(path);
    }
  }
}

