import { TestBed } from '@angular/core/testing';
import { SupportNluService } from './support-nlu.service';

describe('SupportNluService', () => {
  let service: SupportNluService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [SupportNluService]
    });
    service = TestBed.inject(SupportNluService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should recognize create diagram intent', () => {
    const result = service.processQuery('¿Cómo puedo crear un nuevo diagrama?');
    expect(result.suggestedTourId).toBe('tour-create-diagram');
    expect(result.category).toBe('Básico');
    expect(result.reply).toContain('Nuevo Diagrama');
  });

  it('should recognize AI assistant intent', () => {
    const result = service.processQuery('¿Cómo funciona el asistente de voz e IA?');
    expect(result.suggestedTourId).toBe('tour-ai-assistant');
    expect(result.category).toBe('IA & Código');
  });

  it('should recognize Spring Boot codegen intent', () => {
    const result = service.processQuery('quiero descargar el código en zip de spring boot');
    expect(result.suggestedTourId).toBe('tour-codegen-spring');
  });

  it('should recognize frontend prompt intent', () => {
    const result = service.processQuery('cómo genero el prompt para crear el frontend con claude o react?');
    expect(result.suggestedTourId).toBe('tour-frontend-prompt');
  });

  it('should recognize UML modeling intent', () => {
    const result = service.processQuery('cómo agrego una clase o modifico atributos en el panel de propiedades');
    expect(result.suggestedTourId).toBe('tour-uml-modeling');
  });

  it('should recognize collaboration intent', () => {
    const result = service.processQuery('cómo funciona la colaboración en tiempo real y el chat');
    expect(result.suggestedTourId).toBe('tour-collaboration');
  });

  it('should provide default helpful tour on unknown queries', () => {
    const result = service.processQuery('alguna pregunta desconocida xyz123');
    expect(result.suggestedTourId).toBe('tour-create-diagram');
    expect(result.reply).toContain('xyz123');
  });
});
