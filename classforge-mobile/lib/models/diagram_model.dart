class UMLAttributeModel {
  final String visibility; // +, -, #, ~
  final String name;
  final String type;

  UMLAttributeModel({
    required this.visibility,
    required this.name,
    required this.type,
  });

  factory UMLAttributeModel.fromJson(dynamic json) {
    if (json is String) {
      String clean = json.trim();
      String vis = '+';
      if (clean.startsWith('+') || clean.startsWith('-') || clean.startsWith('#') || clean.startsWith('~')) {
        vis = clean[0];
        clean = clean.substring(1).trim();
      }
      List<String> parts = clean.split(':');
      return UMLAttributeModel(
        visibility: vis,
        name: parts[0].trim(),
        type: parts.length > 1 ? parts[1].trim() : 'String',
      );
    }
    return UMLAttributeModel(
      visibility: json['visibility'] ?? '+',
      name: json['name'] ?? '',
      type: json['type'] ?? 'String',
    );
  }
}

class UMLMethodModel {
  final String visibility;
  final String name;
  final String params;
  final String returnType;

  UMLMethodModel({
    required this.visibility,
    required this.name,
    required this.params,
    required this.returnType,
  });

  factory UMLMethodModel.fromJson(dynamic json) {
    if (json is String) {
      String clean = json.trim();
      String vis = '+';
      if (clean.startsWith('+') || clean.startsWith('-') || clean.startsWith('#') || clean.startsWith('~')) {
        vis = clean[0];
        clean = clean.substring(1).trim();
      }
      return UMLMethodModel(
        visibility: vis,
        name: clean,
        params: '()',
        returnType: 'void',
      );
    }
    return UMLMethodModel(
      visibility: json['visibility'] ?? '+',
      name: json['name'] ?? '',
      params: json['params'] ?? '()',
      returnType: json['return_type'] ?? 'void',
    );
  }
}

class DiagramNodeModel {
  final String id;
  final String type; // class | interface | abstract | enum
  final String name;
  final String? stereotype;
  final List<UMLAttributeModel> attributes;
  final List<UMLMethodModel> methods;
  final double x;
  final double y;
  final double width;
  final double height;

  DiagramNodeModel({
    required this.id,
    required this.type,
    required this.name,
    this.stereotype,
    required this.attributes,
    required this.methods,
    required this.x,
    required this.y,
    this.width = 180,
    this.height = 140,
  });

  factory DiagramNodeModel.fromJson(Map<String, dynamic> json) {
    var data = json['data'] as Map<String, dynamic>? ?? {};
    var pos = json['position'] as Map<String, dynamic>? ?? {};
    var size = json['size'] as Map<String, dynamic>? ?? {};

    var rawAttrs = data['attributes'] as List<dynamic>? ?? [];
    var rawMethods = data['methods'] as List<dynamic>? ?? [];

    return DiagramNodeModel(
      id: json['id']?.toString() ?? '',
      type: (json['type'] ?? json['shape'] ?? 'class').toString().replaceAll('uml-', ''),
      name: data['name'] ?? json['label'] ?? 'Clase',
      stereotype: data['stereotype'],
      attributes: rawAttrs.map((a) => UMLAttributeModel.fromJson(a)).toList(),
      methods: rawMethods.map((m) => UMLMethodModel.fromJson(m)).toList(),
      x: (pos['x'] as num?)?.toDouble() ?? (json['x'] as num?)?.toDouble() ?? 50.0,
      y: (pos['y'] as num?)?.toDouble() ?? (json['y'] as num?)?.toDouble() ?? 50.0,
      width: (size['width'] as num?)?.toDouble() ?? (json['width'] as num?)?.toDouble() ?? 180.0,
      height: (size['height'] as num?)?.toDouble() ?? (json['height'] as num?)?.toDouble() ?? 140.0,
    );
  }
}

class DiagramEdgeModel {
  final String id;
  final String type; // inheritance | composition | aggregation | association
  final String sourceId;
  final String targetId;
  final String? label;

  DiagramEdgeModel({
    required this.id,
    required this.type,
    required this.sourceId,
    required this.targetId,
    this.label,
  });

  factory DiagramEdgeModel.fromJson(Map<String, dynamic> json) {
    dynamic s = json['source'];
    dynamic t = json['target'];

    String sId = s is Map ? (s['cell'] ?? '') : s.toString();
    String tId = t is Map ? (t['cell'] ?? '') : t.toString();

    return DiagramEdgeModel(
      id: json['id']?.toString() ?? '',
      type: (json['type'] ?? json['shape'] ?? 'association').toString().replaceAll('uml-', ''),
      sourceId: sId,
      targetId: tId,
      label: json['label'],
    );
  }
}

class DiagramModel {
  final String id;
  final String name;
  final String description;
  final String projectId;
  final String? teamId;
  final String status;
  final int version;
  final List<DiagramNodeModel> nodes;
  final List<DiagramEdgeModel> edges;

  DiagramModel({
    required this.id,
    required this.name,
    required this.description,
    required this.projectId,
    this.teamId,
    required this.status,
    required this.version,
    required this.nodes,
    required this.edges,
  });

  factory DiagramModel.fromJson(Map<String, dynamic> json) {
    var graphData = json['graph_data'] as Map<String, dynamic>? ?? {};
    var rawNodes = (graphData['nodes'] as List<dynamic>?) ?? (json['cells'] as List<dynamic>?) ?? [];
    var rawEdges = (graphData['edges'] as List<dynamic>?) ?? [];

    List<DiagramNodeModel> parsedNodes = [];
    List<DiagramEdgeModel> parsedEdges = [];

    for (var n in rawNodes) {
      if (n is Map<String, dynamic>) {
        String shape = (n['shape'] ?? n['type'] ?? '').toString();
        if (shape.contains('edge') || n.containsKey('source')) {
          parsedEdges.add(DiagramEdgeModel.fromJson(n));
        } else {
          parsedNodes.add(DiagramNodeModel.fromJson(n));
        }
      }
    }

    for (var e in rawEdges) {
      if (e is Map<String, dynamic>) {
        parsedEdges.add(DiagramEdgeModel.fromJson(e));
      }
    }

    return DiagramModel(
      id: json['id'] ?? json['_id'] ?? '',
      name: json['name'] ?? 'Diagrama UML',
      description: json['description'] ?? '',
      projectId: json['project_id'] ?? '',
      teamId: json['team_id'],
      status: json['status'] ?? 'draft',
      version: json['version'] ?? 1,
      nodes: parsedNodes,
      edges: parsedEdges,
    );
  }
}
