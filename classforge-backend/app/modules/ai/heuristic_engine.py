import re
import unicodedata
from typing import Optional, List, Tuple
from app.modules.ai.schemas import (
    UMLCommandResponse,
    UMLClassCommand,
    UMLAttribute,
    UMLMethod,
    UMLRelationCommand
)

def normalize_text(text: str) -> str:
    nfd = unicodedata.normalize('NFD', text)
    clean = "".join([c for c in nfd if unicodedata.category(c) != 'Mn'])
    return clean.lower().strip()

def capitalize_name(name: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9_]', '', name)
    return clean.capitalize() if clean else 'Clase'

def infer_type_from_name(name: str) -> str:
    n = name.lower()
    if n == 'id' or n.endswith('id'): return 'Long'
    if any(k in n for k in ['precio', 'total', 'monto', 'saldo', 'costo', 'descuento', 'subtotal', 'sueldo', 'salario', 'tarifa', 'iva', 'importe', 'interes']): return 'Double'
    if any(k in n for k in ['stock', 'cantidad', 'edad', 'numero', 'nro', 'orden', 'anio', 'puntos', 'intentos', 'semestre', 'piso', 'capacidad']): return 'Integer'
    if any(k in n for k in ['fecha', 'created', 'updated', 'date', 'nacimiento', 'hora']): return 'Date'
    if n.startswith('es') or n.startswith('is') or any(k in n for k in ['activo', 'habilitado', 'bloqueado', 'valido', 'disponible', 'pagado']): return 'Boolean'
    return 'String'

def normalize_type(t: str) -> str:
    t_clean = t.lower().strip()
    if t_clean in ['int', 'integer', 'entero']: return 'Integer'
    if t_clean in ['long', 'bigint']: return 'Long'
    if t_clean in ['float', 'flotante']: return 'Float'
    if t_clean in ['double', 'decimal', 'number', 'moneda']: return 'Double'
    if t_clean in ['bool', 'boolean', 'booleano']: return 'Boolean'
    if t_clean in ['datetime', 'timestamp']: return 'datetime'
    if t_clean in ['date', 'fecha']: return 'Date'
    if t_clean in ['void', 'vacio']: return 'void'
    if t_clean in ['string', 'texto', 'cadena', 'str']: return 'String'
    return t.strip() if t else 'String'

def parse_attributes_list(raw_attrs: Optional[str]) -> List[UMLAttribute]:
    if not raw_attrs:
        return []
    clean = re.sub(r'^(?:llamados?|de\s+nombres?|:)\s*', '', raw_attrs, flags=re.IGNORECASE).strip()
    tokens = re.split(r'[,;\n]|\s+y\s+|\s+e\s+', clean, flags=re.IGNORECASE)
    attributes = []
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        vis = '+'
        if token.startswith(('+', '-', '#', '~')):
            vis = token[0]
            token = token[1:].strip()
        
        if ':' in token:
            parts = [p.strip() for p in token.split(':', 1)]
            attr_name = parts[0]
            attr_type = normalize_type(parts[1]) if len(parts) > 1 else 'String'
        else:
            words = token.split()
            if len(words) >= 2:
                attr_name = words[0]
                attr_type = normalize_type(words[1])
            elif len(words) == 1:
                attr_name = words[0]
                attr_type = infer_type_from_name(attr_name)
            else:
                continue

        attr_name = re.sub(r'[^a-zA-Z0-9_]', '', attr_name)
        if attr_name and attr_name.lower() not in ['los', 'las', 'de', 'con', 'y', 'para', 'que']:
            attributes.append(UMLAttribute(name=attr_name, type=attr_type, visibility=vis))
    return attributes

