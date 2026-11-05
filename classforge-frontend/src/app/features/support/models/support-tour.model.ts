export type PopoverPosition = 'top' | 'bottom' | 'left' | 'right' | 'center';

export type UserRole = 'admin' | 'scrum_master' | 'dev';

export type TourActionType = 'click' | 'manual' | 'navigate';

export interface TourStep {
  id: string;
  targetSelector: string; // Selector CSS o atributo data-tour, ej: '[data-tour="new-diagram-btn"]'
  title: string;
  content: string;
  position: PopoverPosition;
  requiredRoute?: string; // Ruta donde debe estar el usuario, ej: '/diagrams'
  actionHint?: string;    // Ej: "Haz clic en el botón iluminado"
  actionType?: TourActionType; // Acción requerida para avanzar (ej: 'click' en el target)
}

export interface TourDefinition {
  id: string;
  title: string;
  description: string;
  icon: string;
  category: 'Básico' | 'Modelado UML' | 'IA & Código' | 'Colaboración' | 'Gestión & Equipos';
  estimatedTime: string; // Ej: "2 min"
  allowedRoles?: UserRole[]; // Roles autorizados para ver este tour
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
