class ProjectModel {
  final String id;
  final String name;
  final String description;
  final String status; // in_progress | completed | review | archived
  final String type; // personal | team
  final String? teamId;
  final String? teamName;
  final String createdBy;
  final DateTime createdAt;

  ProjectModel({
    required this.id,
    required this.name,
    required this.description,
    required this.status,
    required this.type,
    this.teamId,
    this.teamName,
    required this.createdBy,
    required this.createdAt,
  });

  factory ProjectModel.fromJson(Map<String, dynamic> json) {
    return ProjectModel(
      id: json['id'] ?? json['_id'] ?? '',
      name: json['name'] ?? 'Sin título',
      description: json['description'] ?? '',
      status: json['status'] ?? 'in_progress',
      type: json['type'] ?? 'personal',
      teamId: json['team_id'],
      teamName: json['team_name'],
      createdBy: json['created_by'] ?? '',
      createdAt: json['created_at'] != null 
          ? DateTime.tryParse(json['created_at']) ?? DateTime.now() 
          : DateTime.now(),
    );
  }
}

class DashboardStatsModel {
  final int totalProjects;
  final int activeProjects;
  final int completedProjects;
  final int totalTeams;
  final List<ProjectModel> recentProjects;

  DashboardStatsModel({
    required this.totalProjects,
    required this.activeProjects,
    required this.completedProjects,
    required this.totalTeams,
    required this.recentProjects,
  });

  factory DashboardStatsModel.fromJson(Map<String, dynamic> json) {
    var rawRecent = json['recent_projects'] as List<dynamic>? ?? [];
    return DashboardStatsModel(
      totalProjects: json['total_projects'] ?? 0,
      activeProjects: json['active_projects'] ?? 0,
      completedProjects: json['completed_projects'] ?? 0,
      totalTeams: json['total_teams'] ?? 0,
      recentProjects: rawRecent.map((p) => ProjectModel.fromJson(p)).toList(),
    );
  }
}
