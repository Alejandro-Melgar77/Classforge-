class InAppNotificationModel {
  final String id;
  final String title;
  final String message;
  final String type; // project_update | diagram_update | ai_update | codegen | team_update | info
  final DateTime timestamp;
  final String? diagramId;
  final String? projectId;
  bool isRead;
  final Map<String, dynamic>? meta;

  InAppNotificationModel({
    required this.id,
    required this.title,
    required this.message,
    required this.type,
    required this.timestamp,
    this.diagramId,
    this.projectId,
    this.isRead = false,
    this.meta,
  });

  factory InAppNotificationModel.fromJson(Map<String, dynamic> json) {
    DateTime parsedTime = DateTime.now();
    final rawDate = json['created_at'] ?? json['timestamp'];
    if (rawDate != null) {
      if (rawDate is String) {
        parsedTime = DateTime.tryParse(rawDate) ?? DateTime.now();
      } else if (rawDate is DateTime) {
        parsedTime = rawDate;
      }
    }

    return InAppNotificationModel(
      id: json['id'] ?? json['_id'] ?? DateTime.now().millisecondsSinceEpoch.toString(),
      title: json['title'] ?? 'Notificación ClassForge',
      message: json['message'] ?? '',
      type: json['type'] ?? 'info',
      timestamp: parsedTime,
      diagramId: json['diagram_id']?.toString(),
      projectId: json['project_id']?.toString(),
      isRead: json['is_read'] ?? json['read'] ?? false,
      meta: json['meta'] is Map<String, dynamic> ? json['meta'] : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'message': message,
      'type': type,
      'timestamp': timestamp.toIso8601String(),
      'diagram_id': diagramId,
      'project_id': projectId,
      'is_read': isRead,
      'meta': meta,
    };
  }

  String get typeIcon {
    switch (type) {
      case 'project_update':
        return '📁';
      case 'diagram_update':
      case 'diagram_modified':
        return '✏️';
      case 'ai_update':
        return '🤖';
      case 'codegen':
      case 'backend_generated':
        return '⚡';
      case 'team_update':
      case 'team_member_added':
        return '👥';
      case 'diagram_completed':
        return '✅';
      default:
        return '🔔';
    }
  }
}
