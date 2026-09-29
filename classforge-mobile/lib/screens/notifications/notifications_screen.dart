import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../core/services/api_service.dart';
import '../../core/services/push_notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/notification_model.dart';
import '../diagrams/diagram_viewer_screen.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({Key? key}) : super(key: key);

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  final ApiService _apiService = ApiService();
  List<InAppNotificationModel> _notifications = [];
  bool _isLoading = true;
  String _activeTab = 'all'; // all | unread | project | ai

  @override
  void initState() {
    super.initState();
    _loadNotifications();
  }

  Future<void> _loadNotifications() async {
    setState(() => _isLoading = true);
    final list = await _apiService.getNotifications();
    if (mounted) {
      setState(() {
        _notifications = list;
        _isLoading = false;
      });
    }
  }

  Future<void> _markRead(String id) async {
    await _apiService.markNotificationAsRead(id);
    setState(() {
      final idx = _notifications.indexWhere((n) => n.id == id);
      if (idx != -1) _notifications[idx].isRead = true;
    });
  }

  Future<void> _markAllRead() async {
    await _apiService.markAllNotificationsAsRead();
    setState(() {
      for (var n in _notifications) {
        n.isRead = true;
      }
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Todas las notificaciones marcadas como leídas'),
        backgroundColor: Color(0xFF10B981),
      ),
    );
  }

  void _sendTestPushAlert() {
    PushNotificationService().triggerInstantPush(
      title: '⚡ Modificación en Proyecto Core Banking',
      message: 'Ing. Alejandro Melgar actualizó el esquema de microservicios y generó el backend.',
      type: 'project_update',
      diagramId: 'diag-01',
    );
    _loadNotifications();
  }

  List<InAppNotificationModel> _getFilteredList() {
    switch (_activeTab) {
      case 'unread':
        return _notifications.where((n) => !n.isRead).toList();
      case 'project':
        return _notifications.where((n) => n.type == 'project_update' || n.type == 'team_update').toList();
      case 'ai':
        return _notifications.where((n) => n.type == 'ai_update' || n.type == 'diagram_update' || n.type == 'codegen').toList();
      case 'all':
      default:
        return _notifications;
    }
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _getFilteredList();
    final unreadCount = _notifications.where((n) => !n.isRead).length;

    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(
        title: Text(
          'Buzón de Notificaciones',
          style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        backgroundColor: AppTheme.cardDark,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_active_outlined, color: AppTheme.accentBlue),
            tooltip: 'Probar Notificación Push en Teléfono',
            onPressed: _sendTestPushAlert,
          ),
          if (_notifications.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.done_all, color: Colors.white70),
              tooltip: 'Marcar todas como leídas',
              onPressed: _markAllRead,
            ),
        ],
      ),
      body: Column(
        children: [
          // Banner Informativo
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            color: AppTheme.cardDark,
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Alertas de Proyectos y Colaboración',
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                      Text(
                        unreadCount > 0 ? '$unreadCount notificaciones sin leer' : 'Estás al día con todos tus proyectos',
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          color: unreadCount > 0 ? AppTheme.accentBlue : AppTheme.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.accentBlue.withOpacity(0.18),
                    foregroundColor: AppTheme.accentBlue,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                      side: const BorderSide(color: AppTheme.accentBlue),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  ),
                  icon: const Icon(Icons.refresh, size: 16),
                  label: Text('Refrescar', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold)),
                  onPressed: _loadNotifications,
                ),
              ],
            ),
          ),

          // Pestañas de Filtro
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                _buildFilterChip('all', 'Todas (${_notifications.length})'),
                const SizedBox(width: 8),
                _buildFilterChip('unread', 'No Leídas ($unreadCount)'),
                const SizedBox(width: 8),
                _buildFilterChip('project', 'Proyectos'),
                const SizedBox(width: 8),
                _buildFilterChip('ai', 'IA & Código'),
              ],
            ),
          ),

          // Lista de Notificaciones
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: AppTheme.accentBlue))
                : filtered.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.notifications_none, size: 54, color: Colors.white24),
                            const SizedBox(height: 12),
                            Text(
                              'No hay notificaciones en esta categoría',
                              style: GoogleFonts.inter(fontSize: 14, color: AppTheme.textSecondary),
                            ),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: _loadNotifications,
                        color: AppTheme.accentBlue,
                        child: ListView.separated(
                          padding: const EdgeInsets.all(12),
                          itemCount: filtered.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final notif = filtered[index];
                            return _buildNotificationCard(notif);
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String key, String label) {
    final isSelected = _activeTab == key;
    return InkWell(
      onTap: () => setState(() => _activeTab = key),
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.accentBlue : AppTheme.cardDark,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: isSelected ? AppTheme.accentBlue : Colors.white10),
        ),
        child: Text(
          label,
          style: GoogleFonts.inter(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            color: isSelected ? Colors.white : Colors.white70,
          ),
        ),
      ),
    );
  }

  Widget _buildNotificationCard(InAppNotificationModel notif) {
    return InkWell(
      onTap: () async {
        if (!notif.isRead) {
          await _markRead(notif.id);
        }

        if (notif.diagramId != null) {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => DiagramViewerScreen(
                diagramId: notif.diagramId!,
                initialName: notif.title,
              ),
            ),
          );
        }
      },
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: notif.isRead ? AppTheme.cardDark : AppTheme.cardDark.withOpacity(0.95),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: notif.isRead ? Colors.white.withOpacity(0.04) : AppTheme.accentBlue.withOpacity(0.4),
            width: notif.isRead ? 1 : 1.5,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: notif.isRead ? Colors.white.withOpacity(0.05) : AppTheme.accentBlue.withOpacity(0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(notif.typeIcon, style: const TextStyle(fontSize: 18)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          notif.title,
                          style: GoogleFonts.inter(
                            fontSize: 13,
                            fontWeight: notif.isRead ? FontWeight.w600 : FontWeight.bold,
                            color: notif.isRead ? Colors.white70 : Colors.white,
                          ),
                        ),
                      ),
                      if (!notif.isRead)
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            shape: BoxShape.circle,
                            color: AppTheme.accentBlue,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    notif.message,
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: notif.isRead ? AppTheme.textSecondary : Colors.white70,
                      height: 1.3,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        DateFormat('dd/MM • HH:mm').format(notif.timestamp),
                        style: GoogleFonts.inter(fontSize: 10, color: Colors.white30),
                      ),
                      if (notif.diagramId != null)
                        Row(
                          children: [
                            Text(
                              'Ver Diagrama',
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                color: AppTheme.accentBlue,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const Icon(Icons.chevron_right, size: 14, color: AppTheme.accentBlue),
                          ],
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
