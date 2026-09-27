import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/services/api_service.dart';
import '../../core/services/push_notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/project_model.dart';
import '../../models/team_model.dart';
import '../../models/user_model.dart';
import '../diagrams/diagram_viewer_screen.dart';

class DashboardScreen extends StatefulWidget {
  final Function(int)? onNavigateTab;

  const DashboardScreen({Key? key, this.onNavigateTab}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final ApiService _apiService = ApiService();
  DashboardStatsModel? _stats;
  List<ProjectModel> _recentProjects = [];
  List<TeamModel> _teams = [];
  List<UserModel> _users = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final stats = await _apiService.getDashboardStats();
    final projects = await _apiService.getProjects();
    final teams = await _apiService.getTeams();
    final users = await _apiService.getUsers();

    if (mounted) {
      setState(() {
        _stats = stats;
        _recentProjects = projects.take(4).toList();
        _teams = teams;
        _users = users;
        _isLoading = false;
      });
    }
  }

  String _getGreeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Buenos días';
    if (hour < 19) return 'Buenas tardes';
    return 'Buenas noches';
  }

  @override
  Widget build(BuildContext context) {
    final user = _apiService.currentUser;
    final userName = user?.fullName ?? user?.name ?? 'Ing. Alejandro Melgar';
    final push = Provider.of<PushNotificationService>(context, listen: false);

    return Scaffold(
      backgroundColor: AppTheme.surface1,
      body: RefreshIndicator(
        onRefresh: _loadData,
        color: AppTheme.primary,
        backgroundColor: AppTheme.surface2,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
            : ListView(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
                children: [
                  // Encabezado Formal Ejecutivo
                  Container(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      color: AppTheme.surface2,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppTheme.border),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${_getGreeting()},',
                                  style: GoogleFonts.inter(
                                    fontSize: 13,
                                    color: AppTheme.textSecondary,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  userName,
                                  style: GoogleFonts.inter(
                                    fontSize: 19,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.textPrimary,
                                  ),
                                ),
                              ],
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                              decoration: BoxDecoration(
                                color: AppTheme.primary.withOpacity(0.18),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: AppTheme.primary.withOpacity(0.35)),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    width: 7,
                                    height: 7,
                                    decoration: const BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: Color(0xFF10B981),
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    user?.role.toUpperCase() ?? 'ADMIN',
                                    style: GoogleFonts.inter(
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                      color: AppTheme.primaryLight,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            const Icon(Icons.security, size: 14, color: Color(0xFF10B981)),
                            const SizedBox(width: 6),
                            Text(
                              'Sesión Corporativa Activa • ClassForge Studio',
                              style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textMuted),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Acceso Directo al Lienzo Conceptual UML
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          AppTheme.primary.withOpacity(0.25),
                          const Color(0xFF0F172A),
                        ],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppTheme.primary.withOpacity(0.4)),
                    ),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppTheme.primary,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(Icons.account_tree_outlined, color: Colors.white, size: 28),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Lienzo Conceptual Bancario',
                                style: GoogleFonts.inter(
                                  fontSize: 15,
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.textPrimary,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                'Visor interactivo 60 FPS con zoom, clases y relaciones.',
                                style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textSecondary),
                              ),
                            ],
                          ),
                        ),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primary,
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          onPressed: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => const DiagramViewerScreen(
                                  diagramId: 'diag-01',
                                  initialName: 'Diagrama Conceptual Bancario',
                                ),
                              ),
                            );
                          },
                          child: const Text('Abrir', style: TextStyle(fontSize: 12)),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Métricas KPIs (4 Tarjetas)
                  Row(
                    children: [
                      Expanded(
                        child: _buildKpiCard(
                          title: 'Proyectos',
                          count: '${_stats?.totalProjects ?? 8}',
                          subtitle: '${_stats?.activeProjects ?? 5} en progreso',
                          icon: Icons.folder_outlined,
                          color: AppTheme.primaryLight,
                          onTap: () => widget.onNavigateTab?.call(1),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _buildKpiCard(
                          title: 'Diagramas UML',
                          count: '14',
                          subtitle: 'Sincronizados',
                          icon: Icons.schema_outlined,
                          color: AppTheme.accent,
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => const DiagramViewerScreen(diagramId: 'diag-01'),
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: _buildKpiCard(
                          title: 'Equipos Scrum',
                          count: '${_teams.length}',
                          subtitle: 'Asignados',
                          icon: Icons.groups_outlined,
                          color: const Color(0xFF10B981),
                          onTap: () => widget.onNavigateTab?.call(2),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _buildKpiCard(
                          title: 'Ingenieros',
                          count: '${_users.length}',
                          subtitle: 'Activos',
                          icon: Icons.person_outline,
                          color: const Color(0xFFF59E0B),
                          onTap: () => widget.onNavigateTab?.call(3),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),

                  // Sección: Proyectos Recientes
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Repertorio de Proyectos Recientes',
                        style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                      TextButton(
                        onPressed: () => widget.onNavigateTab?.call(1),
                        child: const Text('Ver Todos →', style: TextStyle(fontSize: 12)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ..._recentProjects.map((project) => _buildProjectCard(project)),
                  const SizedBox(height: 20),

                  // Sección: Notificación en Barra del Teléfono
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: AppTheme.surface2,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: AppTheme.border),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.notifications_active_outlined, color: AppTheme.accent, size: 22),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Probar Alerta en Barra de Android',
                                style: GoogleFonts.inter(
                                  fontSize: 13,
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.textPrimary,
                                ),
                              ),
                              Text(
                                'Genera un evento push directamente en la barra superior del celular.',
                                style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textMuted),
                              ),
                            ],
                          ),
                        ),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.surface3,
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                          ),
                          onPressed: () {
                            push.triggerInstantPush(
                              title: '🚀 ClassForge • Notificación de Sistema',
                              message: 'Código Spring Boot 3 generado y sincronizado con éxito.',
                              type: 'backend_generated',
                              diagramId: 'diag-01',
                            );
                          },
                          child: const Text('Probar', style: TextStyle(fontSize: 11, color: AppTheme.primaryLight)),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
              ),
      ),
    );
  }

  Widget _buildKpiCard({
    required String title,
    required String count,
    required String subtitle,
    required IconData icon,
    required Color color,
    VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.surface2,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppTheme.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  title,
                  style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary),
                ),
                Icon(icon, color: color, size: 18),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              count,
              style: GoogleFonts.inter(fontSize: 22, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textMuted),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProjectCard(ProjectModel project) {
    Color statusColor = const Color(0xFF10B981);
    String statusLabel = 'En Progreso';
    if (project.status == 'completed') {
      statusColor = AppTheme.primaryLight;
      statusLabel = 'Completado';
    } else if (project.status == 'review') {
      statusColor = const Color(0xFFF59E0B);
      statusLabel = 'En Revisión';
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      color: AppTheme.surface2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppTheme.border),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    project.name,
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: statusColor.withOpacity(0.3)),
                  ),
                  child: Text(
                    statusLabel,
                    style: GoogleFonts.inter(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: statusColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              project.description,
              style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  project.teamName ?? 'Equipo Core',
                  style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textMuted),
                ),
                TextButton.icon(
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  ),
                  icon: const Icon(Icons.remove_red_eye, size: 14, color: AppTheme.primaryLight),
                  label: const Text('Ver Diagrama', style: TextStyle(fontSize: 11, color: AppTheme.primaryLight)),
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const DiagramViewerScreen(
                          diagramId: 'diag-01',
                          initialName: 'Diagrama Conceptual Bancario',
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
