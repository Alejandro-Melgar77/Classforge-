import { Injectable } from '@angular/core';

export interface SupportNluResult {
  reply: string;
  suggestedTourId?: string;
  suggestedTourTitle?: string;
  category?: string;
}

@Injectable({
  providedIn: 'root'
})
export class SupportNluService {

  public processQuery(query: string): SupportNluResult {
    const normalized = this.normalize(query);

    // 1. Crear nuevo diagrama
    if (this.matchesAny(normalized, ['crear diagrama', 'nuevo diagrama', 'como creo un diagrama', 'empezar', 'primer diagrama', 'abrir diagramador'])) {
      return {
        reply: 'Para crear un diagrama conceptual UML, dirígete al menú "Diagramas" y haz clic en el botón azul "Nuevo Diagrama". ClassForge generará tu lienzo y lo abrirá automáticamente.',
        suggestedTourId: 'tour-create-diagram',
        suggestedTourTitle: 'Tour: Creación de Diagramas UML',
        category: 'Básico'
      };
    }

    // 2. Asistente IA de Voz y Texto
    if (this.matchesAny(normalized, ['asistente ia', 'voz', 'microfono', 'ia', 'asistente', 'hablar', 'comandos por voz', 'dictar'])) {
      return {
        reply: 'ClassForge cuenta con un Asistente IA híbrido (NLU on-device <1ms + Ollama). En el lienzo, pulsa el botón "✨ Asistente IA & Voz", activa el micrófono o escribe comandos como "crear clase Usuario con atributos id:int, email:string" y pulsa Confirmar para aplicarlo directamente al lienzo.',
        suggestedTourId: 'tour-ai-assistant',
        suggestedTourTitle: 'Tour: Asistente IA de Voz y Modelado',
        category: 'IA & Código'
      };
    }

    // 3. Generación de Código Spring Boot
    if (this.matchesAny(normalized, ['spring boot', 'codigo en vivo', 'generar backend', 'backend', 'java', 'zip', 'descargar codigo', 'descargar proyecto', 'n8n'])) {
      return {
        reply: 'El generador incremental de Spring Boot 3 proyecta en tiempo real las entidades JPA, repositorios, servicios y controladores REST a partir de tus clases UML. Puedes pulsar "💻 Código en Vivo" en el lienzo para ver el árbol de archivos y descargar el archivo .ZIP listo para producción.',
        suggestedTourId: 'tour-codegen-spring',
        suggestedTourTitle: 'Tour: Código Spring Boot 3 en Vivo',
        category: 'IA & Código'
      };
    }

    // 4. Generación de Prompt para Frontend con IA Externa
    if (this.matchesAny(normalized, ['prompt frontend', 'frontend ia', 'claude', 'gpt', 'react', 'angular', 'vue', 'crear frontend', 'interfaz de usuario'])) {
      return {
        reply: 'Para construir tu frontend sin sobrecargar la aplicación, pulsa "🤖 Prompt Frontend IA" en el lienzo. ClassForge generará en menos de 5ms una especificación determinista completa de contratos REST para que Claude 3.5 Sonnet, GPT-4o o v0.dev generen la aplicación completa en React, Angular o Vue.',
        suggestedTourId: 'tour-frontend-prompt',
        suggestedTourTitle: 'Tour: Meta-Prompt Frontend para IA',
        category: 'IA & Código'
      };
    }

    // 5. Modelado UML: Clases, Atributos, Métodos y Relaciones
    if (this.matchesAny(normalized, ['herramientas', 'agregar clase', 'crear clase', 'interfaz', 'relaciones', 'herencia', 'composicion', 'atributos', 'metodos', 'panel propiedades'])) {
      return {
        reply: 'En la barra flotante izquierda encontrarás las herramientas para agregar Clases, Interfaces, Clases Abstractas, Enumeraciones y Notas. Al seleccionar cualquier elemento, en el panel derecho podrás modificar su nombre, visibilidad (+, -, #, ~), atributos y métodos.',
        suggestedTourId: 'tour-uml-modeling',
        suggestedTourTitle: 'Tour: Modelado y Barra de Herramientas',
        category: 'Modelado UML'
      };
    }

    // 6. Colaboración en Tiempo Real y Chat
    if (this.matchesAny(normalized, ['colaborar', 'colaboracion', 'tiempo real', 'chat', 'bloqueo', 'cursores', 'companeros', 'equipo', 'salas'])) {
      return {
        reply: 'ClassForge sincroniza automáticamente los movimientos y adiciones de tus compañeros vía WebSockets. Puedes ver sus cursores en vivo, su estado de presencia y abrir el panel "💬 Colaboradores & Chat" para conversar mientras editan.',
        suggestedTourId: 'tour-collaboration',
        suggestedTourTitle: 'Tour: Colaboración en Tiempo Real y Chat',
        category: 'Colaboración'
      };
    }

    // 7. Navegación general y Repertorio
    if (this.matchesAny(normalized, ['dashboard', 'repertorio', 'proyectos', 'equipos', 'carpetas', 'navegacion'])) {
      return {
        reply: 'El menú lateral te permite acceder al Dashboard con métricas ejecutivas, tus Proyectos organizados por carpetas y los Equipos de trabajo asignados por roles (Admin, Scrum Master, Developer).',
        suggestedTourId: 'tour-create-diagram',
        suggestedTourTitle: 'Tour: Recorrido por ClassForge',
        category: 'Básico'
      };
    }

    // Respuesta por defecto
    return {
      reply: `He analizado tu consulta sobre "${query}". Puedes explorar nuestros tutoriales guiados en vivo o elegir una de las guías interactivas disponibles a continuación para que te muestre los pasos exactos en la pantalla.`,
      suggestedTourId: 'tour-create-diagram',
      suggestedTourTitle: 'Tour Recomendado: Conociendo ClassForge',
      category: 'Básico'
    };
  }

  private normalize(str: string): string {
    return str
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  private matchesAny(input: string, keywords: string[]): boolean {
    return keywords.some(k => input.includes(k));
  }
}
