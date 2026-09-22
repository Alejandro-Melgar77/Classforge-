import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../core/services/websocket_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/notification_model.dart';
import '../diagrams/diagram_viewer_screen.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({Key? key}) : super(key: key);

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  bool _filterUnreadOnly = false;

  @override
  Widget build(BuildContext context) {
    final ws = Provider.of<WebSocketService>(context);
    final allNotifications = ws.notifications;
    final displayNotifications = _filterUnreadOnly
        ? allNotifications.where((n) => !n.isRead).toList()
        : allNotifications;

    return Scaffold(
      backgroundColor: AppTheme.surface1,
      appBar: AppBar(
        title: Text(
          'Notificaciones en Tiempo Real',
          style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        actions: [
          if (allNotifications.isNotEmpty) ...[
            IconButton(
              icon: const Icon(Icons.done_all, size: 20),
              tooltip: 'Marcar todas como leídas',
              onPressed: () => ws.markAllAsRead(),
            ),
            IconButton(
              icon: const Icon(Icons.delete_sweep_outlined, size: 20),
              tooltip: 'Limpiar notificaciones',
              onPressed: () => ws.clearNotifications(),
            ),
          ],
        ],
      ),
      body: Column(
        children: [
          // Filter Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: AppTheme.surface2,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    FilterChip(
                      label: Text('Todas (${allNotifications.length})'),
                      selected: !_filterUnreadOnly,
                      selectedColor: AppTheme.primary,
                      backgroundColor: AppTheme.surface3,
                      labelStyle: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: !_filterUnreadOnly ? FontWeight.bold : FontWeight.normal,
                        color: !_filterUnreadOnly ? Colors.white : AppTheme.textSecondary,
                      ),
                      onSelected: (val) {
                        setState(() => _filterUnreadOnly = false);
                      },
                    ),
                    const SizedBox(width: 8),
                    FilterChip(
                      label: Text('No leídas (${ws.unreadNotificationsCount})'),
                      selected: _filterUnreadOnly,
                      selectedColor: AppTheme.primary,
                      backgroundColor: AppTheme.surface3,
                      labelStyle: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: _filterUnreadOnly ? FontWeight.bold : FontWeight.normal,
                        color: _filterUnreadOnly ? Colors.white : AppTheme.textSecondary,
                      ),
                      onSelected: (val) {
                        setState(() => _filterUnreadOnly = true);
                      },
                    ),
                  ],
                ),
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: ws.isConnected ? AppTheme.accent : AppTheme.danger,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      ws.isConnected ? 'WebSocket Activo' : 'Sin conexión WS',
                      style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textMuted),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Notifications List
          Expanded(
            child: displayNotifications.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.notifications_none, size: 54, color: AppTheme.textMuted),
                        const SizedBox(height: 12),
                        Text(
                          _filterUnreadOnly
                              ? 'No tienes notificaciones pendientes'
                              : 'No hay notificaciones recientes',
                          style: GoogleFonts.inter(
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.textSecondary,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Los eventos colaborativos del lienzo aparecerán aquí.',
                          style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textMuted),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: displayNotifications.length,
                    itemBuilder: (context, index) {
                      final item = displayNotifications[index];
                      return _buildNotificationCard(item, ws);
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildNotificationCard(InAppNotificationModel item, WebSocketService ws) {
    final timeStr = DateFormat('HH:mm - dd/MM/yyyy').format(item.timestamp);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: item.isRead ? AppTheme.surface2 : AppTheme.surface3.withOpacity(0.6),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(
          color: item.isRead ? AppTheme.border : AppTheme.primaryLight.withOpacity(0.5),
          width: item.isRead ? 1 : 1.5,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () {
          ws.markAsRead(item.id);
          if (item.diagramId != null) {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => DiagramViewerScreen(diagramId: item.diagramId!),
              ),
            );
          }
        },
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.surface1,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppTheme.border),
                ),
                child: Text(item.typeIcon, style: const TextStyle(fontSize: 18)),
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
                            item.title,
                            style: GoogleFonts.inter(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                        ),
                        if (!item.isRead)
                          Container(
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              shape: BoxShape.circle,
                              color: AppTheme.primaryLight,
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      item.message,
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          timeStr,
                          style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textMuted),
                        ),
                        if (item.diagramId != null)
                          Text(
                            'Ver Diagrama →',
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.primaryLight,
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
