import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/services/api_service.dart';
import '../../core/services/websocket_service.dart';
import '../../core/theme/app_theme.dart';
import '../dashboard/dashboard_screen.dart';
import '../projects/projects_screen.dart';
import '../teams/teams_screen.dart';
import '../users/users_screen.dart';
import '../notifications/notifications_screen.dart';
import '../assistant/offline_assistant_screen.dart';
import '../auth/login_screen.dart';
import '../profile/profile_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  late final List<Widget> _screens;

  @override
  void initState() {
    super.initState();
    _screens = [
      DashboardScreen(onNavigateTab: (index) {
        setState(() => _currentIndex = index);
      }),
      const ProjectsScreen(),
      const TeamsScreen(),
      const UsersScreen(),
      const OfflineAssistantScreen(),
    ];
  }

  final List<String> _titles = [
    'ClassForge Studio',
    'Repertorio de Proyectos',
    'Equipos de Desarrollo Scrum',
    'Directorio de Usuarios',
    'Asistente de Modelado IA',
  ];

  void _handleLogout() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: AppTheme.surface2,
          title: Text(
            'Cerrar Sesión Corporativa',
            style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
          ),
          content: Text(
            '¿Deseas cerrar tu sesión actual de ClassForge Studio o configurar la conexión al servidor cloud?',
            style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancelar', style: TextStyle(color: AppTheme.textMuted)),
            ),
            OutlinedButton(
              style: OutlinedButton.styleFrom(side: const BorderSide(color: AppTheme.border)),
              onPressed: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => const LoginScreen()),
                );
              },
              child: const Text('Servidor Cloud', style: TextStyle(color: AppTheme.accent)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.danger),
              onPressed: () async {
                Navigator.pop(context);
                final ws = Provider.of<WebSocketService>(context, listen: false);
                ws.disconnect();
                await ApiService().logout();
                if (mounted) {
                  Navigator.pushReplacement(
                    context,
                    MaterialPageRoute(builder: (context) => const LoginScreen()),
                  );
                }
              },
              child: const Text('Cerrar Sesión'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final ws = Provider.of<WebSocketService>(context);
    final unreadCount = ws.unreadNotificationsCount;

    return Scaffold(
      backgroundColor: AppTheme.surface1,
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: AppTheme.primary,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.hub_outlined, color: Colors.white, size: 18),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                _titles[_currentIndex],
                style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        actions: [
          // Botón del Centro de Notificaciones Push
          IconButton(
            icon: Stack(
              clipBehavior: Clip.none,
              children: [
                const Icon(Icons.notifications_none, size: 22, color: AppTheme.textPrimary),
                if (unreadCount > 0)
                  Positioned(
                    top: -2,
                    right: -2,
                    child: Container(
                      padding: const EdgeInsets.all(2),
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppTheme.danger,
                      ),
                      constraints: const BoxConstraints(minWidth: 12, minHeight: 12),
                      child: Text(
                        unreadCount > 9 ? '9+' : '$unreadCount',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 8,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
              ],
            ),
            tooltip: 'Notificaciones Push',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const NotificationsScreen()),
              );
            },
          ),
          // Perfil y Ajustes
          IconButton(
            icon: const Icon(Icons.account_circle_outlined, size: 22, color: AppTheme.accentBlue),
            tooltip: 'Perfil & Ajustes',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const ProfileScreen()),
              );
            },
          ),
          // Menú de opciones de sesión
          IconButton(
            icon: const Icon(Icons.logout, size: 20, color: AppTheme.textSecondary),
            tooltip: 'Cerrar Sesión',
            onPressed: _handleLogout,
          ),
        ],
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() => _currentIndex = index);
        },
        type: BottomNavigationBarType.fixed,
        backgroundColor: AppTheme.surface2,
        selectedItemColor: AppTheme.primaryLight,
        unselectedItemColor: AppTheme.textMuted,
        selectedLabelStyle: GoogleFonts.inter(fontSize: 10, fontWeight: FontWeight.bold),
        unselectedLabelStyle: GoogleFonts.inter(fontSize: 10),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard_outlined),
            activeIcon: Icon(Icons.dashboard),
            label: 'Resumen',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.folder_outlined),
            activeIcon: Icon(Icons.folder),
            label: 'Proyectos',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.groups_outlined),
            activeIcon: Icon(Icons.groups),
            label: 'Equipos',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.people_outline),
            activeIcon: Icon(Icons.people),
            label: 'Usuarios',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.bolt_outlined),
            activeIcon: Icon(Icons.bolt),
            label: 'IA Voz',
          ),
        ],
      ),
    );
  }
}
