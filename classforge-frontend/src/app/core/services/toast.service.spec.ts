import { TestBed } from '@angular/core/testing';
import { ToastService } from './toast.service';

describe('ToastService', () => {
  let service: ToastService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ToastService]
    });
    service = TestBed.inject(ToastService);
  });

  it('should be created and start with empty toasts', () => {
    expect(service).toBeTruthy();
    expect(service.toasts().length).toBe(0);
  });

  it('should add a success toast', () => {
    const id = service.success('Operación exitosa');
    expect(id).toBeTruthy();
    const current = service.toasts();
    expect(current.length).toBe(1);
    expect(current[0].type).toBe('success');
    expect(current[0].message).toBe('Operación exitosa');
  });

  it('should add an error toast', () => {
    service.error('Falló la conexión');
    const current = service.toasts();
    expect(current.length).toBe(1);
    expect(current[0].type).toBe('error');
    expect(current[0].title).toBe('Error');
  });

  it('should dismiss a toast by id', () => {
    const id1 = service.info('Mensaje 1');
    const id2 = service.warning('Mensaje 2');
    expect(service.toasts().length).toBe(2);

    service.dismiss(id1);
    expect(service.toasts().length).toBe(1);
    expect(service.toasts()[0].id).toBe(id2);
  });

  it('should clear all toasts', () => {
    service.info('1');
    service.info('2');
    expect(service.toasts().length).toBe(2);

    service.clearAll();
    expect(service.toasts().length).toBe(0);
  });
});
