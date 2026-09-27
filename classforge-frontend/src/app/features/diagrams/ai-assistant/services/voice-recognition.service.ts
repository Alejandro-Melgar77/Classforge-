import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class VoiceRecognitionService {
  isListening = signal<boolean>(false);
  transcript = signal<string>('');
  interimTranscript = signal<string>('');
  isSupported = signal<boolean>(true);
  error = signal<string | null>(null);
  audioLevel = signal<number>(0);
  isOfflineMode = signal<boolean>(false);
  hasVoiceActivity = signal<boolean>(false);
  isSpeechBlocked = signal<boolean>(false);

  private recognition: any = null;
  private isExplicitlyStopping = false;
  private consecutiveNetworkErrors = 0;
  private restartTimeout: any = null;
  private animInterval: any = null;

  constructor() {
    this.checkSupport();
  }

  private checkSupport(): void {
    if (typeof window === 'undefined') {
      this.isSupported.set(false);
      return;
    }
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    this.isSupported.set(!!SpeechRecognition);
  }

  /**
   * Creates a clean, fresh SpeechRecognition instance on demand.
   * In Chromium/Edge, reusing old instances often results in silent audio capture failures.
   */
  private createAndStartRecognition(): void {
    if (typeof window === 'undefined' || this.isExplicitlyStopping) {
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      this.isSupported.set(false);
      this.error.set('Tu navegador no soporta la API de reconocimiento de voz.');
      return;
    }

    // Clean up any existing instance
    this.destroyRecognition();

    try {
      this.recognition = new SpeechRecognition();

      // Language configuration: standard Spanish (universally supported by Google & Microsoft Edge)
      this.recognition.lang = 'es-ES';

      // Setting continuous=false with an auto-restart loop in onend is the most robust pattern for Chromium/Edge:
      // it delivers instantaneous interim results without gRPC socket deadlocks or buffering delays.
      this.recognition.continuous = false;
      this.recognition.interimResults = true;
      this.recognition.maxAlternatives = 1;

      this.recognition.onstart = () => {
        this.isListening.set(true);
        this.error.set(null);
        this.consecutiveNetworkErrors = 0;
        this.updateAudioLevel(18);
        console.log('[VoiceRecognition] onstart: Mic listening active.');
      };

      this.recognition.onaudiostart = () => {
        console.log('[VoiceRecognition] onaudiostart: Audio hardware stream active.');
        this.updateAudioLevel(25);
      };

      this.recognition.onsoundstart = () => {
        console.log('[VoiceRecognition] onsoundstart: Sound detected.');
        this.hasVoiceActivity.set(true);
        this.updateAudioLevel(45);
      };

      this.recognition.onspeechstart = () => {
        console.log('[VoiceRecognition] onspeechstart: Human speech recognized.');
        this.hasVoiceActivity.set(true);
        this.updateAudioLevel(65);
      };

      this.recognition.onresult = (event: any) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const result = event.results[i];
          if (result.isFinal) {
            final += result[0].transcript;
          } else {
            interim += result[0].transcript;
          }
        }

        console.log('[VoiceRecognition] onresult:', { final, interim });

        if (final) {
          const current = this.transcript().trim();
          const updated = current ? `${current} ${final.trim()}` : final.trim();
          this.transcript.set(updated);
          this.interimTranscript.set('');
          this.hasVoiceActivity.set(true);
          this.consecutiveNetworkErrors = 0;
          this.updateAudioLevel(75);
        } else if (interim) {
          this.interimTranscript.set(interim);
          this.hasVoiceActivity.set(true);
          this.updateAudioLevel(60);
        }
      };

      this.recognition.onspeechend = () => {
        console.log('[VoiceRecognition] onspeechend: Utterance ended.');
        this.updateAudioLevel(20);
      };

      this.recognition.onsoundend = () => {
        console.log('[VoiceRecognition] onsoundend: Sound paused.');
        this.updateAudioLevel(12);
      };

      this.recognition.onaudioend = () => {
        console.log('[VoiceRecognition] onaudioend: Audio cycle ended.');
        this.updateAudioLevel(10);
      };

      this.recognition.onerror = (event: any) => {
        const err = event.error;
        console.warn('[VoiceRecognition] onerror:', err);

        if (this.isExplicitlyStopping) {
          return;
        }

        if (err === 'no-speech') {
          // Normal silence interval: will smoothly restart in onend
          return;
        }

        if (err === 'aborted') {
          return;
        }

        if (err === 'not-allowed' || err === 'permission-denied') {
          this.error.set('Permiso de micrófono denegado. Haz clic en el candado 🔒 de la barra de direcciones de Edge y permite el micrófono.');
          this.stopListening();
          return;
        }

        if (err === 'audio-capture') {
          this.error.set('No se detectó ningún micrófono conectado o está ocupado por otra aplicación.');
          this.stopListening();
          return;
        }

        if (err === 'network') {
          this.consecutiveNetworkErrors++;
          console.warn('[VoiceRecognition] Network error count:', this.consecutiveNetworkErrors);
          if (this.consecutiveNetworkErrors >= 3) {
            this.isSpeechBlocked.set(true);
            this.isOfflineMode.set(true);
            this.error.set('Servicio de reconocimiento de voz no disponible temporalmente. Puedes usar los comandos 1-clic o escribir tu texto.');
          }
          return;
        }

        console.warn('[VoiceRecognition] Speech warning:', err);
      };

      this.recognition.onend = () => {
        console.log('[VoiceRecognition] onend fired. isExplicitlyStopping:', this.isExplicitlyStopping);

        if (this.isExplicitlyStopping) {
          this.consolidateInterim();
          this.isListening.set(false);
          this.hasVoiceActivity.set(false);
          this.updateAudioLevel(0);
          this.stopLevelSimulation();
          return;
        }

        // Loop seamlessly to capture subsequent sentences without dropping
        if (this.isListening() && !this.isSpeechBlocked()) {
          this.scheduleRestart(100);
        } else {
          this.isListening.set(false);
          this.stopLevelSimulation();
        }
      };

      this.recognition.start();
      this.startLevelSimulation();
    } catch (e: any) {
      console.warn('[VoiceRecognition] Error launching SpeechRecognition:', e);
      this.scheduleRestart(300);
    }
  }

  private destroyRecognition(): void {
    if (this.recognition) {
      try {
        this.recognition.onstart = null;
        this.recognition.onaudiostart = null;
        this.recognition.onsoundstart = null;
        this.recognition.onspeechstart = null;
        this.recognition.onresult = null;
        this.recognition.onspeechend = null;
        this.recognition.onsoundend = null;
        this.recognition.onaudioend = null;
        this.recognition.onerror = null;
        this.recognition.onend = null;
        this.recognition.abort();
      } catch (_) {}
      this.recognition = null;
    }
  }

  private startLevelSimulation(): void {
    if (this.animInterval) clearInterval(this.animInterval);

    this.animInterval = setInterval(() => {
      if (!this.isListening()) {
        this.audioLevel.set(0);
        return;
      }

      const current = this.audioLevel();
      if (this.hasVoiceActivity() || this.interimTranscript()) {
        // Natural pulsing around active speech
        const target = 45 + Math.floor(Math.random() * 35);
        const next = Math.round(current * 0.4 + target * 0.6);
        this.audioLevel.set(next);
      } else {
        // Gentle decay to baseline ambient level (10-15%)
        const target = 10 + Math.floor(Math.random() * 6);
        const next = Math.max(target, Math.round(current * 0.85));
        this.audioLevel.set(next);
      }
    }, 90);
  }

  private stopLevelSimulation(): void {
    if (this.animInterval) {
      clearInterval(this.animInterval);
      this.animInterval = null;
    }
    this.audioLevel.set(0);
  }

  private updateAudioLevel(lvl: number): void {
    this.audioLevel.set(lvl);
    if (lvl > 20) {
      this.hasVoiceActivity.set(true);
    }
  }

  private scheduleRestart(delayMs = 150): void {
    if (this.restartTimeout) clearTimeout(this.restartTimeout);
    this.restartTimeout = setTimeout(() => {
      if (!this.isExplicitlyStopping && this.isListening() && !this.isSpeechBlocked()) {
        this.createAndStartRecognition();
      }
    }, delayMs);
  }

  private consolidateInterim(): void {
    const interim = this.interimTranscript().trim();
    if (interim) {
      const current = this.transcript().trim();
      const consolidated = current ? `${current} ${interim}` : interim;
      this.transcript.set(consolidated);
      this.interimTranscript.set('');
    }
  }

  public getBestTranscript(): string {
    const main = this.transcript().trim();
    const interim = this.interimTranscript().trim();
    if (main && interim) return `${main} ${interim}`;
    return main || interim;
  }

  public stopAndGetTranscript(): string {
    this.consolidateInterim();
    const text = this.getBestTranscript();
    this.stopListening();
    return text;
  }

  startListening(): void {
    if (this.restartTimeout) clearTimeout(this.restartTimeout);

    this.transcript.set('');
    this.interimTranscript.set('');
    this.error.set(null);
    this.isExplicitlyStopping = false;
    this.consecutiveNetworkErrors = 0;
    this.isSpeechBlocked.set(false);
    this.isOfflineMode.set(false);
    this.hasVoiceActivity.set(false);
    this.isListening.set(true);

    this.createAndStartRecognition();
  }

  stopListening(): void {
    if (this.restartTimeout) clearTimeout(this.restartTimeout);
    this.isExplicitlyStopping = true;

    this.consolidateInterim();
    this.destroyRecognition();
    this.stopLevelSimulation();

    this.isListening.set(false);
  }

  simulateVoiceInput(phrase: string): void {
    this.transcript.set(phrase);
    this.interimTranscript.set('');
    this.hasVoiceActivity.set(true);
    this.isListening.set(false);
  }

  clear(): void {
    if (this.restartTimeout) clearTimeout(this.restartTimeout);
    this.transcript.set('');
    this.interimTranscript.set('');
    this.error.set(null);
    this.isSpeechBlocked.set(false);
    this.isOfflineMode.set(false);
    this.hasVoiceActivity.set(false);
    this.audioLevel.set(0);
    this.stopLevelSimulation();
  }
}

