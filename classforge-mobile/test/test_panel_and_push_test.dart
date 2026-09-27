import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:classforge_mobile/core/services/api_service.dart';
import 'package:classforge_mobile/core/services/offline_nlu_service.dart';
import 'package:classforge_mobile/core/services/push_notification_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Offline Mode & In-Memory Diagram Tests', () {
    late ApiService apiService;
    late OfflineNluService nluService;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      apiService = ApiService();
      await apiService.init();
      await apiService.enableOfflineDemoMode();
      nluService = OfflineNluService();
    });

    test('ApiService debe iniciar en modo offline y cargar datos mock', () async {
      expect(apiService.isOfflineDemoMode, isTrue);
      expect(apiService.isAuthenticated, isTrue);
      expect(apiService.currentUser?.name, equals('Ing. Alejandro Melgar'));
      expect(apiService.currentUser?.role, equals('admin'));

      final stats = await apiService.getDashboardStats();
      expect(stats, isNotNull);
      expect(stats!.totalProjects, equals(8));

      final projects = await apiService.getProjects();
      expect(projects.isNotEmpty, isTrue);
      expect(projects.any((p) => p.name == 'Sistema Bancario Core'), isTrue);

      final diagram = await apiService.getDiagram('diag-01');
      expect(diagram, isNotNull);
      expect(diagram!.nodes.length, greaterThanOrEqualTo(4));
      expect(diagram.edges.length, greaterThanOrEqualTo(3));
    });

    test('applyNluResultToDiagram debe agregar clases creadas por voz al diagrama en memoria', () async {
      final nluResult = nluService.parse('crear clase Factura con id:long, monto:double');
      expect(nluResult.action, equals('create_class'));
      expect(nluResult.classes.first.name, equals('Factura'));

      final applied = apiService.applyNluResultToDiagram('diag-01', nluResult);
      expect(applied, isTrue);

      final updatedDiagram = await apiService.getDiagram('diag-01');
      expect(updatedDiagram!.nodes.any((n) => n.name == 'Factura'), isTrue);
      final facturaNode = updatedDiagram.nodes.firstWhere((n) => n.name == 'Factura');
      expect(facturaNode.attributes.length, equals(2));
    });
  });

  group('PushNotificationService Tests', () {
    late PushNotificationService pushService;

    setUp(() {
      pushService = PushNotificationService();
    });

    test('triggerInstantPush debe registrar eventos en el historial reciente', () {
      pushService.triggerInstantPush(
        title: 'Prueba Push Instantánea',
        message: 'Mensaje de validación de entrega de evento.',
        type: 'info',
      );

      expect(pushService.recentPushHistory.isNotEmpty, isTrue);
      expect(pushService.recentPushHistory.first.title, equals('Prueba Push Instantánea'));
      expect(pushService.recentPushHistory.first.type, equals('info'));
    });

    test('toggleBackgroundSimulation debe alternar el estado de simulación', () {
      expect(pushService.isSimulationActive, isFalse);

      pushService.toggleBackgroundSimulation(true);
      expect(pushService.isSimulationActive, isTrue);

      pushService.toggleBackgroundSimulation(false);
      expect(pushService.isSimulationActive, isFalse);
    });
  });
}
