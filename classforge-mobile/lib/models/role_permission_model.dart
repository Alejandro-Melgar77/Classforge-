import 'package:flutter/material.dart';

class PermissionItem {
  final String title;
  final String description;
  final bool admin;
  final bool scrumMaster;
  final bool dev;
  final IconData icon;

  const PermissionItem({
    required this.title,
    required this.description,
    required this.admin,
    required this.scrumMaster,
    required this.dev,
    required this.icon,
  });
}

class RolePermissionData {
  static const List<PermissionItem> permissions = [
    PermissionItem(
      title: 'Creación de Proyectos',
      description: 'Crear nuevos proyectos con premisas arquitectónicas y asignación de equipos.',
      admin: true,
      scrumMaster: true,
      dev: false,
      icon: Icons.create_new_folder_outlined,
    ),
    PermissionItem(
      title: 'Eliminación de Proyectos',
      description: 'Eliminar proyectos y su histórico de diagramas del repositorio central.',
      admin: true,
      scrumMaster: false,
      dev: false,
      icon: Icons.delete_forever_outlined,
    ),
    PermissionItem(
      title: 'Edición Colaborativa de Diagramas',
      description: 'Crear, mutar nodos, clases, atributos, métodos y relaciones en el lienzo UML.',
      admin: true,
      scrumMaster: true,
      dev: true,
      icon: Icons.hub_outlined,
    ),
    PermissionItem(
      title: 'Asistente de IA por Voz y Gemini Vision',
      description: 'Dictar prompts por micrófono y digitalizar diagramas mediante fotos de cámara/galería.',
      admin: true,
      scrumMaster: true,
      dev: true,
      icon: Icons.mic_none_outlined,
    ),
    PermissionItem(
      title: 'Generación de Backend Spring Boot 3',
      description: 'Compilar y descargar el proyecto .ZIP Clean Architecture listo para Postman.',
      admin: true,
      scrumMaster: true,
      dev: true,
      icon: Icons.integration_instructions_outlined,
    ),
    PermissionItem(
      title: 'Gestión de Equipos y Células Scrum',
      description: 'Crear equipos, asignar Scrum Masters y distribuir desarrolladores.',
      admin: true,
      scrumMaster: false,
      dev: false,
      icon: Icons.groups_outlined,
    ),
    PermissionItem(
      title: 'Asignación de Participantes en Diagramas',
      description: 'Invitar y autorizar desarrolladores a salas de diagramas específicos.',
      admin: true,
      scrumMaster: true,
      dev: false,
      icon: Icons.person_add_alt_outlined,
    ),
    PermissionItem(
      title: 'Administración de Usuarios y Roles',
      description: 'Dar de alta usuarios, revocar accesos y cambiar roles de seguridad.',
      admin: true,
      scrumMaster: false,
      dev: false,
      icon: Icons.admin_panel_settings_outlined,
    ),
    PermissionItem(
      title: 'Auditoría y Trazabilidad de Sesiones',
      description: 'Visualizar logs de auditoría, sesiones activas e IP de conexión.',
      admin: true,
      scrumMaster: false,
      dev: false,
      icon: Icons.policy_outlined,
    ),
    PermissionItem(
      title: 'Buzón y Alertas Push de Sistema',
      description: 'Recibir notificaciones nativas en el teléfono ante cambios de proyectos partícipes.',
      admin: true,
      scrumMaster: true,
      dev: true,
      icon: Icons.notifications_active_outlined,
    ),
  ];

  static String getRoleDisplayName(String role) {
    switch (role.toLowerCase()) {
      case 'admin':
        return 'Administrador del Sistema';
      case 'scrum_master':
        return 'Scrum Master / Tech Lead';
      case 'dev':
      default:
        return 'Desarrollador de Software';
    }
  }

  static Color getRoleBadgeColor(String role) {
    switch (role.toLowerCase()) {
      case 'admin':
        return const Color(0xFFEF4444);
      case 'scrum_master':
        return const Color(0xFFF59E0B);
      case 'dev':
      default:
        return const Color(0xFF3B82F6);
    }
  }
}
