import { Component, Input, Output, EventEmitter, inject, signal, OnInit, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { VoiceRecognitionService } from '../services/voice-recognition.service';
import { AiService } from '../services/ai.service';
import { CommandExecutorService } from '../services/command-executor.service';
import { AiHistoryService } from '../services/ai-history.service';
import { AuthService } from '../../../../core/services/auth.service';
import { UMLCommandResponse } from '../models/ai-command.model';
import { CommandPreviewCardComponent } from './command-preview-card.component';
import { toObservable } from '@angular/core/rxjs-interop';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-ai-drawer',
  standalone: true,
  imports: [CommonModule, FormsModule, CommandPreviewCardComponent],
  template: `
    <div 
      class="ai-drawer fixed right-0 top-0 h-full bg-slate-900 border-l border-slate-700/80 shadow-2xl transition-transform duration-300 z-50 flex flex-col select-none text-slate-200"
      [style.width.px]="drawerWidth"
      [class.translate-x-full]="!isOpen"
      [class.translate-x-0]="isOpen"
    >
      <!-- Resize Handle (Left border) -->
      <div 
        class="absolute left-0 top-0 bottom-0 w-2 hover:w-3 bg-transparent hover:bg-blue-500/50 cursor-ew-resize transition-all z-20 flex items-center justify-center group"
        (mousedown)="startResize($event)"
        title="Arrastra para redimensionar el panel"
      >
        <div class="w-0.5 h-10 bg-slate-600 group-hover:bg-blue-400 rounded-full"></div>
      </div>

      <!-- Header -->
      <div class="p-3.5 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white text-base shadow-md">
            ✨
          </div>
          <div>
            <h3 class="text-sm font-bold text-white flex items-center gap-1.5 leading-tight">
              Asistente IA UML
              <span class="text-[10px] px-1.5 py-0.2 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium">
                100% Offline
              </span>
            </h3>
            <span class="text-[10px] text-slate-400">
              Usuario: <strong class="text-slate-300 font-semibold">{{ currentUserName }}</strong>
            </span>
          </div>
        </div>

        <!-- Quick width presets & close -->
        <div class="flex items-center gap-1">
          <button (click)="setDrawerWidth(380)" class="px-1.5 py-0.5 text-[10px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700" title="Ancho compacto (380px)">S</button>
          <button (click)="setDrawerWidth(520)" class="px-1.5 py-0.5 text-[10px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700" title="Ancho medio (520px)">M</button>
          <button (click)="setDrawerWidth(720)" class="px-1.5 py-0.5 text-[10px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700" title="Ancho amplio (720px)">L</button>
          <button (click)="close.emit()" class="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors ml-1" title="Cerrar panel">✕</button>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <div class="flex border-b border-slate-800 bg-slate-950/30 text-xs">
        <button 
          (click)="activeTab = 'prompt'"
          class="flex-1 py-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center justify-center gap-1.5"
          [class.text-blue-400]="activeTab === 'prompt'"
          [class.border-blue-500]="activeTab === 'prompt'"
          [class.border-transparent]="activeTab !== 'prompt'"
          [class.text-slate-400]="activeTab !== 'prompt'"
          [class.hover:text-slate-200]="activeTab !== 'prompt'"
        >
          <span>🤖</span> Asistente
        </button>
        <button 
          (click)="activeTab = 'history'"
          class="flex-1 py-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center justify-center gap-1.5 relative"
          [class.text-blue-400]="activeTab === 'history'"
          [class.border-blue-500]="activeTab === 'history'"
          [class.border-transparent]="activeTab !== 'history'"
          [class.text-slate-400]="activeTab !== 'history'"
          [class.hover:text-slate-200]="activeTab !== 'history'"
        >
          <span>📜</span> Mi Historial
          <span *ngIf="historyService.history().length > 0" class="px-1.5 py-0.2 text-[10px] rounded-full bg-blue-600/30 text-blue-300 border border-blue-500/30">
            {{ historyService.history().length }}
          </span>
        </button>
        <button 
          (click)="activeTab = 'examples'"
          class="flex-1 py-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center justify-center gap-1.5"
          [class.text-blue-400]="activeTab === 'examples'"
          [class.border-blue-500]="activeTab === 'examples'"
          [class.border-transparent]="activeTab !== 'examples'"
          [class.text-slate-400]="activeTab !== 'examples'"
          [class.hover:text-slate-200]="activeTab !== 'examples'"
        >
          <span>💡</span> Ejemplos
        </button>
      </div>

      <!-- Main Body Container -->
      <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-3 select-text">
        
        <!-- TAB 1: PROMPT & ASSISTANT -->
        <ng-container *ngIf="activeTab === 'prompt'">
          
          <!-- Command Preview Card -->
          <app-command-preview-card 
            *ngIf="pendingCommand()" 
            [command]="pendingCommand()!" 
            (confirm)="applyCommand()" 
            (discard)="discardCommand()">
          </app-command-preview-card>

          <!-- Voice Listening Feedback Animation -->
          <div *ngIf="voice.isListening()" class="flex flex-col items-center justify-center p-6 bg-slate-800/60 rounded-xl border border-red-500/30 shadow-lg">
            <div class="relative flex justify-center items-center mb-3">
              <div class="absolute w-20 h-20 bg-red-500/30 rounded-full animate-ping"></div>
              <div class="w-14 h-14 bg-red-600 rounded-full flex items-center justify-center text-white text-2xl shadow-lg">
                🎙️
              </div>
            </div>
            <div class="flex items-center gap-1 mb-2">
              <div class="w-1 h-3 bg-red-400 animate-pulse"></div>
              <div class="w-1 h-5 bg-red-500 animate-pulse delay-75"></div>
              <div class="w-1 h-8 bg-red-400 animate-pulse delay-150"></div>
              <div class="w-1 h-4 bg-red-500 animate-pulse delay-100"></div>
              <div class="w-1 h-2 bg-red-400 animate-pulse"></div>
            </div>
            <p class="text-xs text-red-300 font-bold uppercase tracking-wider mb-1">Escuchando tu voz...</p>
            <p class="text-xs text-slate-300 text-center italic min-h-[1.5rem] bg-slate-900/60 px-3 py-1 rounded border border-slate-700/50">
              "{{ voice.transcript() || voice.interimTranscript() || 'Habla ahora para dictar tu comando...' }}"
            </p>
            <button (click)="stopVoiceAndSubmit()" class="mt-3 px-3 py-1 bg-red-700 hover:bg-red-600 text-white rounded text-xs font-bold transition-colors">
              ⏹️ Detener y Procesar
            </button>
          </div>

          <!-- Error Alert -->
          <div *ngIf="voice.error()" class="p-3 bg-red-950/40 border border-red-800/50 rounded-lg text-xs text-red-300 flex items-start gap-2">
            <span class="text-base">⚠️</span>
            <div class="flex-1">
              <p class="font-bold">Aviso de Micrófono:</p>
              <p>{{ voice.error() }}</p>
            </div>
            <button (click)="voice.clear()" class="text-red-400 hover:text-white">✕</button>
          </div>

          <!-- Welcome Info Box -->
          <div *ngIf="!pendingCommand() && !voice.isListening()" class="bg-slate-800/40 p-4 rounded-xl border border-slate-800 text-xs text-slate-400 space-y-2">
            <div class="flex items-center gap-2 text-white font-bold text-sm">
              <span>⚡</span> Asistente UML Offline & Colaborativo
            </div>
            <p>
              Dicta o escribe consultas naturales para construir diagramas de clases UML instantáneamente.
            </p>
            <div class="bg-slate-900/80 p-2.5 rounded-lg border border-slate-700/50 font-mono text-[11px] text-blue-300">
              "crea una tabla con el nombre Producto con 3 atributos de nombres precio, stock, codigo y que se asocie a Categoria con la cardinalidad 1..*"
            </div>
          </div>
        </ng-container>

        <!-- TAB 2: PRIVATE USER HISTORY -->
        <ng-container *ngIf="activeTab === 'history'">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <span>🔒</span> Historial Privado de {{ currentUserName }}
            </h4>
            <button 
              *ngIf="historyService.history().length > 0"
              (click)="historyService.clearUserHistory(diagramId)" 
              class="text-[11px] text-red-400 hover:text-red-300 hover:underline"
              title="Borrar únicamente mi historial"
            >
              Limpiar mi historial
            </button>
          </div>

          <div *ngIf="historyService.history().length === 0" class="text-center py-10 text-slate-500 text-xs">
            <span class="text-3xl block mb-2">📜</span>
            No has realizado consultas en esta sesión todavía.
          </div>

          <div class="space-y-2.5">
            <div 
              *ngFor="let item of historyService.history()" 
              class="p-3 bg-slate-800/70 border border-slate-700/70 rounded-xl hover:border-slate-600 transition-all text-xs flex flex-col gap-1.5"
            >
              <div class="flex items-center justify-between text-[10px] text-slate-400">
                <span class="flex items-center gap-1 font-semibold">
                  <span *ngIf="item.inputType === 'voice'" class="text-red-400" title="Dictado por voz">🎙️ Voz</span>
                  <span *ngIf="item.inputType === 'text'" class="text-blue-400" title="Ingresado por texto">⌨️ Texto</span>
                  <span>• {{ item.timestamp | date:'shortTime' }}</span>
                </span>
                <span 
                  class="px-1.5 py-0.2 rounded font-mono text-[9px] uppercase font-bold"
                  [class.text-emerald-400]="item.status === 'applied'"
                  [class.bg-emerald-950]="item.status === 'applied'"
                  [class.border]="item.status === 'applied'"
                  [class.border-emerald-800]="item.status === 'applied'"
                  [class.bg-slate-800]="item.status === 'discarded'"
                  [class.text-slate-400]="item.status === 'discarded'"
                  [class.bg-red-950]="item.status === 'failed'"
                  [class.text-red-400]="item.status === 'failed'"
                >
                  {{ item.status }}
                </span>
              </div>

              <p class="text-slate-200 font-medium font-sans">
                "{{ item.prompt }}"
              </p>

              <p *ngIf="item.resultSummary" class="text-[11px] text-slate-400 font-mono bg-slate-900/60 p-1.5 rounded border border-slate-800">
                {{ item.resultSummary }}
              </p>

              <div class="flex items-center gap-2 pt-1 border-t border-slate-800 text-[11px]">
                <button 
                  (click)="textInput = item.prompt; activeTab = 'prompt'; submitText(item.inputType === 'voice')" 
                  class="text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1"
                >
                  <span>↻</span> Re-ejecutar
                </button>
                <button 
                  (click)="textInput = item.prompt; activeTab = 'prompt'" 
                  class="text-slate-400 hover:text-slate-200"
                >
                  Cargar en prompt
                </button>
              </div>
            </div>
          </div>
        </ng-container>

        <!-- TAB 3: EXAMPLES -->
        <ng-container *ngIf="activeTab === 'examples'">
          <h4 class="text-xs font-bold text-slate-300 mb-2">Ejemplos Rápidos (Clic para probar):</h4>
          
          <div class="space-y-2">
            <div 
              *ngFor="let ex of complexExamples"
              class="p-3 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-blue-500/50 rounded-xl cursor-pointer transition-all"
              (click)="useExample(ex.prompt)"
            >
              <div class="flex items-center justify-between mb-1">
                <strong class="text-xs text-blue-400">{{ ex.title }}</strong>
                <span class="text-[10px] text-slate-500">Probar ➔</span>
              </div>
              <p class="text-[11px] text-slate-300 font-mono">
                "{{ ex.prompt }}"
              </p>
            </div>
          </div>
        </ng-container>

      </div>

      <!-- Bottom Prompt Bar -->
      <div class="p-3.5 border-t border-slate-800 bg-slate-950/80">
        <!-- Quick Suggestions Chips -->
        <div class="flex flex-wrap gap-1.5 mb-2.5">
          <span class="text-[10px] text-slate-400 self-center">Sugerencias:</span>
          <button 
            *ngFor="let suggestion of quickSuggestions" 
            class="text-[11px] bg-slate-800 hover:bg-slate-700 border border-slate-700/70 px-2 py-0.5 rounded-full text-slate-300 transition-colors cursor-pointer"
            (click)="textInput = suggestion; submitText(false)"
          >
            {{ suggestion }}
          </button>
        </div>

        <!-- Input Bar with Voice Toggle & Submit -->
        <div class="flex items-center gap-2">
          <div class="relative flex-1">
            <input 
              type="text" 
              [(ngModel)]="textInput" 
              (keyup.enter)="submitText(false)"
              placeholder="Ej: crea una tabla Producto con 3 atributos..."
              class="w-full bg-slate-900 border border-slate-700 focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all pr-8"
              [disabled]="isProcessing()"
            />
            <button 
              *ngIf="textInput" 
              (click)="textInput = ''" 
              class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs"
            >
              ✕
            </button>
          </div>

          <!-- Mic Toggle Button -->
          <button 
            (click)="toggleVoice()" 
            class="p-2.5 rounded-xl border transition-all flex items-center justify-center text-sm shadow-md cursor-pointer"
            [class.bg-red-600]="voice.isListening()"
            [class.text-white]="voice.isListening()"
            [class.border-red-500]="voice.isListening()"
            [class.animate-pulse]="voice.isListening()"
            [class.bg-slate-800]="!voice.isListening()"
            [class.hover:bg-slate-700]="!voice.isListening()"
            [class.text-slate-300]="!voice.isListening()"
            [class.border-slate-700]="!voice.isListening()"
            [title]="voice.isListening() ? 'Detener dictado por voz' : 'Iniciar reconocimiento por voz'"
          >
            🎙️
          </button>

          <!-- Submit Button -->
          <button 
            (click)="submitText(false)"
            class="px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold text-xs shadow-lg transition-all flex items-center justify-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            [disabled]="isProcessing() || !textInput.trim()"
          >
            <span *ngIf="!isProcessing()">➤</span>
            <span *ngIf="isProcessing()" class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
          </button>
        </div>
      </div>
    </div>
  `
})
export class AiDrawerComponent implements OnInit, OnDestroy {
  @Input() isOpen = false;
  @Input() diagramId?: string;
  @Output() close = new EventEmitter<void>();

