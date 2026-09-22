import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../constants/api_constants.dart';
import '../../models/user_model.dart';
import '../../models/project_model.dart';
import '../../models/diagram_model.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  String? _accessToken;
  UserModel? _currentUser;

  UserModel? get currentUser => _currentUser;
  bool get isAuthenticated => _accessToken != null;

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _accessToken = prefs.getString('access_token');
    final userJson = prefs.getString('current_user');
    if (userJson != null) {
      _currentUser = UserModel.fromJson(jsonDecode(userJson));
    }
  }

  Map<String, String> _headers({bool auth = true}) {
    final headers = {'Content-Type': 'application/json'};
    if (auth && _accessToken != null) {
      headers['Authorization'] = 'Bearer $_accessToken';
    }
    return headers;
  }

  Future<bool> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConstants.baseUrl}${ApiConstants.login}'),
        headers: _headers(auth: false),
        body: jsonEncode({
          'email': email,
          'password': password,
          'device_info': 'ClassForge Mobile (Flutter)'
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final tokenData = data['data'];
        _accessToken = tokenData['access_token'];

        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access_token', _accessToken!);

        // Fetch user profile
        await fetchCurrentUser();
        return true;
      }
      return false;
    } catch (e) {
      print('Login error: $e');
      return false;
    }
  }

  Future<void> fetchCurrentUser() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConstants.baseUrl}${ApiConstants.me}'),
        headers: _headers(),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _currentUser = UserModel.fromJson(data['data']);
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('current_user', jsonEncode(_currentUser!.toJson()));
      }
    } catch (e) {
      print('Fetch current user error: $e');
    }
  }

  Future<void> logout() async {
    _accessToken = null;
    _currentUser = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('current_user');
  }

  Future<DashboardStatsModel?> getDashboardStats() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConstants.baseUrl}${ApiConstants.stats}'),
        headers: _headers(),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return DashboardStatsModel.fromJson(data['data']);
      }
      return null;
    } catch (e) {
      print('Get dashboard stats error: $e');
      return null;
    }
  }

  Future<List<ProjectModel>> getProjects({String? status}) async {
    try {
      String url = '${ApiConstants.baseUrl}${ApiConstants.projects}';
      if (status != null) {
        url += '?status=$status';
      }

      final response = await http.get(
        Uri.parse(url),
        headers: _headers(),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final list = data['data'] as List<dynamic>? ?? [];
        return list.map((p) => ProjectModel.fromJson(p)).toList();
      }
      return [];
    } catch (e) {
      print('Get projects error: $e');
      return [];
    }
  }

  Future<List<DiagramModel>> getDiagrams({String? projectId}) async {
    try {
      String url = '${ApiConstants.baseUrl}${ApiConstants.diagrams}';
      if (projectId != null) {
        url += '?project_id=$projectId';
      }

      final response = await http.get(
        Uri.parse(url),
        headers: _headers(),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final list = data['data'] as List<dynamic>? ?? [];
        return list.map((d) => DiagramModel.fromJson(d)).toList();
      }
      return [];
    } catch (e) {
      print('Get diagrams error: $e');
      return [];
    }
  }

  Future<DiagramModel?> getDiagram(String diagramId) async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConstants.baseUrl}${ApiConstants.diagrams}/$diagramId'),
        headers: _headers(),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return DiagramModel.fromJson(data['data']);
      }
      return null;
    } catch (e) {
      print('Get diagram details error: $e');
      return null;
    }
  }

  Future<String?> getWsToken(String diagramId) async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConstants.baseUrl}${ApiConstants.diagrams}/$diagramId/ws-token'),
        headers: _headers(),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['data']['token'];
      }
      return null;
    } catch (e) {
      print('Get ws token error: $e');
      return null;
    }
  }
}
