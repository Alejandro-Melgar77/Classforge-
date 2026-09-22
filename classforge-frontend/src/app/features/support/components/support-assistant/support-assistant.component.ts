import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SupportTourService } from '../../services/support-tour.service';
import { SupportNluService } from '../../services/support-nlu.service';
import { SupportChatMessage, TourDefinition } from '../../models/support-tour.model';

@Component({
  selector: 'app-support-assistant',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './support-assistant.component.html',
  styleUrls: ['./support-assistant.component.scss']
})
export class SupportAssistantComponent implements OnInit, OnDestroy {
  public tourService = inject(SupportTourService);
  private nluService = inject(SupportNluService);

  public isOpen = signal<boolean>(false);
  public activeTab = signal<'chat' | 'tours' | 'shortcuts'>('chat');
  public queryText = '';
  public isRecording = false;

  private recognition: any = null;

  public messages: SupportChatMessage[] = [
    {
      id: 'msg-welcome',
      sender: 'assistant',
      text: '¡Hola! Soy tu Asistente de Soporte en Tiempo Real de ClassForge 🛡️. Puedes consultarme cualquier duda sobre el uso del software por texto o por voz, y te mostraré interactivamente en la pantalla los pasos exactos a seguir.',
      timestamp: new Date(),
      suggestedTourId: 'tour-create-diagram',
      suggestedTourTitle: 'Tour: Creación de Diagramas UML'
    }
  ];

  public quickSuggestions = [
    '¿Cómo creo un diagrama?',
    '¿Cómo funciona el Asistente IA?',
    '¿Cómo genero código Spring Boot?',
    '¿Cómo genero el prompt para Frontend?',
    '¿Cómo colaboro en tiempo real?'
  ];

  public keyboardShortcuts = [
    { key: 'V', description: 'Modo selección de elementos' },
    { key: 'Espacio + Arrastre', description: 'Modo paneo del lienzo' },
    { key: 'Ctrl + Z', description: 'Deshacer última acción' },
    { key: 'Ctrl + Y', description: 'Rehacer acción' },
    { key: 'Ctrl + A', description: 'Seleccionar todos los elementos' },
    { key: 'Supr / Delete', description: 'Eliminar elementos seleccionados' },
    { key: 'Ctrl + Shift + F', description: 'Ajustar lienzo a la pantalla (Fit View)' },
    { key: 'Escape', description: 'Cerrar tours y modales activos' }
  ];

  ngOnInit() {
    this.initSpeechRecognition();
  }

  ngOnDestroy() {
    if (this.recognition) {
      try { this.recognition.stop(); } catch (e) {}
    }
  }

  public toggleOpen() {
    this.isOpen.set(!this.isOpen());
  }

  public setTab(tab: 'chat' | 'tours' | 'shortcuts') {
    this.activeTab.set(tab);
  }

  public get tours(): TourDefinition[] {
    return this.tourService.getAllTours();
  }

  public askQuery(text?: string) {
    const q = text || this.queryText;
    if (!q.trim()) return;

    // Mensaje del usuario
    this.messages.push({
      id: `usr-${Date.now()}`,
      sender: 'user',
      text: q.trim(),
      timestamp: new Date()
    });

    this.queryText = '';

    // Procesar con el motor NLU de soporte
    setTimeout(() => {
      const res = this.nluService.processQuery(q);
      this.messages.push({
        id: `ast-${Date.now()}`,
        sender: 'assistant',
        text: res.reply,
        timestamp: new Date(),
        suggestedTourId: res.suggestedTourId,
        suggestedTourTitle: res.suggestedTourTitle
      });
      this.scrollToBottom();
    }, 250);

    this.scrollToBottom();
  }

  public launchTour(tourId: string) {
    // Cerrar el drawer de soporte y arrancar el Spotlight Tour
    this.isOpen.set(false);
    this.tourService.startTour(tourId);
  }

  private scrollToBottom() {
    setTimeout(() => {
      const container = document.getElementById('support-chat-messages');
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }, 100);
  }

  private initSpeechRecognition() {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.lang = 'es-ES';
      this.recognition.continuous = false;
      this.recognition.interimResults = false;

      this.recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        this.queryText = transcript;
        this.isRecording = false;
        this.askQuery(transcript);
      };

      this.recognition.onerror = () => {
        this.isRecording = false;
      };

      this.recognition.onend = () => {
        this.isRecording = false;
      };
    }
  }

  public toggleVoiceRecognition() {
    if (!this.recognition) {
      alert('Tu navegador no soporta reconocimiento de voz nativo (Web Speech API). Por favor escribe tu consulta.');
      return;
    }

    if (this.isRecording) {
      this.recognition.stop();
      this.isRecording = false;
    } else {
      try {
        this.isRecording = true;
        this.recognition.start();
      } catch (e) {
        this.isRecording = false;
      }
    }
  }
}
