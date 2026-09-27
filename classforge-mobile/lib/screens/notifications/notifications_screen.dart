import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../core/services/websocket_service.dart';
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
  bool _filterUnreadOnly = false;

  void _sendTestSystemNotification() {
    final push = Provider.of<PushNotificationService>(context, listen: false);
    push.triggerInstantPush(
      title: '⚡ ClassForge • Evento en Vivo',
      message: 'Ana Torres modificó la clase CuentaBancaria en el lienzo UML.',
      type: 'diagram_modified',
      diagramId: 'diag-01',
    );

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('✓ Notificación enviada a la barra de estado del teléfono'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _scheduleSystemNotification() {
    final push = Provider.of<PushNotificationService>(context, listen: false);
    push.schedulePush(
      delay: const Duration(seconds: 4),
      title: '👥 Colaborador Conectado',
      message: 'David Rojas se ha unido a la sala del proyecto.',
      type: 'team_member_added',
      diagramId: 'diag-01',
    );

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('⏱️ Alerta programada: aparecerá en la barra del teléfono en 4 segundos.'),
        duration: Duration(seconds: 3),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ws = Provider.of<WebSocketService>(context);
    final push = Provider.of<PushNotificationService>(context);
    final allNotifications = ws.notifications;
    final displayNotifications = _filterUnreadOnly
        ? allNotifications.where((n) => !n.isRead).toList()
        : allNotifications;

    return Scaffold(
      backgroundColor: AppTheme.surface1,
      appBar: AppBar(
        title: Text(
          'Centro de Notificaciones Push',
          style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_alert_outlined, size: 20, color: AppTheme.accent),
            tooltip: 'Probar Notificación en Barra',
            onPressed: _sendTestSystemNotification,
          ),
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
          // Banner de prueba en barra de notificaciones del teléfono
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            color: AppTheme.surface2,
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.phone_android, size: 16, color: AppTheme.accent),
                          const SizedBox(width: 6),
                          Text(
                            'Barra de Notificaciones del Teléfono',
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Prueba la llegada de notificaciones al sistema Android',
                        style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textMuted),
                      ),
                    ],
                  ),
                ),
                TextButton.icon(
                  style: TextButton.styleFrom(
                    backgroundColor: AppTheme.primary.withOpacity(0.2),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  ),
                  icon: const Icon(Icons.send, size: 14, color: AppTheme.primaryLight),
                  label: const Text('Disparar', style: TextStyle(fontSize: 11, color: AppTheme.primaryLight)),
                  onPressed: _sendTestSystemNotification,
                ),
                const SizedBox(width: 6),
                IconButton(
                  icon: const Icon(Icons.timer_outlined, size: 18, color: AppTheme.accent),
                  tooltip: 'Disparar en 4 seg',
                  onPressed: _scheduleSystemNotification,
                ),
              ],
            ),
          ),

          // Filter Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: AppTheme.surface1,
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
                        fontSize: 11,
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
                        fontSize: 11,
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
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: Color(0xFF10B981),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'Push Activo',
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
                          'Los eventos colaborativos del sistema se reflejan aquí y en la barra de Android.',
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
