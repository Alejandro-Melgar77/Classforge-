import { Injectable, signal, computed, inject } from '@angular/core';
import { Router } from '@angular/router';
import { TourDefinition, TourStep, UserRole } from '../models/support-tour.model';
import { AuthService } from '../../../core/services/auth.service';

@Injectable({
  providedIn: 'root'
})
export class SupportTourService {
  private router = inject(Router);
  private authService = inject(AuthService);

  // State Signals (Angular 17)
  public activeTour = signal<TourDefinition | null>(null);
  public currentStepIndex = signal<number>(0);
  public targetRect = signal<DOMRect | null>(null);

  // Action-based advancement listeners
  private currentActionCleanup: (() => void) | null = null;

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

  // Catálogo Completo de Tours Guiados Predefinidos
  private tours: TourDefinition[] = [
    {
      id: 'tour-auth-navigation',
      title: 'Navegación General y Dashboard',
      description: 'Conoce las secciones principales de ClassForge, acceso a proyectos y barra lateral.',
      icon: '🧭',
      category: 'Básico',
      estimatedTime: '2 min',
      steps: [
        {
          id: 'step-nav-dashboard',
          targetSelector: '[data-tour="nav-dashboard"]',
          title: 'Panel Principal (Dashboard)',
          content: 'Accede a tus estadísticas consolidadas, proyectos recientes y actividad en tiempo real.',
          position: 'right',
          actionHint: 'Observa la barra de navegación lateral',
          actionType: 'click'
        },
        {
          id: 'step-nav-projects',
          targetSelector: '[data-tour="nav-projects"]',
          title: 'Centro de Proyectos',
          content: 'Gestiona tus proyectos personales y los espacios colaborativos compartidos con tu equipo.',
          position: 'right',
          actionHint: 'Haz clic en Proyectos para ingresar'
        },
        {
          id: 'step-nav-diagrams',
          targetSelector: '[data-tour="nav-diagrams"]',
          title: 'Explorador de Diagramas',
          content: 'Acceso directo a todos los diagramas de clases UML 2.5+ registrados en tu cuenta.',
          position: 'right'
        }
      ]
    },
    {
      id: 'tour-projects-management',
      title: 'Gestión de Proyectos y Carpetas',
      description: 'Aprende a estructurar tus espacios de trabajo, crear proyectos y organizar carpetas.',
      icon: '📁',
      category: 'Gestión & Equipos',
      estimatedTime: '2 min',
      allowedRoles: ['admin', 'scrum_master', 'dev'],
      steps: [
        {
          id: 'step-proj-new-btn',
          targetSelector: '[data-tour="new-project-btn"]',
          title: 'Crear Proyecto',
          content: 'Pulsa aquí para iniciar un nuevo proyecto de software. Puedes configurarlo como personal o asignarlo a un equipo.',
          position: 'bottom',
          requiredRoute: '/projects',
          actionHint: 'Haz clic en "Nuevo Proyecto"'
        },
        {
          id: 'step-proj-filters',
          targetSelector: '[data-tour="project-filters"]',
          title: 'Filtros y Búsqueda',
          content: 'Organiza la vista por estado (En progreso, Revisión, Completado) o filtra por equipo de desarrollo.',
          position: 'bottom',
          requiredRoute: '/projects'
        }
      ]
    },
    {
      id: 'tour-teams-roles',
      title: 'Equipos y Asignación de Roles',
      description: 'Administra miembros del equipo, roles ágiles (Scrum Master, Dev) e invitaciones seguras.',
      icon: '👥',
      category: 'Gestión & Equipos',
      estimatedTime: '3 min',
      allowedRoles: ['admin', 'scrum_master'],
      steps: [
        {
          id: 'step-teams-nav',
          targetSelector: '[data-tour="nav-teams"]',
          title: 'Administración de Equipos',
          content: 'Visualiza la lista de equipos de trabajo a los que perteneces o tienes permisos de gestión.',
          position: 'right'
        },
        {
          id: 'step-team-members',
          targetSelector: '[data-tour="team-members-list"]',
          title: 'Miembros y Roles',
          content: 'Supervisa los integrantes del equipo. Como Scrum Master o Administrador puedes asignar responsabilidades y permisos.',
          position: 'bottom'
        }
      ]
    },
    {
      id: 'tour-create-diagram',
      title: 'Creación de Diagramas UML',
      description: 'Crea tu primer diagrama, organiza proyectos y accede al lienzo interactivo.',
      icon: '📐',
      category: 'Modelado UML',
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
      description: 'Descubre la barra flotante, tipos de clases UML, edición de atributos y autoguardado.',
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
          content: 'ClassForge cuenta con auto-guardado en segundo plano cada 30 segundos y guarda versiones atómicas en MongoDB. También puedes guardar manualmente con un solo clic.',
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
      id: 'tour-ai-team-roles',
      title: 'Equipo de IA Participativa y Propuestas',
      description: 'Interactúa con agentes especializados (Arquitecto, Backend, QA), revisa propuestas y aplica cambios.',
      icon: '🤖',
      category: 'IA & Código',
      estimatedTime: '3 min',
      steps: [
        {
          id: 'step-ai-team-tab',
          targetSelector: '[data-tour="ai-team-tab"]',
          title: 'Pestaña Equipo IA',
          content: 'Accede al espacio donde los agentes de IA analizan el proyecto, sugieren tareas y presentan propuestas de mejora arquitectónica.',
          position: 'bottom'
        },
        {
          id: 'step-ai-proposals',
          targetSelector: '[data-tour="ai-proposals-panel"]',
          title: 'Propuestas de Modificación',
          content: 'Revisa las propuestas emitidas por la IA. Como usuario autorizado puedes aprobarlas y aplicarlas directamente al modelo UML con control de versiones.',
          position: 'left'
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
    },
    {
      id: 'tour-codegen-spring',
      title: 'Generación de Código Spring Boot & FastAPI',
      description: 'Genera microservicios limpios con arquitectura hexagonal / DDD y descarga el proyecto en ZIP.',
      icon: '💻',
      category: 'IA & Código',
      estimatedTime: '2 min',
      steps: [
        {
          id: 'step-live-code-btn',
          targetSelector: '[data-tour="live-code-btn"]',
          title: 'Generador de Código',
          content: 'Haz clic aquí para abrir el panel de código. Cada clase y relación que diseñes se traduce instantáneamente a Entidades JPA/SQLAlchemy, Repositorios, Servicios y Controladores REST.',
          position: 'bottom',
          actionHint: 'Observa la generación incremental'
        }
      ]
    },
    {
      id: 'tour-project-evaluator',
      title: 'Evaluador Inteligente Local de Proyectos',
      description: 'Audita especificaciones técnicas en PDF, aplica la rúbrica CF-SE-2026.1 y descarga dictámenes oficiales.',
      icon: '📑',
      category: 'IA & Código',
      estimatedTime: '3 min',
      steps: [
        {
          id: 'step-eval-tab',
          targetSelector: '[data-tour="eval-tab"]',
          title: 'Módulo Evaluador IA',
          content: 'Sube la documentación PDF de tu proyecto. El motor local analiza el alcance, requisitos, arquitectura UML, persistencia y seguridad.',
          position: 'bottom'
        },
        {
          id: 'step-eval-results',
          targetSelector: '[data-tour="eval-results"]',
          title: 'Dictamen e Informes PDF',
          content: 'Revisa el puntaje ponderado, hallazgos con evidencias de página y descarga el Dictamen Oficial o Pliego de Especificaciones Técnicas.',
          position: 'top'
        }
      ]
    }
  ];

  constructor() {
    window.addEventListener('resize', () => this.updateTargetPosition());
    window.addEventListener('scroll', () => this.updateTargetPosition(), true);
  }

  public getAllTours(): TourDefinition[] {
    return this.tours;
  }

  public getAvailableTours(): TourDefinition[] {
    // Read current user role from AuthService
    let userRole: UserRole = 'dev';
    try {
      const user = this.authService.getCurrentUser ? this.authService.getCurrentUser() : (this.authService as any).currentUserSubject?.value;
      if (user && user.role) {
        userRole = user.role as UserRole;
      }
    } catch {
      userRole = 'dev';
    }

    return this.tours.filter(tour => {
      if (!tour.allowedRoles || tour.allowedRoles.length === 0) {
        return true;
      }
      return tour.allowedRoles.includes(userRole);
    });
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

    this.cleanupActionListener();

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
      this.cleanupActionListener();
      this.currentStepIndex.set(prevIndex);
      this.executeStep(prevIndex);
    }
  }

  public prevStep() {
    this.previousStep();
  }

  public endTour() {
    this.cleanupActionListener();
    this.activeTour.set(null);
    this.currentStepIndex.set(0);
    this.targetRect.set(null);
  }

  private cleanupActionListener() {
    if (this.currentActionCleanup) {
      this.currentActionCleanup();
      this.currentActionCleanup = null;
    }
  }

  private executeStep(index: number) {
    const tour = this.activeTour();
    if (!tour || !tour.steps[index]) return;

    const step = tour.steps[index];

    // Si el paso requiere estar en otra ruta, navegar primero
    if (step.requiredRoute && this.router.url !== step.requiredRoute) {
      this.router.navigate([step.requiredRoute]).then(() => {
        this.locateElementWithRetry(step);
      });
    } else {
      this.locateElementWithRetry(step);
    }
  }

  private locateElementWithRetry(step: TourStep, attempts = 0) {
    const element = document.querySelector(step.targetSelector) as HTMLElement | null;
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
      setTimeout(() => {
        const rect = element.getBoundingClientRect();
        this.targetRect.set(rect);

        // Bind real action listener if step requires it
        if (step.actionType === 'click') {
          const handler = () => {
            this.nextStep();
          };
          element.addEventListener('click', handler, { once: true });
          this.currentActionCleanup = () => {
            element.removeEventListener('click', handler);
          };
        }
      }, 150);
    } else if (attempts < 6) {
      // Reintentar si el componente está cargando o animando
      setTimeout(() => {
        this.locateElementWithRetry(step, attempts + 1);
      }, 200);
    } else {
      // Si el elemento no se encuentra, centrar el popover de forma elegante sin romper la app
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
