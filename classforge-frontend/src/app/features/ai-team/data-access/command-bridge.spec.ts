import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { CommandExecutorService, ExecutionResult } from '../../diagrams/ai-assistant/services/command-executor.service';
import { AiTeamApiService } from './ai-team.api';
import { CommandBridgeService } from './command-bridge';
import { Proposal } from './ai-team.models';
import { UMLCommandResponse } from '../../diagrams/ai-assistant/models/ai-command.model';

describe('CommandBridgeService', () => {
  let bridge: CommandBridgeService;
  let executorSpy: jasmine.SpyObj<CommandExecutorService>;
  let apiSpy: jasmine.SpyObj<AiTeamApiService>;

  const mockCommand: UMLCommandResponse = {
    action: 'create_class',
    classes: [
      {
        name: 'Factura',
        attributes: [{ name: 'id', type: 'Long', visibility: '+' }],
        methods: [{ name: 'calcularTotal', params: '', return_type: 'Double', visibility: '+' }]
      }
    ],
    relations: [],
    deleted_elements: [],
    explanation: 'Crear clase Factura',
    source: 'backend_ai'
  };

  const validProposal: Proposal = {
    id: 'prop-101',
    kind: 'uml_command',
    title: 'Crear entidad Factura',
    rationale: 'Necesaria para el módulo de facturación',
    severity: 'info',
    command: mockCommand
  };

  beforeEach(() => {
    executorSpy = jasmine.createSpyObj('CommandExecutorService', ['execute']);
    apiSpy = jasmine.createSpyObj('AiTeamApiService', ['setProposalState']);

    TestBed.configureTestingModule({
      providers: [
        CommandBridgeService,
        { provide: CommandExecutorService, useValue: executorSpy },
        { provide: AiTeamApiService, useValue: apiSpy }
      ]
    });

    bridge = TestBed.inject(CommandBridgeService);
  });

  it('should be created', () => {
    expect(bridge).toBeTruthy();
  });

  it('should apply valid uml_command directly via CommandExecutorService and record applied state', async () => {
    const execResult: ExecutionResult = {
      success: true,
      createdClasses: 1,
      updatedClasses: 0,
      createdRelations: 0,
      deletedElements: 0,
      message: '1 clase(s) creada(s)'
    };
    executorSpy.execute.and.returnValue(execResult);
    apiSpy.setProposalState.and.returnValue(of({
      message: {} as any,
      proposal_id: 'prop-101',
      status: 'applied'
    }));

    const result = await bridge.applyProposal('proj-1', 'msg-1', validProposal, 'diag-1', 'diag-1');

    expect(executorSpy.execute).toHaveBeenCalledTimes(1);
    expect(executorSpy.execute).toHaveBeenCalledWith(mockCommand);
    expect(apiSpy.setProposalState).toHaveBeenCalledWith('proj-1', 'msg-1', 'prop-101', 'applied');
    expect(result.success).toBeTrue();
    expect(result.message).toContain('1 clase(s) creada(s)');
  });

  it('should reject proposal if kind is not uml_command', async () => {
    const taskProposal: Proposal = {
      id: 'prop-task',
      kind: 'task',
      title: 'Crear tarea',
      rationale: 'No es comando UML',
      severity: 'info'
    };

    const result = await bridge.applyProposal('proj-1', 'msg-1', taskProposal);

    expect(result.success).toBeFalse();
    expect(result.message).toContain('no contiene un comando UML ejecutable');
    expect(executorSpy.execute).not.toHaveBeenCalled();
    expect(apiSpy.setProposalState).not.toHaveBeenCalled();
  });

  it('should reject proposal if command payload is missing', async () => {
    const invalidProposal: Proposal = {
      id: 'prop-empty',
      kind: 'uml_command',
      title: 'Comando sin payload',
      rationale: 'Falta command',
      severity: 'warn'
    };

    const result = await bridge.applyProposal('proj-1', 'msg-1', invalidProposal);

    expect(result.success).toBeFalse();
    expect(executorSpy.execute).not.toHaveBeenCalled();
  });

  it('should detect diagram mismatch and warn without applying changes', async () => {
    const result = await bridge.applyProposal(
      'proj-1',
      'msg-1',
      validProposal,
      'diag-active-A',
      'diag-target-B'
    );

    expect(result.success).toBeFalse();
    expect(result.requiresDiagramSwitch).toBeTrue();
    expect(result.targetDiagramId).toBe('diag-target-B');
    expect(result.message).toContain('no coincide con el diagrama objetivo');
    expect(executorSpy.execute).not.toHaveBeenCalled();
    expect(apiSpy.setProposalState).not.toHaveBeenCalled();
  });

  it('should handle CommandExecutor failure without updating backend state', async () => {
    const failResult: ExecutionResult = {
      success: false,
      createdClasses: 0,
      updatedClasses: 0,
      createdRelations: 0,
      deletedElements: 0,
      message: 'Lienzo no inicializado.'
    };
    executorSpy.execute.and.returnValue(failResult);

    const result = await bridge.applyProposal('proj-1', 'msg-1', validProposal);

    expect(executorSpy.execute).toHaveBeenCalled();
    expect(apiSpy.setProposalState).not.toHaveBeenCalled();
    expect(result.success).toBeFalse();
    expect(result.message).toContain('Lienzo no inicializado');
  });

  it('should dismiss proposal by calling setProposalState with dismissed', async () => {
    apiSpy.setProposalState.and.returnValue(of({
      message: {} as any,
      proposal_id: 'prop-101',
      status: 'dismissed'
    }));

    const result = await bridge.dismissProposal('proj-1', 'msg-1', 'prop-101');

    expect(apiSpy.setProposalState).toHaveBeenCalledWith('proj-1', 'msg-1', 'prop-101', 'dismissed');
    expect(result.success).toBeTrue();
    expect(result.message).toContain('descartada');
  });
});