  public voice = inject(VoiceRecognitionService);
  public aiService = inject(AiService);
  public executor = inject(CommandExecutorService);
  public historyService = inject(AiHistoryService);
  public authService = inject(AuthService);

  public activeTab: 'prompt' | 'history' | 'examples' = 'prompt';
  public drawerWidth = 420;
  private isResizing = false;

  public textInput = '';
  public pendingCommand = signal<UMLCommandResponse | null>(null);
  public isProcessing = signal<boolean>(false);
  private lastInputType: 'voice' | 'text' = 'text';

  private voiceSub?: Subscription;

  public quickSuggestions = [
    'Crear clase Usuario',
    'Relacionar Producto con Categoria',
    'Diseñar tienda e-commerce'
  ];

  public complexExamples = [
    {
      title: 'Crear tabla con atributos y cardinalidad',
      prompt: 'crea una tabla con el nombre Producto con 3 atributos de nombres precio, stock, codigo y que se asocie a Categoria con la cardinalidad 1..*'
    },
    {
      title: 'Crear clase con tipos explícitos',
      prompt: 'crear clase Factura con atributos total:double, fecha:Date, nroFactura:String y asociar a Cliente con cardinalidad *..1'
    },
    {
      title: 'Herencia entre entidades',
      prompt: 'hacer que Administrador herede de Usuario'
    },
    {
      title: 'Composición con cardinalidad',
      prompt: 'crear composicion entre Factura y DetalleFactura con cardinalidad 1..1 a 1..*'
    },
    {
      title: 'Agregar método con parámetros',
      prompt: 'agregar metodo calcularTotal(descuento: float): double a Factura'
    },
    {
      title: 'Generar sistema completo',
      prompt: 'diseñar tienda e-commerce con Usuario, Producto, Pedido, DetallePedido'
    }
  ];

