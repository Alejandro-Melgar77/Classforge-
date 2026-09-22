class InAppNotificationModel {
  final String id;
  final String title;
  final String message;
  final String type; // diagram_modified | backend_generated | team_member_added | diagram_completed
  final DateTime timestamp;
  final String? diagramId;
  final String? projectId;
  bool isRead;

  InAppNotificationModel({
    required this.id,
    required this.title,
    required this.message,
    required this.type,
    required this.timestamp,
    this.diagramId,
    this.projectId,
    this.isRead = false,
  });

  factory InAppNotificationModel.fromJson(Map<String, dynamic> json) {
    return InAppNotificationModel(
      id: json['id'] ?? DateTime.now().millisecondsSinceEpoch.toString(),
      title: json['title'] ?? 'Notificación',
      message: json['message'] ?? '',
      type: json['type'] ?? 'info',
      timestamp: json['timestamp'] != null 
          ? DateTime.tryParse(json['timestamp']) ?? DateTime.now()
          : DateTime.now(),
      diagramId: json['diagram_id'],
      projectId: json['project_id'],
      isRead: json['is_read'] ?? false,
    );
  }

  String get typeIcon {
    switch (type) {
      case 'diagram_modified':
        return '✏️';
      case 'backend_generated':
        return '💻';
      case 'team_member_added':
        return '👥';
      case 'diagram_completed':
        return '✅';
      default:
        return '🔔';
    }
  }
}
