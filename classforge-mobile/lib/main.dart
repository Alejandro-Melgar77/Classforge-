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

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final apiService = ApiService();
  await apiService.init();

  final pushService = PushNotificationService();
  await pushService.init(rootNavigatorKey);

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
    activePushService.init(rootNavigatorKey);

    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: WebSocketService()),
        ChangeNotifierProvider.value(value: activePushService),
        Provider<ApiService>.value(value: activeApiService),
        Provider<OfflineNluService>(create: (_) => OfflineNluService()),
      ],
      child: MaterialApp(
        navigatorKey: rootNavigatorKey,
        title: 'ClassForge Studio',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.darkTheme,
        initialRoute: '/home',
        routes: {
          '/home': (context) => const HomeScreen(),
          '/login': (context) => const LoginScreen(),
          '/notifications': (context) => const NotificationsScreen(),
        },
      ),
    );
  }
}
