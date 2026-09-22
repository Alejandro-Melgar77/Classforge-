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

  private recognition: any;
  private isExplicitlyStopping = false;

  constructor() {
    this.initSpeechRecognition();
  }

  private initSpeechRecognition(): void {
    if (typeof window === 'undefined') {
      this.isSupported.set(false);
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'es-ES';
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.maxAlternatives = 1;

        this.recognition.onstart = () => {
          this.isListening.set(true);
          this.error.set(null);
          this.interimTranscript.set('');
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

          if (final) {
            const current = this.transcript();
            const updated = current ? `${current} ${final.trim()}` : final.trim();
            this.transcript.set(updated);
            this.interimTranscript.set('');
          } else {
            this.interimTranscript.set(interim);
          }
        };

        this.recognition.onerror = (event: any) => {
          const err = event.error;
          let userMsg: string | null = null;
          switch (err) {
            case 'not-allowed':
            case 'permission-denied':
              userMsg = 'Permiso de micrófono denegado. Habilita el micrófono en tu navegador.';
              break;
            case 'no-speech':
              userMsg = 'No se detectó voz. Presiona el micrófono y habla claramente.';
              break;
            case 'audio-capture':
              userMsg = 'No se encontró ningún micrófono conectado en tu equipo.';
              break;
            case 'network':
              userMsg = 'Aviso de reconocimiento de voz. También puedes ingresar tu texto directamente.';
              break;
            case 'aborted':
              userMsg = null;
              break;
            default:
              userMsg = `Aviso de voz (${err}).`;
          }
          if (userMsg) {
            this.error.set(userMsg);
          }
          this.isListening.set(false);
        };

        this.recognition.onend = () => {
          this.isListening.set(false);
          this.interimTranscript.set('');
          this.isExplicitlyStopping = false;
        };
      } catch (e) {
        console.warn('SpeechRecognition initialization error:', e);
        this.isSupported.set(false);
      }
    } else {
      this.isSupported.set(false);
    }
  }

  toggleListening(): void {
    if (this.isListening()) {
      this.stopListening();
    } else {
      this.startListening();
    }
  }

  startListening(): void {
    if (!this.isSupported() || !this.recognition) {
      this.error.set('El reconocimiento de voz no es compatible con este navegador.');
      return;
    }

    this.transcript.set('');
    this.interimTranscript.set('');
    this.error.set(null);
    this.isExplicitlyStopping = false;

    try {
      this.recognition.start();
    } catch (e: any) {
      // If already started or aborting
      try {
        this.recognition.stop();
        setTimeout(() => {
          try { this.recognition.start(); } catch (_) {}
        }, 100);
      } catch (_) {}
    }
  }

  stopListening(): void {
    if (!this.isSupported() || !this.recognition) return;
    this.isExplicitlyStopping = true;
    try {
      this.recognition.stop();
    } catch (e) {
      this.isListening.set(false);
    }
  }

  clear(): void {
    this.transcript.set('');
    this.interimTranscript.set('');
    this.error.set(null);
  }
}