  get currentUserName(): string {
    const user = this.authService.getCurrentUser();
    return user?.name || user?.email || 'Usuario';
  }

  ngOnInit(): void {
    if (typeof localStorage !== 'undefined') {
      const savedWidth = localStorage.getItem('cf_ai_drawer_width');
      if (savedWidth) {
        const w = parseInt(savedWidth, 10);
        if (w >= 320 && w <= 900) this.drawerWidth = w;
      }
    }

    this.historyService.reloadHistory(this.diagramId);

    this.voiceSub = toObservable(this.voice.isListening).subscribe(isListening => {
      if (!isListening) {
        const finalT = this.voice.transcript().trim();
        if (finalT) {
          this.textInput = finalT;
          this.submitText(true);
        }
      }
    });
  }

  ngOnDestroy(): void {
    if (this.voiceSub) {
      this.voiceSub.unsubscribe();
    }
  }

  setDrawerWidth(w: number): void {
    this.drawerWidth = w;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('cf_ai_drawer_width', w.toString());
    }
  }

  startResize(event: MouseEvent): void {
    event.preventDefault();
    this.isResizing = true;
  }

  @HostListener('window:mousemove', ['$event'])
  onMouseMove(event: MouseEvent): void {
    if (!this.isResizing) return;
    const newWidth = window.innerWidth - event.clientX;
    if (newWidth >= 320 && newWidth <= 850) {
      this.drawerWidth = newWidth;
    }
  }

  @HostListener('window:mouseup')
  onMouseUp(): void {
    if (this.isResizing) {
      this.isResizing = false;
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('cf_ai_drawer_width', this.drawerWidth.toString());
      }
    }
  }

  toggleVoice(): void {
    if (this.voice.isListening()) {
      this.stopVoiceAndSubmit();
    } else {
      this.voice.startListening();
    }
  }

  stopVoiceAndSubmit(): void {
    this.voice.stopListening();
  }

  useExample(prompt: string): void {
    this.textInput = prompt;
    this.activeTab = 'prompt';
    this.submitText(false);
  }

  submitText(isVoice = false): void {
    const text = this.textInput.trim();
    if (!text || this.isProcessing()) return;

    this.lastInputType = isVoice ? 'voice' : 'text';
    this.isProcessing.set(true);

    this.aiService.processInput(text).subscribe({
      next: (cmd) => {
        this.pendingCommand.set(cmd);
        this.isProcessing.set(false);
      },
      error: () => {
        this.isProcessing.set(false);
      }
    });
  }

  applyCommand(): void {
    const cmd = this.pendingCommand();
    const promptText = this.textInput.trim() || cmd?.explanation || 'Comando aplicado';

    if (cmd && cmd.action !== 'unknown') {
      this.executor.execute(cmd);
      this.historyService.addEntry(promptText, this.lastInputType, cmd, 'applied', this.diagramId);
    }

    this.pendingCommand.set(null);
    this.textInput = '';
    this.voice.clear();
  }

  discardCommand(): void {
    const cmd = this.pendingCommand();
    const promptText = this.textInput.trim() || 'Comando descartado';
    if (cmd) {
      this.historyService.addEntry(promptText, this.lastInputType, cmd, 'discarded', this.diagramId);
    }
    this.pendingCommand.set(null);
    this.textInput = '';
    this.voice.clear();
  }
}


