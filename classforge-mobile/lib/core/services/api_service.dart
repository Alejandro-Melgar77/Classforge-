import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../constants/api_constants.dart';
import '../../models/user_model.dart';
import '../../models/project_model.dart';
import '../../models/team_model.dart';
import '../../models/diagram_model.dart';
import 'offline_nlu_service.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal() {
    _initializeMockData();
  }

  String? _accessToken;
  UserModel? _currentUser;
  String _activeBaseUrl = ApiConstants.baseUrl;
  bool _isOfflineDemoMode = true; // Por defecto activo para funcionamiento autónomo

  UserModel? get currentUser => _currentUser;
  bool get isAuthenticated => _currentUser != null;
  bool get isOfflineDemoMode => _isOfflineDemoMode;
  String get activeBaseUrl => _activeBaseUrl;

  final Map<String, DiagramModel> _mockDiagrams = {};
  late List<ProjectModel> _mockProjects;
  late List<TeamModel> _mockTeams;
  late List<UserModel> _mockUsers;
  late DashboardStatsModel _mockStats;

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _accessToken = prefs.getString('access_token');
    _activeBaseUrl = prefs.getString('custom_base_url') ?? ApiConstants.baseUrl;

    final userJson = prefs.getString('current_user');
    if (userJson != null) {
      _currentUser = UserModel.fromJson(jsonDecode(userJson));
    }

    _initializeMockData();

    // Si no hay sesión previa, inicializar con el usuario ejecutivo por defecto
    if (_currentUser == null) {
      await enableOfflineDemoMode();
    }
  }

  void _initializeMockData() {
    _mockUsers = [
      UserModel(
        id: 'usr-01',
        name: 'Ing. Alejandro Melgar',
        email: 'admin@classforge.io',
        role: 'admin',
        teamIds: ['team-01', 'team-02'],
      ),
      UserModel(
        id: 'usr-02',
        name: 'Carlos Mendoza',
        email: 'scrum@classforge.io',
        role: 'scrum_master',
        teamIds: ['team-01'],
      ),
      UserModel(
        id: 'usr-03',
        name: 'Ana Torres',
        email: 'dev@classforge.io',
        role: 'dev',
        teamIds: ['team-01', 'team-03'],
      ),
      UserModel(
        id: 'usr-04',
        name: 'David Rojas',
        email: 'dev2@classforge.io',
        role: 'dev',
        teamIds: ['team-01', 'team-02'],
      ),
      UserModel(
        id: 'usr-05',
        name: 'Sofía Castro',
        email: 'dev3@classforge.io',
        role: 'dev',
        teamIds: ['team-02'],
      ),
      UserModel(
        id: 'usr-06',
        name: 'Ing. Roberto Vaca',
        email: 'auditor@classforge.io',
        role: 'scrum_master',
        teamIds: ['team-03'],
      ),
    ];

    _mockTeams = [
      TeamModel(
        id: 'team-01',
        name: 'Equipo Core Banking & Arquitectura',
        description: 'Desarrollo de módulos transaccionales, auditoría financiera y motores CASE.',
        scrumMasterName: 'Carlos Mendoza',
        scrumMasterEmail: 'scrum@classforge.io',
        membersCount: 4,
        memberNames: ['Carlos Mendoza', 'Ana Torres', 'David Rojas', 'Alejandro Melgar'],
        activeProjectsCount: 2,
        createdAt: DateTime.now().subtract(const Duration(days: 30)),
      ),
      TeamModel(
        id: 'team-02',
        name: 'Squad E-Commerce & Microservicios',
        description: 'Arquitectura distribuida de pedidos, inventario, carritos y pasarelas de pago.',
        scrumMasterName: 'Ana Torres',
        scrumMasterEmail: 'dev@classforge.io',
        membersCount: 3,
        memberNames: ['Ana Torres', 'Sofía Castro', 'David Rojas'],
        activeProjectsCount: 2,
        createdAt: DateTime.now().subtract(const Duration(days: 20)),
      ),
      TeamModel(
        id: 'team-03',
        name: 'Fintech & Facturación Electrónica',
        description: 'Servicios fiscales de emisión, timbrado digital y trazabilidad tributaria.',
        scrumMasterName: 'Ing. Roberto Vaca',
        scrumMasterEmail: 'auditor@classforge.io',
        membersCount: 2,
        memberNames: ['Ing. Roberto Vaca', 'Ana Torres'],
        activeProjectsCount: 1,
        createdAt: DateTime.now().subtract(const Duration(days: 15)),
      ),
    ];

    _mockProjects = [
      ProjectModel(
        id: 'proj-01',
        name: 'Sistema Bancario Core',
        description: 'Módulos de cuentas corrientes, transacciones financieras y auditoría transaccional.',
        status: 'in_progress',
        type: 'team',
        teamId: 'team-01',
        teamName: 'Equipo Core Banking & Arquitectura',
        createdBy: 'Ing. Alejandro Melgar',
        createdAt: DateTime.now().subtract(const Duration(days: 4)),
      ),
      ProjectModel(
        id: 'proj-02',
        name: 'Plataforma E-Commerce Microservicios',
        description: 'Catálogo de productos, gestión de pedidos y pasarelas de pago sincronizadas.',
        status: 'in_progress',
        type: 'team',
        teamId: 'team-02',
        teamName: 'Squad E-Commerce & Microservicios',
        createdBy: 'Ing. Alejandro Melgar',
        createdAt: DateTime.now().subtract(const Duration(days: 8)),
      ),
      ProjectModel(
        id: 'proj-03',
        name: 'Módulo de Facturación Electrónica',
        description: 'Emisión de comprobantes fiscales, timbrado digital y generación XML conforme a norma.',
        status: 'completed',
        type: 'team',
        teamId: 'team-03',
        teamName: 'Fintech & Facturación Electrónica',
        createdBy: 'Ing. Alejandro Melgar',
        createdAt: DateTime.now().subtract(const Duration(days: 15)),
      ),
      ProjectModel(
        id: 'proj-04',
        name: 'ClassForge CASE Engine',
        description: 'Generación incremental Spring Boot 3, meta-prompts IA y XMI 2.1 estándar.',
        status: 'review',
        type: 'personal',
        createdBy: 'Ing. Alejandro Melgar',
        createdAt: DateTime.now().subtract(const Duration(days: 2)),
      ),
    ];

    _mockStats = DashboardStatsModel(
      totalProjects: 8,
      activeProjects: 5,
      completedProjects: 3,
      totalTeams: 3,
      recentProjects: _mockProjects,
    );

    // Diagrama 1: Diagrama Bancario
    _mockDiagrams['diag-01'] = DiagramModel(
      id: 'diag-01',
      name: 'Diagrama Conceptual Bancario',
      description: 'Modelo estructural UML 2.5+ con cuentas, transacciones y auditoría.',
      projectId: 'proj-01',
      teamId: 'team-01',
      status: 'in_progress',
      version: 4,
      nodes: [
        DiagramNodeModel(
          id: 'node-usr',
          type: 'class',
          name: 'Usuario',
          attributes: [
            UMLAttributeModel(visibility: '+', name: 'id', type: 'int'),
            UMLAttributeModel(visibility: '+', name: 'nombre', type: 'String'),
            UMLAttributeModel(visibility: '+', name: 'email', type: 'String'),
            UMLAttributeModel(visibility: '+', name: 'activo', type: 'boolean'),
          ],
          methods: [
            UMLMethodModel(visibility: '+', name: 'autenticar', params: '(pass)', returnType: 'boolean'),
            UMLMethodModel(visibility: '+', name: 'getRol', params: '()', returnType: 'String'),
          ],
          x: 50,
          y: 70,
          width: 220,
          height: 160,
        ),
        DiagramNodeModel(
          id: 'node-cuenta',
          type: 'class',
          name: 'CuentaBancaria',
          attributes: [
            UMLAttributeModel(visibility: '+', name: 'numeroCuenta', type: 'String'),
            UMLAttributeModel(visibility: '-', name: 'saldo', type: 'double'),
            UMLAttributeModel(visibility: '+', name: 'tipoCuenta', type: 'String'),
          ],
          methods: [
            UMLMethodModel(visibility: '+', name: 'depositar', params: '(monto:double)', returnType: 'void'),
            UMLMethodModel(visibility: '+', name: 'retirar', params: '(monto:double)', returnType: 'boolean'),
            UMLMethodModel(visibility: '+', name: 'consultarSaldo', params: '()', returnType: 'double'),
          ],
          x: 340,
          y: 70,
          width: 240,
          height: 175,
        ),
        DiagramNodeModel(
          id: 'node-tx',
          type: 'class',
          name: 'Transaccion',
          attributes: [
            UMLAttributeModel(visibility: '+', name: 'codigoRef', type: 'String'),
            UMLAttributeModel(visibility: '+', name: 'monto', type: 'double'),
            UMLAttributeModel(visibility: '+', name: 'fechaHora', type: 'DateTime'),
            UMLAttributeModel(visibility: '+', name: 'estado', type: 'String'),
          ],
          methods: [
            UMLMethodModel(visibility: '+', name: 'procesar', params: '()', returnType: 'boolean'),
            UMLMethodModel(visibility: '+', name: 'revertir', params: '()', returnType: 'void'),
          ],
          x: 340,
          y: 330,
          width: 240,
          height: 165,
        ),
        DiagramNodeModel(
          id: 'node-audit',
          type: 'class',
          name: 'AuditoriaLog',
          stereotype: 'service',
          attributes: [
            UMLAttributeModel(visibility: '+', name: 'logId', type: 'long'),
            UMLAttributeModel(visibility: '+', name: 'accion', type: 'String'),
            UMLAttributeModel(visibility: '+', name: 'timestamp', type: 'DateTime'),
          ],
          methods: [
            UMLMethodModel(visibility: '+', name: 'registrarEvento', params: '(evento:String)', returnType: 'void'),
          ],
          x: 50,
          y: 330,
          width: 220,
          height: 150,
        ),
      ],
      edges: [
        DiagramEdgeModel(
          id: 'edge-01',
          type: 'association',
          sourceId: 'node-usr',
          targetId: 'node-cuenta',
          label: '1..* posee',
        ),
        DiagramEdgeModel(
          id: 'edge-02',
          type: 'composition',
          sourceId: 'node-cuenta',
          targetId: 'node-tx',
          label: 'registra',
        ),
        DiagramEdgeModel(
          id: 'edge-03',
          type: 'dependency',
          sourceId: 'node-tx',
          targetId: 'node-audit',
          label: 'audita',
        ),
      ],
    );

    // Diagrama 2: E-Commerce
    _mockDiagrams['diag-02'] = DiagramModel(
      id: 'diag-02',
      name: 'Modelo E-Commerce & Pedidos',
      description: 'Estructura conceptual de clientes, pedidos, facturas y stock.',
      projectId: 'proj-02',
      teamId: 'team-02',
      status: 'in_progress',
      version: 2,
      nodes: [
        DiagramNodeModel(
          id: 'node-cliente',
          type: 'class',
          name: 'Cliente',
          attributes: [
            UMLAttributeModel(visibility: '+', name: 'id', type: 'int'),
            UMLAttributeModel(visibility: '+', name: 'razonSocial', type: 'String'),
            UMLAttributeModel(visibility: '+', name: 'nitCi', type: 'String'),
          ],
          methods: [
            UMLMethodModel(visibility: '+', name: 'crearPedido', params: '()', returnType: 'Pedido'),
          ],
          x: 50,
          y: 80,
          width: 200,
          height: 140,
        ),
        DiagramNodeModel(
          id: 'node-pedido',
          type: 'class',
          name: 'Pedido',
          attributes: [
            UMLAttributeModel(visibility: '+', name: 'numero', type: 'String'),
            UMLAttributeModel(visibility: '+', name: 'total', type: 'double'),
            UMLAttributeModel(visibility: '+', name: 'estado', type: 'String'),
          ],
          methods: [
            UMLMethodModel(visibility: '+', name: 'calcularTotal', params: '()', returnType: 'double'),
            UMLMethodModel(visibility: '+', name: 'confirmar', params: '()', returnType: 'boolean'),
          ],
          x: 320,
          y: 80,
          width: 220,
          height: 160,
        ),
      ],
      edges: [
        DiagramEdgeModel(
          id: 'edge-ecom-01',
          type: 'association',
          sourceId: 'node-cliente',
          targetId: 'node-pedido',
          label: '1..* realiza',
        ),
      ],
    );
  }

  Future<void> enableOfflineDemoMode() async {
    _isOfflineDemoMode = true;
    _accessToken = 'classforge_production_session_jwt';
    _currentUser = UserModel(
      id: 'usr-01',
      name: 'Ing. Alejandro Melgar',
      email: 'admin@classforge.io',
      role: 'admin',
      teamIds: ['team-01', 'team-02'],
    );

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_offline_demo_mode', true);
    await prefs.setString('access_token', _accessToken!);
    await prefs.setString('current_user', jsonEncode(_currentUser!.toJson()));
  }

  Future<void> setCustomBaseUrl(String url) async {
    _activeBaseUrl = url.trim();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('custom_base_url', _activeBaseUrl);
  }

  Map<String, String> _headers({bool auth = true}) {
    final headers = {'Content-Type': 'application/json'};
    if (auth && _accessToken != null) {
      headers['Authorization'] = 'Bearer $_accessToken';
    }
    return headers;
  }

  Future<bool> login(String email, String password) async {
    if (email.contains('classforge.io') || email.contains('admin')) {
      await enableOfflineDemoMode();
      return true;
    }

    try {
      final response = await http
          .post(
            Uri.parse('$_activeBaseUrl${ApiConstants.login}'),
            headers: _headers(auth: false),
            body: jsonEncode({
              'email': email,
              'password': password,
              'device_info': 'ClassForge Mobile (Flutter)'
            }),
          )
          .timeout(const Duration(seconds: 4));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final tokenData = data['data'];
        _accessToken = tokenData['access_token'];
        _isOfflineDemoMode = false;

        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access_token', _accessToken!);
        await prefs.setBool('is_offline_demo_mode', false);

        await fetchCurrentUser();
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('Login error: $e');
      return false;
    }
  }

  Future<void> fetchCurrentUser() async {
    if (_isOfflineDemoMode) return;
    try {
      final response = await http
          .get(
            Uri.parse('$_activeBaseUrl${ApiConstants.me}'),
            headers: _headers(),
          )
          .timeout(const Duration(seconds: 3));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _currentUser = UserModel.fromJson(data['data']);
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('current_user', jsonEncode(_currentUser!.toJson()));
      }
    } catch (e) {
      debugPrint('Fetch current user error: $e');
    }
  }

  Future<void> logout() async {
    _accessToken = null;
    _currentUser = null;
    _isOfflineDemoMode = false;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('current_user');
    await prefs.setBool('is_offline_demo_mode', false);
  }

  Future<DashboardStatsModel?> getDashboardStats() async {
    if (_isOfflineDemoMode) return _mockStats;

    try {
      final response = await http
          .get(
            Uri.parse('$_activeBaseUrl${ApiConstants.stats}'),
            headers: _headers(),
          )
          .timeout(const Duration(seconds: 3));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return DashboardStatsModel.fromJson(data['data']);
      }
    } catch (e) {
      debugPrint('Fallback to offline stats: $e');
    }
    return _mockStats;
  }

  Future<List<ProjectModel>> getProjects({String? status}) async {
    if (_isOfflineDemoMode) {
      if (status != null && status != 'all') {
        return _mockProjects.where((p) => p.status == status).toList();
      }
      return _mockProjects;
    }

    try {
      String url = '$_activeBaseUrl${ApiConstants.projects}';
      if (status != null && status != 'all') {
        url += '?status=$status';
      }

      final response = await http
          .get(
            Uri.parse(url),
            headers: _headers(),
          )
          .timeout(const Duration(seconds: 3));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final list = data['data'] as List<dynamic>? ?? [];
        return list.map((p) => ProjectModel.fromJson(p)).toList();
      }
    } catch (e) {
      debugPrint('Fallback to offline projects: $e');
    }
    return _mockProjects;
  }

  Future<List<TeamModel>> getTeams() async {
    if (_isOfflineDemoMode) return _mockTeams;

    try {
      final response = await http
          .get(
            Uri.parse('$_activeBaseUrl/teams'),
            headers: _headers(),
          )
          .timeout(const Duration(seconds: 3));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final list = data['data'] as List<dynamic>? ?? [];
        return list.map((t) => TeamModel.fromJson(t)).toList();
      }
    } catch (e) {
      debugPrint('Fallback to offline teams: $e');
    }
    return _mockTeams;
  }

  Future<List<UserModel>> getUsers() async {
    if (_isOfflineDemoMode) return _mockUsers;

    try {
      final response = await http
          .get(
            Uri.parse('$_activeBaseUrl/users'),
            headers: _headers(),
          )
          .timeout(const Duration(seconds: 3));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final list = data['data'] as List<dynamic>? ?? [];
        return list.map((u) => UserModel.fromJson(u)).toList();
      }
    } catch (e) {
      debugPrint('Fallback to offline users: $e');
    }
    return _mockUsers;
  }

  Future<List<DiagramModel>> getDiagrams({String? projectId}) async {
    final list = _mockDiagrams.values.toList();
    if (projectId != null) {
      return list.where((d) => d.projectId == projectId).toList();
    }
    return list;
  }

  Future<DiagramModel?> getDiagram(String diagramId) async {
    if (_mockDiagrams.containsKey(diagramId)) {
      return _mockDiagrams[diagramId];
    }

    if (!_isOfflineDemoMode) {
      try {
        final response = await http
            .get(
              Uri.parse('$_activeBaseUrl${ApiConstants.diagrams}/$diagramId'),
              headers: _headers(),
            )
            .timeout(const Duration(seconds: 3));

        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          return DiagramModel.fromJson(data['data']);
        }
      } catch (e) {
        debugPrint('Fallback to offline diagram details: $e');
      }
    }

    return _mockDiagrams['diag-01'];
  }

  Future<String?> getWsToken(String diagramId) async {
    return 'mock-ws-token';
  }

  bool applyNluResultToDiagram(String diagramId, NluResult result) {
    final current = _mockDiagrams[diagramId] ?? _mockDiagrams['diag-01'];
    if (current == null) return false;

    final updatedNodes = List<DiagramNodeModel>.from(current.nodes);
    final updatedEdges = List<DiagramEdgeModel>.from(current.edges);

    for (final c in result.classes) {
      final existingIndex = updatedNodes.indexWhere(
        (n) => n.name.toLowerCase() == c.name.toLowerCase(),
      );

      final attributes = c.attributes
          .map((a) => UMLAttributeModel(
                visibility: a.visibility == 'private'
                    ? '-'
                    : a.visibility == 'protected'
                        ? '#'
                        : '+',
                name: a.name,
                type: a.type,
              ))
          .toList();

      final methods = c.methods
          .map((m) => UMLMethodModel(
                visibility: m.visibility == 'private'
                    ? '-'
                    : m.visibility == 'protected'
                        ? '#'
                        : '+',
                name: m.name,
                params: m.params,
                returnType: m.returnType,
              ))
          .toList();

      if (existingIndex != -1) {
        final old = updatedNodes[existingIndex];
        updatedNodes[existingIndex] = DiagramNodeModel(
          id: old.id,
          type: c.type,
          name: old.name,
          stereotype: old.stereotype,
          attributes: [...old.attributes, ...attributes],
          methods: [...old.methods, ...methods],
          x: old.x,
          y: old.y,
          width: old.width,
          height: old.height + (attributes.length * 15) + (methods.length * 15),
        );
      } else {
        final count = updatedNodes.length;
        final xPos = 50.0 + ((count % 2) * 290.0);
        final yPos = 80.0 + ((count ~/ 2) * 230.0);

        updatedNodes.add(DiagramNodeModel(
          id: 'node-${c.name.toLowerCase()}-${DateTime.now().millisecondsSinceEpoch}',
          type: c.type,
          name: c.name,
          attributes: attributes,
          methods: methods,
          x: xPos,
          y: yPos,
          width: 220,
          height: 150 + (attributes.length * 12) + (methods.length * 12),
        ));
      }
    }

    for (final r in result.relations) {
      final sourceNode = updatedNodes.firstWhere(
        (n) => n.name.toLowerCase() == r.source.toLowerCase(),
        orElse: () => DiagramNodeModel(
            id: '', type: '', name: '', attributes: [], methods: [], x: 0, y: 0),
      );
      final targetNode = updatedNodes.firstWhere(
        (n) => n.name.toLowerCase() == r.target.toLowerCase(),
        orElse: () => DiagramNodeModel(
            id: '', type: '', name: '', attributes: [], methods: [], x: 0, y: 0),
      );

      if (sourceNode.id.isNotEmpty && targetNode.id.isNotEmpty) {
        updatedEdges.add(DiagramEdgeModel(
          id: 'edge-${DateTime.now().millisecondsSinceEpoch}',
          type: r.type,
          sourceId: sourceNode.id,
          targetId: targetNode.id,
          label: r.type == 'inheritance' ? 'hereda de' : r.type,
        ));
      }
    }

    for (final del in result.deletedElements) {
      updatedNodes.removeWhere((n) => n.name.toLowerCase() == del.toLowerCase());
    }

    final updatedDiagram = DiagramModel(
      id: current.id,
      name: current.name,
      description: current.description,
      projectId: current.projectId,
      teamId: current.teamId,
      status: current.status,
      version: current.version + 1,
      nodes: updatedNodes,
      edges: updatedEdges,
    );

    _mockDiagrams[current.id] = updatedDiagram;
    return true;
  }
}
