import { Injectable } from '@angular/core';
import { UMLCommandResponse, UMLClassCommand, UMLRelationCommand, UMLAttribute, UMLMethod } from '../models/ai-command.model';

@Injectable({
  providedIn: 'root'
})
export class NluParserService {

  public parse(input: string): UMLCommandResponse {
    if (!input || !input.trim()) {
      return this.emptyResponse('Consulta vacía.');
    }

    const raw = input.trim();
    const normalized = this.normalize(raw);

    // 1. Complex create table/class query with attributes and relation + cardinality
    // Example: "crea una tabla con el nombre Producto con 3 atributos de nombres precio, stock, codigo y que se asocie a Categoria con la cardinalidad 1..*"
    const complexRes = this.matchComplexCreate(raw, normalized);
    if (complexRes) return complexRes;

    // 2. Simple Create Class / Table / Entity / Interface / Enum / Abstract
    const createRes = this.matchCreateElement(raw, normalized);
    if (createRes) return createRes;

    // 3. Add Attribute to Class
    const addAttrRes = this.matchAddAttribute(raw, normalized);
    if (addAttrRes) return addAttrRes;

    // 4. Add Method to Class
    const addMethodRes = this.matchAddMethod(raw, normalized);
    if (addMethodRes) return addMethodRes;

    // 5. Create Relation between two classes with optional cardinality and type
    const relationRes = this.matchRelation(raw, normalized);
    if (relationRes) return relationRes;

    // 6. Delete Element
    const deleteRes = this.matchDelete(raw, normalized);
    if (deleteRes) return deleteRes;

    // 7. Domain / System generation templates (e.g. "tienda", "biblioteca", "hospital", etc.)
    const systemRes = this.matchDomainSystem(raw, normalized);
    if (systemRes) return systemRes;

    // 8. General Entity Extractor Fallback (Offline fallback)
    return this.fallbackEntityExtractor(raw, normalized);
  }

  /**
   * Complex table/class creator with attributes and inline association with cardinality.
   * e.g. "crea una tabla con el nombre Producto con 3 atributos de nombres precio, stock, codigo y que se asocie a Categoria con la cardinalidad 1..*"
   */
  private matchComplexCreate(raw: string, norm: string): UMLCommandResponse | null {
    const regex = /(?:crea(?:r)?|nueva?|generar?)\s+(?:una?\s+)?(?:tabla|clase|entidad|modelo)\s+(?:con\s+el\s+nombre\s+|llamada\s+|de\s+nombre\s+)?([a-zA-Z0-9_]+)(?:\s+con\s+(?:(?:\d+|varios|los)\s+)?atributos(?:\s+(?:de\s+nombres?|llamados?|:))?\s+([^]+?))?(?:\s+(?:y\s+)?(?:que\s+)?(?:se\s+)?(?:asocie|relacione|conecte|vincule)\s+(?:a|con)\s+([a-zA-Z0-9_]+)(?:\s+con\s+(?:la\s+)?cardinalidad\s+([^\s,;]+(?:\s+(?:a|..)\s+[^\s,;]+)?))?)?$/i;

    const match = norm.match(regex);
    if (!match) return null;

    const className = this.capitalize(match[1]);
    const attrsStr = match[2];
    const targetClass = match[3] ? this.capitalize(match[3]) : null;
    const cardinalityStr = match[4];

    const attributes: UMLAttribute[] = this.parseAttributeList(attrsStr);
    const classes: UMLClassCommand[] = [{
      name: className,
      attributes: attributes.length > 0 ? attributes : [{ name: 'id', type: 'Long', visibility: '+' }],
      methods: []
    }];

    const relations: UMLRelationCommand[] = [];
    if (targetClass) {
      const { sourceMult, targetMult } = this.parseCardinality(cardinalityStr || '1..*');
      relations.push({
        source: className,
        target: targetClass,
        type: 'association',
        sourceMultiplicity: sourceMult,
        targetMultiplicity: targetMult,
        label: ''
      });

      classes.push({
        name: targetClass,
        attributes: [{ name: 'id', type: 'Long', visibility: '+' }],
        methods: []
      });
    }

    let explanation = `Tabla/Clase '${className}' creada con ${classes[0].attributes.length} atributos`;
    if (targetClass) {
      explanation += ` y asociada a '${targetClass}' con cardinalidad ${cardinalityStr || '1..*'}.`;
    } else {
      explanation += '.';
    }

    return {
      action: 'create_class',
      classes,
      relations,
      deleted_elements: [],
      explanation,
      source: 'offline_nlu'
    };
  }

