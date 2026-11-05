import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CommandConsoleComponent } from './command-console.component';
import { VoiceRecognitionService } from '../../services/voice-recognition.service';
import { AiService } from '../../services/ai.service';
import { CommandExecutorService } from '../../services/command-executor.service';
import { AiHistoryService } from '../../services/ai-history.service';
import { AiTeamStore } from '../../../../ai-team/data-access/ai-team.store';
import { of } from 'rxjs';
import { UMLCommandResponse } from '../../models/ai-command.model';
import { signal } from '@angular/core';

describe('CommandConsoleComponent', () => {
  let component: CommandConsoleComponent;
  let fixture: ComponentFixture<CommandConsoleComponent>;

  let mockVoice: any;
  let mockAi: any;
  let mockExecutor: any;
  let mockHistory: any;

  const mockCommand: UMLCommandResponse = {
    action: 'create_class',
    classes: [{ name: 'Order', attributes: [], methods: [] }],
    relations: [],
    deleted_elements: [],
    explanation: 'Created Order class',
    source: 'offline_nlu'
  };

  beforeEach(async () => {
    mockVoice = {
      isListening: signal(false),
      transcript: signal(''),
      interimTranscript: signal(''),
      audioLevel: signal(0),
      getBestTranscript: jasmine.createSpy().and.returnValue(''),
      startListening: jasmine.createSpy(),
      stopListening: jasmine.createSpy(),
      stopAndGetTranscript: jasmine.createSpy().and.returnValue(''),
      clear: jasmine.createSpy()
    };

    mockAi = {
      processInput: jasmine.createSpy().and.returnValue(of(mockCommand)),
      processImage: jasmine.createSpy().and.returnValue(of(mockCommand)),
      checkHealth: jasmine.createSpy().and.returnValue(of({ local_available: true, local_model: 'qwen2.5:1.5b' }))
    };

    const mockAiTeamStore = {
      isLocalOnly: signal(false)
    };

    mockExecutor = {
      execute: jasmine.createSpy().and.returnValue({ success: true, message: 'Ejecutado con éxito' })
    };

    mockHistory = {
      reloadHistory: jasmine.createSpy(),
      history: signal([]),
      addEntry: jasmine.createSpy(),
      clearUserHistory: jasmine.createSpy()
    };

    await TestBed.configureTestingModule({
      imports: [CommandConsoleComponent],
      providers: [
        { provide: VoiceRecognitionService, useValue: mockVoice },
        { provide: AiService, useValue: mockAi },
        { provide: AiTeamStore, useValue: mockAiTeamStore },
        { provide: CommandExecutorService, useValue: mockExecutor },
        { provide: AiHistoryService, useValue: mockHistory }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(CommandConsoleComponent);
    component = fixture.componentInstance;
    component.diagramId = 'diag-1';
    fixture.detectChanges();
  });

  it('should initialize and reload history for diagram', () => {
    expect(component).toBeTruthy();
    expect(mockHistory.reloadHistory).toHaveBeenCalledWith('diag-1');
  });

  it('should execute command directly when autoApply is true', () => {
    component.autoApply.set(true);
    component.executeDirectly('crear clase Order');

    expect(mockAi.processInput).toHaveBeenCalledWith('crear clase Order', undefined, 'auto', false);
    expect(mockExecutor.execute).toHaveBeenCalledWith(mockCommand);
    expect(mockHistory.addEntry).toHaveBeenCalledWith(
      'crear clase Order',
      'text',
      mockCommand,
      'applied',
      'diag-1'
    );
    expect(component.executionFeedback()?.type).toBe('success');
  });

  it('should show preview card when autoApply is false and command is submitted', () => {
    component.autoApply.set(false);
    component.textInput = 'crear clase Order';
    component.handleSubmit();

    expect(mockAi.processInput).toHaveBeenCalledWith('crear clase Order', undefined, 'auto', false);
    expect(component.pendingCommand()).toEqual(mockCommand);
    expect(mockExecutor.execute).not.toHaveBeenCalled();
  });

  it('should apply pending command and register to history', () => {
    component.pendingCommand.set(mockCommand);
    component.textInput = 'crear clase Order';

    component.applyCommand();

    expect(mockExecutor.execute).toHaveBeenCalledWith(mockCommand);
    expect(mockHistory.addEntry).toHaveBeenCalledWith(
      'crear clase Order',
      'text',
      mockCommand,
      'applied',
      'diag-1'
    );
    expect(component.pendingCommand()).toBeNull();
  });

  it('should discard pending command without executing', () => {
    component.pendingCommand.set(mockCommand);
    component.textInput = 'crear clase Order';

    component.discardCommand();

    expect(mockExecutor.execute).not.toHaveBeenCalled();
    expect(mockHistory.addEntry).toHaveBeenCalledWith(
      'crear clase Order',
      'text',
      mockCommand,
      'discarded',
      'diag-1'
    );
    expect(component.pendingCommand()).toBeNull();
  });

  it('should toggle voice recording', () => {
    component.toggleVoice();
    expect(mockVoice.startListening).toHaveBeenCalled();

    mockVoice.isListening.set(true);
    mockVoice.stopAndGetTranscript.and.returnValue('crear clase User');

    component.toggleVoice();
    expect(mockVoice.stopAndGetTranscript).toHaveBeenCalled();
  });

  it('should switch sections between console, examples and history', () => {
    component.setSection('examples');
    expect(component.activeSection()).toBe('examples');

    component.setSection('history');
    expect(component.activeSection()).toBe('history');

    component.setSection('console');
    expect(component.activeSection()).toBe('console');
  });

  it('should reject invalid image mime types', () => {
    const invalidFile = new File(['dummy'], 'test.txt', { type: 'text/plain' });
    component.handleImageFile(invalidFile);
    expect(component.attachedImage()).toBeNull();
    expect(component.executionFeedback()?.type).toBe('error');
  });

  it('should reject image exceeding 8 MB', () => {
    const bigBlob = new Uint8Array(9 * 1024 * 1024);
    const bigFile = new File([bigBlob], 'huge.png', { type: 'image/png' });
    component.handleImageFile(bigFile);
    expect(component.attachedImage()).toBeNull();
    expect(component.executionFeedback()?.message).toContain('8 MB');
  });

  it('should execute image directly when autoApply is true', () => {
    component.autoApply.set(true);
    component.attachedImage.set({
      dataUrl: 'data:image/png;base64,AAAA',
      base64: 'AAAA',
      mimeType: 'image/png',
      name: 'diagram.png',
      sizeBytes: 1024
    });
    component.textInput = 'boceto a UML';

    component.handleSubmit();

    expect(mockAi.processImage).toHaveBeenCalledWith('AAAA', 'image/png', 'boceto a UML', 'diag-1');
    expect(mockExecutor.execute).toHaveBeenCalledWith(mockCommand);
    expect(component.attachedImage()).toBeNull();
  });

  it('should remove attached image when requested', () => {
    component.attachedImage.set({
      dataUrl: 'data:image/png;base64,AAAA',
      base64: 'AAAA',
      mimeType: 'image/png',
      name: 'diagram.png',
      sizeBytes: 1024
    });
    component.removeImage();
    expect(component.attachedImage()).toBeNull();
  });
});
