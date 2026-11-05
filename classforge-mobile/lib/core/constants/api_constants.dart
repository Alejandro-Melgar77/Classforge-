class ApiConstants {
  // Backend oficial en la nube (Render)
  static const String baseUrl = 'https://classforge-backend-8a14.onrender.com/api/v1';
  static const String wsUrl = 'wss://classforge-backend-8a14.onrender.com/api/v1/ws';

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
