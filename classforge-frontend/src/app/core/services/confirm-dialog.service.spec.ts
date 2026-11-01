import { TestBed } from '@angular/core/testing';
import { ConfirmDialogService } from './confirm-dialog.service';

describe('ConfirmDialogService', () => {
  let service: ConfirmDialogService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ConfirmDialogService]
    });
    service = TestBed.inject(ConfirmDialogService);
  });

  it('should be created and start with null dialog', () => {
    expect(service).toBeTruthy();
    expect(service.dialog()).toBeNull();
  });

  it('should open dialog and resolve true when user confirms', async () => {
    const promise = service.confirm({
      title: 'Eliminar elemento',
      message: '¿Estás seguro?',
      danger: true
    });

    const current = service.dialog();
    expect(current).toBeTruthy();
    expect(current?.options.title).toBe('Eliminar elemento');
    expect(current?.options.danger).toBeTrue();

    service.handleAction(true);
    const result = await promise;
    expect(result).toBeTrue();
    expect(service.dialog()).toBeNull();
  });

  it('should open dialog and resolve false when user cancels', async () => {
    const promise = service.confirm({
      title: 'Cancelar cambios',
      message: '¿Deseas descartar los cambios?'
    });

    service.handleAction(false);
    const result = await promise;
    expect(result).toBeFalse();
    expect(service.dialog()).toBeNull();
  });
});
