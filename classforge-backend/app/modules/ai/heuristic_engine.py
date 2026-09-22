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
    if any(k in n for k in ['precio', 'total', 'monto', 'saldo', 'costo', 'descuento', 'subtotal', 'sueldo', 'salario']): return 'Double'
    if any(k in n for k in ['stock', 'cantidad', 'edad', 'numero', 'nro', 'orden', 'anio', 'puntos', 'intentos']): return 'Integer'
    if any(k in n for k in ['fecha', 'created', 'updated', 'date', 'nacimiento']): return 'Date'
    if n.startswith('es') or n.startswith('is') or any(k in n for k in ['activo', 'habilitado', 'bloqueado', 'valido']): return 'Boolean'
    return 'String'

def normalize_type(t: str) -> str:
    t_clean = t.lower().strip()
    if t_clean in ['int', 'integer', 'entero']: return 'Integer'
    if t_clean in ['long', 'bigint']: return 'Long'
    if t_clean in ['float', 'flotante']: return 'Float'
    if t_clean in ['double', 'decimal', 'number']: return 'Double'
    if t_clean in ['bool', 'boolean', 'booleano']: return 'Boolean'
    if t_clean in ['date', 'datetime', 'fecha', 'timestamp']: return 'Date'
    if t_clean in ['void', 'vacio']: return 'void'
    return 'String'

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
        if token.startswith(('+', '-', '#')):
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
        if attr_name:
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
    # Example: "crea una tabla con el nombre Producto con 3 atributos de nombres precio, stock, codigo y que se asocie a Categoria con la cardinalidad 1..*"
    complex_pattern = re.compile(
        r"(?:crea(?:r)?|nueva?|generar?)\s+(?:una?\s+)?(?:tabla|clase|entidad|modelo)\s+"
        r"(?:con\s+el\s+nombre\s+|llamada\s+|de\s+nombre\s+)?([a-zA-Z0-9_]+)"
        r"(?:\s+con\s+(?:(?:\d+|varios|los)\s+)?atributos(?:\s+(?:de\s+nombres?|llamados?|:))?\s+(.+?))?"
        r"(?:\s+(?:y\s+)?(?:que\s+)?(?:se\s+)?(?:asocie|relacione|conecte|vincule)\s+(?:a|con)\s+([a-zA-Z0-9_]+)"
        r"(?:\s+con\s+(?:la\s+)?cardinalidad\s+([^\s,;]+(?:\s+(?:a|..)\s+[^\s,;]+)?))?)?$",
        re.IGNORECASE
    )
    m = complex_pattern.search(norm)
    if m:
        class_name = capitalize_name(m.group(1))
        attrs_str = m.group(2)
        target_class = capitalize_name(m.group(3)) if m.group(3) else None
        cardinality_str = m.group(4)

        attributes = parse_attributes_list(attrs_str)
        if not attributes:
            attributes = [UMLAttribute(name="id", type="Long", visibility="+")]

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
                attributes=[UMLAttribute(name="id", type="Long", visibility="+")]
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

    # 2. Simple Create Class / Table / Entity / Interface / Enum
    stereotype = None
    if "clase abstracta" in norm or "abstract class" in norm: stereotype = "abstract"
    elif "interfaz" in norm or "interface" in norm: stereotype = "interface"
    elif "enum" in norm or "enumeracion" in norm: stereotype = "enum"

    create_pattern = re.compile(
        r"(?:crear?|nueva?|generar?|agregar?)\s+(?:una?\s+)?(?:clase\s+abstracta|interfaz|interface|enum(?:eracion)?|tabla|clase|entidad|modelo)\s+"
        r"(?:con\s+el\s+nombre\s+|llamada\s+|de\s+nombre\s+)?([a-zA-Z0-9_]+)(?:\s+(?:con\s+(?:los\s+)?(?:atributos|campos|valores))\s+(.+))?",
        re.IGNORECASE
    )
    m = create_pattern.search(norm)
    if m:
        class_name = capitalize_name(m.group(1))
        raw_attrs = m.group(2)
        attributes = parse_attributes_list(raw_attrs)
        if not attributes:
            attributes = [UMLAttribute(name="id", type="Long", visibility="+")]

        return UMLCommandResponse(
            action="create_class",
            classes=[UMLClassCommand(name=class_name, stereotype=stereotype, attributes=attributes)],
            explanation=f"Clase '{class_name}' creada por heurística.",
            source="nlu_heuristic"
        )

    # 3. Add Attribute: "agregar atributo edad int a la clase Usuario"
    add_attr_pattern = re.compile(
        r"(?:agregar?|anadir?|incorporar?|crear?)\s+(?:el\s+)?(?:atributo|campo)\s+([a-zA-Z0-9_]+)(?:\s*:?\s*([a-zA-Z0-9_]+))?\s+(?:a|en)\s+(?:la\s+)?(?:clase|tabla|entidad)?\s*([a-zA-Z0-9_]+)",
        re.IGNORECASE
    )
    m = add_attr_pattern.search(norm)
    if m:
        attr_name = m.group(1)
        explicit_type = m.group(2)
        class_name = capitalize_name(m.group(3))
        attr_type = normalize_type(explicit_type) if explicit_type else infer_type_from_name(attr_name)

        return UMLCommandResponse(
            action="add_attribute",
            classes=[UMLClassCommand(name=class_name, attributes=[UMLAttribute(name=attr_name, type=attr_type, visibility="+")])],
            explanation=f"Atributo {attr_name}: {attr_type} agregado a {class_name}.",
            source="nlu_heuristic"
        )

    # 4. Add Method: "agregar metodo calcularTotal(descuento: float): double a Factura"
    add_method_pattern = re.compile(
        r"(?:agregar?|anadir?|crear?)\s+(?:el\s+)?metodo\s+([a-zA-Z0-9_]+)(?:\s*\(([^)]*)\))?(?:\s*:?\s*([a-zA-Z0-9_]+))?\s+(?:a|en)\s+(?:la\s+)?(?:clase|tabla|entidad)?\s*([a-zA-Z0-9_]+)",
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

    # 6. Relate: "relacionar Usuario con Pedido asociacion con cardinalidad 1 a *"
    rel_pattern = re.compile(
        r"(?:crear?\s+(?:relacion|asociacion|composicion|agregacion|dependencia|herencia)\s+(?:entre|de)\s+|relacionar?\s+|asociar?\s+|conectar?\s+)"
        r"([a-zA-Z0-9_]+)\s+(?:con|y|a)\s+([a-zA-Z0-9_]+)(?:\s+(?:como|por|tipo)?\s*(herencia|composicion|agregacion|dependencia|asociacion|realizacion))?"
        r"(?:\s+(?:con\s+(?:la\s+)?cardinalidad\s+)?([0-9*..a-zA-Z_]+(?:\s+(?:a|..)\s+[0-9*..a-zA-Z_]+)?))?",
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
    del_pattern = re.compile(r"(?:eliminar?|borrar?|quitar?)\s+(?:la\s+)?(?:clase|tabla|entidad|elemento)\s+([a-zA-Z0-9_]+)", re.IGNORECASE)
    m = del_pattern.search(norm)
    if m:
        class_name = capitalize_name(m.group(1))
        return UMLCommandResponse(
            action="delete_element",
            deleted_elements=[class_name],
            explanation=f"Elemento {class_name} eliminado.",
            source="nlu_heuristic"
        )

    return None

