import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_theme.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _emailController = TextEditingController(text: 'admin@classforge.io');
  final TextEditingController _passwordController = TextEditingController(text: 'Admin123!');
  late TextEditingController _urlController;
  final ApiService _apiService = ApiService();

  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _showUrlConfig = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: _apiService.activeBaseUrl);
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final success = await _apiService.login(
      _emailController.text.trim(),
      _passwordController.text,
    );

    if (mounted) {
      setState(() => _isLoading = false);

      if (success) {
        Navigator.pushReplacementNamed(context, '/home');
      } else {
        setState(() {
          _errorMessage = 'Credenciales inválidas o servidor inalcanzable. Puedes usar el Modo Offline.';
        });
      }
    }
  }

  void _enterOfflineMode() async {
    await _apiService.enableOfflineDemoMode();
    if (mounted) {
      Navigator.pushReplacementNamed(context, '/home');
    }
  }

  void _fillDemo(String email, String pass) {
    _emailController.text = email;
    _passwordController.text = pass;
    setState(() => _errorMessage = null);
  }

  void _saveUrl() async {
    await _apiService.setCustomBaseUrl(_urlController.text);
    setState(() => _showUrlConfig = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Endpoint de API actualizado.'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surface1,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          tooltip: 'Volver al Panel de Pruebas',
          onPressed: () => Navigator.pushReplacementNamed(context, '/test-panel'),
        ),
        title: Text(
          'Inicio de Sesión Cloud',
          style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_ethernet, size: 20),
            tooltip: 'Configurar URL Servidor',
            onPressed: () {
              setState(() => _showUrlConfig = !_showUrlConfig);
            },
          ),
        ],
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Logo & App Name
              Center(
                child: Container(
                  width: 60,
                  height: 60,
                  decoration: BoxDecoration(
                    color: AppTheme.primary,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.primary.withOpacity(0.4),
                        blurRadius: 16,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: const Icon(Icons.hub_outlined, color: Colors.white, size: 32),
                ),
              ),
              const SizedBox(height: 14),
              Text(
                'ClassForge Mobile',
                style: GoogleFonts.inter(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Text(
                'Conexión a Servidor Cloud / VPS',
                style: GoogleFonts.inter(
                  fontSize: 13,
                  color: AppTheme.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),

              // Panel de Configuración de URL (Colapsable)
              if (_showUrlConfig) ...[
                Container(
                  padding: const EdgeInsets.all(16),
                  margin: const EdgeInsets.only(bottom: 20),
                  decoration: BoxDecoration(
                    color: AppTheme.surface2,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.accent.withOpacity(0.4)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.dns_outlined, size: 16, color: AppTheme.accent),
                          const SizedBox(width: 6),
                          Text(
                            'Endpoint API del Servidor',
                            style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.accent),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _urlController,
                        style: GoogleFonts.jetBrainsMono(fontSize: 12, color: AppTheme.textPrimary),
                        decoration: const InputDecoration(
                          hintText: 'http://192.168.1.X:8000/api/v1',
                          isDense: true,
                          contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                        ),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          TextButton(
                            onPressed: () => setState(() => _showUrlConfig = false),
                            child: const Text('Cancelar', style: TextStyle(fontSize: 12)),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.accent,
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            ),
                            onPressed: _saveUrl,
                            child: const Text('Guardar URL', style: TextStyle(fontSize: 12, color: Colors.black)),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],

              // Login Card
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppTheme.surface2,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.border),
                ),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (_errorMessage != null) ...[
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppTheme.danger.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.danger.withOpacity(0.4)),
                          ),
                          child: Text(
                            _errorMessage!,
                            style: GoogleFonts.inter(fontSize: 12, color: AppTheme.danger),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],
                      Text(
                        'Correo Electrónico',
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 6),
                      TextFormField(
                        controller: _emailController,
                        keyboardType: TextInputType.emailAddress,
                        style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 14),
                        decoration: const InputDecoration(
                          hintText: 'correo@ejemplo.com',
                          prefixIcon: Icon(Icons.email_outlined, size: 20, color: AppTheme.textMuted),
                        ),
                        validator: (val) {
                          if (val == null || val.trim().isEmpty) return 'Ingresa un correo';
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Contraseña',
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 6),
                      TextFormField(
                        controller: _passwordController,
                        obscureText: _obscurePassword,
                        style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 14),
                        decoration: InputDecoration(
                          hintText: '••••••••',
                          prefixIcon: const Icon(Icons.lock_outline, size: 20, color: AppTheme.textMuted),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscurePassword ? Icons.visibility_off : Icons.visibility,
                              size: 20,
                              color: AppTheme.textMuted,
                            ),
                            onPressed: () {
                              setState(() => _obscurePassword = !_obscurePassword);
                            },
                          ),
                        ),
                        validator: (val) {
                          if (val == null || val.isEmpty) return 'Ingresa tu contraseña';
                          return null;
                        },
                      ),
                      const SizedBox(height: 20),
                      ElevatedButton(
                        onPressed: _isLoading ? null : _handleLogin,
                        child: _isLoading
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                              )
                            : Text(
                                'Conectar y Autenticar',
                                style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.bold),
                              ),
                      ),
                      const SizedBox(height: 10),
                      OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          side: const BorderSide(color: AppTheme.border),
                        ),
                        icon: const Icon(Icons.flash_on, size: 16, color: Color(0xFF10B981)),
                        label: Text(
                          'Acceso Inmediato en Modo Offline',
                          style: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF10B981)),
                        ),
                        onPressed: _enterOfflineMode,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Demo quick buttons
              Text(
                'Acceso Rápido de Prueba (Demo)',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: AppTheme.textMuted,
                  fontWeight: FontWeight.w600,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 10),
              Wrap(
                alignment: WrapAlignment.center,
                spacing: 8,
                children: [
                  ActionChip(
                    label: const Text('Admin'),
                    backgroundColor: AppTheme.surface3,
                    labelStyle: GoogleFonts.inter(fontSize: 11, color: AppTheme.textPrimary),
                    onPressed: () => _fillDemo('admin@classforge.io', 'Admin123!'),
                  ),
                  ActionChip(
                    label: const Text('Scrum Master'),
                    backgroundColor: AppTheme.surface3,
                    labelStyle: GoogleFonts.inter(fontSize: 11, color: AppTheme.textPrimary),
                    onPressed: () => _fillDemo('scrum@classforge.io', 'Scrum123!'),
                  ),
                  ActionChip(
                    label: const Text('Developer'),
                    backgroundColor: AppTheme.surface3,
                    labelStyle: GoogleFonts.inter(fontSize: 11, color: AppTheme.textPrimary),
                    onPressed: () => _fillDemo('dev@classforge.io', 'Dev12345!'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
