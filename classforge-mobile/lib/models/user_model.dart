class UserModel {
  final String id;
  final String name;
  final String email;
  final String role; // admin | scrum_master | dev
  final String? avatarUrl;
  final List<String> teamIds;

  UserModel({
    required this.id,
    required this.name,
    required this.email,
    required this.role,
    this.avatarUrl,
    this.teamIds = const [],
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    List<String> parsedTeamIds = [];
    if (json['team_ids'] is List) {
      parsedTeamIds = (json['team_ids'] as List).map((e) => e.toString()).toList();
    } else if (json['team_ids'] is String && (json['team_ids'] as String).isNotEmpty) {
      parsedTeamIds = (json['team_ids'] as String).split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    }

    return UserModel(
      id: json['id'] ?? json['_id'] ?? '',
      name: json['name'] ?? '',
      email: json['email'] ?? '',
      role: json['role'] ?? 'dev',
      avatarUrl: json['avatar_url'],
      teamIds: parsedTeamIds,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'role': role,
      'avatar_url': avatarUrl,
      'team_ids': teamIds,
    };
  }

  String get fullName => name;

  String get roleLabel {
    switch (role) {
      case 'admin':
        return 'Administrador';
      case 'scrum_master':
        return 'Scrum Master';
      case 'dev':
        return 'Desarrollador';
      default:
        return role;
    }
  }
}