  private matchCreateElement(raw: string, norm: string): UMLCommandResponse | null {
    let stereotype: string | undefined = undefined;
    if (norm.includes('clase abstracta') || norm.includes('abstract class')) {
      stereotype = 'abstract';
    } else if (norm.includes('interfaz') || norm.includes('interface')) {
      stereotype = 'interface';
    } else if (norm.includes('enum') || norm.includes('enumeracion') || norm.includes('enumerado')) {
      stereotype = 'enum';
    }

    const regex = /(?:crear?|nueva?|generar?|agregar?)\s+(?:una?\s+)?(?:clase\s+abstracta|interfaz|interface|enum(?:eracion)?|tabla|clase|entidad|modelo)\s+(?:con\s+el\s+nombre\s+|llamada\s+|de\s+nombre\s+)?([a-zA-Z0-9_]+)(?:\s+(?:con\s+(?:los\s+)?(?:atributos|campos|valores))\s+(.+))?/i;
    const match = norm.match(regex);
    if (!match) return null;

    const className = this.capitalize(match[1]);
    const rawAttrs = match[2];
    const attributes = this.parseAttributeList(rawAttrs);

    return {
      action: 'create_class',
      classes: [{
        name: className,
        stereotype,
        attributes: attributes.length > 0 ? attributes : [{ name: 'id', type: 'Long', visibility: '+' }],
        methods: []
      }],
      relations: [],
      deleted_elements: [],
      explanation: `${stereotype ? this.capitalize(stereotype) : 'Clase'} '${className}' creada correctamente.`,
      source: 'offline_nlu'
    };
  }

  private matchAddAttribute(raw: string, norm: string): UMLCommandResponse | null {
    const regex = /(?:agregar?|anadir?|incorporar?|crear?)\s+(?:el\s+)?(?:atributo|campo)\s+([a-zA-Z0-9_]+)(?:\s*:?\s*([a-zA-Z0-9_]+))?\s+(?:a|en)\s+(?:la\s+)?(?:clase|tabla|entidad)?\s*([a-zA-Z0-9_]+)/i;
    const match = norm.match(regex);
    if (!match) return null;

    const attrName = match[1];
    const explicitType = match[2];
    const className = this.capitalize(match[3]);
    const attrType = explicitType ? this.normalizeType(explicitType) : this.inferTypeFromName(attrName);

    return {
      action: 'add_attribute',
      classes: [{
        name: className,
        attributes: [{ name: attrName, type: attrType, visibility: '+' }],
        methods: []
      }],
      relations: [],
      deleted_elements: [],
      explanation: `Atributo '${attrName}: ${attrType}' agregado a '${className}'.`,
      source: 'offline_nlu'
    };
  }

  private matchAddMethod(raw: string, norm: string): UMLCommandResponse | null {
    const regex = /(?:agregar?|anadir?|crear?)\s+(?:el\s+)?metodo\s+([a-zA-Z0-9_]+)(?:\s*\(([^)]*)\))?(?:\s*:?\s*([a-zA-Z0-9_]+))?\s+(?:a|en)\s+(?:la\s+)?(?:clase|tabla|entidad)?\s*([a-zA-Z0-9_]+)/i;
    const match = norm.match(regex);
    if (!match) return null;

    const methodName = match[1];
    const params = match[2] || '';
    const returnType = match[3] ? this.normalizeType(match[3]) : 'void';
    const className = this.capitalize(match[4]);