def parse_cardinality_str(card: Optional[str]) -> Tuple[str, str]:
    if not card:
        return ('1', '1..*')
    c = card.lower().strip()
    if 'uno a muchos' in c or '1 a muchos' in c or '1 a *' in c or '1 a n' in c:
        return ('1', '1..*')
    if 'cero a muchos' in c or '0 a muchos' in c or '0 a *' in c:
        return ('1', '0..*')
    if 'muchos a uno' in c or '* a 1' in c or 'muchos a 1' in c:
        return ('0..*', '1')
    if 'muchos a muchos' in c or '* a *' in c or 'n a m' in c:
        return ('0..*', '0..*')
    if 'uno a uno' in c or '1 a 1' in c:
        return ('1', '1')
    if '0 a 1' in c or 'cero a uno' in c:
        return ('1', '0..1')
    
    if '..' in c:
        parts = [p.strip().upper() for p in c.split('..', 1)]
        if len(parts) == 2:
            return (parts[0], f"{parts[0]}..{parts[1]}")
    
    if ' a ' in c:
        parts = [p.strip() for p in c.split(' a ', 1)]
        return (parts[0] or '1', parts[1] or '1..*')
    
    return ('1', card.strip())

def parse_heuristic(prompt: str) -> Optional[UMLCommandResponse]:
    norm = normalize_text(prompt)

    # 1. Complex create table/class query with attributes and relation + cardinality
    complex_pattern = re.compile(
        r"(?:(?:crea(?:r|me)?|genera(?:r|me)?|haz(?:me)?|agrega(?:r|me)?|pon(?:er|me)?)\s+)?(?:una?\s+)?(?:tabla|clase|entidad|modelo)\s+"
        r"(?:con\s+el\s+nombre\s+|llamada\s+|de\s+nombre\s+)?([a-zA-Z0-9_]+)"
        r"(?:\s+(?:con|de|con\s+los|con\s+\d+)?\s*(?:atributos|campos|propiedades|columnas)?(?:\s+(?:de\s+nombres?|llamados?|:))?\s+(.+?))?"
        r"\s+(?:y\s+)?(?:que\s+)?(?:se\s+)?(?:asocie|asociar|relacione|relacionar|conecte|conectar|vincule|vincular)\s+(?:a|con)\s+([a-zA-Z0-9_]+)"
        r"(?:\s+(?:con\s+(?:la\s+)?cardinalidad\s+|cardinalidad\s+)?([0-9*..a-zA-Z_\s]+))?$",
        re.IGNORECASE
    )
    m = complex_pattern.search(norm)
    if not m:
        regex_b = re.compile(r"^(?:tabla|clase|entidad|modelo)\s+([a-zA-Z0-9_]+)\s+con\s+(.+?)\s+(?:y\s+)?(?:que\s+)?(?:se\s+)?(?:asocie|asociar|relacione|relacionar|conecte|conectar|vincule|vincular)\s+(?:a|con)\s+([a-zA-Z0-9_]+)(?:\s+(?:con\s+(?:la\s+)?cardinalidad\s+|cardinalidad\s+)?([0-9*..a-zA-Z_\s]+))?$", re.IGNORECASE)
        m = regex_b.search(norm)

    if m:
        class_name = capitalize_name(m.group(1))
        attrs_str = m.group(2)
        target_class = capitalize_name(m.group(3)) if m.group(3) else None
        cardinality_str = m.group(4)

        attributes = parse_attributes_list(attrs_str)
        if not attributes:
            attributes = [UMLAttribute(name="id", type="Long", visibility="+"), UMLAttribute(name="nombre", type="String", visibility="+")]

        classes = [UMLClassCommand(name=class_name, attributes=attributes)]
        relations = []

        if target_class:
            src_mult, tgt_mult = parse_cardinality_str(cardinality_str)
            relations.append(UMLRelationCommand(
                source=class_name,
                target=target_class,
                type="association",
                source_multiplicity=src_mult,
                target_multiplicity=tgt_mult,
                label=""
            ))
            classes.append(UMLClassCommand(
                name=target_class,
                attributes=[UMLAttribute(name="id", type="Long", visibility="+"), UMLAttribute(name="nombre", type="String", visibility="+")]
            ))

        explanation = f"Tabla/Clase '{class_name}' creada con {len(attributes)} atributos"
        if target_class:
            explanation += f" y asociada a '{target_class}' con cardinalidad {cardinality_str or '1..*'}."
        else:
            explanation += "."

        return UMLCommandResponse(
            action="create_class",
            classes=classes,
            relations=relations,
            explanation=explanation,
            source="nlu_heuristic"
        )

    # 2. Multi-class creation: "crear clases Usuario, Rol, Permiso, Perfil"
    multi_pattern = re.compile(r"(?:crea(?:r|me)?|genera(?:r|me)?|haz(?:me)?|agrega(?:r|me)?|pon(?:er|me)?)\s+(?:las\s+)?(?:clases|tablas|entidades|modelos)\s+(.+)", re.IGNORECASE)
    m = multi_pattern.search(norm)
    if m:
        raw_list = m.group(1).strip()
        names = [s.strip() for s in re.split(r'[,;\n]|\s+y\s+|\s+e\s+', raw_list, flags=re.IGNORECASE)]
        names = [capitalize_name(n) for n in names if n and len(n) > 1 and n.lower() not in ['con', 'de', 'para', 'las', 'los', 'que', 'una', 'un']]
        if len(names) > 1:
            classes = [UMLClassCommand(name=n, attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String")]) for n in names]
            return UMLCommandResponse(
                action="generate_system",
                classes=classes,
                relations=[],
                explanation=f"Se crearon {len(classes)} clases: {', '.join(names)}.",
                source="nlu_heuristic"
            )

    # 3. Add Attribute
    add_attr_pattern = re.compile(
        r"(?:agrega(?:r|me)?|anadi(?:r|me)?|incorpora(?:r)?|pon(?:er|me|le)?|meter?|crea(?:r|me)?)\s+(?:el\s+|los?\s+)?(?:atributos?|campos?|propiedades?|columnas?)\s+(.+?)\s+(?:a|en|para)\s+(?:la\s+)?(?:clase|tabla|entidad)?\s*([a-zA-Z0-9_]+)$",
        re.IGNORECASE
    )
    m = add_attr_pattern.search(norm)
    if m:
        raw_attrs = m.group(1)
        class_name = capitalize_name(m.group(2))
        attributes = parse_attributes_list(raw_attrs)
        if attributes:
            return UMLCommandResponse(
                action="add_attribute",
                classes=[UMLClassCommand(name=class_name, attributes=attributes)],
                explanation=f"{len(attributes)} atributo(s) agregados a {class_name}.",
                source="nlu_heuristic"
            )

    # 4. Add Method
    add_method_pattern = re.compile(
        r"(?:agrega(?:r|me)?|anadi(?:r|me)?|crea(?:r|me)?|implementa(?:r)?|pon(?:er|me|le)?)\s+(?:el\s+)?(?:metodo|funcion|operacion)\s+([a-zA-Z0-9_]+)(?:\s*\(([^)]*)\))?(?:\s*:?\s*([a-zA-Z0-9_]+))?\s+(?:a|en)\s+(?:la\s+)?(?:clase|tabla|entidad)?\s*([a-zA-Z0-9_]+)",
        re.IGNORECASE
    )
    m = add_method_pattern.search(norm)
    if m:
        method_name = m.group(1)
        params = m.group(2) or ""
        return_type = normalize_type(m.group(3)) if m.group(3) else "void"
        class_name = capitalize_name(m.group(4))

        return UMLCommandResponse(
            action="add_method",
            classes=[UMLClassCommand(name=class_name, methods=[UMLMethod(name=method_name, params=params, return_type=return_type, visibility="+")])],
            explanation=f"Método {method_name}({params}): {return_type} agregado a {class_name}.",
            source="nlu_heuristic"
        )

    # 5. Inheritance special case: "hacer que Administrador herede de Usuario"
    inherit_pattern = re.compile(r"(?:hacer\s+que\s+)?([a-zA-Z0-9_]+)\s+(?:hereda|herede|extiende|extienda)\s+de\s+([a-zA-Z0-9_]+)", re.IGNORECASE)
    m = inherit_pattern.search(norm)
    if m:
        source_class = capitalize_name(m.group(1))
        target_class = capitalize_name(m.group(2))
        return UMLCommandResponse(
            action="create_relation",
            relations=[UMLRelationCommand(source=source_class, target=target_class, type="inheritance")],
            explanation=f"Herencia: {source_class} hereda de {target_class}.",
            source="nlu_heuristic"
        )

    # 6. Relate: "relacionar Usuario con Pedido asociacion con cardinalidad 1 a *" or "relacionar Factura con Cliente (composicion)"
    rel_pattern = re.compile(
        r"(?:(?:crea(?:r|me)?|genera(?:r)?)\s+(?:relacion|asociacion|composicion|agregacion|dependencia|herencia)\s+(?:entre|de)\s+|relaciona(?:r)?\s+|asocia(?:r)?\s+|conecta(?:r)?\s+|vincula(?:r)?\s+)"
        r"([a-zA-Z0-9_]+)\s+(?:con|y|a)\s+([a-zA-Z0-9_]+)(?:\s*\(?(?:como|por|tipo\s+de|tipo)?\s*(herencia|composicion|agregacion|dependencia|asociacion|realizacion)\)?)?"
        r"(?:\s+(?:con\s+(?:la\s+)?cardinalidad\s+|cardinalidad\s+)?([0-9*..a-zA-Z_\s]+))?",
        re.IGNORECASE
    )
    m = rel_pattern.search(norm)
    if m:
        source_class = capitalize_name(m.group(1))
        target_class = capitalize_name(m.group(2))
        rel_type_raw = m.group(3)
        raw_card = m.group(4)
        
        rel_type = "association"
        if rel_type_raw:
            rel_type_raw = rel_type_raw.lower()
            if "herencia" in rel_type_raw: rel_type = "inheritance"
            elif "composicion" in rel_type_raw: rel_type = "composition"
            elif "agregacion" in rel_type_raw: rel_type = "aggregation"
            elif "dependencia" in rel_type_raw: rel_type = "dependency"
            elif "realizacion" in rel_type_raw: rel_type = "realization"

        src_mult, tgt_mult = parse_cardinality_str(raw_card)

        return UMLCommandResponse(
            action="create_relation",
            relations=[UMLRelationCommand(
                source=source_class,
                target=target_class,
                type=rel_type,
                source_multiplicity=src_mult,
                target_multiplicity=tgt_mult
            )],
            explanation=f"Relación {rel_type} creada entre {source_class} y {target_class}.",
            source="nlu_heuristic"
        )

    # 7. Delete element: "eliminar clase Usuario"
    del_pattern = re.compile(r"(?:elimina(?:r|me)?|borra(?:r|me)?|quita(?:r|me)?|remov(?:er|e))\s+(?:la\s+|el\s+)?(?:clase|tabla|entidad|elemento)\s+([a-zA-Z0-9_]+)", re.IGNORECASE)
    m = del_pattern.search(norm)
    if m:
        class_name = capitalize_name(m.group(1))
        return UMLCommandResponse(
            action="delete_element",
            deleted_elements=[class_name],
            explanation=f"Elemento {class_name} eliminado.",
            source="nlu_heuristic"
        )

    # 8. Single Create Class / Table / Entity / Interface / Enum
    stereotype = None
    if "clase abstracta" in norm or "abstract class" in norm or "abstracta" in norm: stereotype = "abstract"
    elif "interfaz" in norm or "interface" in norm: stereotype = "interface"
    elif "enum" in norm or "enumeracion" in norm: stereotype = "enum"

    create_pattern = re.compile(
        r"(?:(?:crea(?:r|me)?|genera(?:r|me)?|haz(?:me)?|agrega(?:r|me)?|pon(?:er|me)?|nueva?)\s+)?(?:una?\s+)?(?:clase\s+abstracta|interfaz|interface|enum(?:eracion)?|tabla|clase|entidad|modelo)\s+"
        r"(?:con\s+el\s+nombre\s+|llamada\s+|llamado\s+|de\s+nombre\s+)?([a-zA-Z0-9_]+)(?:\s+(?:con|con\s+los|con\s+\d+|de)\s*(?:atributos|campos|valores|propiedades|columnas)?(?:\s+(?:de\s+nombres?|llamados?|:))?\s+(.+))?",
        re.IGNORECASE
    )
    m = create_pattern.search(norm)
    if m:
        class_name = capitalize_name(m.group(1))
        raw_attrs = m.group(2)
        attributes = parse_attributes_list(raw_attrs)
        if not attributes:
            attributes = [UMLAttribute(name="id", type="Long", visibility="+"), UMLAttribute(name="nombre", type="String", visibility="+")]

        return UMLCommandResponse(
            action="create_class",
            classes=[UMLClassCommand(name=class_name, stereotype=stereotype, attributes=attributes)],
            explanation=f"Clase '{class_name}' creada por heurística.",
            source="nlu_heuristic"
        )

    # 9. Domain Systems (when explicitly requested as domain or system)
    if any(k in norm for k in ['e-commerce', 'ecommerce', 'tienda', 'comercio', 'carrito']):
        return UMLCommandResponse(
            action="generate_system",
            classes=[
                UMLClassCommand(name="Usuario", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="email", type="String")]),
                UMLClassCommand(name="Cliente", attributes=[UMLAttribute(name="direccion", type="String"), UMLAttribute(name="telefono", type="String")]),
                UMLClassCommand(name="Producto", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="precio", type="Double"), UMLAttribute(name="stock", type="Integer")]),
                UMLClassCommand(name="Categoria", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String")]),
                UMLClassCommand(name="Pedido", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="fecha", type="Date"), UMLAttribute(name="total", type="Double")]),
                UMLClassCommand(name="DetallePedido", attributes=[UMLAttribute(name="cantidad", type="Integer"), UMLAttribute(name="subtotal", type="Double")])
            ],
            relations=[
                UMLRelationCommand(source="Cliente", target="Usuario", type="inheritance"),
                UMLRelationCommand(source="Cliente", target="Pedido", type="association", source_multiplicity="1", target_multiplicity="0..*"),
                UMLRelationCommand(source="Pedido", target="DetallePedido", type="composition", source_multiplicity="1", target_multiplicity="1..*"),
                UMLRelationCommand(source="DetallePedido", target="Producto", type="association", source_multiplicity="*", target_multiplicity="1"),
                UMLRelationCommand(source="Producto", target="Categoria", type="association", source_multiplicity="*", target_multiplicity="1")
            ],
            explanation="Sistema E-Commerce generado.",
            source="nlu_heuristic"
        )

    if any(k in norm for k in ['factura', 'facturacion', 'ventas', 'pos', 'caja']):
        return UMLCommandResponse(
            action="generate_system",
            classes=[
                UMLClassCommand(name="Factura", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nroFactura", type="String"), UMLAttribute(name="fecha", type="Date"), UMLAttribute(name="total", type="Double")]),
                UMLClassCommand(name="DetalleFactura", attributes=[UMLAttribute(name="cantidad", type="Integer"), UMLAttribute(name="precioUnitario", type="Double"), UMLAttribute(name="subtotal", type="Double")]),
                UMLClassCommand(name="Cliente", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="razonSocial", type="String"), UMLAttribute(name="nitCi", type="String")]),
                UMLClassCommand(name="Producto", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="codigo", type="String"), UMLAttribute(name="descripcion", type="String"), UMLAttribute(name="precio", type="Double")])
            ],
            relations=[
                UMLRelationCommand(source="Factura", target="Cliente", type="association", source_multiplicity="*", target_multiplicity="1"),
                UMLRelationCommand(source="Factura", target="DetalleFactura", type="composition", source_multiplicity="1", target_multiplicity="1..*"),
                UMLRelationCommand(source="DetalleFactura", target="Producto", type="association", source_multiplicity="*", target_multiplicity="1")
            ],
            explanation="Sistema de Facturación y Ventas generado.",
            source="nlu_heuristic"
        )

    if any(k in norm for k in ['banco', 'bancario', 'cuenta', 'financiero']):
        return UMLCommandResponse(
            action="generate_system",
            classes=[
                UMLClassCommand(name="Cliente", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="ci", type="String")]),
                UMLClassCommand(name="CuentaBancaria", stereotype="abstract", attributes=[UMLAttribute(name="nroCuenta", type="String"), UMLAttribute(name="saldo", type="Double", visibility="#")]),
                UMLClassCommand(name="CuentaAhorro", attributes=[UMLAttribute(name="tasaInteres", type="Double")]),
                UMLClassCommand(name="CuentaCorriente", attributes=[UMLAttribute(name="limiteSobregiro", type="Double")]),
                UMLClassCommand(name="Transaccion", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="monto", type="Double"), UMLAttribute(name="fecha", type="Date")])
            ],
            relations=[
                UMLRelationCommand(source="CuentaAhorro", target="CuentaBancaria", type="inheritance"),
                UMLRelationCommand(source="CuentaCorriente", target="CuentaBancaria", type="inheritance"),
                UMLRelationCommand(source="Cliente", target="CuentaBancaria", type="association", source_multiplicity="1", target_multiplicity="1..*"),
                UMLRelationCommand(source="CuentaBancaria", target="Transaccion", type="composition", source_multiplicity="1", target_multiplicity="0..*")
            ],
            explanation="Sistema Bancario generado.",
            source="nlu_heuristic"
        )

    if any(k in norm for k in ['hospital', 'clinica', 'medico', 'paciente', 'salud']):
        return UMLCommandResponse(
            action="generate_system",
            classes=[
                UMLClassCommand(name="Persona", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="dni", type="String")]),
                UMLClassCommand(name="Paciente", attributes=[UMLAttribute(name="nroHistoriaClinica", type="String"), UMLAttribute(name="grupoSanguineo", type="String")]),
                UMLClassCommand(name="Medico", attributes=[UMLAttribute(name="matricula", type="String"), UMLAttribute(name="especialidad", type="String")]),
                UMLClassCommand(name="CitaMedica", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="fechaHora", type="Date"), UMLAttribute(name="motivo", type="String")])
            ],
            relations=[
                UMLRelationCommand(source="Paciente", target="Persona", type="inheritance"),
                UMLRelationCommand(source="Medico", target="Persona", type="inheritance"),
                UMLRelationCommand(source="CitaMedica", target="Paciente", type="association", source_multiplicity="*", target_multiplicity="1"),
                UMLRelationCommand(source="CitaMedica", target="Medico", type="association", source_multiplicity="*", target_multiplicity="1")
            ],
            explanation="Sistema Hospitalario generado.",
            source="nlu_heuristic"
        )

    if any(k in norm for k in ['universidad', 'universitari', 'academico', 'estudiante', 'colegio', 'escuela', 'instituto']):
        return UMLCommandResponse(
            action="generate_system",
            classes=[
                UMLClassCommand(name="Persona", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="email", type="String")]),
                UMLClassCommand(name="Estudiante", attributes=[UMLAttribute(name="matricula", type="String"), UMLAttribute(name="semestre", type="Integer")]),
                UMLClassCommand(name="Docente", attributes=[UMLAttribute(name="codigoDocente", type="String"), UMLAttribute(name="departamento", type="String")]),
                UMLClassCommand(name="Materia", attributes=[UMLAttribute(name="sigla", type="String"), UMLAttribute(name="nombre", type="String")]),
                UMLClassCommand(name="Inscripcion", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="fecha", type="Date"), UMLAttribute(name="notaFinal", type="Double")])
            ],
            relations=[
                UMLRelationCommand(source="Estudiante", target="Persona", type="inheritance"),
                UMLRelationCommand(source="Docente", target="Persona", type="inheritance"),
                UMLRelationCommand(source="Docente", target="Materia", type="association", source_multiplicity="1", target_multiplicity="1..*"),
                UMLRelationCommand(source="Inscripcion", target="Estudiante", type="association", source_multiplicity="*", target_multiplicity="1"),
                UMLRelationCommand(source="Inscripcion", target="Materia", type="association", source_multiplicity="*", target_multiplicity="1")
            ],
            explanation="Sistema Académico Universitario generado.",
            source="nlu_heuristic"
        )

    if any(k in norm for k in ['delivery', 'restaurante', 'comida', 'repartidor']):
        return UMLCommandResponse(
            action="generate_system",
            classes=[
                UMLClassCommand(name="Restaurante", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="direccion", type="String")]),
                UMLClassCommand(name="Plato", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="precio", type="Double")]),
                UMLClassCommand(name="PedidoDelivery", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="fecha", type="Date"), UMLAttribute(name="total", type="Double")]),
                UMLClassCommand(name="Repartidor", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="telefono", type="String")]),
                UMLClassCommand(name="Cliente", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="direccion", type="String")])
            ],
            relations=[
                UMLRelationCommand(source="Plato", target="Restaurante", type="association", source_multiplicity="*", target_multiplicity="1"),
                UMLRelationCommand(source="PedidoDelivery", target="Cliente", type="association", source_multiplicity="*", target_multiplicity="1"),
                UMLRelationCommand(source="PedidoDelivery", target="Repartidor", type="association", source_multiplicity="*", target_multiplicity="1")
            ],
            explanation="Sistema de Delivery generado.",
            source="nlu_heuristic"
        )

    if any(k in norm for k in ['inventario', 'almacen', 'stock', 'proveedor']):
        return UMLCommandResponse(
            action="generate_system",
            classes=[
                UMLClassCommand(name="Producto", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="codigo", type="String"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="stock", type="Integer")]),
                UMLClassCommand(name="Proveedor", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="razonSocial", type="String"), UMLAttribute(name="telefono", type="String")]),
                UMLClassCommand(name="Almacen", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="ubicacion", type="String")]),
                UMLClassCommand(name="Movimiento", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="tipo", type="String"), UMLAttribute(name="cantidad", type="Integer"), UMLAttribute(name="fecha", type="Date")])
            ],
            relations=[
                UMLRelationCommand(source="Producto", target="Proveedor", type="association", source_multiplicity="*", target_multiplicity="1..*"),
                UMLRelationCommand(source="Movimiento", target="Producto", type="association", source_multiplicity="*", target_multiplicity="1"),
                UMLRelationCommand(source="Movimiento", target="Almacen", type="association", source_multiplicity="*", target_multiplicity="1")
            ],
            explanation="Sistema de Inventario generado.",
            source="nlu_heuristic"
        )

    if any(k in norm for k in ['biblioteca', 'libro', 'prestamo']):
        return UMLCommandResponse(
            action="generate_system",
            classes=[
                UMLClassCommand(name="Libro", attributes=[UMLAttribute(name="isbn", type="String"), UMLAttribute(name="titulo", type="String")]),
                UMLClassCommand(name="Autor", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String")]),
                UMLClassCommand(name="Lector", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String")]),
                UMLClassCommand(name="Prestamo", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="fecha", type="Date")])
            ],
            relations=[
                UMLRelationCommand(source="Libro", target="Autor", type="association", source_multiplicity="*", target_multiplicity="1..*"),
                UMLRelationCommand(source="Prestamo", target="Lector", type="association", source_multiplicity="*", target_multiplicity="1"),
                UMLRelationCommand(source="Prestamo", target="Libro", type="association", source_multiplicity="*", target_multiplicity="1")
            ],
            explanation="Sistema de Biblioteca generado.",
            source="nlu_heuristic"
        )

    if any(k in norm for k in ['hotel', 'reserva', 'huesped', 'habitacion']):
        return UMLCommandResponse(
            action="generate_system",
            classes=[
                UMLClassCommand(name="Huesped", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String"), UMLAttribute(name="documento", type="String")]),
                UMLClassCommand(name="Habitacion", attributes=[UMLAttribute(name="numero", type="Integer"), UMLAttribute(name="precio", type="Double")]),
                UMLClassCommand(name="Reserva", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="fechaInicio", type="Date"), UMLAttribute(name="fechaFin", type="Date")])
            ],
            relations=[
                UMLRelationCommand(source="Reserva", target="Huesped", type="association", source_multiplicity="*", target_multiplicity="1"),
                UMLRelationCommand(source="Reserva", target="Habitacion", type="association", source_multiplicity="*", target_multiplicity="1")
            ],
            explanation="Sistema Hotelero generado.",
            source="nlu_heuristic"
        )

    if any(k in norm for k in ['red social', 'social', 'publicacion', 'post', 'comentario']):
        return UMLCommandResponse(
            action="generate_system",
            classes=[
                UMLClassCommand(name="Usuario", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="username", type="String"), UMLAttribute(name="email", type="String")]),
                UMLClassCommand(name="Perfil", attributes=[UMLAttribute(name="biografia", type="String"), UMLAttribute(name="foto", type="String")]),
                UMLClassCommand(name="Publicacion", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="contenido", type="String"), UMLAttribute(name="fecha", type="Date")]),
                UMLClassCommand(name="Comentario", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="texto", type="String")])
            ],
            relations=[
                UMLRelationCommand(source="Usuario", target="Perfil", type="composition", source_multiplicity="1", target_multiplicity="1"),
                UMLRelationCommand(source="Publicacion", target="Usuario", type="association", source_multiplicity="*", target_multiplicity="1"),
                UMLRelationCommand(source="Publicacion", target="Comentario", type="composition", source_multiplicity="1", target_multiplicity="0..*")
            ],
            explanation="Sistema de Red Social generado.",
            source="nlu_heuristic"
        )

    # 10. Fallback extractor
    words = re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]{3,}', prompt)
    stop_words = {'para', 'como', 'este', 'esta', 'estos', 'estas', 'sistema', 'aplicacion', 'quiero', 'necesito', 'crear', 'crea', 'creame', 'genera', 'un', 'una', 'el', 'la', 'los', 'las', 'con', 'por', 'que', 'del', 'al', 'tabla', 'clase', 'entidad', 'modelo'}
    candidates = [capitalize_name(w) for w in words if w.lower() not in stop_words]
    unique = list(dict.fromkeys(candidates))[:4]
    
    if unique:
        classes = [UMLClassCommand(name=name, attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String")]) for name in unique]
        return UMLCommandResponse(
            action="generate_system",
            classes=classes,
            relations=[],
            explanation=f"Entidades generadas: {', '.join(unique)}.",
            source="nlu_heuristic"
        )

    return UMLCommandResponse(
        action="create_class",
        classes=[UMLClassCommand(name="NuevaClase", attributes=[UMLAttribute(name="id", type="Long"), UMLAttribute(name="nombre", type="String")])],
        explanation="Se ha creado una nueva clase.",
        source="nlu_heuristic"
    )
