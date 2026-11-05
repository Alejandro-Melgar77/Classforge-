import { Graph, Node } from '@antv/x6';
import { UMLNodeData, NodeType, UMLAttribute, UMLMethod } from '../models/diagram.model';

let gIsLightMode = false;

export function setUMLNodeTheme(isLight: boolean) {
  gIsLightMode = isLight;
}

/**
 * Format UML 2.5+ attributes according to standard:
 * [visibility] [/] name : type [multiplicity] [= defaultValue]
 */
export function formatAttributesText(attrs?: UMLAttribute[]): string {
  if (!attrs || attrs.length === 0) {
    return '— sin atributos —';
  }
  return attrs.map(a => {
    const vis = a.visibility || '+';
    const isDerived = !!(a.is_derived || (a as any).isDerived);
    const derivedPrefix = isDerived ? '/ ' : '';
    const isStatic = !!(a.is_static || (a as any).isStatic);
    const staticMark = isStatic ? '_' : '';
    const name = a.name || 'attr';
    const type = a.type || 'String';
    const mult = a.multiplicity ? ` [${a.multiplicity}]` : '';
    const defaultVal = a.default_value ? ` = ${a.default_value}` : '';
    return `${vis} ${derivedPrefix}${staticMark}${name}${staticMark} : ${type}${mult}${defaultVal}`;
  }).join('\n');
}

/**
 * Format UML 2.5+ methods according to standard:
 * [visibility] name(param1: type1, ...) : returnType [{abstract}]
 */
export function formatMethodsText(methods?: UMLMethod[]): string {
  if (!methods || methods.length === 0) {
    return '— sin métodos —';
  }
  return methods.map(m => {
    const vis = m.visibility || '+';
    const isStatic = !!(m.is_static || (m as any).isStatic);
    const staticMark = isStatic ? '_' : '';
    const name = m.name || 'metodo';
    const params = m.params ? `(${m.params})` : '()';
    const ret = m.return_type ? `: ${m.return_type}` : ': void';
    const isAbstract = !!(m.is_abstract || (m as any).isAbstract);
    const abs = isAbstract ? ' {abstract}' : '';
    return `${vis} ${staticMark}${name}${staticMark}${params} ${ret}${abs}`;
  }).join('\n');
}

export function calculateNodeHeight(data: UMLNodeData, nodeType: NodeType): number {
  if (nodeType === 'note') return 110;
  if (nodeType === 'package') return 150;

  const hasStereotype = !!(
    data.stereotype ||
    nodeType === 'interface' ||
    nodeType === 'enum' ||
    nodeType === 'abstract' ||
    data.stereotype === 'class'
  );
  const headerH = hasStereotype ? 42 : 32;
  const attrCount = Math.max(1, data.attributes?.length || 1);
  const methodCount = Math.max(1, data.methods?.length || 1);

  const attrH = attrCount * 18 + 12;
  const methodH = methodCount * 18 + 12;

  return Math.max(120, headerH + attrH + methodH + 10);
}

/**
 * Builds standard UML 2.5+ edge labels preventing overlap with node boxes:
 * - Center (0.5): main label
 * - Near source (distance 35, y: -14): source multiplicity
 * - Near target (distance -35, y: -14): target multiplicity
 * - Near source (distance 45, y: 14): source role name
 * - Near target (distance -45, y: 14): target role name
 */
