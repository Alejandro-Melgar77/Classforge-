import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { AutoSaveService } from './auto-save.service';
import { DiagramService } from './diagram.service';
import { ToastService } from '../../../core/services/toast.service';
import { of, throwError } from 'rxjs';
import { GraphData } from '../models/diagram.model';

describe('AutoSaveService', () => {
  let service: AutoSaveService;
  let diagramServiceSpy: jasmine.SpyObj<DiagramService>;
  let toastServiceSpy: jasmine.SpyObj<ToastService>;

  const mockGraphData: GraphData = {
    nodes: [],
    edges: [],
    viewport: { x: 0, y: 0, zoom: 1 }
  };

  beforeEach(() => {
    diagramServiceSpy = jasmine.createSpyObj('DiagramService', ['saveGraph']);
    toastServiceSpy = jasmine.createSpyObj('ToastService', ['error', 'warning', 'info', 'success']);

    TestBed.configureTestingModule({
      providers: [
        AutoSaveService,
        { provide: DiagramService, useValue: diagramServiceSpy },
        { provide: ToastService, useValue: toastServiceSpy }
      ]
    });

    service = TestBed.inject(AutoSaveService);
  });

  afterEach(() => {
    service.destroy();
  });

  it('debe inicializarse en estado saved y limpio', () => {
    service.init('diag-1', () => mockGraphData);
    expect(service.saveStatus()).toBe('saved');
  });

  it('debe marcarse como dirty y pasar a unsaved al modificar el lienzo', () => {
    service.init('diag-1', () => mockGraphData);
    service.markDirty();
    expect(service.saveStatus()).toBe('unsaved');
  });

  it('debe ejecutar auto-save tras el debounce de 5s y pasar a saved', fakeAsync(() => {
    diagramServiceSpy.saveGraph.and.returnValue(of({ success: true, message: 'Saved', data: {} as any }));
    service.init('diag-1', () => mockGraphData);
    
    service.markDirty();
    expect(service.saveStatus()).toBe('unsaved');

    tick(5000);
    expect(diagramServiceSpy.saveGraph).toHaveBeenCalledWith('diag-1', mockGraphData, 'Auto-save');
    expect(service.saveStatus()).toBe('saved');
  }));

  it('debe reintentar con backoff exponencial si la petición falla y pasar a error tras agotar reintentos', fakeAsync(() => {
    diagramServiceSpy.saveGraph.and.returnValue(throwError(() => new Error('Network error')));
    service.init('diag-1', () => mockGraphData);

    service.markDirty();
    tick(5000); // 1er intento falla

    expect(diagramServiceSpy.saveGraph).toHaveBeenCalledTimes(1);

    tick(1000); // Reintento 1 (1s backoff)
    expect(diagramServiceSpy.saveGraph).toHaveBeenCalledTimes(2);

    tick(2000); // Reintento 2 (2s backoff)
    expect(diagramServiceSpy.saveGraph).toHaveBeenCalledTimes(3);

    tick(4000); // Reintento 3 (4s backoff)
    expect(diagramServiceSpy.saveGraph).toHaveBeenCalledTimes(4);

    expect(service.saveStatus()).toBe('error');
    expect(toastServiceSpy.error).toHaveBeenCalled();
  }));

  it('forceSaveNow debe guardar inmediatamente sin esperar el debounce', fakeAsync(() => {
    diagramServiceSpy.saveGraph.and.returnValue(of({ success: true, message: 'Saved', data: {} as any }));
    service.init('diag-1', () => mockGraphData);
    service.markDirty();

    service.forceSaveNow();
    tick();
    expect(diagramServiceSpy.saveGraph).toHaveBeenCalledTimes(1);
    expect(service.saveStatus()).toBe('saved');
  }));
});
