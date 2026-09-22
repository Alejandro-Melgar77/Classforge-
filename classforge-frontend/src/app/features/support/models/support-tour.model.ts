export type PopoverPosition = 'top' | 'bottom' | 'left' | 'right' | 'center';

export interface TourStep {
  id: string;
  targetSelector: string; // Selector CSS o atributo data-tour, ej: '[data-tour="new-diagram-btn"]'
  title: string;
  content: string;
  position: PopoverPosition;
  requiredRoute?: string; // Ruta donde debe estar el usuario, ej: '/diagrams'
  actionHint?: string;    // Ej: "Haz clic en el botón iluminado"
}

export interface TourDefinition {
  id: string;
  title: string;
  description: string;
  icon: string;
  category: 'Básico' | 'Modelado UML' | 'IA & Código' | 'Colaboración';
  estimatedTime: string; // Ej: "2 min"
  steps: TourStep[];
}

export interface SupportChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: Date;
  suggestedTourId?: string;
  suggestedTourTitle?: string;
  quickActions?: { label: string; action: string }[];
}

export interface TourState {
  isActive: boolean;
  currentTour: TourDefinition | null;
  currentStepIndex: number;
  totalSteps: number;
  targetRect: DOMRect | null;
}
