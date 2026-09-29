import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FileTreeNode } from '../models/codegen.model';

@Component({
  selector: 'app-file-tree',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="flex flex-col h-full text-xs font-mono text-[var(--text-secondary)] select-none">
      
      <!-- Search & Controls Header -->
      <div class="flex flex-col gap-1.5 pb-2 mb-2 border-b border-[var(--border)] shrink-0">
        <!-- Search Input -->
        <div class="relative flex items-center">
          <span class="absolute left-2 text-[10px] text-slate-400">🔍</span>
          <input 
            type="text" 
            [(ngModel)]="searchQuery" 
            (ngModelChange)="onSearchChange()"
            placeholder="Buscar archivos..." 
            class="w-full bg-[var(--surface-1)] border border-[var(--border)] rounded px-2 py-1 pl-6 text-[11px] text-[var(--text-primary)] placeholder-slate-500 outline-none focus:border-[var(--primary)] transition-colors">
          
          <button 
            *ngIf="searchQuery" 
            (click)="clearSearch()" 
            class="absolute right-1.5 text-[10px] text-slate-400 hover:text-white p-0.5"
            title="Limpiar búsqueda">
            ✕
          </button>
        </div>

        <!-- Quick Toolbar (Expand All, Collapse All, Count) -->
        <div class="flex items-center justify-between text-[10px] text-slate-400 px-1">
          <span>{{ filteredPaths.length }} archivo{{ filteredPaths.length !== 1 ? 's' : '' }}</span>
          
          <div class="flex items-center gap-1.5">
            <button 
              (click)="expandAll()" 
              class="hover:text-white transition-colors px-1 py-0.5 rounded hover:bg-[var(--surface-3)]"
              title="Expandir todas las carpetas">
              📂+ Expandir
            </button>
            <span class="text-slate-600">|</span>
            <button 
              (click)="collapseAll()" 
              class="hover:text-white transition-colors px-1 py-0.5 rounded hover:bg-[var(--surface-3)]"
              title="Colapsar todas las carpetas">
              📁− Colapsar
            </button>
          </div>
        </div>
      </div>

      <!-- File Tree Body (Scrollable) -->
      <div class="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar pr-1">
        <div *ngIf="filteredPaths.length === 0" class="py-6 text-center text-slate-500 italic">
          No se encontraron archivos
        </div>

        <ng-container *ngTemplateOutlet="nodeTemplate; context: { $implicit: rootNodes }"></ng-container>

        <ng-template #nodeTemplate let-nodes>
          <ul class="pl-2 border-l border-slate-800/80 ml-1">
            <li *ngFor="let node of nodes" class="my-0.5">
              
              <!-- Node Row -->
              <div 
                class="flex items-center gap-1.5 px-2 py-1 rounded cursor-pointer transition-all group overflow-hidden"
                [ngClass]="(!node.isDirectory && selectedPath === node.path) 
                  ? 'bg-blue-600/30 text-blue-300 font-semibold border border-blue-500/50 shadow-xs' 
                  : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'"
                [title]="node.path"
                (click)="onNodeClick(node)">
                
                <!-- Expand / Collapse chevron for folders -->
                <span class="text-[9px] w-3.5 text-center text-slate-400 group-hover:text-white shrink-0" *ngIf="node.isDirectory">
                  {{ node.isExpanded ? '▼' : '▶' }}
                </span>
                <span class="w-3.5 shrink-0" *ngIf="!node.isDirectory"></span>
                
                <!-- Icon -->
                <span class="text-xs shrink-0">{{ getNodeIcon(node) }}</span>
                
                <!-- Label -->
                <span 
                  class="truncate text-[11px]" 
                  [class.font-bold]="!node.isDirectory && selectedPath === node.path"
                  [class.text-white]="node.isDirectory || selectedPath === node.path">
                  {{ node.name }}
                </span>

                <!-- Directory children badge -->
                <span *ngIf="node.isDirectory && node.children?.length" class="ml-auto text-[9px] text-slate-500 font-sans group-hover:text-slate-400 shrink-0">
                  {{ node.children?.length }}
                </span>
              </div>

              <!-- Nested Children -->
              <div *ngIf="node.isDirectory && node.isExpanded && node.children?.length">
                <ng-container *ngTemplateOutlet="nodeTemplate; context: { $implicit: node.children }"></ng-container>
              </div>

            </li>
          </ul>
        </ng-template>
      </div>

    </div>
  `
})
export class FileTreeComponent implements OnChanges {
  @Input() paths: string[] = [];
  @Input() selectedPath: string = '';
  @Output() fileSelected = new EventEmitter<string>();

  private cdr = inject(ChangeDetectorRef);

  searchQuery = '';
  filteredPaths: string[] = [];
  rootNodes: FileTreeNode[] = [];

  ngOnChanges(changes: SimpleChanges) {
    if (changes['paths']) {
      this.filterPaths();
    }
    if (changes['selectedPath']) {
      this.cdr.markForCheck();
    }
  }

  onSearchChange() {
    this.filterPaths();
  }

  clearSearch() {
    this.searchQuery = '';
    this.filterPaths();
  }

  expandAll() {
    this.setExpansionState(this.rootNodes, true);
    this.cdr.markForCheck();
  }

  collapseAll() {
    this.setExpansionState(this.rootNodes, false);
    this.cdr.markForCheck();
  }

  private setExpansionState(nodes: FileTreeNode[], expanded: boolean) {
    nodes.forEach(node => {
      if (node.isDirectory) {
        node.isExpanded = expanded;
        if (node.children) {
          this.setExpansionState(node.children, expanded);
        }
      }
    });
  }

  onNodeClick(node: FileTreeNode) {
    if (node.isDirectory) {
      node.isExpanded = !node.isExpanded;
    } else {
      this.selectedPath = node.path;
      this.fileSelected.emit(node.path);
    }
    this.cdr.markForCheck();
  }

  getNodeIcon(node: FileTreeNode): string {
    if (node.isDirectory) {
      return node.isExpanded ? '📂' : '📁';
    }
    const lowerName = node.name.toLowerCase();
    if (lowerName.endsWith('.java')) return '☕';
    if (lowerName.endsWith('.xml')) return '📄';
    if (lowerName.endsWith('.yml') || lowerName.endsWith('.yaml')) return '⚙️';
    if (lowerName.endsWith('.md')) return '📝';
    if (lowerName.endsWith('.json')) return '📦';
    if (lowerName.endsWith('.properties')) return '🔧';
    return '📄';
  }

  private filterPaths() {
    const query = this.searchQuery.trim().toLowerCase();
    if (!query) {
      this.filteredPaths = [...this.paths];
    } else {
      this.filteredPaths = this.paths.filter(p => p.toLowerCase().includes(query));
    }
    this.buildTree();
  }

  private buildTree() {
    const root: FileTreeNode[] = [];

    this.filteredPaths.forEach(path => {
      const parts = path.split('/');
      let currentLevel = root;

      parts.forEach((part, index) => {
        const isLast = index === parts.length - 1;
        const existingPath = parts.slice(0, index + 1).join('/');
        let node = currentLevel.find(n => n.name === part);

        if (!node) {
          node = {
            name: part,
            path: existingPath,
            isDirectory: !isLast,
            isExpanded: true,
            children: isLast ? undefined : []
          };
          currentLevel.push(node);
        }

        if (!isLast && node.children) {
          currentLevel = node.children;
        }
      });
    });

    this.sortNodes(root);
    this.rootNodes = root;
  }

  private sortNodes(nodes: FileTreeNode[]) {
    nodes.sort((a, b) => {
      if (a.isDirectory && !b.isDirectory) return -1;
      if (!a.isDirectory && b.isDirectory) return 1;
      return a.name.localeCompare(b.name);
    });
    nodes.forEach(node => {
      if (node.children) {
        this.sortNodes(node.children);
      }
    });
  }
}

