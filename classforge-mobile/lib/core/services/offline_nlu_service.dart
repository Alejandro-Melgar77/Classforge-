class UMLAttributeNlu {
  final String name;
  final String type;
  final String visibility;

  UMLAttributeNlu({
    required this.name,
    required this.type,
    this.visibility = 'public',
  });

  Map<String, dynamic> toJson() => {
        'name': name,
        'type': type,
        'visibility': visibility,
      };
}

class UMLMethodNlu {
  final String name;
  final String params;
  final String returnType;
  final String visibility;

  UMLMethodNlu({
    required this.name,
    this.params = '()',
    this.returnType = 'void',
    this.visibility = 'public',
  });

  Map<String, dynamic> toJson() => {
        'name': name,
        'params': params,
        'return_type': returnType,
        'visibility': visibility,
      };
}

class UMLClassNlu {
  final String name;
  final String type; // class | interface | abstract | enum
  final List<UMLAttributeNlu> attributes;
  final List<UMLMethodNlu> methods;

  UMLClassNlu({
    required this.name,
    this.type = 'class',
    required this.attributes,
    required this.methods,
  });

  Map<String, dynamic> toJson() => {
        'name': name,
        'type': type,
        'attributes': attributes.map((a) => a.toJson()).toList(),
        'methods': methods.map((m) => m.toJson()).toList(),
      };
}

class UMLRelationNlu {
  final String source;
  final String target;
  final String type; // inheritance | composition | aggregation | association | dependency

  UMLRelationNlu({
    required this.source,
    required this.target,
    required this.type,
  });

  Map<String, dynamic> toJson() => {
        'source': source,
        'target': target,
        'type': type,
      };
}

class NluResult {
  final String action; // create_class | update_class | add_relation | delete_element | query_class | query_summary | unknown
  final List<UMLClassNlu> classes;
  final List<UMLRelationNlu> relations;
  final List<String> deletedElements;
  final String? queryTarget;
  final String explanation;
  final String source;
  final double latencyMs;

  NluResult({
    required this.action,
    required this.classes,
    required this.relations,
    required this.deletedElements,
    this.queryTarget,
    required this.explanation,
    this.source = 'offline_dart_nlu',
    this.latencyMs = 0.5,
  });
}

class OfflineNluService {
  static final OfflineNluService _instance = OfflineNluService._internal();
  factory OfflineNluService() => _instance;
  OfflineNluService._internal();