    return {
      action: 'add_method',
      classes: [{
        name: className,
        attributes: [],
        methods: [{ name: methodName, params, return_type: returnType, visibility: '+' }]
      }],
      relations: [],
      deleted_elements: [],
      explanation: `Método '${methodName}(${params}): ${returnType}' agregado a '${className}'.`,
      source: 'offline_nlu'
    };
  }

  private matchRelation(raw: string, norm: string): UMLCommandResponse | null {
    const inheritRegex = /(?:hacer\s+que\s+)?([a-zA-Z0-9_]+)\s+(?:hereda|herede|extiende|extienda)\s+de\s+([a-zA-Z0-9_]+)/i;
    const inheritMatch = norm.match(inheritRegex);
    if (inheritMatch) {
      const source = this.capitalize(inheritMatch[1]);
      const target = this.capitalize(inheritMatch[2]);
      return {
        action: 'create_relation',
        classes: [],
        relations: [{
          source,
          target,
          type: 'inheritance',
          label: ''
        }],
        deleted_elements: [],
        explanation: `Herencia: '${source}' hereda de '${target}'.`,
        source: 'offline_nlu'
      };
    }

    const relRegex = /(?:crear?\s+(?:relacion|asociacion|composicion|agregacion|dependencia|herencia)\s+(?:entre|de)\s+|relacionar?\s+|asociar?\s+|conectar?\s+)([a-zA-Z0-9_]+)\s+(?:con|y|a)\s+([a-zA-Z0-9_]+)(?:\s+(?:como|por|tipo)?\s*(herencia|composicion|agregacion|dependencia|asociacion|realizacion))?(?:\s+(?:con\s+(?:la\s+)?cardinalidad\s+)?([0-9*..a-zA-Z_]+(?:\s+(?:a|..)\s+[0-9*..a-zA-Z_]+)?))?/i;
    const match = norm.match(relRegex);
    if (!match) return null;

    const source = this.capitalize(match[1]);
    const target = this.capitalize(match[2]);
    const rawType = match[3];
    const rawCard = match[4];

    const type = this.normalizeRelationType(rawType || (norm.includes('composicion') ? 'composition' : norm.includes('agregacion') ? 'aggregation' : norm.includes('herencia') ? 'inheritance' : norm.includes('dependencia') ? 'dependency' : 'association'));
    const { sourceMult, targetMult } = this.parseCardinality(rawCard);

    return {
      action: 'create_relation',
      classes: [],
      relations: [{
        source,
        target,
        type,
        sourceMultiplicity: sourceMult,
        targetMultiplicity: targetMult,
        label: ''
      }],
      deleted_elements: [],
      explanation: `Relación '${type}' creada entre '${source}' y '${target}'${sourceMult || targetMult ? ` (${sourceMult || '1'} ── ${targetMult || '*'})` : ''}.`,
      source: 'offline_nlu'
    };
  }

  private matchDelete(raw: string, norm: string): UMLCommandResponse | null {
    const regex = /(?:eliminar?|borrar?|quitar?)\s+(?:la\s+)?(?:clase|tabla|entidad|elemento)\s+([a-zA-Z0-9_]+)/i;
    const match = norm.match(regex);
    if (!match) return null;

    const name = this.capitalize(match[1]);
    return {
      action: 'delete_element',
      classes: [],
      relations: [],
      deleted_elements: [name],
      explanation: `Elemento '${name}' eliminado.`,
      source: 'offline_nlu'
    };
  }

  private matchDomainSystem(raw: string, norm: string): UMLCommandResponse | null {
    if (norm.includes('tienda') || norm.includes('e-commerce') || norm.includes('comercio') || norm.includes('ventas')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Usuario',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'email', type: 'String', visibility: '+' },
              { name: 'password', type: 'String', visibility: '-' }
            ],
            methods: [{ name: 'autenticar', params: 'pass: String', return_type: 'Boolean', visibility: '+' }]
          },
          {
            name: 'Cliente',
            attributes: [
              { name: 'direccion', type: 'String', visibility: '+' },
              { name: 'telefono', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Producto',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'precio', type: 'Double', visibility: '+' },
              { name: 'stock', type: 'Integer', visibility: '+' }
            ],
            methods: [{ name: 'actualizarStock', params: 'cant: int', return_type: 'void', visibility: '+' }]
          },
          {
            name: 'Categoria',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'descripcion', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Pedido',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'fecha', type: 'Date', visibility: '+' },
              { name: 'total', type: 'Double', visibility: '+' },
              { name: 'estado', type: 'String', visibility: '+' }
            ],
            methods: [{ name: 'calcularTotal', params: '', return_type: 'Double', visibility: '+' }]
          },
          {
            name: 'DetallePedido',
            attributes: [
              { name: 'cantidad', type: 'Integer', visibility: '+' },
              { name: 'precioUnitario', type: 'Double', visibility: '+' },
              { name: 'subtotal', type: 'Double', visibility: '+' }
            ],
            methods: []
          }
        ],
        relations: [
          { source: 'Cliente', target: 'Usuario', type: 'inheritance', label: '' },
          { source: 'Cliente', target: 'Pedido', type: 'association', sourceMultiplicity: '1', targetMultiplicity: '0..*', label: 'realiza' },
          { source: 'Pedido', target: 'DetallePedido', type: 'composition', sourceMultiplicity: '1', targetMultiplicity: '1..*', label: 'contiene' },
          { source: 'DetallePedido', target: 'Producto', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'referencia' },
          { source: 'Producto', target: 'Categoria', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'clasificado en' }
        ],
        deleted_elements: [],
        explanation: 'Sistema E-Commerce completo generado (Usuario, Cliente, Producto, Categoria, Pedido, DetallePedido) con relaciones y cardinalidades.',
        source: 'offline_nlu'
      };
    }

    if (norm.includes('biblioteca') || norm.includes('prestamo') || norm.includes('libro')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Libro',
            attributes: [
              { name: 'isbn', type: 'String', visibility: '+' },
              { name: 'titulo', type: 'String', visibility: '+' },
              { name: 'anioPublicacion', type: 'Integer', visibility: '+' },
              { name: 'disponible', type: 'Boolean', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Autor',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'nacionalidad', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Lector',
            attributes: [
              { name: 'nroCarnet', type: 'String', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'email', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Prestamo',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'fechaPrestamo', type: 'Date', visibility: '+' },
              { name: 'fechaDevolucion', type: 'Date', visibility: '+' }
            ],
            methods: [{ name: 'registrarDevolucion', params: '', return_type: 'void', visibility: '+' }]
          }
        ],
        relations: [
          { source: 'Libro', target: 'Autor', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1..*', label: 'escrito por' },
          { source: 'Prestamo', target: 'Lector', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'solicitado por' },
          { source: 'Prestamo', target: 'Libro', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1..*', label: 'incluye' }
        ],
        deleted_elements: [],
        explanation: 'Sistema de Biblioteca generado (Libro, Autor, Lector, Prestamo) con relaciones y cardinalidades.',
        source: 'offline_nlu'
      };
    }

    if (norm.includes('hospital') || norm.includes('clinica') || norm.includes('medico') || norm.includes('paciente')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Persona',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'dni', type: 'String', visibility: '+' },
              { name: 'telefono', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Paciente',
            attributes: [
              { name: 'nroHistoriaClinica', type: 'String', visibility: '+' },
              { name: 'grupoSanguineo', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Medico',
            attributes: [
              { name: 'matricula', type: 'String', visibility: '+' },
              { name: 'especialidad', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'CitaMedica',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'fechaHora', type: 'Date', visibility: '+' },
              { name: 'motivo', type: 'String', visibility: '+' },
              { name: 'estado', type: 'String', visibility: '+' }
            ],
            methods: []
          }
        ],
        relations: [
          { source: 'Paciente', target: 'Persona', type: 'inheritance', label: '' },
          { source: 'Medico', target: 'Persona', type: 'inheritance', label: '' },
          { source: 'CitaMedica', target: 'Paciente', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'asiste' },
          { source: 'CitaMedica', target: 'Medico', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'atiende' }
        ],
        deleted_elements: [],
        explanation: 'Sistema Hospitalario generado (Persona, Paciente, Medico, CitaMedica) con herencia y asociaciones.',
        source: 'offline_nlu'
      };
    }

    return null;
  }

  private fallbackEntityExtractor(raw: string, norm: string): UMLCommandResponse {
    const words = raw.match(/[a-zA-ZáéíóúÁÉÍÓÚñÑ]{3,}/g) || [];
    const stopWords = new Set([
      'para', 'como', 'este', 'esta', 'estos', 'estas', 'sistema', 'aplicacion', 'quiero', 'necesito',
      'crear', 'crea', 'un', 'una', 'unos', 'unas', 'el', 'la', 'los', 'las', 'con', 'por', 'que',
      'del', 'al', 'tabla', 'clase', 'entidad', 'modelo', 'atributos', 'atributo', 'nombre', 'nombres',
      'llamada', 'llamado', 'llamados', 'tanto', 'tipo', 'cardinalidad', 'asocie', 'asociar', 'relacionar'
    ]);

    const candidates = words
      .map(w => this.capitalize(w))
      .filter(w => !stopWords.has(w.toLowerCase()));

    const uniqueEntities = Array.from(new Set(candidates)).slice(0, 4);

    if (uniqueEntities.length === 0) {
      return {
        action: 'create_class',
        classes: [{
          name: 'NuevaClase',
          attributes: [
            { name: 'id', type: 'Long', visibility: '+' },
            { name: 'nombre', type: 'String', visibility: '+' }
          ],
          methods: []
        }],
        relations: [],
        deleted_elements: [],
        explanation: 'Se ha creado una clase base.',
        source: 'offline_nlu'
      };
    }

    const classes: UMLClassCommand[] = uniqueEntities.map((ent) => ({
      name: ent,
      attributes: [
        { name: 'id', type: 'Long', visibility: '+' },
        { name: 'nombre', type: 'String', visibility: '+' },
        { name: 'descripcion', type: 'String', visibility: '+' }
      ],
      methods: []
    }));

    const relations: UMLRelationCommand[] = [];
    if (classes.length > 1) {
      for (let i = 0; i < classes.length - 1; i++) {
        relations.push({
          source: classes[i].name,
          target: classes[i + 1].name,
          type: 'association',
          sourceMultiplicity: '1',
          targetMultiplicity: '0..*',
          label: ''
        });
      }
    }

    return {
      action: 'generate_system',
      classes,
      relations,
      deleted_elements: [],
      explanation: `Entidades generadas offline: ${uniqueEntities.join(', ')}.`,
      source: 'offline_nlu'
    };
  }

  public parseAttributeList(raw: string | undefined): UMLAttribute[] {
    if (!raw) return [];
    let clean = raw.replace(/^(?:llamados?|de\s+nombres?|:)\s*/i, '').trim();
    const tokens = clean.split(/[,;\n]|\s+y\s+|\s+e\s+/i).map(s => s.trim()).filter(Boolean);

    const attributes: UMLAttribute[] = [];

    for (const token of tokens) {
      let name = '';
      let type = 'String';
      let visibility = '+';

      if (token.startsWith('+') || token.startsWith('-') || token.startsWith('#')) {
        visibility = token.charAt(0);
      }

      const stripped = token.replace(/^[+\-#]\s*/, '');

      if (stripped.includes(':')) {
        const parts = stripped.split(':').map(p => p.trim());
        name = parts[0];
        type = this.normalizeType(parts[1] || 'String');
      } else {
        const words = stripped.split(/\s+/);
        if (words.length >= 2) {
          name = words[0];
          type = this.normalizeType(words[1]);
        } else if (words.length === 1) {
          name = words[0];
          type = this.inferTypeFromName(name);
        }
      }

      name = name.replace(/[^a-zA-Z0-9_]/g, '');
      if (name) {
        attributes.push({ name, type, visibility });
      }
    }

    return attributes;
  }

  public parseCardinality(raw: string | undefined): { sourceMult: string; targetMult: string } {
    if (!raw) return { sourceMult: '1', targetMult: '1..*' };

    const norm = raw.trim().toLowerCase();

    if (norm.includes('uno a muchos') || norm.includes('1 a muchos') || norm.includes('1 a *') || norm.includes('1 a n')) {
      return { sourceMult: '1', targetMult: '1..*' };
    }
    if (norm.includes('cero a muchos') || norm.includes('0 a muchos') || norm.includes('0 a *')) {
      return { sourceMult: '1', targetMult: '0..*' };
    }
    if (norm.includes('muchos a uno') || norm.includes('* a 1') || norm.includes('muchos a 1')) {
      return { sourceMult: '0..*', targetMult: '1' };
    }
    if (norm.includes('muchos a muchos') || norm.includes('* a *') || norm.includes('n a m')) {
      return { sourceMult: '0..*', targetMult: '0..*' };
    }
    if (norm.includes('uno a uno') || norm.includes('1 a 1')) {
      return { sourceMult: '1', targetMult: '1' };
    }

    if (norm.includes('..')) {
      const parts = norm.split('..').map(p => p.trim());
      if (parts.length === 2) {
        const src = parts[0].toUpperCase();
        const tgt = parts[1].toUpperCase();
        return { sourceMult: src, targetMult: `${src}..${tgt}` };
      }
    }

    if (norm.includes(' a ')) {
      const parts = norm.split(' a ').map(p => p.trim());
      return {
        sourceMult: parts[0] || '1',
        targetMult: parts[1] || '1..*'
      };
    }

    return { sourceMult: '1', targetMult: raw.trim() };
  }

  public normalizeRelationType(type: string): string {
    const t = (type || '').toLowerCase();
    if (t.includes('herencia') || t.includes('inherit') || t.includes('generalizacion')) return 'inheritance';
    if (t.includes('composicion') || t.includes('composición') || t.includes('composition')) return 'composition';
    if (t.includes('agregacion') || t.includes('agregación') || t.includes('aggregation')) return 'aggregation';
    if (t.includes('dependencia') || t.includes('dependency')) return 'dependency';
    if (t.includes('realizacion') || t.includes('realización') || t.includes('realization')) return 'realization';
    return 'association';
  }

  public inferTypeFromName(name: string): string {
    const n = name.toLowerCase();
    if (n === 'id' || n.endsWith('id')) return 'Long';
    if (n.includes('precio') || n.includes('total') || n.includes('monto') || n.includes('saldo') || n.includes('costo') || n.includes('descuento') || n.includes('subtotal') || n.includes('sueldo')) return 'Double';
    if (n.includes('stock') || n.includes('cantidad') || n.includes('edad') || n.includes('numero') || n.includes('nro') || n.includes('orden') || n.includes('anio') || n.includes('puntos') || n.includes('intentos')) return 'Integer';
    if (n.includes('fecha') || n.includes('created') || n.includes('updated') || n.includes('date') || n.includes('nacimiento')) return 'Date';
    if (n.startsWith('es') || n.startsWith('is') || n.includes('activo') || n.includes('habilitado') || n.includes('bloqueado') || n.includes('valido')) return 'Boolean';
    return 'String';
  }

  public normalizeType(type: string): string {
    const t = (type || '').toLowerCase().trim();
    if (t === 'int' || t === 'integer' || t === 'entero') return 'Integer';
    if (t === 'long' || t === 'bigint') return 'Long';
    if (t === 'float' || t === 'flotante') return 'Float';
    if (t === 'double' || t === 'decimal' || t === 'number') return 'Double';
    if (t === 'bool' || t === 'boolean' || t === 'booleano') return 'Boolean';
    if (t === 'date' || t === 'datetime' || t === 'fecha' || t === 'timestamp') return 'Date';
    if (t === 'void' || t === 'vacio') return 'void';
    return 'String';
  }

  public normalize(str: string): string {
    return (str || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  public capitalize(str: string): string {
    if (!str) return '';
    const clean = str.replace(/[^a-zA-Z0-9_]/g, '');
    if (!clean) return 'Clase';
    return clean.charAt(0).toUpperCase() + clean.slice(1);
  }

  private emptyResponse(message: string): UMLCommandResponse {
    return {
      action: 'unknown',
      classes: [],
      relations: [],
      deleted_elements: [],
      explanation: message,
      source: 'offline_nlu'
    };
  }
}
