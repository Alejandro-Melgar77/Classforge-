class TeamModel {
  final String id;
  final String name;
  final String description;
  final String scrumMasterName;
  final String scrumMasterEmail;
  final int membersCount;
  final List<String> memberNames;
  final int activeProjectsCount;
  final DateTime createdAt;

  TeamModel({
    required this.id,
    required this.name,
    required this.description,
    required this.scrumMasterName,
    required this.scrumMasterEmail,
    required this.membersCount,
    required this.memberNames,
    required this.activeProjectsCount,
    required this.createdAt,
  });

  factory TeamModel.fromJson(Map<String, dynamic> json) {
    return TeamModel(
      id: json['id'] ?? json['_id'] ?? '',
      name: json['name'] ?? 'Equipo',
      description: json['description'] ?? '',
      scrumMasterName: json['scrum_master_name'] ?? 'Scrum Master',
      scrumMasterEmail: json['scrum_master_email'] ?? '',
      membersCount: json['members_count'] ?? (json['member_ids'] as List?)?.length ?? 1,
      memberNames: (json['member_names'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      activeProjectsCount: json['active_projects_count'] ?? 1,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at']) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}
