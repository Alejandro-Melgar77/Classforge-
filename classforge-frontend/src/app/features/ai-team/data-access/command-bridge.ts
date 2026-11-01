import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { CommandExecutorService, ExecutionResult } from '../../diagrams/ai-assistant/services/command-executor.service';
import { AiTeamApiService } from './ai-team.api';
import { Proposal } from './ai-team.models';

export interface ApplyProposalResult {
  success: boolean;
  message: string;
  requiresDiagramSwitch?: boolean;
  targetDiagramId?: string;
  executionResult?: ExecutionResult;
}

@Injectable({
  providedIn: 'root'
})
export class CommandBridgeService {
  private commandExecutor = inject(CommandExecutorService);
  private api = inject(AiTeamApiService);

  /**
   * Applies an AI Proposal with kind 'uml_command' onto the canvas using CommandExecutorService.
   * Crucial: NEVER re-submits text to /ai/generate! Directly executes the pre-structured command.
   * On success, registers the proposal state as 'applied' in the backend.
   */
  public async applyProposal(
    projectId: string,
    messageId: string,
    proposal: Proposal,
    currentDiagramId?: string,
    proposalDiagramId?: string
  ): Promise<ApplyProposalResult> {
    if (!proposal || proposal.kind !== 'uml_command' || !proposal.command) {
      return {
        success: false,
        message: 'La propuesta no contiene un comando UML ejecutable válido.'
      };
    }

    // Check if the current canvas diagram matches the proposal's diagram context
    if (proposalDiagramId && currentDiagramId && proposalDiagramId !== currentDiagramId) {
      return {
        success: false,
        requiresDiagramSwitch: true,
        targetDiagramId: proposalDiagramId,
        message: `El diagrama activo (${currentDiagramId}) no coincide con el diagrama objetivo de la propuesta (${proposalDiagramId}). Abre el diagrama correspondiente antes de aplicar los cambios.`
      };
    }

    // Execute directly on the canvas graph
    const execution = this.commandExecutor.execute(proposal.command);

    if (!execution.success) {
      return {
        success: false,
        message: `Error al aplicar comando en el lienzo: ${execution.message}`,
        executionResult: execution
      };
    }

    // Successfully applied to canvas: notify backend to record audit and broadcast via WS
    try {
      await firstValueFrom(this.api.setProposalState(projectId, messageId, proposal.id, 'applied'));
    } catch {
      // The canvas change is already applied, but backend state update failed
      return {
        success: true,
        message: `${execution.message} (Nota: no se pudo sincronizar el estado en el servidor)`,
        executionResult: execution
      };
    }

    return {
      success: true,
      message: execution.message,
      executionResult: execution
    };
  }

  /**
   * Marks a proposal as dismissed in the backend audit log.
   */
  public async dismissProposal(
    projectId: string,
    messageId: string,
    proposalId: string
  ): Promise<{ success: boolean; message: string }> {
    try {
      await firstValueFrom(this.api.setProposalState(projectId, messageId, proposalId, 'dismissed'));
      return {
        success: true,
        message: 'Propuesta descartada correctamente.'
      };
    } catch {
      return {
        success: false,
        message: 'Error al descartar la propuesta en el servidor.'
      };
    }
  }
}
