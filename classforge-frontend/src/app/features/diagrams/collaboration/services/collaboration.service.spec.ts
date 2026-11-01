import { TestBed } from '@angular/core/testing';
import { CollaborationService } from './collaboration.service';
import { DiagramService } from '../../services/diagram.service';
import { ToastService } from '../../../../core/services/toast.service';
import { of } from 'rxjs';

describe('CollaborationService', () => {
  let service: CollaborationService;
  let diagramServiceSpy: jasmine.SpyObj<DiagramService>;
  let toastServiceSpy: jasmine.SpyObj<ToastService>;

  beforeEach(() => {
    diagramServiceSpy = jasmine.createSpyObj('DiagramService', ['getWsToken']);
    toastServiceSpy = jasmine.createSpyObj('ToastService', ['warning', 'info', 'error', 'success']);

    TestBed.configureTestingModule({
      providers: [
        CollaborationService,
        { provide: DiagramService, useValue: diagramServiceSpy },
        { provide: ToastService, useValue: toastServiceSpy }
      ]
    });

    service = TestBed.inject(CollaborationService);
  });

  afterEach(() => {
    service.disconnect();
  });

  it('debe iniciar en estado disconnected', () => {
    expect(service.connectionStatus()).toBe('disconnected');
    expect(service.connectedUsers()).toEqual([]);
  });

  it('debe manejar OP_REJECTED emitiendo por opRejected$ y mostrando un Toast warning', (done) => {
    service.opRejected$.subscribe(({ element_id, reason }) => {
      expect(element_id).toBe('node-123');
      expect(reason).toBe('locked');
      expect(toastServiceSpy.warning).toHaveBeenCalled();
      done();
    });

    // Simular recepción de mensaje OP_REJECTED del servidor
    (service as any).handleMessage({
      type: 'OP_REJECTED',
      element_id: 'node-123',
      reason: 'locked'
    });
  });

  it('debe manejar AI_FOCUS emitiendo por aiFocus$', (done) => {
    service.aiFocus$.subscribe(({ element_ids, role }) => {
      expect(element_ids).toEqual(['node-1', 'node-2']);
      expect(role).toBe('architect');
      done();
    });

    (service as any).handleMessage({
      type: 'AI_FOCUS',
      element_ids: ['node-1', 'node-2'],
      role: 'architect'
    });
  });

  it('debe encolar operaciones si el WebSocket no está abierto (cola offline)', () => {
    service.sendNodeOperation('move', 'node-1', { x: 100, y: 150 });
    const queue = (service as any).offlineQueue;
    expect(queue.length).toBe(1);
    expect(queue[0].type).toBe('NODE_OPERATION');
    expect(queue[0].node_id).toBe('node-1');
  });

  it('debe permitir añadir la IA como integrante autónomo a la presencia', () => {
    service.setAiMemberPresence(true, 'architect');
    const users = service.connectedUsers();
    const aiUser = users.find(u => u.is_ai);
    expect(aiUser).toBeDefined();
    expect(aiUser?.name).toBe('Arquitecto IA');
    expect(aiUser?.role).toBe('architect');

    service.setAiMemberPresence(false);
    expect(service.connectedUsers().find(u => u.is_ai)).toBeUndefined();
  });
});