  /// Procesa texto natural en <1ms sin internet ni modelo pesado (0MB memoria)
  NluResult parse(String input) {
    final stopwatch = Stopwatch()..start();
    final normalized = _normalize(input);

    String action = 'unknown';
    final List<UMLClassNlu> classes = [];
    final List<UMLRelationNlu> relations = [];
    final List<String> deletedElements = [];
    String? queryTarget;
    String explanation = '';

    // 1. Crear Clase (con o sin atributos)
    // Ej: "crear clase Usuario con atributos id:int, nombre:string"
    final createClassRegex = RegExp(
      r'(?:crear|crea|nueva)\s+clase\s+([a-zA-Z0-9_]+)(?:\s+con\s+(?:atributos|campos)\s+(.+))?',
      caseSensitive: false,
    );
    final createMatch = createClassRegex.firstMatch(normalized);

    if (createMatch != null) {
      action = 'create_class';
      final className = _capitalize(createMatch.group(1)!);
      final attrsStr = createMatch.group(2);
      final List<UMLAttributeNlu> attributes = [];

      if (attrsStr != null && attrsStr.isNotEmpty) {
        final parts = attrsStr.split(RegExp(r',|\s+y\s+'));
        for (final part in parts) {
          final trimmed = part.trim();
          if (trimmed.isNotEmpty) {
            final colParts = trimmed.split(':');
            final name = colParts[0].trim();
            final type = colParts.length > 1 ? colParts[1].trim() : 'String';
            attributes.add(UMLAttributeNlu(name: name, type: type));
          }
        }
      }

      classes.add(UMLClassNlu(
        name: className,
        attributes: attributes,
        methods: [],
      ));
      explanation = 'Clase $className creada${attributes.isNotEmpty ? ' con ${attributes.length} atributo(s)' : ''}.';
    }

    // 2. Eliminar Clase o Elemento
    if (action == 'unknown') {
      final deleteRegex = RegExp(
        r'(?:eliminar|borrar)\s+(?:clase|elemento)\s+([a-zA-Z0-9_]+)',
        caseSensitive: false,
      );
      final deleteMatch = deleteRegex.firstMatch(normalized);
      if (deleteMatch != null) {
        action = 'delete_element';
        final elemName = _capitalize(deleteMatch.group(1)!);
        deletedElements.add(elemName);
        explanation = 'Elemento $elemName eliminado del diagrama.';
      }
    }

    // 3. Agregar Atributo a Clase
    if (action == 'unknown') {
      final addAttrRegex = RegExp(
        r'(?:agregar|anadir|añadir)\s+(?:atributo|campo)\s+([a-zA-Z0-9_]+)(?:\s*:?\s*([a-zA-Z0-9_]+))?\s+a\s+(?:la\s+)?clase\s+([a-zA-Z0-9_]+)',
        caseSensitive: false,
      );
      final attrMatch = addAttrRegex.firstMatch(normalized);
      if (attrMatch != null) {
        action = 'update_class';
        final attrName = attrMatch.group(1)!;
        final attrType = attrMatch.group(2) ?? 'String';
        final className = _capitalize(attrMatch.group(3)!);

        classes.add(UMLClassNlu(
          name: className,
          attributes: [UMLAttributeNlu(name: attrName, type: attrType)],
          methods: [],
        ));
        explanation = 'Atributo $attrName: $attrType añadido a la clase $className.';
      }
    }

    // 4. Agregar Método a Clase
    if (action == 'unknown') {
      final addMethodRegex = RegExp(
        r'(?:agregar|anadir|añadir)\s+(?:metodo|método)\s+([a-zA-Z0-9_]+)\s*(?:\(([^)]*)\))?(?:\s*:?\s*([a-zA-Z0-9_]+))?\s+a\s+(?:la\s+)?clase\s+([a-zA-Z0-9_]+)',
        caseSensitive: false,
      );
      final methodMatch = addMethodRegex.firstMatch(normalized);
      if (methodMatch != null) {
        action = 'update_class';
        final methodName = methodMatch.group(1)!;
        final params = methodMatch.group(2) != null ? '(${methodMatch.group(2)})' : '()';
        final returnType = methodMatch.group(3) ?? 'void';
        final className = _capitalize(methodMatch.group(4)!);

        classes.add(UMLClassNlu(
          name: className,
          attributes: [],
          methods: [
            UMLMethodNlu(
              name: methodName,
              params: params,
              returnType: returnType,
            )
          ],
        ));
        explanation = 'Método $methodName$params: $returnType añadido a la clase $className.';
      }
    }

    // 5. Relaciones Directas
    if (action == 'unknown') {
      final relateRegex = RegExp(
        r'(?:relacionar|conectar)\s+([a-zA-Z0-9_]+)\s+con\s+([a-zA-Z0-9_]+)\s+(?:por|como)\s+(herencia|composicion|composición|agregacion|agregación|asociacion|asociación|dependencia)',
        caseSensitive: false,
      );
      final relateMatch = relateRegex.firstMatch(normalized);
      if (relateMatch != null) {
        action = 'add_relation';
        final source = _capitalize(relateMatch.group(1)!);
        final target = _capitalize(relateMatch.group(2)!);
        final relType = _normalizeRelationType(relateMatch.group(3)!);

        relations.add(UMLRelationNlu(
          source: source,
          target: target,
          type: relType,
        ));
        explanation = 'Relación de $relType creada entre $source y $target.';
      }
    }

    // 6. Herencia Caso Especial
    if (action == 'unknown') {
      final inheritRegex = RegExp(
        r'(?:hacer\s+que\s+)?([a-zA-Z0-9_]+)\s+herede\s+de\s+([a-zA-Z0-9_]+)',
        caseSensitive: false,
      );
      final inheritMatch = inheritRegex.firstMatch(normalized);
      if (inheritMatch != null) {
        action = 'add_relation';
        final source = _capitalize(inheritMatch.group(1)!);
        final target = _capitalize(inheritMatch.group(2)!);

        relations.add(UMLRelationNlu(
          source: source,
          target: target,
          type: 'inheritance',
        ));
        explanation = '$source ahora hereda de $target (herencia).';
      }
    }

    // 7. Consultas / Inquiries para el Asistente Readonly de Móvil
    if (action == 'unknown') {
      final searchRegex = RegExp(
        r'(?:buscar|mostrar|ver|inspeccionar)\s+(?:la\s+)?clase\s+([a-zA-Z0-9_]+)',
        caseSensitive: false,
      );
      final searchMatch = searchRegex.firstMatch(normalized);
      if (searchMatch != null) {
        action = 'query_class';
        queryTarget = _capitalize(searchMatch.group(1)!);
        explanation = 'Buscando detalles de la clase $queryTarget en el diagrama.';
      }
    }

    if (action == 'unknown') {
      final summaryRegex = RegExp(
        r'(?:resumen|cuantas\s+clases|cuántas\s+clases|contar\s+clases|analizar\s+diagrama)',
        caseSensitive: false,
      );
      if (summaryRegex.hasMatch(normalized)) {
        action = 'query_summary';
        explanation = 'Generando métricas y resumen estructural del diagrama.';
      }
    }

    stopwatch.stop();
    final latency = stopwatch.elapsedMicroseconds / 1000.0;

    if (action == 'unknown') {
      explanation = 'No se reconoció el comando. Intenta: "crear clase Producto", "buscar clase Usuario", o "relacionar Pedido con Cliente".';
    }

    return NluResult(
      action: action,
      classes: classes,
      relations: relations,
      deletedElements: deletedElements,
      queryTarget: queryTarget,
      explanation: explanation,
      latencyMs: latency < 0.1 ? 0.1 : latency,
    );
  }

  String _normalize(String str) {
    String withoutAccents = str
        .replaceAll('á', 'a')
        .replaceAll('é', 'e')
        .replaceAll('í', 'i')
        .replaceAll('ó', 'o')
        .replaceAll('ú', 'u')
        .replaceAll('Á', 'A')
        .replaceAll('É', 'E')
        .replaceAll('Í', 'I')
        .replaceAll('Ó', 'O')
        .replaceAll('Ú', 'U')
        .replaceAll('ñ', 'n')
        .replaceAll('Ñ', 'N');
    return withoutAccents.toLowerCase().trim();
  }

  String _capitalize(String str) {
    if (str.isEmpty) return '';
    return str[0].toUpperCase() + str.substring(1);
  }

  String _normalizeRelationType(String type) {
    final lower = _normalize(type);
    if (lower.contains('herenc')) return 'inheritance';
    if (lower.contains('compos')) return 'composition';
    if (lower.contains('agreg')) return 'aggregation';
    if (lower.contains('depend')) return 'dependency';
    return 'association';
  }
}
