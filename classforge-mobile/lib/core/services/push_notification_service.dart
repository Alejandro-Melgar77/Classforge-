import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../../models/notification_model.dart';
import 'websocket_service.dart';

class PushNotificationEvent {
  final String id;
  final String title;
  final String message;
  final String type;
  final DateTime timestamp;
  final String? diagramId;

  PushNotificationEvent({
    required this.id,
    required this.title,
    required this.message,
    this.type = 'info',
    required this.timestamp,
    this.diagramId,
  });
}

class PushNotificationService extends ChangeNotifier {
  static final PushNotificationService _instance = PushNotificationService._internal();
  factory PushNotificationService() => _instance;
  PushNotificationService._internal();

  GlobalKey<NavigatorState>? _navigatorKey;
  Timer? _simulationTimer;
  bool _isSimulationActive = false;
  int _simulationIndex = 0;

  final FlutterLocalNotificationsPlugin _localNotifications = FlutterLocalNotificationsPlugin();
  bool _isLocalNotificationsInitialized = false;

  final List<PushNotificationEvent> _recentPushHistory = [];
  List<PushNotificationEvent> get recentPushHistory => List.unmodifiable(_recentPushHistory);
  bool get isSimulationActive => _isSimulationActive;

  Future<void> init(GlobalKey<NavigatorState> navKey) async {
    _navigatorKey = navKey;
    await _initLocalNotifications();
  }

  Future<void> _initLocalNotifications() async {
    if (_isLocalNotificationsInitialized) return;

    try {
      const AndroidInitializationSettings initializationSettingsAndroid =
          AndroidInitializationSettings('@mipmap/ic_launcher');

      const InitializationSettings initializationSettings =
          InitializationSettings(android: initializationSettingsAndroid);

      await _localNotifications.initialize(
        settings: initializationSettings,
        onDidReceiveNotificationResponse: (NotificationResponse response) {
          debugPrint('Notification tapped in system bar: ${response.payload}');
          if (_navigatorKey?.currentState != null) {
            _navigatorKey!.currentState!.pushNamed('/home');
          }
        },
      );

      // Solicitar permisos de notificación para Android 13+ (POST_NOTIFICATIONS)
      final androidPlugin = _localNotifications
          .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
      if (androidPlugin != null) {
        await androidPlugin.requestNotificationsPermission();
      }

      _isLocalNotificationsInitialized = true;
      debugPrint('✓ FlutterLocalNotificationsPlugin inicializado exitosamente.');
    } catch (e) {
      debugPrint('Advertencia inicializando FlutterLocalNotificationsPlugin: $e');
    }
  }

  /// Dispara una notificación push tanto en la BARRA DE NOTIFICACIONES DEL TELÉFONO como en la app
  Future<void> triggerInstantPush({
    required String title,
    required String message,
    String type = 'info',
    String? diagramId,
  }) async {
    final event = PushNotificationEvent(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: title,
      message: message,
      type: type,
      timestamp: DateTime.now(),
      diagramId: diagramId,
    );

    _recentPushHistory.insert(0, event);
    if (_recentPushHistory.length > 20) {
      _recentPushHistory.removeLast();
    }

    // 1. Vibración háptica física del dispositivo móvil
    try {
      HapticFeedback.heavyImpact();
    } catch (_) {}

    // 2. DISPARAR EN LA BARRA DE NOTIFICACIONES DEL SISTEMA ANDROID
    try {
      if (!_isLocalNotificationsInitialized) {
        await _initLocalNotifications();
      }

      final int notifId = (DateTime.now().millisecondsSinceEpoch % 100000);
      const AndroidNotificationDetails androidPlatformChannelSpecifics =
          AndroidNotificationDetails(
        'classforge_system_channel',
        'ClassForge Notificaciones',
        channelDescription: 'Alertas de colaboración UML y generación de backend en tiempo real',
        importance: Importance.max,
        priority: Priority.high,
        ticker: 'ClassForge Notificación',
        icon: '@mipmap/ic_launcher',
        enableVibration: true,
        playSound: true,
        showWhen: true,
      );

      const NotificationDetails platformChannelSpecifics =
          NotificationDetails(android: androidPlatformChannelSpecifics);

      await _localNotifications.show(
        id: notifId,
        title: title,
        body: message,
        notificationDetails: platformChannelSpecifics,
        payload: diagramId ?? 'default',
      );
    } catch (e) {
      debugPrint('Error enviando notificación a la barra del sistema: $e');
    }

    // 3. Registrar en el centro de avisos de WebSocketService
    try {
      final ws = WebSocketService();
      ws.addNotification(InAppNotificationModel(
        id: event.id,
        title: event.title,
        message: event.message,
        type: event.type,
        timestamp: event.timestamp,
        diagramId: event.diagramId,
      ));
    } catch (e) {
      debugPrint('Error agregando a WebSocketService: $e');
    }

    // 4. Mostrar banner flotante en la UI si la app está en primer plano
    _showHeadsUpBanner(event);
    notifyListeners();
  }

  /// Programa una notificación push para dispararse tras un retardo específico
  void schedulePush({
    required Duration delay,
    required String title,
    required String message,
    String type = 'info',
    String? diagramId,
  }) {
    Timer(delay, () {
      triggerInstantPush(
        title: title,
        message: message,
        type: type,
        diagramId: diagramId,
      );
    });
  }

