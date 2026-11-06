import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/services/api_service.dart';
import 'core/services/websocket_service.dart';
import 'core/services/push_notification_service.dart';
import 'core/services/offline_nlu_service.dart';
import 'core/theme/app_theme.dart';
import 'screens/auth/login_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/notifications/notifications_screen.dart';

final GlobalKey<NavigatorState> rootNavigatorKey = GlobalKey<NavigatorState>();


class ClassforgeHttpOverrides extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    return super.createHttpClient(context)
      ..badCertificateCallback = (X509Certificate cert, String host, int port) => true;
  }
}

void main() async {
  HttpOverrides.global = ClassforgeHttpOverrides();

  WidgetsFlutterBinding.ensureInitialized();

  final apiService = ApiService();
  try {
    await apiService.init();
  } catch (e) {
    debugPrint('Error inicializando ApiService en arranque: $e');
  }

  final pushService = PushNotificationService();
  try {
    await pushService.init(rootNavigatorKey);
  } catch (e) {
    debugPrint('Error inicializando PushNotificationService en arranque: $e');
  }

  runApp(
    ClassForgeMobileApp(
      apiService: apiService,
      pushService: pushService,
    ),
  );
}

class ClassForgeMobileApp extends StatelessWidget {
  final ApiService? apiService;
  final PushNotificationService? pushService;

  const ClassForgeMobileApp({
    Key? key,
    this.apiService,
    this.pushService,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final activeApiService = apiService ?? ApiService();
    final activePushService = pushService ?? PushNotificationService();
    try {
      activePushService.init(rootNavigatorKey);
    } catch (_) {}

    final bool isUserLoggedIn = activeApiService.isAuthenticated;

    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: WebSocketService()),
        ChangeNotifierProvider.value(value: activePushService),
        Provider<ApiService>.value(value: activeApiService),
        Provider<OfflineNluService>(create: (_) => OfflineNluService()),
      ],
      child: MaterialApp(
        navigatorKey: rootNavigatorKey,
        title: 'Classforge Visualizer',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.darkTheme,
        initialRoute: isUserLoggedIn ? '/home' : '/login',
        routes: {
          '/home': (context) => const HomeScreen(),
          '/login': (context) => const LoginScreen(),
          '/notifications': (context) => const NotificationsScreen(),
        },
      ),
    );
  }
}
