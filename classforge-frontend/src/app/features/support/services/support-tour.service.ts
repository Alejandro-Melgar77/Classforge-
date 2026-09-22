import { Injectable, signal, computed, inject } from '@angular/core';
import { Router } from '@angular/router';
import { TourDefinition, TourStep } from '../models/support-tour.model';

@Injectable({
  providedIn: 'root'
})
export class SupportTourService {
  private router = inject(Router);

  // State Signals (Angular 17)
  public activeTour = signal<TourDefinition | null>(null);
  public currentStepIndex = signal<number>(0);
  public targetRect = signal<DOMRect | null>(null);

  public isTourActive = computed(() => this.activeTour() !== null);
  public currentStep = computed(() => {
    const tour = this.activeTour();
    if (!tour || tour.steps.length === 0) return null;
    return tour.steps[this.currentStepIndex()] || null;
  });

  public progressPercentage = computed(() => {
    const tour = this.activeTour();
    if (!tour || tour.steps.length === 0) return 0;
    return Math.round(((this.currentStepIndex() + 1) / tour.steps.length) * 100);
  });

  // Catálogo de Tours Guiados Predefinidos
  private tours: TourDefinition[] = [
    {
      id: 'tour-create-diagram',
      title: 'Creación de Diagramas UML',
      description: 'Aprende a crear tu primer diagrama, organizar proyectos y acceder al lienzo.',
      icon: '📐',
      category: 'Básico',
      estimatedTime: '2 min',
      steps: [
        {
          id: 'step-nav-diagrams',
          targetSelector: '[data-tour="nav-diagrams"]',
          title: 'Acceso a Diagramas',
          content: 'Haz clic aquí para ver todos tus diagramas conceptuales UML y administrar tus borradores o versiones en equipo.',
          position: 'right',
          actionHint: 'Observa la barra de navegación lateral'
        },
        {
          id: 'step-new-diagram-btn',
          targetSelector: '[data-tour="new-diagram-btn"]',
          title: 'Crear Nuevo Diagrama',
          content: 'Pulsa este botón para crear un nuevo diagrama conceptual. El sistema generará tu lienzo y te redirigirá automáticamente a la mesa de trabajo.',
          position: 'bottom',
          requiredRoute: '/diagrams',
          actionHint: 'Haz clic en "Nuevo Diagrama"'
        },
        {
          id: 'step-status-filter',
          targetSelector: '[data-tour="status-filter"]',
          title: 'Filtro por Estados',
          content: 'Filtra tus diagramas según su ciclo de vida: Borrador (Draft), En Progreso o Completado.',
          position: 'bottom',
          requiredRoute: '/diagrams'
        }
      ]
    },
    {
      id: 'tour-uml-modeling',
      title: 'Modelado en el Lienzo y Herramientas',
      description: 'Descubre la barra flotante, tipos de clases UML y edición de atributos en tiempo real.',
      icon: '🛠️',
      category: 'Modelado UML',
      estimatedTime: '3 min',
      steps: [
        {
          id: 'step-canvas-toolbar',
          targetSelector: '[data-tour="toolbar"]',
          title: 'Barra de Herramientas UML',
          content: 'Desde aquí puedes alternar entre modo selección (V) y paneo (Space), agregar Clases, Interfaces, Clases Abstractas, Enumeraciones y Notas, o borrar elementos seleccionados.',
          position: 'right',
          actionHint: 'Explora los nodos UML'
        },
        {
          id: 'step-properties-panel',
          targetSelector: '[data-tour="properties-panel"]',
          title: 'Panel de Propiedades',
          content: 'Al seleccionar una clase o relación en el lienzo, este panel te permite modificar su nombre, visibilidad (+, -, #, ~), agregar campos tipados o ajustar multiplicidades.',
          position: 'left',
          actionHint: 'Edita atributos y métodos en vivo'
        },
        {
          id: 'step-save-controls',
          targetSelector: '[data-tour="save-controls"]',
          title: 'Guardado y Versionado Automático',
          content: 'ClassForge cuenta con auto-guardado en segundo plano cada 30 segundos y guarda hasta 20 versiones en MongoDB. También puedes guardar manualmente con un solo clic.',
          position: 'bottom'
        }
      ]
    },
    {
      id: 'tour-ai-assistant',
      title: 'Asistente IA de Voz y Modelado',
      description: 'Usa lenguaje natural o comandos por voz para modelar clases y relaciones sin tocar el teclado.',
      icon: '✨',
      category: 'IA & Código',
      estimatedTime: '2 min',
      steps: [
        {
          id: 'step-ai-btn',
          targetSelector: '[data-tour="ai-assistant-btn"]',
          title: 'Asistente IA & Voz',
          content: 'Abre el asistente inteligente. Puedes dictar por voz usando el micrófono o escribir requerimientos en lenguaje natural.',
          position: 'bottom',
          actionHint: 'Haz clic para abrir el drawer de IA'
        },
        {
          id: 'step-colab-presence',
          targetSelector: '[data-tour="presence-bar"]',
          title: 'Presencia Colaborativa',
          content: 'Visualiza en todo momento cuántos compañeros están conectados en vivo, sus avatares y colores asignados en el diagrama.',
          position: 'bottom'
        }
      ]
    },
    {
      id: 'tour-codegen-spring',
      title: 'Proyección Spring Boot 3 & ZIP',
      description: 'Genera microservicios Java 17 / Spring Boot 3 limpios y descarga el proyecto completo.',
      icon: '💻',
      category: 'IA & Código',
      estimatedTime: '2 min',
      steps: [
        {
          id: 'step-live-code-btn',
          targetSelector: '[data-tour="live-code-btn"]',
          title: 'Código en Vivo',
          content: 'Haz clic aquí para abrir el panel de código. Cada clase y relación que diseñes se traduce instantáneamente (<15ms) a Entidades JPA, Repositorios, Servicios y Controladores REST.',
          position: 'bottom',
          actionHint: 'Observa la generación incremental'
        }
      ]
    },
    {
      id: 'tour-frontend-prompt',
      title: 'Meta-Prompt Frontend para IA Externa',
      description: 'Sintetiza contratos REST listos para Claude 3.5 Sonnet, GPT-4o o v0.dev sin sobrecargar tu app.',
      icon: '🤖',
      category: 'IA & Código',
      estimatedTime: '2 min',
      steps: [
        {
          id: 'step-prompt-frontend-btn',
          targetSelector: '[data-tour="prompt-frontend-btn"]',
          title: 'Prompt Frontend IA',
          content: 'Genera en <5ms una especificación completa de contratos REST, payloads JSON y componentes para construir tu frontend en React, Angular o Vue con IA externa.',
          position: 'bottom',
          actionHint: 'Copia el prompt en un clic'
        }
      ]
    },
    {
      id: 'tour-collaboration',
      title: 'Colaboración en Tiempo Real y Chat',
      description: 'Edita simultáneamente con tu equipo, visualiza cursores y chatea en directo.',
      icon: '💬',
      category: 'Colaboración',
      estimatedTime: '2 min',
      steps: [
        {
          id: 'step-colab-btn',
          targetSelector: '[data-tour="colab-btn"]',
          title: 'Colaboradores & Chat',
          content: 'Abre la sala de chat colaborativa en vivo y revisa los bloqueos optimistas de elementos para evitar colisiones de edición.',
          position: 'bottom',
          actionHint: 'Chatea y colabora en vivo'
        }
      ]
    }
  ];