export function buildUmlEdgeLabels(
  label?: string | null,
  sourceMult?: string | null,
  targetMult?: string | null,
  sourceRole?: string | null,
  targetRole?: string | null,
  isLight: boolean = gIsLightMode
): any[] {
  const edgeLabels: any[] = [];

  // 0: Center relationship label
  if (label && label.trim()) {
    edgeLabels.push({
      position: 0.5,
      attrs: {
        label: {
          text: label.trim(),
          fill: isLight ? '#0F172A' : '#F1F5F9',
          fontSize: 11,
          fontFamily: 'Inter, sans-serif',
          fontWeight: '600'
        },
        body: {
          fill: isLight ? '#FFFFFF' : '#1E293B',
          stroke: isLight ? '#CBD5E1' : '#475569',
          strokeWidth: 1,
          rx: 3,
          ry: 3
        }
      }
    });
  }

  // 1: Source Multiplicity (offset top)
  if (sourceMult && sourceMult.trim()) {
    edgeLabels.push({
      position: { distance: 35, offset: { x: 0, y: -14 } },
      attrs: {
        label: {
          text: sourceMult.trim(),
          fill: isLight ? '#0284C7' : '#38BDF8',
          fontSize: 11,
          fontFamily: "'JetBrains Mono', monospace",
          fontWeight: 'bold'
        },
        body: { fill: 'transparent', stroke: 'none' }
      }
    });
  }

  // 2: Target Multiplicity (offset top)
  if (targetMult && targetMult.trim()) {
    edgeLabels.push({
      position: { distance: -35, offset: { x: 0, y: -14 } },
      attrs: {
        label: {
          text: targetMult.trim(),
          fill: isLight ? '#0284C7' : '#38BDF8',
          fontSize: 11,
          fontFamily: "'JetBrains Mono', monospace",
          fontWeight: 'bold'
        },
        body: { fill: 'transparent', stroke: 'none' }
      }
    });
  }

  // 3: Source Role (offset bottom)
  if (sourceRole && sourceRole.trim()) {
    edgeLabels.push({
      position: { distance: 45, offset: { x: 0, y: 14 } },
      attrs: {
        label: {
          text: `+${sourceRole.trim()}`,
          fill: isLight ? '#475569' : '#94A3B8',
          fontSize: 10,
          fontFamily: "'JetBrains Mono', monospace",
          fontStyle: 'italic'
        },
        body: { fill: 'transparent', stroke: 'none' }
      }
    });
  }

  // 4: Target Role (offset bottom)
  if (targetRole && targetRole.trim()) {
    edgeLabels.push({
      position: { distance: -45, offset: { x: 0, y: 14 } },
      attrs: {
        label: {
          text: `+${targetRole.trim()}`,
          fill: isLight ? '#475569' : '#94A3B8',
          fontSize: 10,
          fontFamily: "'JetBrains Mono', monospace",
          fontStyle: 'italic'
        },
        body: { fill: 'transparent', stroke: 'none' }
      }
    });
  }

  return edgeLabels;
}

