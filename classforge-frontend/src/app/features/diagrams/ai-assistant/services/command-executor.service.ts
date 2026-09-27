import { Injectable, inject } from '@angular/core';
import { CanvasService } from '../../services/canvas.service';
import { CollaborationService } from '../../collaboration/services/collaboration.service';
import { AutoSaveService } from '../../services/auto-save.service';
import { UMLCommandResponse, UMLClassCommand, UMLRelationCommand } from '../models/ai-command.model';
import { NodeType, EdgeType, UMLNodeData, UMLAttribute, UMLMethod, Visibility } from '../../models/diagram.model';

export interface ExecutionResult {
  success: boolean;
  createdClasses: number;
  updatedClasses: number;
  createdRelations: number;
  deletedElements: number;
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class CommandExecutorService {
  private canvasService = inject(CanvasService);
  private collaborationService = inject(CollaborationService);
  private autoSaveService = inject(AutoSaveService);

  public execute(command: UMLCommandResponse): ExecutionResult {
    const graph = this.canvasService.getGraph();
    if (!graph) {
      return {
        success: false,
        createdClasses: 0,
        updatedClasses: 0,
        createdRelations: 0,
        deletedElements: 0,
        message: 'Lienzo no inicializado.'
      };
    }

    const createdNodeMap = new Map<string, any>();
    const affectedNodes: any[] = [];
    let createdCount = 0;
    let updatedCount = 0;
    let relCount = 0;
    let delCount = 0;

    // 1. Process classes (create, update, or generate_system)
    if (command.classes && command.classes.length > 0) {
      const existingNodes = graph.getNodes();

      command.classes.forEach((cls, idx) => {
        const clsNameNorm = cls.name.trim().toLowerCase();
        let existingNode = graph.getNodes().find((n: any) => {
          const name = (n.getData()?.name || n.data?.name || '').trim().toLowerCase();
          return name === clsNameNorm;
        });

        const normalizeVis = (v?: string): Visibility => {
          if (v === '-' || v === '#' || v === '~') return v;
          return '+';
        };

        const attributesFormatted: UMLAttribute[] = (cls.attributes || []).map(a => ({
          name: a.name,
          type: a.type || 'String',
          visibility: normalizeVis(a.visibility),
          default_value: null,
          is_static: false
        }));

        const methodsFormatted: UMLMethod[] = (cls.methods || []).map(m => ({
          name: m.name,
          params: m.params || '',
          return_type: m.return_type || 'void',
          visibility: normalizeVis(m.visibility),
          is_static: false,
          is_abstract: false
        }));

        const nodeType: NodeType = (
          cls.stereotype === 'abstract' ? 'abstract' :
          cls.stereotype === 'interface' ? 'interface' :
          cls.stereotype === 'enum' ? 'enum' : 'class'
        );

        if (existingNode) {
          const currentData = (existingNode.getData() as UMLNodeData) || { name: cls.name, stereotype: null, notes: null, attributes: [], methods: [] };
          
          // Merge attributes without duplicates
          const existingAttrNames = new Set((currentData.attributes || []).map(a => a.name.toLowerCase()));
          const newAttrs = attributesFormatted.filter(a => !existingAttrNames.has(a.name.toLowerCase()));
          const mergedAttrs: UMLAttribute[] = [...(currentData.attributes || []), ...newAttrs];

          // Merge methods without duplicates
          const existingMethodNames = new Set((currentData.methods || []).map(m => m.name.toLowerCase()));
          const newMethods = methodsFormatted.filter(m => !existingMethodNames.has(m.name.toLowerCase()));
          const mergedMethods: UMLMethod[] = [...(currentData.methods || []), ...newMethods];

          const updatedData: UMLNodeData = {
            name: cls.name,
            stereotype: currentData.stereotype || cls.stereotype || null,
            attributes: mergedAttrs,
            methods: mergedMethods,
            notes: currentData.notes || null
          };

          this.canvasService.updateNodeData(existingNode, updatedData, nodeType);
          this.collaborationService.sendNodeOperation('update', existingNode.id, {
            nodeType,
            data: updatedData
          });
          createdNodeMap.set(clsNameNorm, existingNode);
          affectedNodes.push(existingNode);
          updatedCount++;
        } else {
          // Dynamic non-overlapping grid layout
          const totalExisting = existingNodes.length + idx;
          const cols = 3;
          const col = totalExisting % cols;
          const row = Math.floor(totalExisting / cols);
          const pos = {
            x: 80 + (col * 280),
            y: 80 + (row * 210)
          };

          const initialData: UMLNodeData = {
            name: cls.name,
            stereotype: cls.stereotype || null,
            attributes: attributesFormatted.length > 0 ? attributesFormatted : [
              { name: 'id', type: 'Long', visibility: '+', default_value: null, is_static: false },
              { name: 'nombre', type: 'String', visibility: '+', default_value: null, is_static: false }
            ],
            methods: methodsFormatted,
            notes: null
          };

          const newNode = this.canvasService.addNode(nodeType, pos, undefined, initialData, undefined, false);
          if (newNode) {
            createdNodeMap.set(clsNameNorm, newNode);
            affectedNodes.push(newNode);
            createdCount++;
            this.collaborationService.sendNodeOperation('add', newNode.id, {
              nodeType,
              position: pos,
              size: newNode.size(),
              data: newNode.getData()
            });
          }
        }
      });
    }

    // 2. Process relations
    if (command.relations && command.relations.length > 0) {
      command.relations.forEach((rel, rIdx) => {
        const srcNorm = rel.source.trim().toLowerCase();
        const tgtNorm = rel.target.trim().toLowerCase();

        let sourceNode = graph.getNodes().find((n: any) => (n.getData()?.name || '').trim().toLowerCase() === srcNorm) || createdNodeMap.get(srcNorm);
        let targetNode = graph.getNodes().find((n: any) => (n.getData()?.name || '').trim().toLowerCase() === tgtNorm) || createdNodeMap.get(tgtNorm);

        // If target or source doesn't exist yet, create them dynamically
        if (!sourceNode) {
          const pos = { x: 80 + (rIdx * 280), y: 80 };
          sourceNode = this.canvasService.addNode('class', pos, undefined, {
            name: rel.source,
            stereotype: null,
            notes: null,
            attributes: [{ name: 'id', type: 'Long', visibility: '+', default_value: null, is_static: false }],
            methods: []
          }, undefined, false);
          if (sourceNode) {
            createdNodeMap.set(srcNorm, sourceNode);
            affectedNodes.push(sourceNode);
            createdCount++;
            this.collaborationService.sendNodeOperation('add', sourceNode.id, {
              nodeType: 'class',
              position: pos,
              size: sourceNode.size(),
              data: sourceNode.getData()
            });
          }
        }

        if (!targetNode) {
          const pos = { x: 380 + (rIdx * 280), y: 80 };
          targetNode = this.canvasService.addNode('class', pos, undefined, {
            name: rel.target,
            stereotype: null,
            notes: null,
            attributes: [{ name: 'id', type: 'Long', visibility: '+', default_value: null, is_static: false }],
            methods: []
          }, undefined, false);
          if (targetNode) {
            createdNodeMap.set(tgtNorm, targetNode);
            affectedNodes.push(targetNode);
            createdCount++;
            this.collaborationService.sendNodeOperation('add', targetNode.id, {
              nodeType: 'class',
              position: pos,
              size: targetNode.size(),
              data: targetNode.getData()
            });
          }
        }

        if (sourceNode && targetNode) {
          const edgeType: EdgeType = (rel.type as EdgeType) || 'association';
          const edgeId = `edge_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;

          const newEdge = this.canvasService.addRemoteEdge(
            edgeId,
            edgeType,
            sourceNode.id,
            targetNode.id,
            rel.label,
            rel.sourceMultiplicity,
            rel.targetMultiplicity
          );

          if (newEdge) {
            relCount++;
            this.collaborationService.sendEdgeOperation('add', edgeId, {
              type: edgeType,
              source: { cell: sourceNode.id },
              target: { cell: targetNode.id },
              label: rel.label,
              source_multiplicity: rel.sourceMultiplicity,
              target_multiplicity: rel.targetMultiplicity
            });
          }
        }
      });
    }

    // 3. Process deletions
    if (command.deleted_elements && command.deleted_elements.length > 0) {
      command.deleted_elements.forEach(name => {
        const nameNorm = name.trim().toLowerCase();
        const node = graph.getNodes().find((n: any) => (n.getData()?.name || '').trim().toLowerCase() === nameNorm);
        if (node) {
          const id = node.id;
          graph.removeCell(node);
          delCount++;
          this.collaborationService.sendNodeOperation('delete', id, null);
        }
      });
    }

    // 4. Select newly created/updated elements and adjust canvas view
    if (affectedNodes.length > 0) {
      graph.cleanSelection();
      graph.select(affectedNodes);
      this.canvasService.fitView();
    }

    this.autoSaveService.markDirty();

    const summaryParts: string[] = [];
    if (createdCount > 0) summaryParts.push(`${createdCount} clase(s) creada(s)`);
    if (updatedCount > 0) summaryParts.push(`${updatedCount} clase(s) modificada(s)`);
    if (relCount > 0) summaryParts.push(`${relCount} relacion(es)`);
    if (delCount > 0) summaryParts.push(`${delCount} elemento(s) eliminado(s)`);

    return {
      success: true,
      createdClasses: createdCount,
      updatedClasses: updatedCount,
      createdRelations: relCount,
      deletedElements: delCount,
      message: summaryParts.length > 0 ? summaryParts.join(', ') : 'Comando ejecutado en el lienzo.'
    };
  }
}
