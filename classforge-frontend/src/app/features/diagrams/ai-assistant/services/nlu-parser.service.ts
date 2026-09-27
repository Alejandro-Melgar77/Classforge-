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
    const complexRes = this.matchComplexCreate(raw, normalized);
    if (complexRes) return complexRes;

    // 2. Multi-class creation with possible inline definitions: "crear clases Factura(total, fecha) y Cliente(nombre, nit)" or "crear clases Usuario, Rol, Permiso"
    const multiClassRes = this.matchMultiClassCreate(raw, normalized);
    if (multiClassRes) return multiClassRes;

    // 3. Add Attribute(s) to Class
    const addAttrRes = this.matchAddAttribute(raw, normalized);
    if (addAttrRes) return addAttrRes;

    // 4. Add Method to Class
    const addMethodRes = this.matchAddMethod(raw, normalized);
    if (addMethodRes) return addMethodRes;

    // 5. Create Relation between two classes with optional cardinality and type
    const relationRes = this.matchRelation(raw, normalized);
    if (relationRes) return relationRes;

    // 6. Delete Element / Class
    const deleteRes = this.matchDelete(raw, normalized);
    if (deleteRes) return deleteRes;

    // 7. Single Create Class / Table / Entity / Interface / Enum / Abstract
    const createRes = this.matchCreateElement(raw, normalized);
    if (createRes) return createRes;

    // 8. Domain / System generation templates (e-commerce, facturación, banco, hospital, delivery, inventario, etc.)
    const systemRes = this.matchDomainSystem(raw, normalized);
    if (systemRes) return systemRes;

    // 9. Universal Entity Extractor Fallback (Guarantees offline reliability)
    return this.fallbackEntityExtractor(raw, normalized);
  }

  /**
   * Complex table/class creator with attributes and inline association with cardinality.
   * e.g. "crea una tabla con el nombre Producto con 3 atributos de nombres precio, stock, codigo y que se asocie a Categoria con la cardinalidad 1..*"
   * e.g. "crear tabla Producto con precio, stock, codigo y asociar a Categoria 1..*"
   * e.g. "tabla Venta con total, fecha y que se conecte a Empleado 1..*"
   */
  private matchComplexCreate(raw: string, norm: string): UMLCommandResponse | null {
    const regexA = /(?:(?:crea(?:r|me)?|genera(?:r|me)?|haz(?:me)?|constru(?:ir|ye)?|disena(?:r)?|agrega(?:r|me)?|pon(?:er|me)?)\s+)?(?:una?\s+)?(?:tabla|clase|entidad|modelo)\s+(?:con\s+el\s+nombre\s+|llamada\s+|de\s+nombre\s+)?([a-zA-Z0-9_]+)(?:\s+(?:con|de|con\s+los|con\s+\d+)?\s*(?:atributos|campos|propiedades|columnas)?(?:\s+(?:de\s+nombres?|llamados?|:))?\s+([^]+?))?\s+(?:y\s+)?(?:que\s+)?(?:se\s+)?(?:asocie|asociar|relacione|relacionar|conecte|conectar|vincule|vincular)\s+(?:a|con)\s+([a-zA-Z0-9_]+)(?:\s+(?:con\s+(?:la\s+)?cardinalidad\s+|cardinalidad\s+|tipo\s+)?([0-9*..a-zA-Z_\s]+))?$/i;

    let match = norm.match(regexA);
    if (!match) {
      const regexB = /^(?:tabla|clase|entidad|modelo)\s+([a-zA-Z0-9_]+)\s+con\s+([^]+?)\s+(?:y\s+)?(?:que\s+)?(?:se\s+)?(?:asocie|asociar|relacione|relacionar|conecte|conectar|vincule|vincular)\s+(?:a|con)\s+([a-zA-Z0-9_]+)(?:\s+(?:con\s+(?:la\s+)?cardinalidad\s+|cardinalidad\s+)?([0-9*..a-zA-Z_\s]+))?$/i;
      match = norm.match(regexB);
    }

    if (!match) return null;

    const className = this.capitalize(match[1]);
    const attrsStr = match[2];
    const targetClass = match[3] ? this.capitalize(match[3]) : null;
    const cardinalityStr = match[4];

    if (!className || className.length < 2) return null;

    const attributes: UMLAttribute[] = this.parseAttributeList(attrsStr);
    const classes: UMLClassCommand[] = [{
      name: className,
      attributes: attributes.length > 0 ? attributes : [
        { name: 'id', type: 'Long', visibility: '+' },
        { name: 'nombre', type: 'String', visibility: '+' }
      ],
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
        attributes: [
          { name: 'id', type: 'Long', visibility: '+' },
          { name: 'nombre', type: 'String', visibility: '+' }
        ],
        methods: []
      });
    }

    let explanation = `Clase '${className}' creada con ${classes[0].attributes.length} atributo(s)`;
    if (targetClass) {
      explanation += ` y asociada a '${targetClass}' con cardinalidad ${cardinalityStr ? cardinalityStr.trim() : '1..*'}.`;
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

  /**
   * Multi-class creator:
   * e.g. "crear clases Usuario, Rol, Permiso, Perfil"
   * e.g. "crear tablas Factura(total, fecha) y Cliente(nombre, nit)"
   */
  private matchMultiClassCreate(raw: string, norm: string): UMLCommandResponse | null {
    const regex = /(?:crea(?:r|me)?|genera(?:r|me)?|haz(?:me)?|agrega(?:r|me)?|pon(?:er|me)?)\s+(?:las\s+)?(?:clases|tablas|entidades|modelos)\s+([^]+)/i;
    const match = norm.match(regex);
    if (!match) return null;

    const content = match[1].trim();
    if (content.includes('(') && content.includes(')')) {
      const classBlocks = content.match(/[a-zA-Z0-9_]+\s*\([^)]*\)/g);
      if (classBlocks && classBlocks.length > 0) {
        const classes: UMLClassCommand[] = classBlocks.map(block => {
          const nameMatch = block.match(/^([a-zA-Z0-9_]+)\s*\(([^)]*)\)/);
          if (nameMatch) {
            const name = this.capitalize(nameMatch[1]);
            const attrs = this.parseAttributeList(nameMatch[2]);
            return {
              name,
              attributes: attrs.length > 0 ? attrs : [{ name: 'id', type: 'Long', visibility: '+' }],
              methods: []
            };
          }
          return { name: 'Clase', attributes: [{ name: 'id', type: 'Long', visibility: '+' }], methods: [] };
        });

        return {
          action: 'generate_system',
          classes,
          relations: [],
          deleted_elements: [],
          explanation: `Se crearon ${classes.length} clases con sus atributos: ${classes.map(c => c.name).join(', ')}.`,
          source: 'offline_nlu'
        };
      }
    }

    const rawList = content;
    const names = rawList
      .split(/[,;\n]|\s+y\s+|\s+e\s+/i)
      .map(s => s.trim())
      .filter(s => s && s.length > 1 && !['con', 'de', 'para', 'las', 'los', 'que', 'una', 'un'].includes(s.toLowerCase()));

    if (names.length <= 1) return null;

    const classes: UMLClassCommand[] = names.map(n => ({
      name: this.capitalize(n),
      attributes: [
        { name: 'id', type: 'Long', visibility: '+' },
        { name: 'nombre', type: 'String', visibility: '+' }
      ],
      methods: []
    }));

    return {
      action: 'generate_system',
      classes,
      relations: [],
      deleted_elements: [],
      explanation: `Se crearon ${classes.length} clases: ${classes.map(c => c.name).join(', ')}.`,
      source: 'offline_nlu'
    };
  }

  /**
   * Single Class/Table/Interface/Enum creation with or without attributes.
   * e.g. "creame una tabla llamada Cliente con nombre, nit, telefono"
   * e.g. "crear clase abstracta Vehiculo con marca, modelo"
   * e.g. "crear enum EstadoPedido con PENDIENTE, ENVIADO, ENTREGADO"
   */
  private matchCreateElement(raw: string, norm: string): UMLCommandResponse | null {
    let stereotype: string | undefined = undefined;
    if (norm.includes('clase abstracta') || norm.includes('abstract class') || norm.includes('abstracta')) {
      stereotype = 'abstract';
    } else if (norm.includes('interfaz') || norm.includes('interface')) {
      stereotype = 'interface';
    } else if (norm.includes('enum') || norm.includes('enumeracion') || norm.includes('enumerado')) {
      stereotype = 'enum';
    }

    const regex = /(?:(?:crea(?:r|me)?|genera(?:r|me)?|haz(?:me)?|agrega(?:r|me)?|pon(?:er|me)?|constru(?:ir|ye)?|nueva?)\s+)?(?:una?\s+)?(?:clase\s+abstracta|interfaz|interface|enum(?:eracion)?|tabla|clase|entidad|modelo)\s+(?:con\s+el\s+nombre\s+|llamada\s+|llamado\s+|de\s+nombre\s+)?([a-zA-Z0-9_]+)(?:\s+(?:con|con\s+los|con\s+\d+|de)\s*(?:atributos|campos|valores|propiedades|columnas)?(?:\s+(?:de\s+nombres?|llamados?|:))?\s+([^]+))?/i;
    const match = norm.match(regex);
    if (!match) return null;

    const className = this.capitalize(match[1]);
    if (!className || className.length < 2) return null;

    const rawAttrs = match[2];
    const attributes = this.parseAttributeList(rawAttrs);

    return {
      action: 'create_class',
      classes: [{
        name: className,
        stereotype,
        attributes: attributes.length > 0 ? attributes : [
          { name: 'id', type: 'Long', visibility: '+' },
          { name: 'nombre', type: 'String', visibility: '+' }
        ],
        methods: []
      }],
      relations: [],
      deleted_elements: [],
      explanation: `${stereotype ? this.capitalize(stereotype) : 'Clase'} '${className}' creada correctamente con ${attributes.length > 0 ? attributes.length : 2} atributo(s).`,
      source: 'offline_nlu'
    };
  }

  /**
   * Add attribute(s) to an existing class.
   * e.g. "agregar atributo email string a la clase Usuario"
   * e.g. "anadir campo direccion a la tabla Cliente"
   * e.g. "ponle el atributo telefono a Usuario"
   */
  private matchAddAttribute(raw: string, norm: string): UMLCommandResponse | null {
    const regex = /(?:agrega(?:r|me)?|anadi(?:r|me)?|incorpora(?:r)?|pon(?:er|me|le)?|meter?|crea(?:r|me)?)\s+(?:el\s+|los?\s+)?(?:atributos?|campos?|propiedades?|columnas?)\s+([^]+?)\s+(?:a|en|para)\s+(?:la\s+)?(?:clase|tabla|entidad)?\s*([a-zA-Z0-9_]+)$/i;
    const match = norm.match(regex);
    if (!match) return null;

    const rawAttrs = match[1];
    const className = this.capitalize(match[2]);
    const attributes = this.parseAttributeList(rawAttrs);

    if (attributes.length === 0) return null;

    return {
      action: 'add_attribute',
      classes: [{
        name: className,
        attributes,
        methods: []
      }],
      relations: [],
      deleted_elements: [],
      explanation: `${attributes.length} atributo(s) agregado(s) a '${className}': ${attributes.map(a => a.name + (a.type ? ': ' + a.type : '')).join(', ')}.`,
      source: 'offline_nlu'
    };
  }

  /**
   * Add method to an existing class.
   * e.g. "agregar metodo calcularDescuento(porcentaje: float): double a Factura"
   */
  private matchAddMethod(raw: string, norm: string): UMLCommandResponse | null {
    const regex = /(?:agrega(?:r|me)?|anadi(?:r|me)?|crea(?:r|me)?|implementa(?:r)?|pon(?:er|me|le)?)\s+(?:el\s+)?(?:metodo|funcion|operacion)\s+([a-zA-Z0-9_]+)(?:\s*\(([^)]*)\))?(?:\s*:?\s*([a-zA-Z0-9_]+))?\s+(?:a|en)\s+(?:la\s+)?(?:clase|tabla|entidad)?\s*([a-zA-Z0-9_]+)/i;
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

  /**
   * Create relationship between classes.
   */
  private matchRelation(raw: string, norm: string): UMLCommandResponse | null {
    // 1. Inheritance / Generalization
    const inheritRegex = /(?:hacer\s+que\s+)?([a-zA-Z0-9_]+)\s+(?:hereda|herede|extiende|extienda|es\s+una?|subclase\s+de)\s+(?:de\s+)?([a-zA-Z0-9_]+)/i;
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

    // 2. Realization / Implementation
    const realRegex = /([a-zA-Z0-9_]+)\s+(?:implementa|implemente|realiza|realice)\s+(?:a\s+|la\s+)?(?:interfaz\s+)?([a-zA-Z0-9_]+)/i;
    const realMatch = norm.match(realRegex);
    if (realMatch) {
      const source = this.capitalize(realMatch[1]);
      const target = this.capitalize(realMatch[2]);
      return {
        action: 'create_relation',
        classes: [],
        relations: [{
          source,
          target,
          type: 'realization',
          label: 'implements'
        }],
        deleted_elements: [],
        explanation: `Realización: '${source}' implementa la interfaz '${target}'.`,
        source: 'offline_nlu'
      };
    }

    // 3. Dependency
    const depRegex = /([a-zA-Z0-9_]+)\s+(?:depende|dependa)\s+de\s+([a-zA-Z0-9_]+)/i;
    const depMatch = norm.match(depRegex);
    if (depMatch) {
      const source = this.capitalize(depMatch[1]);
      const target = this.capitalize(depMatch[2]);
      return {
        action: 'create_relation',
        classes: [],
        relations: [{
          source,
          target,
          type: 'dependency',
          label: 'depends on'
        }],
        deleted_elements: [],
        explanation: `Dependencia: '${source}' depende de '${target}'.`,
        source: 'offline_nlu'
      };
    }

    // 4. Composition / Aggregation / Association
    const relRegex = /(?:(?:crea(?:r|me)?|genera(?:r)?)\s+(?:relacion|asociacion|composicion|agregacion|dependencia|herencia)\s+(?:entre|de)\s+|relaciona(?:r)?\s+|asocia(?:r)?\s+|conecta(?:r)?\s+|vincula(?:r)?\s+)([a-zA-Z0-9_]+)\s+(?:con|y|a)\s+([a-zA-Z0-9_]+)(?:\s+(?:como|por|tipo)?\s*(herencia|composicion|agregacion|dependencia|asociacion|realizacion))?(?:\s+(?:con\s+(?:la\s+)?cardinalidad\s+|cardinalidad\s+)?([0-9*..a-zA-Z_\s]+))?/i;
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

  /**
   * Delete class/table/element.
   */
  private matchDelete(raw: string, norm: string): UMLCommandResponse | null {
    const regex = /(?:elimina(?:r|me)?|borra(?:r|me)?|quita(?:r|me)?|remov(?:er|e))\s+(?:la\s+|el\s+)?(?:clase|tabla|entidad|elemento)\s+([a-zA-Z0-9_]+)/i;
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

  /**
   * Pre-built Domain Systems (14 diverse business domains).
   */
  private matchDomainSystem(raw: string, norm: string): UMLCommandResponse | null {
    // 1. E-Commerce / Tienda / Carrito
    if (norm.includes('e-commerce') || norm.includes('ecommerce') || norm.includes('tienda') || norm.includes('comercio') || norm.includes('carrito')) {
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
        explanation: 'Sistema E-Commerce generado con éxito (Usuario, Cliente, Producto, Categoria, Pedido, DetallePedido).',
        source: 'offline_nlu'
      };
    }

    // 2. Facturación / Ventas
    if (norm.includes('factura') || norm.includes('facturacion') || norm.includes('ventas') || norm.includes('pos') || norm.includes('caja')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Factura',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nroFactura', type: 'String', visibility: '+' },
              { name: 'fechaEmision', type: 'Date', visibility: '+' },
              { name: 'subtotal', type: 'Double', visibility: '+' },
              { name: 'iva', type: 'Double', visibility: '+' },
              { name: 'total', type: 'Double', visibility: '+' }
            ],
            methods: [{ name: 'calcularTotal', params: '', return_type: 'Double', visibility: '+' }]
          },
          {
            name: 'DetalleFactura',
            attributes: [
              { name: 'cantidad', type: 'Integer', visibility: '+' },
              { name: 'precioUnitario', type: 'Double', visibility: '+' },
              { name: 'descuento', type: 'Double', visibility: '+' },
              { name: 'importe', type: 'Double', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Cliente',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'razonSocial', type: 'String', visibility: '+' },
              { name: 'nitCi', type: 'String', visibility: '+' },
              { name: 'email', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Vendedor',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'codigoEmpleado', type: 'String', visibility: '+' },
              { name: 'comision', type: 'Double', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Producto',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'codigo', type: 'String', visibility: '+' },
              { name: 'descripcion', type: 'String', visibility: '+' },
              { name: 'precio', type: 'Double', visibility: '+' }
            ],
            methods: []
          }
        ],
        relations: [
          { source: 'Factura', target: 'Cliente', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'emitida a' },
          { source: 'Factura', target: 'Vendedor', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'atendida por' },
          { source: 'Factura', target: 'DetalleFactura', type: 'composition', sourceMultiplicity: '1', targetMultiplicity: '1..*', label: 'incluye' },
          { source: 'DetalleFactura', target: 'Producto', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'detalla' }
        ],
        deleted_elements: [],
        explanation: 'Sistema de Facturación y Ventas generado (Factura, DetalleFactura, Cliente, Vendedor, Producto).',
        source: 'offline_nlu'
      };
    }

    // 3. Bancario / Finanzas
    if (norm.includes('banco') || norm.includes('bancario') || norm.includes('cuenta') || norm.includes('financiero') || norm.includes('tarjeta')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Cliente',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'ci', type: 'String', visibility: '+' },
              { name: 'telefono', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'CuentaBancaria',
            stereotype: 'abstract',
            attributes: [
              { name: 'nroCuenta', type: 'String', visibility: '+' },
              { name: 'saldo', type: 'Double', visibility: '#' },
              { name: 'fechaApertura', type: 'Date', visibility: '+' }
            ],
            methods: [
              { name: 'depositar', params: 'monto: Double', return_type: 'Boolean', visibility: '+' },
              { name: 'retirar', params: 'monto: Double', return_type: 'Boolean', visibility: '+' }
            ]
          },
          {
            name: 'CuentaAhorro',
            attributes: [{ name: 'tasaInteres', type: 'Double', visibility: '+' }],
            methods: []
          },
          {
            name: 'CuentaCorriente',
            attributes: [{ name: 'limiteSobregiro', type: 'Double', visibility: '+' }],
            methods: []
          },
          {
            name: 'Transaccion',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'monto', type: 'Double', visibility: '+' },
              { name: 'tipo', type: 'String', visibility: '+' },
              { name: 'fechaHora', type: 'Date', visibility: '+' }
            ],
            methods: []
          }
        ],
        relations: [
          { source: 'CuentaAhorro', target: 'CuentaBancaria', type: 'inheritance', label: '' },
          { source: 'CuentaCorriente', target: 'CuentaBancaria', type: 'inheritance', label: '' },
          { source: 'Cliente', target: 'CuentaBancaria', type: 'association', sourceMultiplicity: '1', targetMultiplicity: '1..*', label: 'posee' },
          { source: 'CuentaBancaria', target: 'Transaccion', type: 'composition', sourceMultiplicity: '1', targetMultiplicity: '0..*', label: 'registra' }
        ],
        deleted_elements: [],
        explanation: 'Sistema Bancario generado (Cliente, CuentaBancaria, CuentaAhorro, CuentaCorriente, Transaccion).',
        source: 'offline_nlu'
      };
    }

    // 4. Universidad / Académico / Escuela / Colegio
    if (norm.includes('universidad') || norm.includes('universitari') || norm.includes('academico') || norm.includes('estudiante') || norm.includes('colegio') || norm.includes('escuela') || norm.includes('instituto')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Persona',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'email', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Estudiante',
            attributes: [
              { name: 'matricula', type: 'String', visibility: '+' },
              { name: 'semestre', type: 'Integer', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Docente',
            attributes: [
              { name: 'codigoDocente', type: 'String', visibility: '+' },
              { name: 'departamento', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Materia',
            attributes: [
              { name: 'sigla', type: 'String', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'creditos', type: 'Integer', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Inscripcion',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'fecha', type: 'Date', visibility: '+' },
              { name: 'notaFinal', type: 'Double', visibility: '+' }
            ],
            methods: []
          }
        ],
        relations: [
          { source: 'Estudiante', target: 'Persona', type: 'inheritance', label: '' },
          { source: 'Docente', target: 'Persona', type: 'inheritance', label: '' },
          { source: 'Docente', target: 'Materia', type: 'association', sourceMultiplicity: '1', targetMultiplicity: '1..*', label: 'dicta' },
          { source: 'Inscripcion', target: 'Estudiante', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'pertenece a' },
          { source: 'Inscripcion', target: 'Materia', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'cursa' }
        ],
        deleted_elements: [],
        explanation: 'Sistema Académico generado (Persona, Estudiante, Docente, Materia, Inscripcion).',
        source: 'offline_nlu'
      };
    }

    // 5. Hospital / Clínica / Salud / Médico
    if (norm.includes('hospital') || norm.includes('clinica') || norm.includes('medico') || norm.includes('paciente') || norm.includes('salud')) {
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
        explanation: 'Sistema Hospitalario generado (Persona, Paciente, Medico, CitaMedica).',
        source: 'offline_nlu'
      };
    }

    // 6. Biblioteca / Libros / Préstamos
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
        explanation: 'Sistema de Biblioteca generado (Libro, Autor, Lector, Prestamo).',
        source: 'offline_nlu'
      };
    }

    // 7. Hotel / Reservas / Huéspedes
    if (norm.includes('hotel') || norm.includes('reserva') || norm.includes('huesped') || norm.includes('habitacion')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Huesped',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'documento', type: 'String', visibility: '+' },
              { name: 'email', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Habitacion',
            attributes: [
              { name: 'numero', type: 'Integer', visibility: '+' },
              { name: 'piso', type: 'Integer', visibility: '+' },
              { name: 'precioNoche', type: 'Double', visibility: '+' },
              { name: 'disponible', type: 'Boolean', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'TipoHabitacion',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'capacidad', type: 'Integer', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Reserva',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'fechaInicio', type: 'Date', visibility: '+' },
              { name: 'fechaFin', type: 'Date', visibility: '+' },
              { name: 'costoTotal', type: 'Double', visibility: '+' }
            ],
            methods: []
          }
        ],
        relations: [
          { source: 'Habitacion', target: 'TipoHabitacion', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'tipo' },
          { source: 'Reserva', target: 'Huesped', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'solicitada por' },
          { source: 'Reserva', target: 'Habitacion', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'asigna' }
        ],
        deleted_elements: [],
        explanation: 'Sistema Hotelero generado (Huesped, Habitacion, TipoHabitacion, Reserva).',
        source: 'offline_nlu'
      };
    }

    // 8. Delivery / Restaurante / Comida
    if (norm.includes('delivery') || norm.includes('restaurante') || norm.includes('comida') || norm.includes('pedidosya') || norm.includes('repartidor')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Restaurante',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'direccion', type: 'String', visibility: '+' },
              { name: 'telefono', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Plato',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'precio', type: 'Double', visibility: '+' },
              { name: 'disponible', type: 'Boolean', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'PedidoDelivery',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'fechaHora', type: 'Date', visibility: '+' },
              { name: 'total', type: 'Double', visibility: '+' },
              { name: 'estado', type: 'String', visibility: '+' }
            ],
            methods: [{ name: 'calcularEnvio', params: '', return_type: 'Double', visibility: '+' }]
          },
          {
            name: 'Repartidor',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'vehiculo', type: 'String', visibility: '+' },
              { name: 'telefono', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Cliente',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'direccionEntrega', type: 'String', visibility: '+' }
            ],
            methods: []
          }
        ],
        relations: [
          { source: 'Plato', target: 'Restaurante', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'ofrecido por' },
          { source: 'PedidoDelivery', target: 'Cliente', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'solicitado por' },
          { source: 'PedidoDelivery', target: 'Repartidor', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'entregado por' },
          { source: 'PedidoDelivery', target: 'Restaurante', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'preparado en' }
        ],
        deleted_elements: [],
        explanation: 'Sistema de Delivery y Restaurante generado (Restaurante, Plato, PedidoDelivery, Repartidor, Cliente).',
        source: 'offline_nlu'
      };
    }

    // 9. Inventario / Almacén / Stock
    if (norm.includes('inventario') || norm.includes('almacen') || norm.includes('stock') || norm.includes('bodega') || norm.includes('proveedor')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Producto',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'codigoBarras', type: 'String', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'stockMinimo', type: 'Integer', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Proveedor',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'razonSocial', type: 'String', visibility: '+' },
              { name: 'nit', type: 'String', visibility: '+' },
              { name: 'telefono', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Almacen',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'ubicacion', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'MovimientoInventario',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'tipo', type: 'String', visibility: '+' },
              { name: 'cantidad', type: 'Integer', visibility: '+' },
              { name: 'fecha', type: 'Date', visibility: '+' }
            ],
            methods: []
          }
        ],
        relations: [
          { source: 'Producto', target: 'Proveedor', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1..*', label: 'suministrado por' },
          { source: 'MovimientoInventario', target: 'Producto', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'aplica a' },
          { source: 'MovimientoInventario', target: 'Almacen', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'origen/destino' }
        ],
        deleted_elements: [],
        explanation: 'Sistema de Control de Inventario generado (Producto, Proveedor, Almacen, MovimientoInventario).',
        source: 'offline_nlu'
      };
    }

    // 10. Red Social / Chat / Mensajería
    if (norm.includes('red social') || norm.includes('social') || norm.includes('publicacion') || norm.includes('post') || norm.includes('comentario')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Usuario',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'username', type: 'String', visibility: '+' },
              { name: 'email', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Perfil',
            attributes: [
              { name: 'biografia', type: 'String', visibility: '+' },
              { name: 'fotoUrl', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Publicacion',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'contenido', type: 'String', visibility: '+' },
              { name: 'fechaCreacion', type: 'Date', visibility: '+' }
            ],
            methods: [{ name: 'darLike', params: '', return_type: 'void', visibility: '+' }]
          },
          {
            name: 'Comentario',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'texto', type: 'String', visibility: '+' },
              { name: 'fecha', type: 'Date', visibility: '+' }
            ],
            methods: []
          }
        ],
        relations: [
          { source: 'Usuario', target: 'Perfil', type: 'composition', sourceMultiplicity: '1', targetMultiplicity: '1', label: 'tiene' },
          { source: 'Publicacion', target: 'Usuario', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'creada por' },
          { source: 'Publicacion', target: 'Comentario', type: 'composition', sourceMultiplicity: '1', targetMultiplicity: '0..*', label: 'contiene' },
          { source: 'Comentario', target: 'Usuario', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'escrito por' }
        ],
        deleted_elements: [],
        explanation: 'Sistema de Red Social generado (Usuario, Perfil, Publicacion, Comentario).',
        source: 'offline_nlu'
      };
    }

    // 11. Veterinaria / Mascotas
    if (norm.includes('veterinaria') || norm.includes('mascota') || norm.includes('animal')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Dueno',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'telefono', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Mascota',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'especie', type: 'String', visibility: '+' },
              { name: 'edad', type: 'Integer', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Veterinario',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'matricula', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'ConsultaVeterinaria',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'fecha', type: 'Date', visibility: '+' },
              { name: 'diagnostico', type: 'String', visibility: '+' }
            ],
            methods: []
          }
        ],
        relations: [
          { source: 'Mascota', target: 'Dueno', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'pertenece a' },
          { source: 'ConsultaVeterinaria', target: 'Mascota', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'atiende a' },
          { source: 'ConsultaVeterinaria', target: 'Veterinario', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'realizada por' }
        ],
        deleted_elements: [],
        explanation: 'Sistema Veterinario generado (Dueno, Mascota, Veterinario, ConsultaVeterinaria).',
        source: 'offline_nlu'
      };
    }

    // 12. Transporte / Logística
    if (norm.includes('transporte') || norm.includes('logistica') || norm.includes('camion') || norm.includes('viaje') || norm.includes('ruta')) {
      return {
        action: 'generate_system',
        classes: [
          {
            name: 'Vehiculo',
            attributes: [
              { name: 'placa', type: 'String', visibility: '+' },
              { name: 'marca', type: 'String', visibility: '+' },
              { name: 'capacidadKg', type: 'Double', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Conductor',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'nombre', type: 'String', visibility: '+' },
              { name: 'nroLicencia', type: 'String', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Ruta',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'origen', type: 'String', visibility: '+' },
              { name: 'destino', type: 'String', visibility: '+' },
              { name: 'distanciaKm', type: 'Double', visibility: '+' }
            ],
            methods: []
          },
          {
            name: 'Viaje',
            attributes: [
              { name: 'id', type: 'Long', visibility: '+' },
              { name: 'fechaSalida', type: 'Date', visibility: '+' },
              { name: 'fechaLlegada', type: 'Date', visibility: '+' }
            ],
            methods: []
          }
        ],
        relations: [
          { source: 'Viaje', target: 'Vehiculo', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'utiliza' },
          { source: 'Viaje', target: 'Conductor', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'conducido por' },
          { source: 'Viaje', target: 'Ruta', type: 'association', sourceMultiplicity: '*', targetMultiplicity: '1', label: 'recorre' }
        ],
        deleted_elements: [],
        explanation: 'Sistema de Logística y Transporte generado (Vehiculo, Conductor, Ruta, Viaje).',
        source: 'offline_nlu'
      };
    }

    return null;
  }

  /**
   * Universal Fallback Semantic Extractor (Guarantees Offline Reliability).
   */
  private fallbackEntityExtractor(raw: string, norm: string): UMLCommandResponse {
    const words = raw.match(/[a-zA-ZáéíóúÁÉÍÓÚñÑ]{3,}/g) || [];
    const stopWords = new Set([
      'para', 'como', 'este', 'esta', 'estos', 'estas', 'sistema', 'aplicacion', 'quiero', 'necesito',
      'crear', 'crea', 'creame', 'genera', 'generame', 'haz', 'hazme', 'agrega', 'agregame',
      'un', 'una', 'unos', 'unas', 'el', 'la', 'los', 'las', 'con', 'por', 'que', 'del', 'al',
      'tabla', 'clase', 'entidad', 'modelo', 'atributos', 'atributo', 'nombre', 'nombres',
      'llamada', 'llamado', 'llamados', 'tanto', 'tipo', 'cardinalidad', 'asocie', 'asociar', 'relacionar', 'conectar',
      'gestionar', 'disenar', 'disena', 'hacer'
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
        explanation: 'Se ha creado una nueva clase en el diagrama.',
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

      if (token.startsWith('+') || token.startsWith('-') || token.startsWith('#') || token.startsWith('~')) {
        visibility = token.charAt(0);
      }

      const stripped = token.replace(/^[+\-#~]\s*/, '');

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
      if (name && !['los', 'las', 'de', 'con', 'y', 'para', 'que'].includes(name.toLowerCase())) {
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
    if (norm.includes('cero a muchos') || norm.includes('0 a muchos') || norm.includes('0 a *') || norm.includes('0 a n')) {
      return { sourceMult: '1', targetMult: '0..*' };
    }
    if (norm.includes('muchos a uno') || norm.includes('* a 1') || norm.includes('muchos a 1') || norm.includes('n a 1')) {
      return { sourceMult: '0..*', targetMult: '1' };
    }
    if (norm.includes('muchos a muchos') || norm.includes('* a *') || norm.includes('n a m') || norm.includes('n a n')) {
      return { sourceMult: '0..*', targetMult: '0..*' };
    }
    if (norm.includes('uno a uno') || norm.includes('1 a 1') || norm.includes('1..1 a 1..1')) {
      return { sourceMult: '1', targetMult: '1' };
    }
    if (norm.includes('0 a 1') || norm.includes('cero a uno')) {
      return { sourceMult: '1', targetMult: '0..1' };
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
    if (t.includes('herencia') || t.includes('inherit') || t.includes('generalizacion') || t.includes('generalización')) return 'inheritance';
    if (t.includes('composicion') || t.includes('composición') || t.includes('composition')) return 'composition';
    if (t.includes('agregacion') || t.includes('agregación') || t.includes('aggregation')) return 'aggregation';
    if (t.includes('dependencia') || t.includes('dependency')) return 'dependency';
    if (t.includes('realizacion') || t.includes('realización') || t.includes('realization')) return 'realization';
    return 'association';
  }

  public inferTypeFromName(name: string): string {
    const n = name.toLowerCase();
    if (n === 'id' || n.endsWith('id')) return 'Long';
    if (n.includes('precio') || n.includes('total') || n.includes('monto') || n.includes('saldo') || n.includes('costo') || n.includes('descuento') || n.includes('subtotal') || n.includes('sueldo') || n.includes('tarifa') || n.includes('interes') || n.includes('iva') || n.includes('importe')) return 'Double';
    if (n.includes('stock') || n.includes('cantidad') || n.includes('edad') || n.includes('numero') || n.includes('nro') || n.includes('orden') || n.includes('anio') || n.includes('puntos') || n.includes('intentos') || n.includes('semestre') || n.includes('piso') || n.includes('capacidad')) return 'Integer';
    if (n.includes('fecha') || n.includes('created') || n.includes('updated') || n.includes('date') || n.includes('nacimiento') || n.includes('hora')) return 'Date';
    if (n.startsWith('es') || n.startsWith('is') || n.includes('activo') || n.includes('habilitado') || n.includes('bloqueado') || n.includes('valido') || n.includes('disponible') || n.includes('pagado')) return 'Boolean';
    return 'String';
  }

  public normalizeType(type: string): string {
    const t = (type || '').toLowerCase().trim();
    if (t === 'int' || t === 'integer' || t === 'entero') return 'Integer';
    if (t === 'long' || t === 'bigint') return 'Long';
    if (t === 'float' || t === 'flotante') return 'Float';
    if (t === 'double' || t === 'decimal' || t === 'number' || t === 'numero' || t === 'moneda') return 'Double';
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
