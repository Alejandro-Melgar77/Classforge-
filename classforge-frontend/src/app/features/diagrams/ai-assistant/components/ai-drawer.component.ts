import {
  Component,
  Input,
  Output,
  EventEmitter,
  inject,
  signal,
  effect,
  OnInit,
  OnDestroy,
  HostListener,
  ChangeDetectorRef
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { VoiceRecognitionService } from '../services/voice-recognition.service';
import { AiService } from '../services/ai.service';
import { CommandExecutorService } from '../services/command-executor.service';
import { AiHistoryService } from '../services/ai-history.service';
import { AuthService } from '../../../../core/services/auth.service';
import { UMLCommandResponse } from '../models/ai-command.model';
import { CommandPreviewCardComponent } from './command-preview-card.component';
import { AiChatService } from '../../../ai-chat/services/ai-chat.service';
import {
  AiMessage,
  AiRoleId,
  AI_ROLE_THEMES,
  AiRoleTheme
} from '../../../ai-chat/models/ai-conversation.model';

type DrawerTab = 'prompt' | 'history' | 'grupo' | 'examples';

@Component({
  selector: 'app-ai-drawer',
  standalone: true,
  imports: [CommonModule, FormsModule, CommandPreviewCardComponent],
  template: `
    <div 
      class="ai-drawer fixed right-0 top-0 h-full bg-slate-900 border-l border-slate-700/80 shadow-2xl transition-transform duration-300 z-50 flex flex-col select-none text-slate-200 max-w-[96vw]"
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

      <!-- Header Principal -->
      <div class="p-3 border-b border-slate-800 bg-slate-950/80 flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <!-- Title & Model badge -->
          <div class="flex items-center gap-2">
            <div 
              class="w-8 h-8 rounded-lg flex items-center justify-center text-white text-base shadow-md transition-colors"
              [style.background]="aiParticipativeEnabled() && activeRoleTheme ? activeRoleTheme.borderColor : 'linear-gradient(135deg, #2563eb, #7c3aed)'"
            >
              {{ aiParticipativeEnabled() && activeRoleTheme ? activeRoleTheme.emoji : '✨' }}
            </div>
            <div>
              <h3 class="text-xs font-bold text-white flex items-center gap-1.5 leading-tight">
                {{ aiParticipativeEnabled() && activeRoleTheme ? activeRoleTheme.label : 'Asistente IA UML' }}
                <button 
                  (click)="showModelPicker.set(!showModelPicker())"
                  class="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/40 font-semibold flex items-center gap-1 hover:bg-blue-500/30 transition-colors cursor-pointer"
                  title="Cambiar modelo de IA"
                >
                  <span>🧠</span> {{ getModelShortName(selectedModel) }} ▾
                </button>
              </h3>
              <span class="text-[10px] text-slate-400">
                Usuario: <strong class="text-slate-300 font-semibold">{{ currentUserName }}</strong>
              </span>
            </div>
          </div>

          <!-- Quick actions & Settings Toggle -->
          <div class="flex items-center gap-1">
            <!-- Participative AI Quick Toggle -->
            <button 
              (click)="toggleAiParticipative()"
              class="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-semibold border transition-all cursor-pointer"
              [ngClass]="aiParticipativeEnabled() 
                ? 'bg-purple-950/80 border-purple-500/50 text-purple-300 shadow-sm animate-pulse' 
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-300'"
              title="Activar / Desactivar IA como integrante del equipo"
            >
              <span>{{ aiParticipativeEnabled() ? '🤖 Miembro Activo' : '👤 IA Pasiva' }}</span>
            </button>

            <!-- Auto-apply Toggle -->
            <button 
              (click)="autoApply.set(!autoApply())"
              class="flex items-center gap-1 px-1.5 py-1 rounded-lg text-[10px] font-semibold border transition-all cursor-pointer"
              [ngClass]="autoApply() 
                ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300' 
                : 'bg-slate-800 border-slate-700 text-slate-400'"
              [title]="autoApply() ? 'Modo directo: se aplica inmediatamente al lienzo' : 'Modo previa: requiere confirmación'"
            >
              <span>{{ autoApply() ? '⚡ Directo' : '👁️ Previa' }}</span>
            </button>

            <!-- Settings Button ⚙️ -->
            <button 
              (click)="showConfigPanel.set(!showConfigPanel())"
              class="p-1.5 rounded-lg border transition-colors cursor-pointer"
              [class.bg-blue-600]="showConfigPanel()"
              [class.text-white]="showConfigPanel()"
              [class.border-blue-500]="showConfigPanel()"
              [class.bg-slate-800]="!showConfigPanel()"
              [class.text-slate-400]="!showConfigPanel()"
              [class.border-slate-700]="!showConfigPanel()"
              title="Configuración de Roles e IA"
            >
              ⚙️
            </button>

            <!-- Width Presets -->
            <button (click)="setDrawerWidth(400)" class="px-1.5 py-0.5 text-[9px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 cursor-pointer">S</button>
            <button (click)="setDrawerWidth(540)" class="px-1.5 py-0.5 text-[9px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 cursor-pointer">M</button>
            <button (click)="setDrawerWidth(760)" class="px-1.5 py-0.5 text-[9px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 cursor-pointer">L</button>
            <button (click)="close.emit()" class="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors cursor-pointer" title="Cerrar panel">✕</button>
          </div>
        </div>

        <!-- Role Badge Banner (When Participative AI is active) -->
        <div 
          *ngIf="aiParticipativeEnabled() && activeRoleTheme"
          class="px-2.5 py-1.5 rounded-lg border text-xs flex items-center justify-between transition-all"
          [style.background]="activeRoleTheme.bgColor"
          [style.border-color]="activeRoleTheme.borderColor"
          [style.color]="activeRoleTheme.textColor"
        >
          <div class="flex items-center gap-1.5 font-bold">
            <span class="text-sm">{{ activeRoleTheme.emoji }}</span>
            <span>Modo {{ activeRoleTheme.label }} Activo:</span>
            <span class="font-normal opacity-90 text-[11px] truncate">{{ activeRoleTheme.description }}</span>
          </div>
          <button 
            (click)="showConfigPanel.set(true)" 
            class="text-[10px] underline hover:opacity-80 cursor-pointer shrink-0 ml-1"
          >
            Cambiar Rol
          </button>
        </div>

        <!-- Model Picker Dropdown (Flyout) -->
        <div *ngIf="showModelPicker()" class="p-2.5 bg-slate-900 border border-blue-500/40 rounded-xl space-y-1.5 animate-in fade-in text-xs shadow-xl">
          <div class="flex items-center justify-between text-slate-300 font-semibold text-[11px]">
            <span>🧠 Seleccionar Modelo de Google Gemini</span>
            <button (click)="showModelPicker.set(false)" class="text-slate-500 hover:text-white">✕</button>
          </div>
          <div class="grid grid-cols-2 gap-1.5">
            <button 
              *ngFor="let m of availableModels"
              (click)="selectModel(m.id)"
              class="p-2 rounded-lg border text-left transition-all cursor-pointer"
              [class.bg-blue-950]="selectedModel === m.id"
              [class.border-blue-500]="selectedModel === m.id"
              [class.text-blue-300]="selectedModel === m.id"
              [class.bg-slate-800]="selectedModel !== m.id"
              [class.border-slate-700]="selectedModel !== m.id"
              [class.text-slate-300]="selectedModel !== m.id"
            >
              <div class="font-bold text-[11px]">{{ m.label }}</div>
              <div class="text-[9px] text-slate-400">{{ m.badge }}</div>
            </button>
          </div>
        </div>

        <!-- Config Panel ⚙️ (Slide Down) -->
        <div *ngIf="showConfigPanel()" class="p-3 bg-slate-950/90 border border-purple-500/40 rounded-xl space-y-2.5 animate-in fade-in text-xs shadow-2xl">
          <div class="flex items-center justify-between border-b border-slate-800 pb-1.5">
            <h4 class="font-bold text-white flex items-center gap-1.5">
              <span>🎭</span> IA Participativa como Integrante del Equipo
            </h4>
            <button (click)="showConfigPanel.set(false)" class="text-slate-400 hover:text-white cursor-pointer">✕</button>
          </div>

          <!-- Switch to enable/disable participative AI -->
          <div class="flex items-center justify-between bg-slate-900/80 p-2 rounded-lg border border-slate-800">
            <div>
              <span class="font-semibold text-slate-200 block">Incorporar IA al equipo de trabajo</span>
              <span class="text-[10px] text-slate-400">La IA asume un rol formal y participa en decisiones de arquitectura y código</span>
            </div>
            <button 
              (click)="toggleAiParticipative()"
              class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer shrink-0 ml-2"
              [class.bg-purple-600]="aiParticipativeEnabled()"
              [class.bg-slate-700]="!aiParticipativeEnabled()"
            >
              <span 
                class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform"
                [class.translate-x-6]="aiParticipativeEnabled()"
                [class.translate-x-1]="!aiParticipativeEnabled()"
              ></span>
            </button>
          </div>

          <!-- Role Selector Grid -->
          <div *ngIf="aiParticipativeEnabled()" class="space-y-1.5">
            <span class="text-[11px] font-semibold text-slate-300 block">Elige el rol especializado de la IA:</span>
            <div class="grid grid-cols-2 gap-2">
              <button 
                *ngFor="let r of availableRoles"
                (click)="selectRole(r.id)"
                class="p-2.5 rounded-xl border text-left transition-all cursor-pointer relative overflow-hidden group"
                [style.background]="activeAiRole() === r.id ? r.theme.bgColor : '#1e293b'"
                [style.border-color]="activeAiRole() === r.id ? r.theme.borderColor : '#334155'"
                [style.color]="activeAiRole() === r.id ? r.theme.textColor : '#cbd5e1'"
              >
                <div class="flex items-center gap-1.5 font-bold text-xs mb-1">
                  <span class="text-base">{{ r.theme.emoji }}</span>
                  <span>{{ r.theme.label }}</span>
                  <span *ngIf="activeAiRole() === r.id" class="ml-auto text-xs">✓</span>
                </div>
                <p class="text-[10px] leading-tight opacity-80">{{ r.theme.description }}</p>
              </button>
            </div>
          </div>

          <!-- Optional API Key Input -->
          <div class="pt-1.5 border-t border-slate-800">
            <div class="flex items-center justify-between mb-1">
              <span class="text-[10px] text-slate-400">Clave API de Google Gemini (opcional / personal):</span>
              <span *ngIf="hasCustomApiKey" class="text-[9px] text-emerald-400 font-mono">Personalizada guardada</span>
            </div>
            <div class="flex gap-1.5">
              <input 
                type="password"
                [(ngModel)]="apiKeyInput"
                placeholder="AIzaSy... (deja vacío para usar clave de servidor)"
                class="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-[11px] text-slate-200 focus:outline-none focus:border-blue-500"
              />
              <button 
                (click)="saveApiKey()"
                class="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-[10px] font-bold cursor-pointer"
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Feedback Toast Notification -->
      <div 
        *ngIf="executionFeedback()" 
        class="mx-3 mt-2 p-2.5 rounded-xl border flex items-center justify-between text-xs animate-in fade-in slide-in-from-top-2 shadow-lg z-30"
        [ngClass]="executionFeedback()!.type === 'success' 
          ? 'bg-emerald-950/90 border-emerald-500/50 text-emerald-200' 
          : 'bg-red-950/90 border-red-500/50 text-red-200'"
      >
        <div class="flex items-center gap-2">
          <span class="text-sm">{{ executionFeedback()!.type === 'success' ? '✓' : '⚠️' }}</span>
          <span class="font-semibold">{{ executionFeedback()!.message }}</span>
        </div>
        <button (click)="executionFeedback.set(null)" class="text-slate-400 hover:text-white text-xs px-1 cursor-pointer">✕</button>
      </div>

      <!-- Navigation Tabs (4 TABS) -->
      <div class="flex border-b border-slate-800 bg-slate-950/50 text-xs">
        <button 
          (click)="setTab('prompt')"
          class="flex-1 py-2.5 px-2 font-semibold transition-colors border-b-2 flex items-center justify-center gap-1 cursor-pointer text-center"
          [class.text-blue-400]="activeTab === 'prompt'"
          [class.border-blue-500]="activeTab === 'prompt'"
          [class.border-transparent]="activeTab !== 'prompt'"
          [class.text-slate-400]="activeTab !== 'prompt'"
          [class.hover:text-slate-200]="activeTab !== 'prompt'"
        >
          <span>🤖</span> <span>Asistente</span>
        </button>

        <button 
          (click)="setTab('history')"
          class="flex-1 py-2.5 px-2 font-semibold transition-colors border-b-2 flex items-center justify-center gap-1 cursor-pointer text-center"
          [class.text-blue-400]="activeTab === 'history'"
          [class.border-blue-500]="activeTab === 'history'"
          [class.border-transparent]="activeTab !== 'history'"
          [class.text-slate-400]="activeTab !== 'history'"
          [class.hover:text-slate-200]="activeTab !== 'history'"
        >
          <span>💬</span> <span>Mi Chat</span>
          <span *ngIf="historyService.history().length > 0" class="px-1 py-0.2 text-[9px] rounded-full bg-blue-600/30 text-blue-300 font-mono">
            {{ historyService.history().length }}
          </span>
        </button>

        <button 
          (click)="setTab('grupo')"
          class="flex-1 py-2.5 px-2 font-semibold transition-colors border-b-2 flex items-center justify-center gap-1 cursor-pointer text-center relative"
          [class.text-purple-400]="activeTab === 'grupo'"
          [class.border-purple-500]="activeTab === 'grupo'"
          [class.border-transparent]="activeTab !== 'grupo'"
          [class.text-slate-400]="activeTab !== 'grupo'"
          [class.hover:text-slate-200]="activeTab !== 'grupo'"
        >
          <span>👥</span> <span>Grupo</span>
          <span *ngIf="groupMessages().length > 0" class="px-1.5 py-0.2 text-[9px] rounded-full bg-purple-600/30 text-purple-300 font-mono border border-purple-500/30">
            {{ groupMessages().length }}
          </span>
        </button>

        <button 
          (click)="setTab('examples')"
          class="flex-1 py-2.5 px-2 font-semibold transition-colors border-b-2 flex items-center justify-center gap-1 cursor-pointer text-center"
          [class.text-blue-400]="activeTab === 'examples'"
          [class.border-blue-500]="activeTab === 'examples'"
          [class.border-transparent]="activeTab !== 'examples'"
          [class.text-slate-400]="activeTab !== 'examples'"
          [class.hover:text-slate-200]="activeTab !== 'examples'"
        >
          <span>💡</span> <span>Ejemplos</span>
        </button>
      </div>

      <!-- Main Body Container with guaranteed scrollable viewport -->
      <div 
        class="flex-1 overflow-y-auto p-3.5 flex flex-col gap-3 select-text custom-scrollbar"
        style="min-height: 0;"
      >
        
        <!-- ═══ TAB 1: ASISTENTE PROMPT ═══ -->
        <ng-container *ngIf="activeTab === 'prompt'">
          
          <!-- Command Preview Card (When in preview mode) -->
          <app-command-preview-card 
            *ngIf="pendingCommand()" 
            [command]="pendingCommand()!" 
            (confirm)="applyCommand()" 
            (discard)="discardCommand()">
          </app-command-preview-card>

          <!-- Voice Listening Feedback & Real-time Ghost Text -->
          <div *ngIf="voice.isListening()" class="flex flex-col p-3.5 bg-slate-850/90 rounded-2xl border border-red-500/40 shadow-2xl space-y-2.5 animate-in fade-in zoom-in-95 duration-150">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <div class="w-7 h-7 bg-red-600 rounded-full flex items-center justify-center text-white text-xs shadow-md animate-pulse">
                  🎙️
                </div>
                <div>
                  <h4 class="text-xs font-bold uppercase tracking-wider text-red-300 leading-tight">
                    {{ voice.hasVoiceActivity() ? 'Escuchando tu voz...' : 'Micrófono Activo' }}
                  </h4>
                  <span class="text-[10px] text-slate-400">
                    {{ voice.audioLevel() > 10 ? 'Habla detectada' : 'Esperando que hables...' }}
                  </span>
                </div>
              </div>
              <div class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-900 border border-slate-700">
                <span class="text-slate-400">NIVEL:</span> <strong [ngClass]="voice.audioLevel() > 10 ? 'text-emerald-400' : 'text-slate-400'">{{ voice.audioLevel() }}%</strong>
              </div>
            </div>

            <!-- Equalizer Wave Bars -->
            <div class="flex items-end justify-center gap-1.5 h-6 px-3 py-1 bg-slate-950 rounded-xl border border-slate-800">
              <div *ngFor="let bar of audioWaveBars; let i = index" 
                   class="w-1.5 rounded-full transition-all duration-75"
                   [ngClass]="voice.audioLevel() > 10 ? 'bg-gradient-to-t from-red-500 to-rose-400' : 'bg-slate-700'"
                   [style.height.px]="getBarHeight(i, voice.audioLevel())">
              </div>
            </div>

            <!-- Ghost text live display -->
            <div class="p-3 bg-slate-950 rounded-xl border border-blue-500/40 min-h-[4rem] flex flex-col justify-between shadow-inner">
              <div class="text-xs leading-relaxed font-sans">
                <span *ngIf="voice.transcript()" class="text-white font-semibold text-[12px]">
                  {{ voice.transcript() }}
                </span>
                <span *ngIf="voice.interimTranscript()" class="text-blue-200/40 opacity-40 italic font-mono text-[12px] animate-pulse ml-1 bg-blue-500/10 px-1 py-0.5 rounded">
                  {{ voice.interimTranscript() }}
                </span>
                <span *ngIf="!voice.transcript() && !voice.interimTranscript()" class="text-slate-500 italic text-[11px]">
                  Habla ahora... las palabras que dices aparecen aquí en tiempo real.
                </span>
                <span class="inline-block w-1.5 h-3.5 bg-blue-400 ml-1 animate-pulse align-middle"></span>
              </div>
            </div>

            <div class="flex items-center gap-2 pt-1">
              <button 
                (click)="stopVoiceAndSubmit()" 
                class="flex-1 py-1.5 px-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold transition-all shadow cursor-pointer"
              >
                ✓ Aplicar al Lienzo
              </button>
              <button 
                (click)="cancelVoice()" 
                class="py-1.5 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium cursor-pointer"
              >
                Cancelar
              </button>
            </div>
          </div>

          <!-- Welcome Info Box (When Idle) -->
          <div *ngIf="!pendingCommand() && !voice.isListening()" class="bg-slate-850/60 p-3.5 rounded-xl border border-slate-800 text-xs text-slate-400 space-y-2">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-white font-bold">
                <span>⚡</span> Asistente de Modelado UML
              </div>
              <span class="text-[10px] font-semibold text-emerald-400 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30">
                Online: {{ getModelShortName(selectedModel) }}
              </span>
            </div>
            <p class="leading-relaxed text-[11px]">
              Escribe o dicta en lenguaje natural para modelar diagramas de clases instantáneamente.
            </p>
            <div 
              class="bg-slate-900/90 p-2.5 rounded-lg border border-slate-700/60 font-mono text-[11px] text-blue-300 cursor-pointer hover:border-blue-500 transition-colors"
              (click)="executeDirectly('crea una tabla Producto con atributos id, precio, stock, codigo y asociar a Categoria 1..*')"
              title="Haz clic para probar esta orden"
            >
              "crea una tabla Producto con atributos id, precio, stock, codigo y asociar a Categoria 1..*"
              <span class="block text-[9px] text-emerald-400 mt-1 font-sans font-bold">➔ Clic para probar comando</span>
            </div>
          </div>
        </ng-container>

        <!-- ═══ TAB 2: MI CHAT (HISTORIAL PERSONAL + REMOTO) ═══ -->
        <ng-container *ngIf="activeTab === 'history'">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <span>💬</span> Mis Conversaciones con la IA
            </h4>
            <div class="flex items-center gap-2">
              <button 
                *ngIf="projectId" 
                (click)="loadMyHistory()" 
                class="text-[10px] text-blue-400 hover:text-blue-300 cursor-pointer flex items-center gap-1"
                title="Recargar historial persistente"
              >
                <span>↻</span> Sincronizar
              </button>
              <button 
                *ngIf="historyService.history().length > 0"
                (click)="historyService.clearUserHistory(diagramId)" 
                class="text-[10px] text-red-400 hover:text-red-300 hover:underline cursor-pointer"
                title="Limpiar consultas de esta sesión"
              >
                Limpiar sesión
              </button>
            </div>
          </div>

          <!-- Historial de la sesión activa en el lienzo -->
          <div *ngIf="historyService.history().length > 0" class="space-y-2 mb-3">
            <div class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Consultas en esta sesión:</div>
            <div 
              *ngFor="let item of historyService.history()" 
              class="p-2.5 bg-slate-800/80 border border-slate-700/80 rounded-xl hover:border-slate-600 transition-all text-xs flex flex-col gap-1.5"
            >
              <div class="flex items-center justify-between text-[10px] text-slate-400">
                <span class="flex items-center gap-1 font-semibold">
                  <span *ngIf="item.inputType === 'voice'" class="text-red-400">🎙️ Voz</span>
                  <span *ngIf="item.inputType === 'text'" class="text-blue-400">⌨️ Texto</span>
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

              <p *ngIf="item.resultSummary" class="text-[11px] text-slate-400 font-mono bg-slate-900/80 p-1.5 rounded border border-slate-800">
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
                  (click)="textInput = item.prompt; setTab('prompt')" 
                  class="text-slate-400 hover:text-slate-200 cursor-pointer"
                >
                  Cargar en prompt
                </button>
              </div>
            </div>
          </div>

          <!-- Historial persistente guardado en base de datos -->
          <div *ngIf="myPersistentMessages().length > 0" class="space-y-2">
            <div class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Historial guardado en el proyecto:</div>
            <div 
              *ngFor="let msg of myPersistentMessages()"
              class="p-2.5 rounded-xl border text-xs flex flex-col gap-1"
              [class.bg-slate-800]="msg.author_type === 'user'"
              [class.border-slate-700]="msg.author_type === 'user'"
              [class.bg-blue-950/40]="msg.author_type === 'ai'"
              [class.border-blue-500/30]="msg.author_type === 'ai'"
            >
              <div class="flex items-center justify-between text-[10px]">
                <span class="font-bold flex items-center gap-1" [class.text-blue-300]="msg.author_type === 'ai'" [class.text-slate-300]="msg.author_type === 'user'">
                  <span>{{ msg.author_type === 'ai' ? (getAiRoleEmoji(msg.ai_role) + ' ' + msg.author_name) : '👤 ' + msg.author_name }}</span>
                </span>
                <span class="text-slate-500">{{ formatTimestamp(msg.timestamp) }}</span>
              </div>
              <p class="text-slate-200 leading-relaxed font-sans text-[11px] whitespace-pre-line">{{ msg.content }}</p>
            </div>
          </div>

          <!-- Empty state -->
          <div *ngIf="historyService.history().length === 0 && myPersistentMessages().length === 0" class="text-center py-12 text-slate-500 text-xs">
            <span class="text-3xl block mb-2">💬</span>
            No has realizado consultas en esta sesión todavía.
          </div>
        </ng-container>

        <!-- ═══ TAB 3: GRUPO (CHAT COLABORATIVO SIMULTÁNEO) ═══ -->
        <ng-container *ngIf="activeTab === 'grupo'">
          <div class="flex items-center justify-between mb-2">
            <div>
              <h4 class="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <span>👥</span> Chat Colaborativo del Equipo
              </h4>
              <span class="text-[10px] text-slate-400">Todos los integrantes ven y nutren esta conversación con la IA</span>
            </div>
            <button 
              (click)="loadGroupHistory()" 
              class="text-[10px] px-2 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-blue-300 font-semibold cursor-pointer flex items-center gap-1"
              [disabled]="isLoadingGroup()"
            >
              <span [class.animate-spin]="isLoadingGroup()">↻</span> Sincronizar
            </button>
          </div>

          <!-- Active AI Role Indicator in Group -->
          <div 
            *ngIf="aiParticipativeEnabled() && activeRoleTheme"
            class="p-2 rounded-xl border flex items-center justify-between text-xs mb-2"
            [style.background]="activeRoleTheme.bgColor"
            [style.border-color]="activeRoleTheme.borderColor"
            [style.color]="activeRoleTheme.textColor"
          >
            <div class="flex items-center gap-2">
              <span class="text-base">{{ activeRoleTheme.emoji }}</span>
              <div>
                <strong class="block text-[11px] leading-tight">{{ activeRoleTheme.label }} en el equipo</strong>
                <span class="text-[9px] opacity-80">La IA responderá a las consultas del grupo con este rol</span>
              </div>
            </div>
            <span class="text-[9px] font-bold px-1.5 py-0.5 rounded bg-black/30 border border-white/20">Activo</span>
          </div>

          <!-- Empty State -->
          <div *ngIf="!projectId" class="text-center py-10 text-slate-500 text-xs">
            <span class="text-3xl block mb-2">📂</span>
            Este diagrama no está asociado a un proyecto activo.
          </div>

          <div *ngIf="projectId && groupMessages().length === 0" class="text-center py-10 text-slate-500 text-xs">
            <span class="text-3xl block mb-2">👥</span>
            Aún no hay mensajes en el chat grupal de este proyecto.<br/>
            Escribe un mensaje abajo para iniciar la conversación comunitaria.
          </div>

          <!-- Messages List with Auto-scroll capability -->
          <div 
            *ngIf="projectId && groupMessages().length > 0" 
            class="space-y-2.5 overflow-y-auto pr-1 custom-scrollbar"
            style="max-height: calc(100vh - 430px);"
          >
            <div 
              *ngFor="let msg of groupMessages()"
              class="p-3 rounded-xl border text-xs flex flex-col gap-1.5 transition-all shadow-sm"
              [class.bg-slate-800]="msg.author_type === 'user'"
              [class.border-slate-700]="msg.author_type === 'user'"
              [class.bg-slate-900]="msg.author_type === 'ai'"
              [style.border-color]="msg.author_type === 'ai' ? (getRoleThemeById(msg.ai_role)?.borderColor || '#3b82f6') : '#334155'"
            >
              <!-- Author Header -->
              <div class="flex items-center justify-between text-[11px]">
                <div class="flex items-center gap-1.5">
                  <div 
                    class="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white shadow"
                    [class.bg-blue-600]="msg.author_type === 'user'"
                    [style.background]="msg.author_type === 'ai' ? (getRoleThemeById(msg.ai_role)?.borderColor || '#7c3aed') : '#2563eb'"
                  >
                    {{ msg.author_type === 'user' ? getInitials(msg.author_name) : getAiRoleEmoji(msg.ai_role) }}
                  </div>
                  <strong [class.text-white]="msg.author_type === 'user'" [style.color]="msg.author_type === 'ai' ? (getRoleThemeById(msg.ai_role)?.textColor || '#93c5fd') : '#fff'">
                    {{ msg.author_name }}
                  </strong>
                  <span class="text-[9px] px-1 py-0.2 rounded bg-slate-950/60 text-slate-400 border border-slate-800 font-mono">
                    {{ msg.author_role_label }}
                  </span>
                </div>
                <span class="text-[10px] text-slate-500 font-mono">{{ formatTimestamp(msg.timestamp) }}</span>
              </div>

              <!-- Message Body -->
              <p class="text-slate-200 leading-relaxed font-sans text-xs whitespace-pre-line pl-6">
                {{ msg.content }}
              </p>

              <!-- Diagram changes notification and 1-click apply -->
              <div 
                *ngIf="msg.has_diagram_changes" 
                class="mt-1 ml-6 p-2 rounded-lg bg-emerald-950/60 border border-emerald-500/40 flex items-center justify-between gap-2"
              >
                <div class="text-[10px] text-emerald-300 font-semibold flex items-center gap-1">
                  <span>✨</span> Esta propuesta de la IA contiene modificaciones al diagrama UML
                </div>
                <button 
                  (click)="applyDiagramChangesFromMessage(msg)"
                  class="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[10px] font-bold shrink-0 cursor-pointer shadow"
                >
                  ✓ Aplicar al Lienzo
                </button>
              </div>
            </div>
          </div>

          <!-- Group Chat Input Bar -->
          <div *ngIf="projectId" class="mt-auto pt-2 border-t border-slate-800 space-y-1.5">
            <div class="flex items-center gap-1.5">
              <input 
                type="text"
                [(ngModel)]="groupChatInput"
                (keyup.enter)="sendGroupMessage()"
                placeholder="Escribe al equipo o consulta al rol de IA..."
                class="flex-1 bg-slate-950 border border-slate-700 focus:border-purple-500 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-purple-500 transition-all"
                [disabled]="isSendingGroup()"
              />
              <button 
                (click)="sendGroupMessage()"
                [disabled]="isSendingGroup() || !groupChatInput.trim()"
                class="px-3.5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white font-bold text-xs shadow-lg transition-all flex items-center justify-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                title="Enviar mensaje al grupo"
              >
                <span *ngIf="!isSendingGroup()">➤</span>
                <span *ngIf="isSendingGroup()" class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              </button>
            </div>
            <div class="flex items-center justify-between text-[10px] text-slate-500 px-1">
              <span>Envía una duda o requerimiento al equipo y a la IA</span>
              <span *ngIf="aiParticipativeEnabled()">Rol activo: <strong>{{ activeRoleTheme?.label }}</strong></span>
            </div>
          </div>
        </ng-container>

        <!-- ═══ TAB 4: EJEMPLOS DE MODELADO ═══ -->
        <ng-container *ngIf="activeTab === 'examples'">
          <h4 class="text-xs font-bold text-slate-300 mb-2">Ejemplos de Modelado UML (1-Clic para Aplicar):</h4>
          
          <div class="space-y-2 max-h-[70vh] overflow-y-auto pr-1 custom-scrollbar">
            <div 
              *ngFor="let ex of complexExamples"
              class="p-3 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-blue-500/50 rounded-xl cursor-pointer transition-all flex flex-col gap-1 group"
              (click)="executeDirectly(ex.prompt)"
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

      <!-- Bottom Prompt Bar (Only visible in Asistente tab) -->
      <div *ngIf="activeTab === 'prompt'" class="p-3.5 border-t border-slate-800 bg-slate-950/90">
        <!-- Quick Suggestions Chips -->
        <div class="flex flex-wrap gap-1.5 mb-2.5 max-h-16 overflow-y-auto custom-scrollbar">
          <span class="text-[10px] text-slate-400 self-center">Sugerencias:</span>
          <button 
            *ngFor="let suggestion of quickSuggestions" 
            class="text-[10px] bg-slate-800 hover:bg-slate-700 border border-slate-700/70 px-2 py-0.5 rounded-full text-slate-300 transition-colors cursor-pointer"
            (click)="executeDirectly(suggestion)"
          >
            {{ suggestion }}
          </button>
        </div>

        <!-- Input Bar with Voice Toggle, Ghost Text overlay & Submit -->
        <div class="flex items-center gap-2">
          <div class="relative flex-1">
            <!-- Ghost Text inside the input field while speaking -->
            <div 
              *ngIf="voice.isListening() && (voice.transcript() || voice.interimTranscript())" 
              class="absolute inset-0 px-3.5 py-2.5 text-xs pointer-events-none flex items-center overflow-hidden whitespace-nowrap z-10"
            >
              <span class="text-white font-medium">{{ voice.transcript() }}</span>
              <span class="text-blue-200/40 opacity-40 italic font-mono ml-1 animate-pulse">{{ voice.interimTranscript() }}</span>
            </div>

            <input 
              type="text" 
              [(ngModel)]="textInput" 
              (keyup.enter)="handleSubmit()"
              [placeholder]="voice.isListening() ? '🎙️ Habla ahora (voz en tiempo real)...' : 'Ej: crea una clase Cliente con atributos nombre, id, ci, numero, nit...'"
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
            [title]="voice.isListening() ? 'Detener dictado y aplicar' : 'Iniciar reconocimiento por voz'"
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
  @Input() projectId?: string;
  @Output() close = new EventEmitter<void>();

  public voice = inject(VoiceRecognitionService);
  public aiService = inject(AiService);
  public executor = inject(CommandExecutorService);
  public historyService = inject(AiHistoryService);
  public authService = inject(AuthService);
  public aiChatService = inject(AiChatService);
  private cdr = inject(ChangeDetectorRef);

  public activeTab: DrawerTab = 'prompt';
  public drawerWidth = 490;
  public autoApply = signal<boolean>(true);
  private isResizing = false;

  // Participative AI role configuration
  public aiParticipativeEnabled = signal<boolean>(false);
  public activeAiRole = signal<AiRoleId>('architect');
  public showConfigPanel = signal<boolean>(false);
  public showModelPicker = signal<boolean>(false);

  // Group collaborative chat
  public groupMessages = signal<AiMessage[]>([]);
  public myPersistentMessages = signal<AiMessage[]>([]);
  public groupChatInput = '';
  public isSendingGroup = signal<boolean>(false);
  public isLoadingGroup = signal<boolean>(false);
  private pollingTimer: any = null;

  // Model & API Key
  public selectedModel = 'gemini-2.0-flash';
  public apiKeyInput = '';
  public hasCustomApiKey = false;

  public textInput = '';
  public pendingCommand = signal<UMLCommandResponse | null>(null);
  public isProcessing = signal<boolean>(false);
  public executionFeedback = signal<{ message: string; type: 'success' | 'error' } | null>(null);
  private feedbackTimeout: any = null;
  private lastInputType: 'voice' | 'text' = 'text';

  public audioWaveBars = [0, 1, 2, 3, 4, 5, 6];

  public availableRoles: { id: AiRoleId; theme: AiRoleTheme }[] = [
    { id: 'architect', theme: AI_ROLE_THEMES.architect },
    { id: 'qa', theme: AI_ROLE_THEMES.qa },
    { id: 'tech_lead', theme: AI_ROLE_THEMES.tech_lead },
    { id: 'mentor', theme: AI_ROLE_THEMES.mentor }
  ];

  public availableModels = [
    { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash', badge: 'Recomendado / Rápido' },
    { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', badge: 'Última Generación' },
    { id: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash', badge: 'Alta Disponibilidad' },
    { id: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro', badge: 'Razonamiento Complejo' }
  ];

  public quickSuggestions = [
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

  get currentUserName(): string {
    const user = this.authService.getCurrentUser();
    return user?.name || user?.email || 'Usuario';
  }

  get activeRoleTheme(): AiRoleTheme | null {
    const r = this.activeAiRole();
    return r ? AI_ROLE_THEMES[r] : null;
  }

  getRoleThemeById(roleId?: string): AiRoleTheme | null {
    if (!roleId) return null;
    return AI_ROLE_THEMES[roleId as AiRoleId] || null;
  }

  getAiRoleEmoji(roleId?: string): string {
    if (!roleId) return '🤖';
    return AI_ROLE_THEMES[roleId as AiRoleId]?.emoji || '🤖';
  }

  getInitials(name: string): string {
    return (name || '?')
      .split(' ')
      .map(w => w[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  }

  getModelShortName(modelId: string): string {
    if (modelId.includes('2.0')) return 'Gemini 2.0';
    if (modelId.includes('2.5')) return 'Gemini 2.5';
    if (modelId.includes('1.5-pro')) return 'Gemini 1.5 Pro';
    if (modelId.includes('1.5')) return 'Gemini 1.5';
    return 'Gemini AI';
  }

  getBarHeight(index: number, level: number): number {
    const weights = [0.4, 0.7, 1.0, 0.9, 1.0, 0.7, 0.4];
    const w = weights[index % weights.length];
    return Math.max(4, Math.min(24, Math.round(4 + (level * 0.2 * w))));
  }

  ngOnInit(): void {
    if (typeof localStorage !== 'undefined') {
      const savedWidth = localStorage.getItem('cf_ai_drawer_width');
      if (savedWidth) {
        const w = parseInt(savedWidth, 10);
        if (w >= 340 && w <= 950) this.drawerWidth = w;
      }
      const savedModel = localStorage.getItem('classforge_gemini_model');
      if (savedModel) {
        this.selectedModel = savedModel;
      }
      const savedKey = localStorage.getItem('classforge_gemini_api_key');
      if (savedKey) {
        this.hasCustomApiKey = true;
        this.apiKeyInput = savedKey;
      }
      const savedRole = localStorage.getItem('cf_active_ai_role');
      if (savedRole && (savedRole as any) in AI_ROLE_THEMES) {
        this.activeAiRole.set(savedRole as AiRoleId);
      }
      const savedParticipative = localStorage.getItem('cf_ai_participative');
      if (savedParticipative === 'true') {
        this.aiParticipativeEnabled.set(true);
      }
    }

    this.historyService.reloadHistory(this.diagramId);

    if (this.projectId) {
      this.loadGroupHistory();
      this.loadMyHistory();
      // Setup periodic polling for group chat (every 12 seconds)
      this.pollingTimer = setInterval(() => {
        if (this.activeTab === 'grupo' && this.projectId) {
          this.loadGroupHistory(true);
        }
      }, 12000);
    }
  }

  ngOnDestroy(): void {
    if (this.voice.isListening()) {
      this.voice.stopListening();
    }
    if (this.feedbackTimeout) {
      clearTimeout(this.feedbackTimeout);
    }
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
    }
  }

  setTab(tab: DrawerTab): void {
    this.activeTab = tab;
    if (tab === 'grupo' && this.projectId) {
      this.loadGroupHistory();
    } else if (tab === 'history' && this.projectId) {
      this.loadMyHistory();
    }
    this.cdr.markForCheck();
  }

  toggleAiParticipative(): void {
    const newState = !this.aiParticipativeEnabled();
    this.aiParticipativeEnabled.set(newState);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('cf_ai_participative', newState ? 'true' : 'false');
    }
    if (newState && !this.activeAiRole()) {
      this.activeAiRole.set('architect');
    }
    if (this.projectId && newState) {
      this.aiChatService.setRole(this.projectId, this.activeAiRole(), true).subscribe({
        next: () => {
          this.showFeedback(`Rol ${this.activeRoleTheme?.label} activado como integrante del proyecto`, 'success');
        },
        error: (err) => console.warn('[AiDrawer] Error updating role on project:', err)
      });
    }
  }

  selectRole(roleId: AiRoleId): void {
    this.activeAiRole.set(roleId);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('cf_active_ai_role', roleId);
    }
    if (this.projectId && this.aiParticipativeEnabled()) {
      this.aiChatService.setRole(this.projectId, roleId, true).subscribe({
        next: () => {
          this.showFeedback(`Rol actualizado: ${this.activeRoleTheme?.label}`, 'success');
        },
        error: (err) => console.warn('[AiDrawer] Error activating role:', err)
      });
    }
  }

  selectModel(modelId: string): void {
    this.selectedModel = modelId;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('classforge_gemini_model', modelId);
    }
    this.showModelPicker.set(false);
    this.showFeedback(`Modelo activo: ${this.getModelShortName(modelId)}`, 'success');
  }

  saveApiKey(): void {
    if (typeof localStorage !== 'undefined') {
      const key = this.apiKeyInput.trim();
      if (key) {
        localStorage.setItem('classforge_gemini_api_key', key);
        this.hasCustomApiKey = true;
        this.showFeedback('Clave API guardada correctamente', 'success');
      } else {
        localStorage.removeItem('classforge_gemini_api_key');
        this.hasCustomApiKey = false;
        this.showFeedback('Se usará la clave API configurada en el servidor', 'success');
      }
    }
  }

  loadGroupHistory(silent = false): void {
    if (!this.projectId) return;
    if (!silent) this.isLoadingGroup.set(true);

    this.aiChatService.getGroupHistory(this.projectId).subscribe({
      next: (res) => {
        this.isLoadingGroup.set(false);
        this.groupMessages.set(res.messages || []);
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isLoadingGroup.set(false);
        console.warn('[AiDrawer] Error fetching group history:', err);
      }
    });
  }

  loadMyHistory(): void {
    if (!this.projectId) return;
    this.aiChatService.getMyHistory(this.projectId).subscribe({
      next: (res) => {
        this.myPersistentMessages.set(res.messages || []);
        this.cdr.markForCheck();
      },
      error: (err) => console.warn('[AiDrawer] Error fetching my history:', err)
    });
  }

  sendGroupMessage(): void {
    const text = this.groupChatInput.trim();
    if (!text || !this.projectId || this.isSendingGroup()) return;

    const role: AiRoleId = this.aiParticipativeEnabled() ? this.activeAiRole() : 'architect';
    this.isSendingGroup.set(true);
    const sentText = text;
    this.groupChatInput = '';

    this.aiChatService.sendMessage(this.projectId, sentText, role, this.diagramId).subscribe({
      next: (res) => {
        this.isSendingGroup.set(false);
        this.loadGroupHistory();
        if (res.has_diagram_changes) {
          this.showFeedback(`✨ El ${res.role_label} propuso cambios UML en el chat grupal`, 'success');
        }
      },
      error: (err) => {
        this.isSendingGroup.set(false);
        this.groupChatInput = sentText; // Restore on failure
        this.showFeedback('No se pudo enviar el mensaje grupal', 'error');
        console.error('[AiDrawer] sendGroupMessage error:', err);
      }
    });
  }

  applyDiagramChangesFromMessage(msg: AiMessage): void {
    if (!msg.content) return;
    this.isProcessing.set(true);
    // Process the text using AI parser to execute changes
    this.aiService.processInput(msg.content).subscribe({
      next: (cmd) => {
        this.isProcessing.set(false);
        if (cmd && cmd.action !== 'unknown') {
          const result = this.executor.execute(cmd);
          this.showFeedback(`✓ Cambios aplicados: ${result.message}`, 'success');
        } else {
          this.showFeedback('No se detectó un comando ejecutable en esta respuesta.', 'error');
        }
      },
      error: () => {
        this.isProcessing.set(false);
        this.showFeedback('Error al aplicar cambios en el lienzo.', 'error');
      }
    });
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
    if (newWidth >= 340 && newWidth <= 920) {
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
      this.showFeedback('No se detectó ninguna palabra hablada.', 'error');
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
          this.showFeedback('⚠️ No se reconoció la orden. Intenta: "crear clase Producto con atributos precio, stock, codigo y asociar a Categoria 1..*"', 'error');
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
    }
    this.pendingCommand.set(null);
    this.textInput = '';
    this.voice.clear();
  }

  showFeedback(message: string, type: 'success' | 'error'): void {
    this.executionFeedback.set({ message, type });
    if (this.feedbackTimeout) {
      clearTimeout(this.feedbackTimeout);
    }
    this.feedbackTimeout = setTimeout(() => {
      this.executionFeedback.set(null);
    }, 4500);
  }
}