export function applyUMLNodeAttrs(node: Node, isLight: boolean = gIsLightMode) {
  if (!node || !node.isNode()) return;

  const data = (node.getData() as UMLNodeData) || {
    name: 'Clase',
    stereotype: null,
    is_abstract: false,
    attributes: [],
    methods: [],
    notes: null
  };
  const nodeType = (node.prop('nodeType') || 'class') as NodeType;
  const size = node.size() || { width: 220, height: 140 };
  const nodeWidth = size.width > 0 ? size.width : 220;

  const headerColors: Record<string, { bg: string; text: string; border: string }> = {
    class: { bg: '#2563EB', text: '#FFFFFF', border: isLight ? '#3B82F6' : '#60A5FA' },
    interface: { bg: '#0F766E', text: '#FFFFFF', border: isLight ? '#14B8A6' : '#2DD4BF' },
    abstract: { bg: '#7C3AED', text: '#FFFFFF', border: isLight ? '#8B5CF6' : '#A78BFA' },
    enum: { bg: '#B45309', text: '#FFFFFF', border: isLight ? '#D97706' : '#F59E0B' },
    package: { bg: '#475569', text: '#FFFFFF', border: isLight ? '#64748B' : '#94A3B8' },
    note: { bg: isLight ? '#FEF3C7' : '#334155', text: isLight ? '#78350F' : '#F1F5F9', border: isLight ? '#FDE68A' : '#475569' }
  };

  const currentTheme = headerColors[nodeType] || headerColors['class'];

  const theme = isLight ? {
    bodyFill: '#FFFFFF',
    bodyStroke: '#CBD5E1',
    dividerStroke: '#CBD5E1',
    textDark: '#0F172A',
    textMuted: '#64748B',
    noteBody: '#FFFBEB'
  } : {
    bodyFill: '#1E293B',
    bodyStroke: '#334155',
    dividerStroke: '#334155',
    textDark: '#F1F5F9',
    textMuted: '#94A3B8',
    noteBody: '#1E293B'
  };

  // ═══ UML NOTE ═══
  if (nodeType === 'note') {
    node.setAttrs({
      body: {
        fill: theme.noteBody,
        stroke: currentTheme.border,
        strokeWidth: 1.5,
        rx: 4,
        ry: 4,
      },
      header: {
        fill: currentTheme.bg,
        height: 24,
        rx: 4,
        ry: 4,
      },
      headerText: {
        text: '📝 NOTA',
        fill: isLight ? '#78350F' : '#E2E8F0',
        fontSize: 10,
        fontWeight: 'bold',
        refX: 8,
        refY: 12,
        textVerticalAnchor: 'middle'
      },
      bodyText: {
        text: data.notes || 'Nota / Restricción UML...',
        fill: theme.textDark,
        fontSize: 11,
        fontStyle: 'italic',
        refX: 8,
        refY: 34,
        textWrap: { width: nodeWidth - 16, ellipsis: true }
      }
    });
    return;
  }

  // ═══ UML PACKAGE ═══
  if (nodeType === 'package') {
    node.setAttrs({
      body: {
        fill: theme.bodyFill,
        stroke: currentTheme.border,
        strokeWidth: 1.5,
        rx: 6,
        ry: 6,
      },
      pkgTab: {
        fill: '#475569',
        stroke: '#64748B',
        strokeWidth: 1.5,
        width: 80,
        height: 22,
        rx: 4,
        ry: 4,
        x: 0,
        y: 0,
      },
      pkgTabText: {
        text: 'pkg',
        fill: '#FFFFFF',
        fontSize: 10,
        fontWeight: 'bold',
        x: 40,
        y: 11,
        textAnchor: 'middle',
        textVerticalAnchor: 'middle'
      },
      nameText: {
        text: data.name || 'Paquete',
        fill: theme.textDark,
        fontSize: 13,
        fontWeight: 'bold',
        refX: 0.5,
        refY: 0.5,
        textAnchor: 'middle',
        textVerticalAnchor: 'middle'
      }
    });
    return;
  }

  // ═══ STANDARD UML 2.5+ CLASSIFIER (Class, Interface, Abstract, Enum) ═══
  const isAbstractClass = !!(
    nodeType === 'abstract' ||
    data.is_abstract ||
    (data as any).isAbstract ||
    data.stereotype === 'abstract'
  );

  let stereotypeLabel = '';
  if (nodeType === 'interface' || data.stereotype === 'interface') stereotypeLabel = '«interface»';
  else if (nodeType === 'enum' || data.stereotype === 'enum' || data.stereotype === 'enumeration') stereotypeLabel = '«enumeration»';
  else if (isAbstractClass) stereotypeLabel = '«abstract»';
  else if (data.stereotype === 'class') stereotypeLabel = '«class»';
  else if (data.stereotype) stereotypeLabel = `«${data.stereotype}»`;

  const hasStereotype = !!stereotypeLabel;
  const headerHeight = hasStereotype ? 42 : 32;

  const attrsText = formatAttributesText(data.attributes);
  const attrLineCount = Math.max(1, data.attributes?.length || 1);
  const attrSectionHeight = attrLineCount * 18 + 12;
  const attrDividerY = headerHeight + attrSectionHeight;

  const methodsText = formatMethodsText(data.methods);

  node.setAttrs({
    body: {
      fill: theme.bodyFill,
      stroke: currentTheme.border,
      strokeWidth: 1.5,
      rx: 6,
      ry: 6,
    },
    header: {
      fill: currentTheme.bg,
      height: headerHeight,
      rx: 6,
      ry: 6,
    },
    stereotypeText: {
      text: stereotypeLabel,
      fill: 'rgba(255, 255, 255, 0.88)',
      fontSize: 9,
      fontWeight: '600',
      fontFamily: 'Inter, sans-serif',
      refX: 0.5,
      refY: 11,
      textAnchor: 'middle',
      textVerticalAnchor: 'middle',
      display: hasStereotype ? 'block' : 'none'
    },
    nameText: {
      text: data.name || 'NombreClase',
      fill: '#FFFFFF',
      fontSize: 12,
      fontWeight: 'bold',
      fontStyle: isAbstractClass ? 'italic' : 'normal',
      fontFamily: 'Inter, sans-serif',
      refX: 0.5,
      refY: hasStereotype ? 27 : 16,
      textAnchor: 'middle',
      textVerticalAnchor: 'middle'
    },
    headerLine: {
      d: `M 0 ${headerHeight} L ${nodeWidth} ${headerHeight}`,
      stroke: theme.dividerStroke,
      strokeWidth: 1.5
    },
    attrsText: {
      text: attrsText,
      fill: data.attributes && data.attributes.length > 0 ? theme.textDark : theme.textMuted,
      fontSize: 11,
      fontFamily: "'JetBrains Mono', Consolas, monospace",
      lineHeight: 18,
      textAnchor: 'start',
      refX: 10,
      refY: headerHeight + 6,
      textVerticalAnchor: 'top'
    },
    addAttrBtnBg: {
      x: nodeWidth - 24,
      y: headerHeight + 4,
      width: 18,
      height: 16,
      rx: 3,
      ry: 3,
      fill: isLight ? '#EFF6FF' : '#1E293B',
      stroke: isLight ? '#93C5FD' : '#3B82F6',
      strokeWidth: 1,
      cursor: 'pointer'
    },
    addAttrBtnText: {
      text: '+',
      x: nodeWidth - 15,
      y: headerHeight + 12,
      fill: isLight ? '#2563EB' : '#60A5FA',
      fontSize: 13,
      fontWeight: 'bold',
      fontFamily: 'Inter, sans-serif',
      textAnchor: 'middle',
      textVerticalAnchor: 'middle',
      cursor: 'pointer'
    },
    attrLine: {
      d: `M 0 ${attrDividerY} L ${nodeWidth} ${attrDividerY}`,
      stroke: theme.dividerStroke,
      strokeWidth: 1.5
    },
    methodsText: {
      text: methodsText,
      fill: data.methods && data.methods.length > 0 ? theme.textDark : theme.textMuted,
      fontSize: 11,
      fontFamily: "'JetBrains Mono', Consolas, monospace",
      lineHeight: 18,
      textAnchor: 'start',
      refX: 10,
      refY: attrDividerY + 6,
      textVerticalAnchor: 'top'
    },
    addMethodBtnBg: {
      x: nodeWidth - 24,
      y: attrDividerY + 4,
      width: 18,
      height: 16,
      rx: 3,
      ry: 3,
      fill: isLight ? '#EFF6FF' : '#1E293B',
      stroke: isLight ? '#93C5FD' : '#3B82F6',
      strokeWidth: 1,
      cursor: 'pointer'
    },
    addMethodBtnText: {
      text: '+',
      x: nodeWidth - 15,
      y: attrDividerY + 12,
      fill: isLight ? '#2563EB' : '#60A5FA',
      fontSize: 13,
      fontWeight: 'bold',
      fontFamily: 'Inter, sans-serif',
      textAnchor: 'middle',
      textVerticalAnchor: 'middle',
      cursor: 'pointer'
    }
  });
}

