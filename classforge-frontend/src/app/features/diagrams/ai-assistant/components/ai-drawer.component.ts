import { Component, Input, Output, EventEmitter, inject, signal, effect, OnInit, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { VoiceRecognitionService } from '../services/voice-recognition.service';
import { AiService } from '../services/ai.service';
import { CommandExecutorService } from '../services/command-executor.service';
import { AiHistoryService } from '../services/ai-history.service';
import { AuthService } from '../../../../core/services/auth.service';
import { UMLCommandResponse } from '../models/ai-command.model';
import { CommandPreviewCardComponent } from './command-preview-card.component';

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
              <span class="text-[10px] px-1.5 py-0.2 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/40 font-semibold flex items-center gap-1">
                <span>🧠</span> Gemini 3.7 Flash + NLU
              </span>
            </h3>
            <span class="text-[10px] text-slate-400">
              Usuario: <strong class="text-slate-300 font-semibold">{{ currentUserName }}</strong>
            </span>
          </div>
        </div>

        <!-- Quick actions, auto-apply toggle & close -->
        <div class="flex items-center gap-1.5">
          <!-- Auto-apply Toggle -->
          <button 
            (click)="autoApply.set(!autoApply())"
            class="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-semibold border transition-all cursor-pointer"
            [ngClass]="autoApply() 
              ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300 shadow-sm' 
              : 'bg-slate-800 border-slate-700 text-slate-400'"
            [title]="autoApply() ? 'Modo directo activado: los comandos se ejecutan al instante en el lienzo' : 'Modo previsualización: requiere confirmación antes de aplicar'"
          >
            <span>{{ autoApply() ? '⚡ Directo' : '👁️ Previa' }}</span>
          </button>

          <!-- Drawer sizes -->
          <button (click)="setDrawerWidth(380)" class="px-1.5 py-0.5 text-[10px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 cursor-pointer" title="Ancho compacto (380px)">S</button>
          <button (click)="setDrawerWidth(520)" class="px-1.5 py-0.5 text-[10px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 cursor-pointer" title="Ancho medio (520px)">M</button>
          <button (click)="setDrawerWidth(720)" class="px-1.5 py-0.5 text-[10px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 cursor-pointer" title="Ancho amplio (720px)">L</button>
          <button (click)="close.emit()" class="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors ml-1 cursor-pointer" title="Cerrar panel">✕</button>
        </div>
      </div>

      <!-- Feedback Toast Notification -->
      <div *ngIf="executionFeedback()" 
           class="mx-3 mt-2.5 p-2.5 rounded-xl border flex items-center justify-between text-xs animate-in fade-in slide-in-from-top-2 shadow-lg z-30"
           [ngClass]="executionFeedback()!.type === 'success' 
             ? 'bg-emerald-950/90 border-emerald-500/50 text-emerald-200' 
             : 'bg-red-950/90 border-red-500/50 text-red-200'">
        <div class="flex items-center gap-2">
          <span class="text-sm">{{ executionFeedback()!.type === 'success' ? '✓' : '⚠️' }}</span>
          <span class="font-semibold">{{ executionFeedback()!.message }}</span>
        </div>
        <button (click)="executionFeedback.set(null)" class="text-slate-400 hover:text-white text-xs px-1 cursor-pointer">✕</button>
      </div>

      <!-- Navigation Tabs -->
      <div class="flex border-b border-slate-800 bg-slate-950/30 text-xs mt-1">
        <button 
          (click)="activeTab = 'prompt'"
          class="flex-1 py-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center justify-center gap-1.5 cursor-pointer"
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
          class="flex-1 py-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center justify-center gap-1.5 relative cursor-pointer"
          [class.text-blue-400]="activeTab === 'history'"
          [class.border-blue-500]="activeTab === 'history'"
          [class.border-transparent]="activeTab !== 'history'"
          [class.text-slate-400]="activeTab !== 'history'"
          [class.hover:text-slate-200]="activeTab !== 'history'"
        >
          <span>📜</span> Mi Historial
          <span *ngIf="historyService.history().length > 0" class="px-1.5 py-0.2 text-[10px] rounded-full bg-blue-600/30 text-blue-300 border border-blue-500/30 font-mono">
            {{ historyService.history().length }}
          </span>
        </button>
        <button 
          (click)="activeTab = 'examples'"
          class="flex-1 py-2.5 px-3 font-semibold transition-colors border-b-2 flex items-center justify-center gap-1.5 cursor-pointer"
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
          
          <!-- Command Preview Card (When in preview mode) -->
          <app-command-preview-card 
            *ngIf="pendingCommand()" 
            [command]="pendingCommand()!" 
            (confirm)="applyCommand()" 
            (discard)="discardCommand()">
          </app-command-preview-card>

          <!-- Voice Listening Feedback & REAL-TIME GHOST TEXT -->
          <div *ngIf="voice.isListening()" class="flex flex-col p-4 bg-slate-850/90 rounded-2xl border border-red-500/40 shadow-2xl space-y-3 animate-in fade-in zoom-in-95 duration-150">
            
            <!-- Voice Status Header with decibels -->
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <div class="relative flex justify-center items-center">
                  <div class="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center text-white text-sm shadow-md animate-pulse">
                    🎙️
                  </div>
                </div>
                <div>
                  <h4 class="text-xs font-bold uppercase tracking-wider text-red-300 leading-tight">
                    {{ voice.hasVoiceActivity() ? 'Escuchando tu voz...' : 'Micrófono Activo' }}
                  </h4>
                  <span class="text-[10.5px] text-slate-400">
                    {{ voice.audioLevel() > 10 ? 'Habla detectada en micrófono' : 'Esperando que hables...' }}
                  </span>
                </div>
              </div>

              <!-- Audio level badge -->
              <div class="flex items-center gap-1.5 text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-900/80 border border-slate-700">
                <span class="text-[9px] text-slate-400">NIVEL:</span>
                <span class="font-bold" [ngClass]="voice.audioLevel() > 10 ? 'text-emerald-400' : 'text-slate-400'">
                  {{ voice.audioLevel() }}%
                </span>
              </div>
            </div>

            <!-- Equalizer Sound Wave Bars -->
            <div class="flex items-end justify-center gap-1.5 h-7 px-3 py-1 bg-slate-950/70 rounded-xl border border-slate-800">
              <div *ngFor="let bar of audioWaveBars; let i = index" 
                   class="w-1.5 rounded-full transition-all duration-75"
                   [ngClass]="voice.audioLevel() > 10 ? 'bg-gradient-to-t from-red-500 to-rose-400' : 'bg-slate-700'"
                   [style.height.px]="getBarHeight(i, voice.audioLevel())">
              </div>
            </div>

            <!-- LIVE TRANSCRIPTION WITH GHOST TEXT DISPLAY (THE REQUESTED FEATURE) -->
            <div class="p-3.5 bg-slate-950/90 rounded-xl border border-blue-500/40 min-h-[5rem] flex flex-col justify-between shadow-inner">
              <div class="text-xs leading-relaxed font-sans select-text">
                <!-- Finalized/Confirmed text in SOLID WHITE -->
                <span *ngIf="voice.transcript()" class="text-white font-semibold text-[13px]">
                  {{ voice.transcript() }}
                </span>

                <!-- In-progress interim speech in SEMI-TRANSPARENT / CASI TRANSPARENTE GHOST TEXT -->
                <span *ngIf="voice.interimTranscript()" 
                      class="text-blue-200/40 opacity-40 italic font-mono text-[13px] animate-pulse ml-1 bg-blue-500/10 px-1 py-0.5 rounded"
                      title="Palabras detectadas en curso (texto fantasma en tiempo real)">
                  {{ voice.interimTranscript() }}
                </span>

                <!-- Placeholder when waiting for user speech -->
                <span *ngIf="!voice.transcript() && !voice.interimTranscript()" class="text-slate-500 italic text-xs">
                  Habla ahora para dictar tu orden... Las palabras que vas diciendo aparecen aquí en <strong>texto casi transparente</strong> en tiempo real.
                </span>

                <!-- Animated typing cursor -->
                <span class="inline-block w-1.5 h-4 bg-blue-400 ml-1 animate-pulse align-middle"></span>
              </div>

              <!-- Legend showing white = confirmed, transparent = interim -->
              <div class="text-[10px] text-slate-400 italic flex items-center justify-between mt-2 pt-2 border-t border-slate-800/80">
                <span class="flex items-center gap-1">
                  <span class="text-white font-bold">Blanco:</span> confirmado | 
                  <span class="text-slate-300/40 font-semibold italic">Semitransparente:</span> habla en curso
                </span>
                <span *ngIf="voice.interimTranscript()" class="text-blue-400 text-[9px] font-mono font-bold uppercase">
                  [Dictado activo]
                </span>
              </div>
            </div>

            <!-- Browser Speech API warning banner (if Brave or Chromium blocks cloud Speech API) -->
            <div *ngIf="voice.isSpeechBlocked()" class="p-2.5 bg-amber-950/40 border border-amber-500/40 rounded-xl text-xs text-amber-200 space-y-1">
              <div class="flex items-center gap-1.5 font-bold text-amber-300">
                <span>🛡️</span> <span>Micrófono detecta sonido ({{ voice.audioLevel() }}%), pero el navegador bloqueó la transcripción en la nube</span>
              </div>
              <p class="text-[11px] text-amber-200/90 leading-tight">
                Brave bloquea la API de voz de Google por defecto. Para habilitar dictado por voz directo en Brave:
              </p>
              <div class="text-[10.5px] text-slate-300 space-y-0.5 font-sans">
                <div>• Abre <code class="bg-slate-900 px-1 py-0.5 rounded text-amber-300 font-mono">brave://settings/privacy</code> y activa <em>"Use Google services for push messaging and speech recognition"</em>.</div>
                <div>• O abre ClassForge en <strong>Microsoft Edge / Chrome</strong> para voz nativa instantánea.</div>
                <div>• O haz clic en cualquier comando rápido de 1-clic a continuación.</div>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="flex items-center gap-2 pt-1">
              <button 
                (click)="stopVoiceAndSubmit()" 
                class="flex-1 py-2 px-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <span>✓</span> Detener y Aplicar al Lienzo
              </button>
              <button 
                (click)="cancelVoice()" 
                class="py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium transition-colors cursor-pointer"
              >
                Cancelar
              </button>
            </div>

            <!-- Quick Voice Commands List (1-Click Execute) -->
            <div class="bg-slate-900/90 p-3 rounded-xl border border-blue-500/30 text-left mt-1">
              <div class="flex items-center justify-between text-[11px] text-blue-300 font-bold mb-1.5">
                <span class="flex items-center gap-1"><span>⚡</span> Comandos Rápidos por Voz (1-Clic):</span>
                <span class="text-[9px] px-1.5 py-0.2 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded font-mono">Mic Activo</span>
              </div>
              <p class="text-[10px] text-slate-400 mb-2 leading-tight">
                Pulsa cualquier opción para aplicarla directamente en el diagrama:
              </p>
              <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
                <button 
                  *ngFor="let opt of offlineVoiceOptions" 
                  (click)="executeDirectly(opt, true)" 
                  class="w-full text-left px-2.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-blue-900/50 border border-slate-700 hover:border-blue-500 text-[11px] text-slate-200 transition-all flex items-center justify-between group cursor-pointer"
                >
                  <span class="font-mono text-[10.5px] truncate mr-2 text-slate-300 group-hover:text-white">"{{ opt }}"</span>
                  <span class="text-emerald-400 text-[10px] font-bold shrink-0 group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
                    <span>✓ Aplicar</span> <span>➔</span>
                  </span>
                </button>
              </div>
            </div>

          </div>

          <!-- Error Alert -->
          <div *ngIf="voice.error()" class="p-3 bg-red-950/40 border border-red-800/50 rounded-xl text-xs text-red-300 flex items-start gap-2">
            <span class="text-base">⚠️</span>
            <div class="flex-1">
              <p class="font-bold">Aviso de Micrófono:</p>
              <p>{{ voice.error() }}</p>
            </div>
            <button (click)="voice.clear()" class="text-red-400 hover:text-white cursor-pointer">✕</button>
          </div>

          <!-- Welcome Info Box (When Idle) -->
          <div *ngIf="!pendingCommand() && !voice.isListening()" class="bg-slate-800/40 p-4 rounded-xl border border-slate-800 text-xs text-slate-400 space-y-2.5">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-white font-bold text-sm">
                <span>⚡</span> Asistente UML Offline & Colaborativo
              </div>
              <span class="text-[10px] font-semibold text-emerald-400 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30">
                Listo
              </span>
            </div>
            <p class="leading-relaxed">
              Dicta por voz con el micrófono o escribe tus peticiones en lenguaje natural para modelar diagramas de clases UML instantáneamente.
            </p>
            <div class="bg-slate-900/80 p-2.5 rounded-lg border border-slate-700/50 font-mono text-[11px] text-blue-300 leading-relaxed cursor-pointer hover:border-blue-500/50 transition-colors"
                 (click)="executeDirectly('crea una tabla con el nombre Producto con 3 atributos de nombres precio, stock, codigo y que se asocie a Categoria con la cardinalidad 1..*', false)"
                 title="Haz clic para probar esta consulta">
              "crea una tabla con el nombre Producto con 3 atributos de nombres precio, stock, codigo y que se asocie a Categoria con la cardinalidad 1..*"
              <span class="block text-[9px] text-emerald-400 mt-1 font-sans font-bold">➔ Clic para probar</span>
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
              class="text-[11px] text-red-400 hover:text-red-300 hover:underline cursor-pointer"
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
                  <span>• {{ formatTimestamp(item.timestamp) }}</span>
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
                  (click)="executeDirectly(item.prompt, item.inputType === 'voice')" 
                  class="text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1 cursor-pointer"
                >
                  <span>↻</span> Re-ejecutar en lienzo
                </button>
                <button 
                  (click)="textInput = item.prompt; activeTab = 'prompt'" 
                  class="text-slate-400 hover:text-slate-200 cursor-pointer"
                >
                  Cargar en prompt
                </button>
              </div>
            </div>
          </div>
        </ng-container>

        <!-- TAB 3: EXAMPLES -->
        <ng-container *ngIf="activeTab === 'examples'">
          <h4 class="text-xs font-bold text-slate-300 mb-2">Ejemplos de Modelado UML (1-Clic para Aplicar):</h4>
          
          <div class="space-y-2 max-h-[70vh] overflow-y-auto pr-1 custom-scrollbar">
            <div 
              *ngFor="let ex of complexExamples"
              class="p-3 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-blue-500/50 rounded-xl cursor-pointer transition-all flex flex-col gap-1 group"
              (click)="executeDirectly(ex.prompt, false)"
            >
              <div class="flex items-center justify-between">
                <strong class="text-xs text-blue-400 group-hover:text-blue-300">{{ ex.title }}</strong>
                <span class="text-[10px] text-emerald-400 font-bold group-hover:translate-x-0.5 transition-transform">✓ Aplicar ➔</span>
              </div>
              <p class="text-[11px] text-slate-300 font-mono leading-relaxed">
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
            (click)="executeDirectly(suggestion, false)"
          >
            {{ suggestion }}
          </button>
        </div>

        <!-- Input Bar with Voice Toggle, Ghost Text overlay & Submit -->
        <div class="flex items-center gap-2">
          <div class="relative flex-1">
            
            <!-- Real-time Ghost Text inside the input field while speaking -->
            <div *ngIf="voice.isListening() && (voice.transcript() || voice.interimTranscript())" 
                 class="absolute inset-0 px-3.5 py-2.5 text-xs pointer-events-none flex items-center overflow-hidden whitespace-nowrap z-10">
              <span class="text-white font-medium">{{ voice.transcript() }}</span>
              <span class="text-blue-200/40 opacity-40 italic font-mono ml-1 animate-pulse">{{ voice.interimTranscript() }}</span>
            </div>

            <input 
              type="text" 
              [(ngModel)]="textInput" 
              (keyup.enter)="handleSubmit()"
              [placeholder]="voice.isListening() ? '🎙️ Habla ahora (tu voz aparecerá aquí en tiempo real)...' : 'Ej: crea una tabla Producto con 3 atributos...'"
              class="w-full bg-slate-900 border border-slate-700 focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all pr-8"
              [class.text-transparent]="voice.isListening() && (voice.transcript() || voice.interimTranscript())"
              [disabled]="isProcessing()"
            />
            <button 
              *ngIf="textInput" 
              (click)="textInput = ''" 
              class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs cursor-pointer z-20"
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
            [title]="voice.isListening() ? 'Detener dictado por voz y aplicar' : 'Iniciar reconocimiento por voz'"
          >
            🎙️
          </button>

          <!-- Submit Button -->
          <button 
            (click)="handleSubmit()"
            class="px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold text-xs shadow-lg transition-all flex items-center justify-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            [disabled]="isProcessing() || (!textInput.trim() && !voice.getBestTranscript().trim())"
            [title]="autoApply() ? 'Ejecutar directamente en el lienzo' : 'Interpretar y previsualizar'"
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
  public drawerWidth = 460;
  public autoApply = signal<boolean>(true);
  private isResizing = false;

  public textInput = '';
  public pendingCommand = signal<UMLCommandResponse | null>(null);
  public isProcessing = signal<boolean>(false);
  public executionFeedback = signal<{ message: string; type: 'success' | 'error' } | null>(null);
  private feedbackTimeout: any = null;
  private lastInputType: 'voice' | 'text' = 'text';

  public audioWaveBars = [0, 1, 2, 3, 4, 5, 6];

  public quickSuggestions = [
    'Crear tienda e-commerce completa con Cliente, Pedido, DetallePedido, Producto, Categoria',
    'Crear sistema hospitalario con Medico, Paciente, CitaMedica, Receta y Medicamento',
    'Crear sistema bancario con Cliente, CuentaBancaria, CuentaAhorro, Transaccion',
    'Crear tabla Producto con precio, stock, codigo y asociar a Categoria 1..*',
    'Hacer que Administrador herede de Usuario',
    'Crear sistema universitario con Estudiante, Docente, Materia, Inscripcion',
    'Crear sistema de delivery con Restaurante, Plato, PedidoDelivery, Repartidor'
  ];

  public offlineVoiceOptions = [
    'Crear clase Factura con total, fecha, nroFactura',
    'Crear tabla Producto con precio, stock, codigo y asociar a Categoria 1..*',
    'Crear clases Usuario, Rol, Permiso, Perfil',
    'Hacer que Administrador herede de Usuario',
    'Crear composicion entre Factura y DetalleFactura 1 a muchos',
    'Diseñar tienda e-commerce completa con Cliente, Pedido, DetallePedido, Producto, Categoria',
    'Diseñar sistema bancario con Cliente, CuentaBancaria, CuentaAhorro, Transaccion',
    'Diseñar sistema universitario con Estudiante, Docente, Materia, Inscripcion',
    'Diseñar sistema hospitalario con Medico, Paciente, CitaMedica, Receta',
    'Diseñar sistema de delivery con Restaurante, Plato, PedidoDelivery, Repartidor',
    'Diseñar sistema de inventario con Proveedor, Producto, Almacen, Movimiento'
  ];

  public complexExamples = [
    {
      title: 'Sistema E-Commerce Completo (1 solo Prompt)',
      prompt: 'Diseñar tienda e-commerce con Cliente (id, nombre, email, direccion), Pedido (id, codigo, fecha, total, estado), DetallePedido (id, cantidad, precioUnitario), Producto (id, nombre, precio, stock) y Categoria (id, nombre, descripcion). Composición de Pedido a DetallePedido 1 a 1..*, asociación de DetallePedido a Producto * a 1, agregación de Producto a Categoria * a 1, y asociación de Cliente a Pedido 1 a 0..*'
    },
    {
      title: 'Sistema Hospitalario / Clínica Médica (1 solo Prompt)',
      prompt: 'Diseñar sistema de hospital con Medico (id, nombre, especialidad, nroColegiado), Paciente (id, nombre, ci, historialClinico), CitaMedica (id, fecha, hora, estado, motivo), Receta (id, fechaEmision, indicaciones) y Medicamento (id, nombreComercial, dosis). Medico se asocia 1 a 0..* con CitaMedica, Paciente se asocia 1 a 0..* con CitaMedica, CitaMedica tiene composición 1 a 0..1 con Receta, y Receta tiene agregación 1 a 1..* con Medicamento'
    },
    {
      title: 'Sistema Bancario y Financiero con Herencia (1 solo Prompt)',
      prompt: 'Diseñar sistema bancario con Cliente (id, ci, nombre, telefono), CuentaBancaria (id, numeroCuenta, saldo, tipoMoneda), CuentaAhorro (tasaInteres), CuentaCorriente (limiteSobregiro), Transaccion (id, fecha, monto, tipo). CuentaAhorro y CuentaCorriente heredan de CuentaBancaria. Cliente tiene asociación 1 a 1..* con CuentaBancaria, y CuentaBancaria tiene composición 1 a 0..* con Transaccion'
    },
    {
      title: 'Sistema Universitario / Académico (1 solo Prompt)',
      prompt: 'Diseñar sistema universitario con Estudiante (id, matricula, nombre, semestre), Docente (id, codigoDocente, nombre, especialidad), Materia (id, sigla, nombre, creditos), e Inscripcion (id, fecha, notaFinal, estado). Estudiante se asocia 1 a 0..* con Inscripcion, Materia se asocia 1 a 0..* con Inscripcion, y Docente se asocia 1 a 1..* con Materia'
    },
    {
      title: 'Sistema de Delivery / Restaurante (1 solo Prompt)',
      prompt: 'Crear sistema de delivery con Restaurante (id, nombre, direccion), Plato (id, nombre, precio, categoria), PedidoDelivery (id, nroPedido, direccionEntrega, total), Repartidor (id, nombre, vehiculo, telefono) y Cliente (id, nombre, telefono). Restaurante tiene composición 1 a 1..* con Plato, Cliente se asocia 1 a 0..* con PedidoDelivery, PedidoDelivery tiene agregación * a 1 con Repartidor, y PedidoDelivery tiene asociación * a 1 con Restaurante'
    },
    {
      title: 'Crear tabla con atributos y cardinalidad',
      prompt: 'crea una tabla con el nombre Producto con 3 atributos de nombres precio, stock, codigo y que se asocie a Categoria con la cardinalidad 1..*'
    },
    {
      title: 'Crear múltiples clases a la vez',
      prompt: 'crear clases Usuario, Rol, Permiso, Perfil'
    },
    {
      title: 'Crear clase con tipos explícitos y visibilidad',
      prompt: 'crear clase Factura con atributos id:Long, total:double, fecha:Date, - nroFactura:String y asociar a Cliente con cardinalidad *..1'
    },
    {
      title: 'Herencia / Generalización',
      prompt: 'hacer que Administrador herede de Usuario'
    },
    {
      title: 'Composición con cardinalidad',
      prompt: 'crear composicion entre Factura y DetalleFactura con cardinalidad 1..1 a 1..*'
    },
    {
      title: 'Agregación entre entidades',
      prompt: 'crear agregacion entre Departamento y Empleado con cardinalidad 1 a muchos'
    },
    {
      title: 'Agregar método con parámetros y retorno',
      prompt: 'agregar metodo calcularTotal(descuento: float): double a Factura'
    },
    {
      title: 'Sistema de Inventario / Almacén',
      prompt: 'diseñar sistema de inventario con Producto, Proveedor, Almacen, Movimiento'
    }
  ];

  constructor() {
    // Automatically capture speech updates into textInput if user was not manually editing
    effect(() => {
      const isListening = this.voice.isListening();
      const best = this.voice.getBestTranscript();
      if (!isListening && best && !this.textInput.trim()) {
        setTimeout(() => {
          this.textInput = best;
        }, 0);
      }
    });
  }

  get currentUserName(): string {
    const user = this.authService.getCurrentUser();
    return user?.name || user?.email || 'Usuario';
  }

  getBarHeight(index: number, level: number): number {
    const weights = [0.4, 0.7, 1.0, 0.9, 1.0, 0.7, 0.4];
    const w = weights[index % weights.length];
    return Math.max(5, Math.min(26, Math.round(5 + (level * 0.22 * w))));
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
  }

  ngOnDestroy(): void {
    if (this.voice.isListening()) {
      this.voice.stopListening();
    }
    if (this.feedbackTimeout) {
      clearTimeout(this.feedbackTimeout);
    }
  }

  formatTimestamp(val: any): string {
    if (!val) return '';
    try {
      const d = new Date(val);
      if (isNaN(d.getTime())) return '';
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
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

  cancelVoice(): void {
    this.voice.stopListening();
    this.voice.clear();
  }

  stopVoiceAndSubmit(): void {
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
      if (this.voice.hasVoiceActivity() && this.voice.isSpeechBlocked()) {
        this.showFeedback('Micrófono detectó voz, pero el navegador bloqueó la transcripción. Revisa la indicación de Brave o escribe tu consulta.', 'error');
      } else {
        this.showFeedback('No se detectó ninguna palabra hablada.', 'error');
      }
    }
  }

  handleSubmit(): void {
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

  useExample(prompt: string): void {
    this.textInput = prompt;
    this.activeTab = 'prompt';
    if (this.autoApply()) {
      this.executeDirectly(prompt, false);
    } else {
      this.submitText(false);
    }
  }

  /**
   * Direct execution of command: parses, applies immediately to canvas, auto-fits view, and adds to user history.
   */
  executeDirectly(prompt: string, isVoice = false): void {
    const text = prompt.trim();
    if (!text) return;

    this.activeTab = 'prompt';
    this.textInput = text;
    this.lastInputType = isVoice ? 'voice' : 'text';
    this.isProcessing.set(true);

    if (this.voice.isListening()) {
      this.voice.stopListening();
    }

    this.aiService.processInput(text).subscribe({
      next: (cmd) => {
        this.isProcessing.set(false);
        if (cmd && cmd.action !== 'unknown') {
          const result = this.executor.execute(cmd);
          this.historyService.addEntry(text, this.lastInputType, cmd, 'applied', this.diagramId);
          this.showFeedback(`✓ ${result.message}`, 'success');
          this.textInput = '';
          this.pendingCommand.set(null);
          this.voice.clear();
        } else {
          this.showFeedback('⚠️ No se reconoció la orden. Intenta: "crea una tabla Producto con 3 atributos precio, stock, codigo y asociar a Categoria 1..*"', 'error');
        }
      },
      error: () => {
        this.isProcessing.set(false);
        this.showFeedback('Error al procesar el comando en el lienzo.', 'error');
      }
    });
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
        this.showFeedback('Error al interpretar el comando.', 'error');
      }
    });
  }

  applyCommand(): void {
    const cmd = this.pendingCommand();
    const promptText = this.textInput.trim() || cmd?.explanation || 'Comando aplicado';

    if (cmd && cmd.action !== 'unknown') {
      const result = this.executor.execute(cmd);
      this.historyService.addEntry(promptText, this.lastInputType, cmd, 'applied', this.diagramId);
      this.showFeedback(`✓ ${result.message}`, 'success');
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
      this.showFeedback('Comando descartado.', 'error');
    }
    this.pendingCommand.set(null);
    this.textInput = '';
    this.voice.clear();
  }

  private showFeedback(message: string, type: 'success' | 'error'): void {
    if (this.feedbackTimeout) clearTimeout(this.feedbackTimeout);
    this.executionFeedback.set({ message, type });
    this.feedbackTimeout = setTimeout(() => {
      this.executionFeedback.set(null);
    }, 4500);
  }
}

