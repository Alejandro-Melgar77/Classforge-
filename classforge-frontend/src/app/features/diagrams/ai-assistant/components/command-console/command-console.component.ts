import {
  Component,
  Input,
  inject,
  signal,
  effect,
  OnInit,
  OnDestroy,
  ChangeDetectorRef,
  ChangeDetectionStrategy
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { VoiceRecognitionService } from '../../services/voice-recognition.service';
import { AiService } from '../../services/ai.service';
import { CommandExecutorService } from '../../services/command-executor.service';
import { AiHistoryService } from '../../services/ai-history.service';
import { UMLCommandResponse, AiHistoryEntry } from '../../models/ai-command.model';
import { CommandPreviewCardComponent } from '../command-preview-card.component';
import { AiTeamStore } from '../../../../ai-team/data-access/ai-team.store';

export type CommandConsoleSection = 'console' | 'examples' | 'history';

@Component({
  selector: 'app-command-console',
  standalone: true,
  imports: [CommonModule, FormsModule, CommandPreviewCardComponent],
  templateUrl: './command-console.component.html',
  styleUrl: './command-console.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CommandConsoleComponent implements OnInit, OnDestroy {
  @Input() diagramId?: string;
  @Input() projectId?: string;

  public voice = inject(VoiceRecognitionService);
  public aiService = inject(AiService);
  public executor = inject(CommandExecutorService);
  public historyService = inject(AiHistoryService);
  public aiTeamStore = inject(AiTeamStore);
  private cdr = inject(ChangeDetectorRef);

  public activeSection = signal<CommandConsoleSection>('console');
  public autoApply = signal<boolean>(true);
  public textInput = '';
  public pendingCommand = signal<UMLCommandResponse | null>(null);
  public isProcessing = signal<boolean>(false);
  public executionFeedback = signal<{ message: string; type: 'success' | 'error'; source?: string } | null>(null);

  // Provider preferences & local LLM state (P8a)
  public providerPreference = signal<'auto' | 'gemini' | 'local'>('auto');
  public localAvailable = signal<boolean>(false);
  public localModel = signal<string>('qwen2.5:1.5b');
  public localLatency = signal<number | null>(null);
  public elapsedSeconds = signal<number>(0);
  public showUseGeminiNow = signal<boolean>(false);

  private feedbackTimeout: ReturnType<typeof setTimeout> | null = null;
  private processingTimer: ReturnType<typeof setInterval> | null = null;
  private currentRunningPrompt = '';
  private lastInputType: 'voice' | 'text' = 'text';

  public quickSuggestions: string[] = [
    'Crear clase Cliente con nombre, id, ci, numero, nit',
    'Crear tienda e-commerce completa con Cliente, Pedido, DetallePedido, Producto, Categoria',
    'Crear sistema hospitalario con Medico, Paciente, CitaMedica, Receta y Medicamento',
    'Crear sistema bancario con Cliente, CuentaBancaria, CuentaAhorro, Transaccion',
    'Crear tabla Producto con precio, stock, codigo y asociar a Categoria 1..*',
    'Hacer que Administrador herede de Usuario',
    'Crear sistema universitario con Estudiante, Docente, Materia, Inscripcion'
  ];

  public complexExamples = [
    {
      title: 'Sistema E-Commerce Completo',
      prompt: 'Diseñar tienda e-commerce con Cliente (id, nombre, email, direccion), Pedido (id, codigo, fecha, total, estado), DetallePedido (id, cantidad, precioUnitario), Producto (id, nombre, precio, stock) y Categoria (id, nombre, descripcion). Composición de Pedido a DetallePedido 1 a 1..*, asociación de DetallePedido a Producto * a 1, agregación de Producto a Categoria * a 1, y asociación de Cliente a Pedido 1 a 0..*'
    },
    {
      title: 'Sistema Hospitalario / Clínica Médica',
      prompt: 'Diseñar sistema de hospital con Medico (id, nombre, especialidad, nroColegiado), Paciente (id, nombre, ci, historialClinico), CitaMedica (id, fecha, hora, estado, motivo), Receta (id, fechaEmision, indicaciones) y Medicamento (id, nombreComercial, dosis). Medico se asocia 1 a 0..* con CitaMedica, Paciente se asocia 1 a 0..* con CitaMedica, CitaMedica tiene composición 1 a 0..1 con Receta, y Receta tiene agregación 1 a 1..* con Medicamento'
    },
    {
      title: 'Sistema Bancario y Financiero con Herencia',
      prompt: 'Diseñar sistema bancario con Cliente (id, ci, nombre, telefono), CuentaBancaria (id, numeroCuenta, saldo, tipoMoneda), CuentaAhorro (tasaInteres), CuentaCorriente (limiteSobregiro), Transaccion (id, fecha, monto, tipo). CuentaAhorro y CuentaCorriente heredan de CuentaBancaria. Cliente tiene asociación 1 a 1..* con CuentaBancaria, y CuentaBancaria tiene composición 1 a 0..* con Transaccion'
    },
    {
      title: 'Sistema Universitario / Académico',
      prompt: 'Diseñar sistema universitario con Estudiante (id, matricula, nombre, semestre), Docente (id, codigoDocente, nombre, especialidad), Materia (id, sigla, nombre, creditos), e Inscripcion (id, fecha, notaFinal, estado). Estudiante se asocia 1 a 0..* con Inscripcion, Materia se asocia 1 a 0..* con Inscripcion, y Docente se asocia 1 a 1..* con Materia'
    },
    {
      title: 'Clase con atributos y tipos',
      prompt: 'crear clase Cliente con atributos nombre:String, id:Long, ci:String, numero:Integer, nit:String'
    },
    {
      title: 'Composición con cardinalidad',
      prompt: 'crear composicion entre Factura y DetalleFactura con cardinalidad 1..1 a 1..*'
    }
  ];

  constructor() {
    effect(() => {
      const isListening = this.voice.isListening();
      const best = this.voice.getBestTranscript();
      if (!isListening && best && !this.textInput.trim()) {
        setTimeout(() => {
          this.textInput = best;
          this.cdr.markForCheck();
        }, 0);
      }
    });
  }

  ngOnInit(): void {
    this.historyService.reloadHistory(this.diagramId);
    this.refreshHealth();
  }

  ngOnDestroy(): void {
    if (this.voice.isListening()) {
      this.voice.stopListening();
    }
    if (this.feedbackTimeout) {
      clearTimeout(this.feedbackTimeout);
    }
    if (this.processingTimer) {
      clearInterval(this.processingTimer);
    }
  }

  public refreshHealth(): void {
    this.aiService.checkHealth().subscribe({
      next: (res) => {
        this.localAvailable.set(!!(res.local_available || res.ollama_available));
        if (res.local_model) this.localModel.set(res.local_model);
        if (res.local_latency_ms !== undefined) this.localLatency.set(res.local_latency_ms);
        this.cdr.markForCheck();
      },
      error: () => {
        this.localAvailable.set(false);
        this.cdr.markForCheck();
      }
    });
  }

  public setProvider(pref: 'auto' | 'gemini' | 'local'): void {
    this.providerPreference.set(pref);
    this.cdr.markForCheck();
  }

  public setSection(section: CommandConsoleSection): void {
    this.activeSection.set(section);
    this.cdr.markForCheck();
  }

  public getHistoryEntries(): AiHistoryEntry[] {
    return this.historyService.history();
  }

  public toggleVoice(): void {
    if (this.voice.isListening()) {
      this.stopVoiceAndSubmit();
    } else {
      this.voice.startListening();
    }
  }

  public cancelVoice(): void {
    this.voice.stopListening();
    this.voice.clear();
  }

  public stopVoiceAndSubmit(): void {
    const text = this.voice.stopAndGetTranscript() || this.textInput.trim();
    if (text) {
      this.textInput = text;
      if (this.autoApply()) {
        this.executeDirectly(text, true);
      } else {
        this.submitText(true);
      }
    } else {
      this.voice.stopListening();
      this.showFeedback('No se detectó ninguna palabra hablada.', 'error');
    }
  }

  public handleSubmit(): void {
    const text = this.textInput.trim() || this.voice.getBestTranscript().trim();
    if (!text || this.isProcessing()) return;

    const isVoice = this.voice.isListening() || this.lastInputType === 'voice';

    if (this.voice.isListening()) {
      this.voice.stopListening();
    }

    if (this.autoApply()) {
      this.executeDirectly(text, isVoice);
    } else {
      this.textInput = text;
      this.submitText(isVoice);
    }
  }

  private startProcessingTracker(text: string): void {
    this.isProcessing.set(true);
    this.elapsedSeconds.set(0);
    this.showUseGeminiNow.set(false);
    this.currentRunningPrompt = text;

    if (this.processingTimer) {
      clearInterval(this.processingTimer);
    }

    this.processingTimer = setInterval(() => {
      this.elapsedSeconds.update((s) => s + 1);
      if (this.elapsedSeconds() >= 3 && this.providerPreference() !== 'gemini') {
        this.showUseGeminiNow.set(true);
      }
      this.cdr.markForCheck();
    }, 1000);
  }

  private stopProcessingTracker(): void {
    if (this.processingTimer) {
      clearInterval(this.processingTimer);
      this.processingTimer = null;
    }
    this.isProcessing.set(false);
    this.showUseGeminiNow.set(false);
  }

  public useGeminiNow(): void {
    if (!this.currentRunningPrompt) return;
    this.showFeedback('Cambiando inmediatamente a Gemini 3.8 Flash...', 'success');
    this.executeDirectly(this.currentRunningPrompt, false, 'gemini');
  }

  public executeDirectly(prompt: string, isVoice = false, forcedProvider?: 'gemini'): void {
    const text = prompt.trim();
    if (!text) return;

    this.activeSection.set('console');
    this.textInput = text;
    this.lastInputType = isVoice ? 'voice' : 'text';

    if (this.voice.isListening()) {
      this.voice.stopListening();
    }

    this.startProcessingTracker(text);

    const providerPref = forcedProvider || this.providerPreference();
    const isLocalOnly = this.aiTeamStore.isLocalOnly();

    this.aiService.processInput(text, undefined, providerPref, isLocalOnly).subscribe({
      next: (cmd) => {
        this.stopProcessingTracker();
        if (cmd && cmd.action !== 'unknown') {
          const result = this.executor.execute(cmd);
          this.historyService.addEntry(text, this.lastInputType, cmd, 'applied', this.diagramId);
          const badge = this.getSourceBadgeText(cmd.source);
          this.showFeedback(`✓ ${result.message} (${badge})`, 'success', cmd.source);
          this.textInput = '';
          this.pendingCommand.set(null);
          this.voice.clear();
        } else {
          this.showFeedback('⚠️ No se reconoció la orden. Intenta con un formato descriptivo.', 'error');
        }
        this.cdr.markForCheck();
      },
      error: () => {
        this.stopProcessingTracker();
        this.showFeedback('Error al procesar el comando en el lienzo.', 'error');
        this.cdr.markForCheck();
      }
    });
  }

  public submitText(isVoice = false, forcedProvider?: 'gemini'): void {
    const text = this.textInput.trim();
    if (!text || this.isProcessing()) return;

    this.lastInputType = isVoice ? 'voice' : 'text';
    this.startProcessingTracker(text);

    const providerPref = forcedProvider || this.providerPreference();
    const isLocalOnly = this.aiTeamStore.isLocalOnly();

    this.aiService.processInput(text, undefined, providerPref, isLocalOnly).subscribe({
      next: (cmd) => {
        this.pendingCommand.set(cmd);
        this.stopProcessingTracker();
        this.cdr.markForCheck();
      },
      error: () => {
        this.stopProcessingTracker();
        this.showFeedback('Error al interpretar el comando.', 'error');
        this.cdr.markForCheck();
      }
    });
  }

  public applyCommand(): void {
    const cmd = this.pendingCommand();
    const promptText = this.textInput.trim() || cmd?.explanation || 'Comando aplicado';

    if (cmd && cmd.action !== 'unknown') {
      const result = this.executor.execute(cmd);
      this.historyService.addEntry(promptText, this.lastInputType, cmd, 'applied', this.diagramId);
      const badge = this.getSourceBadgeText(cmd.source);
      this.showFeedback(`✓ ${result.message} (${badge})`, 'success', cmd.source);
    }

    this.pendingCommand.set(null);
    this.textInput = '';
    this.voice.clear();
    this.cdr.markForCheck();
  }

  public discardCommand(): void {
    const cmd = this.pendingCommand();
    const promptText = this.textInput.trim() || 'Comando descartado';
    if (cmd) {
      this.historyService.addEntry(promptText, this.lastInputType, cmd, 'discarded', this.diagramId);
    }
    this.pendingCommand.set(null);
    this.textInput = '';
    this.voice.clear();
    this.cdr.markForCheck();
  }

  public reapplyHistoryEntry(entry: AiHistoryEntry): void {
    if (entry.command) {
      const result = this.executor.execute(entry.command);
      const badge = this.getSourceBadgeText(entry.command.source);
      this.showFeedback(`✓ Reaplicado: ${result.message} (${badge})`, 'success', entry.command.source);
      this.historyService.addEntry(entry.prompt, 'text', entry.command, 'applied', this.diagramId);
      this.cdr.markForCheck();
    }
  }

  public clearHistory(): void {
    this.historyService.clearUserHistory(this.diagramId);
    this.cdr.markForCheck();
  }

  public formatTimestamp(val: unknown): string {
    if (!val) return '';
    try {
      const d = new Date(val as string);
      if (isNaN(d.getTime())) return '';
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  }

  public getSourceBadgeText(source?: string): string {
    if (!source) return 'Heurístico';
    if (source === 'local') return '🖥️ Local';
    if (source === 'gemini' || source === 'backend_ai') return '✨ Gemini 3.8 Flash';
    return '⚡ Heurístico';
  }

  private showFeedback(message: string, type: 'success' | 'error', source?: string): void {
    this.executionFeedback.set({ message, type, source });
    if (this.feedbackTimeout) {
      clearTimeout(this.feedbackTimeout);
    }
    this.feedbackTimeout = setTimeout(() => {
      this.executionFeedback.set(null);
      this.cdr.markForCheck();
    }, 4500);
    this.cdr.markForCheck();
  }
}
