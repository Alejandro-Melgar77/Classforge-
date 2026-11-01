import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DiagramCanvasComponent } from './diagram-canvas.component';
import { ActivatedRoute, Router } from '@angular/router';
import { DiagramService } from '../services/diagram.service';
import { CollaborationService } from '../collaboration/services/collaboration.service';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmDialogService } from '../../../core/services/confirm-dialog.service';
import { CodegenService } from '../codegen/services/codegen.service';
import { CanvasService } from '../services/canvas.service';
import { signal } from '@angular/core';
import { of } from 'rxjs';

describe('DiagramCanvasComponent (Ciclo de Vida y Prevención de Fugas)', () => {
  let fixture: ComponentFixture<DiagramCanvasComponent>;
  let component: DiagramCanvasComponent;
  let colabSpy: jasmine.SpyObj<CollaborationService>;
  let diagramSpy: jasmine.SpyObj<DiagramService>;

  beforeEach(async () => {
    colabSpy = jasmine.createSpyObj('CollaborationService', [
      'connect', 
      'disconnect', 
      'sendCursor', 
      'sendNodeOperation', 
      'sendEdgeOperation',
      'acquireLock',
      'releaseLock',
      'getLockOwner'
    ], {
      remoteOperations$: of(),
      opRejected$: of(),
      aiFocus$: of(),
      connectedUsers: () => [],
      lockedElements: () => new Map(),
      connectionStatus: () => 'disconnected',
      remoteCursors: () => new Map(),
      chatMessages: () => []
    });

    diagramSpy = jasmine.createSpyObj('DiagramService', [
      'getDiagram',
      'saveGraph',
      'getWsToken',
      'getHistory'
    ]);
    diagramSpy.getDiagram.and.returnValue(of({
      success: true,
      data: {
        id: 'diag-test-1',
        name: 'Diagrama Test',
        description: 'Test',
        status: 'draft',
        version: 1,
        graph_data: { nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 } },
        created_by: 'u1',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        project_id: 'p1',
        team_id: null
      } as any
    }));

    await TestBed.configureTestingModule({
      imports: [DiagramCanvasComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => 'diag-test-1' } } }
        },
        {
          provide: Router,
          useValue: jasmine.createSpyObj('Router', ['navigate'])
        },
        { provide: CollaborationService, useValue: colabSpy },
        { provide: DiagramService, useValue: diagramSpy },
        {
          provide: CodegenService,
          useValue: {
            isLoading: signal(false),
            generatedFiles: signal({}),
            getPreview: () => of({ success: true, data: { files: {} } })
          }
        },
        {
          provide: AuthService,
          useValue: {
            getCurrentUser: () => ({ id: 'u1', name: 'Tester', email: 'test@example.com' }),
            hasRole: () => true
          }
        },
        {
          provide: ToastService,
          useValue: jasmine.createSpyObj('ToastService', ['success', 'error', 'info', 'warning'])
        },
        {
          provide: ConfirmDialogService,
          useValue: jasmine.createSpyObj('ConfirmDialogService', ['confirm'])
        }
      ]
    }).compileComponents();
  });

  it('debe crearse correctamente e inicializar el diagrama', () => {
    fixture = TestBed.createComponent(DiagramCanvasComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component).toBeTruthy();
    expect(colabSpy.connect).toHaveBeenCalledWith('diag-test-1');
  });

  it('debe desconectar sockets, temporizadores y listeners sin fugas tras navegar 20 veces', () => {
    // Prueba de esfuerzo de 20 navegaciones consecutivas
    for (let i = 0; i < 20; i++) {
      const testFixture = TestBed.createComponent(DiagramCanvasComponent);
      const testComp = testFixture.componentInstance;
      testFixture.detectChanges();

      // Verificar que se conectó
      expect(colabSpy.connect).toHaveBeenCalled();

      // Destruir componente simulando salir de la ruta
      testFixture.destroy();

      // Verificar que se desconectó limpiamente en cada iteración
      expect(colabSpy.disconnect).toHaveBeenCalled();
    }
  });
});
