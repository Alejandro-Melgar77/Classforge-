import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../constants/api_constants.dart';
import '../../models/notification_model.dart';

class WebSocketService extends ChangeNotifier {
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal();

  WebSocketChannel? _channel;
  StreamSubscription? _subscription;

  bool _isConnected = false;
  String? _currentDiagramId;
  int _onlineUsersCount = 1;
  final List<String> _onlineUsers = [];
  final List<InAppNotificationModel> _notifications = [];

  // Stream controllers for reactive subscriptions
  final StreamController<InAppNotificationModel> _notificationStreamController =
      StreamController<InAppNotificationModel>.broadcast();
  final StreamController<Map<String, dynamic>> _messageStreamController =
      StreamController<Map<String, dynamic>>.broadcast();

  // Getters
  bool get isConnected => _isConnected;
  String? get currentDiagramId => _currentDiagramId;
  int get onlineUsersCount => _onlineUsersCount;
  List<String> get onlineUsers => List.unmodifiable(_onlineUsers);
  List<InAppNotificationModel> get notifications => List.unmodifiable(_notifications);
  int get unreadNotificationsCount => _notifications.where((n) => !n.isRead).length;

  Stream<InAppNotificationModel> get notificationStream => _notificationStreamController.stream;
  Stream<Map<String, dynamic>> get messageStream => _messageStreamController.stream;

  /// Conecta al WebSocket del diagrama con el token temporal obtenido del backend
  void connect(String diagramId, String token) {
    if (_isConnected && _currentDiagramId == diagramId) return;

    disconnect();

    try {
      _currentDiagramId = diagramId;
      final uri = Uri.parse('${ApiConstants.wsUrl}/diagrams/$diagramId?token=$token');

      _channel = WebSocketChannel.connect(uri);

      _subscription = _channel!.stream.listen(
        (data) {
          _handleIncomingMessage(data);
        },
        onDone: () {
          _isConnected = false;
          notifyListeners();
        },
        onError: (error) {
          debugPrint('WebSocket error: $error');
          _isConnected = false;
          notifyListeners();
        },
      );

      _isConnected = true;
      notifyListeners();

      // Añadir notificación local de conexión
      addNotification(InAppNotificationModel(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        title: 'Lienzo Conectado',
        message: 'Conexión en vivo establecida con el diagrama.',
        type: 'info',
        timestamp: DateTime.now(),
        diagramId: diagramId,
      ));
    } catch (e) {
      debugPrint('Error connecting WebSocket: $e');
      _isConnected = false;
      notifyListeners();
    }
  }

  void _handleIncomingMessage(dynamic rawData) {
    try {
      final Map<String, dynamic> data = jsonDecode(rawData.toString());
      final String type = data['type'] ?? '';

      _messageStreamController.add(data);

      switch (type) {
        case 'USER_JOINED':
          final user = data['user_name'] ?? data['user'] ?? 'Un usuario';
          if (!_onlineUsers.contains(user)) {
            _onlineUsers.add(user);
          }
          _onlineUsersCount = _onlineUsers.isNotEmpty ? _onlineUsers.length : (_onlineUsersCount + 1);
          addNotification(InAppNotificationModel(
            id: DateTime.now().millisecondsSinceEpoch.toString(),
            title: 'Colaborador Unido',
            message: '$user se ha unido al diagrama.',
            type: 'team_member_added',
            timestamp: DateTime.now(),
            diagramId: _currentDiagramId,
          ));
          break;

        case 'USER_LEFT':
          final user = data['user_name'] ?? data['user'] ?? 'Un usuario';
          _onlineUsers.remove(user);
          if (_onlineUsersCount > 1) _onlineUsersCount--;
          addNotification(InAppNotificationModel(
            id: DateTime.now().millisecondsSinceEpoch.toString(),
            title: 'Colaborador Desconectado',
            message: '$user ha salido del diagrama.',
            type: 'info',
            timestamp: DateTime.now(),
            diagramId: _currentDiagramId,
          ));
          break;

        case 'NODE_OPERATION':
          final op = data['op'] ?? 'actualización';
          final nodeName = data['data']?['name'] ?? 'Elemento UML';
          addNotification(InAppNotificationModel(
            id: DateTime.now().millisecondsSinceEpoch.toString(),
            title: 'Diagrama Modificado',
            message: 'Operación "$op" en nodo "$nodeName" por otro colaborador.',
            type: 'diagram_modified',
            timestamp: DateTime.now(),
            diagramId: _currentDiagramId,
          ));
          break;

        case 'BACKEND_GENERATED':
        case 'CODEGEN_READY':
          addNotification(InAppNotificationModel(
            id: DateTime.now().millisecondsSinceEpoch.toString(),
            title: 'Backend Spring Boot Generado',
            message: 'Nuevo código Java Spring Boot generado para este diagrama.',
            type: 'backend_generated',
            timestamp: DateTime.now(),
            diagramId: _currentDiagramId,
          ));
          break;

        case 'NOTIFICATION':
          final title = data['title'] ?? 'Notificación';
          final msg = data['message'] ?? '';
          addNotification(InAppNotificationModel(
            id: DateTime.now().millisecondsSinceEpoch.toString(),
            title: title,
            message: msg,
            type: data['notification_type'] ?? 'info',
            timestamp: DateTime.now(),
            diagramId: _currentDiagramId,
          ));
          break;

        case 'PING':
          sendMessage({'type': 'PONG', 'timestamp': DateTime.now().toIso8601String()});
          break;
      }

      notifyListeners();
    } catch (e) {
      debugPrint('Error parsing WebSocket message: $e');
    }
  }

  void sendMessage(Map<String, dynamic> message) {
    if (_isConnected && _channel != null) {
      _channel!.sink.add(jsonEncode(message));
    }
  }

  void addNotification(InAppNotificationModel notification) {
    // Insert at beginning for chronological descending order
    _notifications.insert(0, notification);
    if (_notifications.length > 50) {
      _notifications.removeLast();
    }
    _notificationStreamController.add(notification);
    notifyListeners();
  }

  void markAsRead(String id) {
    final index = _notifications.indexWhere((n) => n.id == id);
    if (index != -1) {
      _notifications[index].isRead = true;
      notifyListeners();
    }
  }

  void markAllAsRead() {
    for (var n in _notifications) {
      n.isRead = true;
    }
    notifyListeners();
  }

  void clearNotifications() {
    _notifications.clear();
    notifyListeners();
  }

  void disconnect() {
    _subscription?.cancel();
    _channel?.sink.close();
    _channel = null;
    _subscription = null;
    _isConnected = false;
    _currentDiagramId = null;
    _onlineUsers.clear();
    _onlineUsersCount = 1;
    notifyListeners();
  }

  @override
  void dispose() {
    disconnect();
    _notificationStreamController.close();
    _messageStreamController.close();
    super.dispose();
  }
}