export function registerUMLNodesAndEdges() {
  // ═══ 1. UML CLASS / INTERFACE / ABSTRACT / ENUM ═══
  const standardTypes = ['uml-class', 'uml-interface', 'uml-abstract', 'uml-enum'];

  standardTypes.forEach(type => {
    Graph.registerNode(
      type,
      {
        inherit: 'rect',
        width: 220,
        height: 140,
        markup: [
          { tagName: 'rect', selector: 'body' },
          { tagName: 'rect', selector: 'header' },
          { tagName: 'text', selector: 'stereotypeText' },
          { tagName: 'text', selector: 'nameText' },
          { tagName: 'path', selector: 'headerLine' },
          { tagName: 'text', selector: 'attrsText' },
          { tagName: 'rect', selector: 'addAttrBtnBg' },
          { tagName: 'text', selector: 'addAttrBtnText' },
          { tagName: 'path', selector: 'attrLine' },
          { tagName: 'text', selector: 'methodsText' },
          { tagName: 'rect', selector: 'addMethodBtnBg' },
          { tagName: 'text', selector: 'addMethodBtnText' }
        ],
        attrs: {
          body: {
            refWidth: '100%',
            refHeight: '100%',
            fill: '#1E293B',
            stroke: '#3B82F6',
            strokeWidth: 1.5,
            rx: 6,
            ry: 6,
          },
          header: {
            refWidth: '100%',
            height: 32,
            fill: '#2563EB',
            rx: 6,
            ry: 6,
          }
        }
      },
      true
    );
  });

  // ═══ 2. UML PACKAGE ═══
  Graph.registerNode(
    'uml-package',
    {
      inherit: 'rect',
      width: 260,
      height: 160,
      markup: [
        { tagName: 'rect', selector: 'body' },
        { tagName: 'rect', selector: 'pkgTab' },
        { tagName: 'text', selector: 'pkgTabText' },
        { tagName: 'text', selector: 'nameText' }
      ],
      attrs: {
        body: {
          refWidth: '100%',
          refHeight: '100%',
          fill: '#1E293B',
          stroke: '#64748B',
          strokeWidth: 1.5,
          rx: 6,
          ry: 6,
        }
      }
    },
    true
  );

  // ═══ 3. UML NOTE ═══
  Graph.registerNode(
    'uml-note',
    {
      inherit: 'rect',
      width: 200,
      height: 100,
      markup: [
        { tagName: 'rect', selector: 'body' },
        { tagName: 'rect', selector: 'header' },
        { tagName: 'text', selector: 'headerText' },
        { tagName: 'text', selector: 'bodyText' }
      ],
      attrs: {
        body: {
          refWidth: '100%',
          refHeight: '100%',
          fill: '#1E293B',
          stroke: '#475569',
          strokeWidth: 1.5,
          rx: 4,
          ry: 4,
        }
      }
    },
    true
  );

  const defaultLabel = {
    markup: [
      { tagName: 'rect', selector: 'body' },
      { tagName: 'text', selector: 'label' },
    ],
    attrs: {
      label: { fill: '#94A3B8', fontSize: 11, textAnchor: 'middle', yAlignment: 'middle', pointerEvents: 'none' },
      body: { ref: 'label', fill: '#1E293B', stroke: '#334155', strokeWidth: 1, rx: 3, ry: 3, refWidth: '100%', refHeight: '100%', refX: 0, refY: 0 }
    },
  };

  // ═══ REGISTER STRICT UML 2.5+ RELATIONSHIPS & EDGES ═══

  // 1. Generalization / Inheritance (Solid line, hollow closed triangle pointing to superclass at target)
  Graph.registerEdge('uml-inheritance', {
    inherit: 'edge',
    defaultLabel,
    attrs: {
      line: {
        stroke: '#64748B',
        strokeWidth: 1.5,
        sourceMarker: null,
        targetMarker: {
          name: 'path',
          d: 'M 0 -8 L 15 0 L 0 8 Z',
          fill: '#FFFFFF',
          stroke: '#64748B',
          strokeWidth: 1.5
        }
      }
    }
  }, true);

  // 2. Realization / Interface Implementation (Dashed line, hollow closed triangle at target)
  Graph.registerEdge('uml-realization', {
    inherit: 'edge',
    defaultLabel,
    attrs: {
      line: {
        stroke: '#64748B',
        strokeWidth: 1.5,
        strokeDasharray: '6,4',
        sourceMarker: null,
        targetMarker: {
          name: 'path',
          d: 'M 0 -8 L 15 0 L 0 8 Z',
          fill: '#FFFFFF',
          stroke: '#64748B',
          strokeWidth: 1.5
        }
      }
    }
  }, true);

  // 3. Composition (Solid line, filled diamond at container source, NO arrow at target)
  Graph.registerEdge('uml-composition', {
    inherit: 'edge',
    defaultLabel,
    attrs: {
      line: {
        stroke: '#64748B',
        strokeWidth: 1.5,
        sourceMarker: {
          name: 'path',
          d: 'M 0 0 L 9 -6 L 18 0 L 9 6 Z',
          fill: '#0284C7',
          stroke: '#0284C7',
          strokeWidth: 1.5
        },
        targetMarker: null
      }
    }
  }, true);

  // 4. Aggregation (Solid line, hollow diamond at container source, NO arrow at target)
  Graph.registerEdge('uml-aggregation', {
    inherit: 'edge',
    defaultLabel,
    attrs: {
      line: {
        stroke: '#64748B',
        strokeWidth: 1.5,
        sourceMarker: {
          name: 'path',
          d: 'M 0 0 L 9 -6 L 18 0 L 9 6 Z',
          fill: '#FFFFFF',
          stroke: '#0284C7',
          strokeWidth: 1.5
        },
        targetMarker: null
      }
    }
  }, true);

  // 5. Association (Solid line, open arrowhead at target for navigability)
  Graph.registerEdge('uml-association', {
    inherit: 'edge',
    defaultLabel,
    attrs: {
      line: {
        stroke: '#64748B',
        strokeWidth: 1.5,
        sourceMarker: null,
        targetMarker: {
          name: 'classic',
          size: 10,
          fill: 'none',
          stroke: '#64748B',
          strokeWidth: 1.5
        }
      }
    }
  }, true);

  // 6. Dependency (Dashed line, open arrowhead pointing to provider at target)
  Graph.registerEdge('uml-dependency', {
    inherit: 'edge',
    defaultLabel,
    attrs: {
      line: {
        stroke: '#64748B',
        strokeWidth: 1.5,
        strokeDasharray: '6,4',
        sourceMarker: null,
        targetMarker: {
          name: 'classic',
          size: 10,
          fill: 'none',
          stroke: '#64748B',
          strokeWidth: 1.5
        }
      }
    }
  }, true);
}