  /// Activa o desactiva la simulación de eventos colaborativos
  void toggleBackgroundSimulation(bool enable) {
    _isSimulationActive = enable;
    _simulationTimer?.cancel();
    _simulationTimer = null;

    if (enable) {
      _fireSimulatedTeamEvent();
      _simulationTimer = Timer.periodic(const Duration(seconds: 10), (_) {
        _fireSimulatedTeamEvent();
      });
    }
    notifyListeners();
  }

  final List<Map<String, String>> _simulatedScenarios = [
    {
      'title': '👤 Colaborador en Línea',
      'message': 'Carlos Mendoza se ha conectado al Diagrama de Arquitectura.',
      'type': 'team_member_added',
      'diagramId': 'diag-01',
    },
    {
      'title': '✏️ Clase UML Actualizada',
      'message': 'Ana Torres agregó el método validarToken() a la clase AuthService.',
      'type': 'diagram_modified',
      'diagramId': 'diag-01',
    },
    {
      'title': '⚡ Backend Spring Boot Compilado',
      'message': 'Se generaron exitosamente las entidades JPA y Repositorios Maven.',
      'type': 'backend_generated',
      'diagramId': 'diag-01',
    },
    {
      'title': '🔒 Nodo Bloqueado por Edición',
      'message': 'David Rojas está editando la clase Transaccion (Bloqueo pesimista).',
      'type': 'warning',
      'diagramId': 'diag-01',
    },
    {
      'title': '💬 Nota de Arquitectura',
      'message': 'Sofía Castro: "Revisar multiplicidad 1..* en CuentaBancaria".',
      'type': 'info',
      'diagramId': 'diag-01',
    },
  ];

  void _fireSimulatedTeamEvent() {
    final scenario = _simulatedScenarios[_simulationIndex % _simulatedScenarios.length];
    _simulationIndex++;
    triggerInstantPush(
      title: scenario['title']!,
      message: scenario['message']!,
      type: scenario['type']!,
      diagramId: scenario['diagramId'],
    );
  }

  void _showHeadsUpBanner(PushNotificationEvent event) {
    final overlayState = _navigatorKey?.currentState?.overlay;
    if (overlayState == null) return;

    late OverlayEntry entry;
    entry = OverlayEntry(
      builder: (context) => _HeadsUpNotificationWidget(
        event: event,
        onDismiss: () {
          entry.remove();
        },
        onTap: () {
          entry.remove();
        },
      ),
    );

    overlayState.insert(entry);
  }

  @override
  void dispose() {
    _simulationTimer?.cancel();
    super.dispose();
  }
}

class _HeadsUpNotificationWidget extends StatefulWidget {
  final PushNotificationEvent event;
  final VoidCallback onDismiss;
  final VoidCallback onTap;

  const _HeadsUpNotificationWidget({
    Key? key,
    required this.event,
    required this.onDismiss,
    required this.onTap,
  }) : super(key: key);

  @override
  State<_HeadsUpNotificationWidget> createState() => _HeadsUpNotificationWidgetState();
}

class _HeadsUpNotificationWidgetState extends State<_HeadsUpNotificationWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _offsetAnimation;
  late Animation<double> _fadeAnimation;
  Timer? _autoDismissTimer;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    );

    _offsetAnimation = Tween<Offset>(
      begin: const Offset(0, -1.2),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutBack,
    ));

    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeIn,
    );

    _controller.forward();

    _autoDismissTimer = Timer(const Duration(milliseconds: 4000), () {
      _dismissWithAnimation();
    });
  }

  void _dismissWithAnimation() {
    if (!mounted) return;
    _autoDismissTimer?.cancel();
    _controller.reverse().then((_) {
      widget.onDismiss();
    });
  }

  Color _getTypeColor(String type) {
    switch (type) {
      case 'team_member_added':
        return AppTheme.accent;
      case 'backend_generated':
        return const Color(0xFF10B981);
      case 'diagram_modified':
        return AppTheme.primaryLight;
      case 'warning':
        return const Color(0xFFF59E0B);
      default:
        return AppTheme.primary;
    }
  }

  IconData _getTypeIcon(String type) {
    switch (type) {
      case 'team_member_added':
        return Icons.person_add_alt_1;
      case 'backend_generated':
        return Icons.auto_awesome;
      case 'diagram_modified':
        return Icons.edit_note;
      case 'warning':
        return Icons.lock_clock;
      default:
        return Icons.notifications_active;
    }
  }

  @override
  void dispose() {
    _autoDismissTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final typeColor = _getTypeColor(widget.event.type);
    final topPadding = MediaQuery.of(context).padding.top;

    return Positioned(
      top: topPadding + 8,
      left: 14,
      right: 14,
      child: SlideTransition(
        position: _offsetAnimation,
        child: FadeTransition(
          opacity: _fadeAnimation,
          child: Material(
            color: Colors.transparent,
            child: Dismissible(
              key: Key(widget.event.id),
              direction: DismissDirection.up,
              onDismissed: (_) => widget.onDismiss(),
              child: GestureDetector(
                onTap: widget.onTap,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF161F30).withOpacity(0.97),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: typeColor.withOpacity(0.5), width: 1.2),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.35),
                        blurRadius: 16,
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: typeColor.withOpacity(0.15),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(_getTypeIcon(widget.event.type), color: typeColor, size: 20),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              widget.event.title,
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.textPrimary,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 2),
                            Text(
                              widget.event.message,
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                color: AppTheme.textSecondary,
                              ),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