  constructor() {
    // Listener para recalcular posición del foco en redimensionamiento o scroll
    window.addEventListener('resize', () => this.updateTargetPosition());
    window.addEventListener('scroll', () => this.updateTargetPosition(), true);
  }

  public getAllTours(): TourDefinition[] {
    return this.tours;
  }

  public getTourById(id: string): TourDefinition | null {
    return this.tours.find(t => t.id === id) || null;
  }

  public startTour(tourId: string) {
    const tour = this.getTourById(tourId);
    if (!tour) return;

    this.activeTour.set(tour);
    this.currentStepIndex.set(0);
    this.executeStep(0);
  }

  public nextStep() {
    const tour = this.activeTour();
    if (!tour) return;

    const nextIndex = this.currentStepIndex() + 1;
    if (nextIndex < tour.steps.length) {
      this.currentStepIndex.set(nextIndex);
      this.executeStep(nextIndex);
    } else {
      this.endTour();
    }
  }

  public previousStep() {
    const prevIndex = this.currentStepIndex() - 1;
    if (prevIndex >= 0) {
      this.currentStepIndex.set(prevIndex);
      this.executeStep(prevIndex);
    }
  }

  public endTour() {
    this.activeTour.set(null);
    this.currentStepIndex.set(0);
    this.targetRect.set(null);
  }

  private executeStep(index: number) {
    const tour = this.activeTour();
    if (!tour || !tour.steps[index]) return;

    const step = tour.steps[index];

    // Si el paso requiere estar en otra ruta, navegar primero
    if (step.requiredRoute && this.router.url !== step.requiredRoute) {
      this.router.navigate([step.requiredRoute]).then(() => {
        this.locateElementWithRetry(step.targetSelector);
      });
    } else {
      this.locateElementWithRetry(step.targetSelector);
    }
  }

  private locateElementWithRetry(selector: string, attempts = 0) {
    const element = document.querySelector(selector);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
      setTimeout(() => {
        const rect = element.getBoundingClientRect();
        this.targetRect.set(rect);
      }, 150);
    } else if (attempts < 8) {
      // Reintentar si el componente está cargando o animando
      setTimeout(() => {
        this.locateElementWithRetry(selector, attempts + 1);
      }, 200);
    } else {
      // Si el elemento no se encuentra (ej. estamos en otra pantalla), centrar popover
      this.targetRect.set(null);
    }
  }

  public updateTargetPosition() {
    const step = this.currentStep();
    if (!step) return;

    const element = document.querySelector(step.targetSelector);
    if (element) {
      this.targetRect.set(element.getBoundingClientRect());
    }
  }
}
