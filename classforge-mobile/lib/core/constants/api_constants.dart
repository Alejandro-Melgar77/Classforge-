class ApiConstants {
  // Default to 10.0.2.2 for Android Emulator, localhost for iOS/desktop
  static const String baseUrl = 'http://10.0.2.2:8000/api/v1';
  static const String wsUrl = 'ws://10.0.2.2:8000/api/v1/ws';

  // Alternative for physical devices on local network
  // static const String baseUrl = 'http://192.168.1.100:8000/api/v1';
  // static const String wsUrl = 'ws://192.168.1.100:8000/api/v1/ws';

  // Auth endpoints
  static const String login = '/auth/login';
  static const String refresh = '/auth/refresh';
  static const String me = '/auth/me';

  // Dashboard & Projects endpoints
  static const String stats = '/dashboard/stats';
  static const String projects = '/projects';
  static const String teams = '/teams';
  static const String diagrams = '/diagrams';
}
