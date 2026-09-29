import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/role_permission_model.dart';
import '../permissions/permissions_matrix_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({Key? key}) : super(key: key);

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final ApiService _apiService = ApiService();
  final TextEditingController _serverController = TextEditingController();
  bool _isTestingServer = false;
  String? _serverPingResult;
  bool _isServerOk = false;

  @override
  void initState() {
    super.initState();
    _serverController.text = _apiService.activeBaseUrl;
  }

  @override
  void dispose() {
    _serverController.dispose();
    super.dispose();
  }

  Future<void> _testServerConnection() async {
    setState(() {
      _isTestingServer = true;
      _serverPingResult = null;
    });

    final url = _serverController.text.trim();
    final ok = await _apiService.pingServer(testUrl: url);

    if (mounted) {
      setState(() {
        _isTestingServer = false;
        _isServerOk = ok;
        _serverPingResult = ok
            ? '✓ Servidor conectado exitosamente'
            : '✗ No se pudo conectar al servidor';
      });

      if (ok) {
        await _apiService.setCustomBaseUrl(url);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Endpoint de servidor guardado exitosamente'),
            backgroundColor: Color(0xFF10B981),
          ),
        );
      }
    }
  }

  void _showChangePasswordDialog() {
    final oldPassController = TextEditingController();
    final newPassController = TextEditingController();
    final confirmPassController = TextEditingController();
    bool obscure = true;
    bool isLoading = false;
    String? error;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setModalState) => AlertDialog(
          backgroundColor: AppTheme.cardDark,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Row(
            children: [
              const Icon(Icons.lock_outline, color: AppTheme.accentBlue),
              const SizedBox(width: 8),
              Text(
                'Cambiar Contraseña',
                style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (error != null) ...[
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.redAccent.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.redAccent.withOpacity(0.4)),
                    ),
                    child: Text(
                      error!,
                      style: GoogleFonts.inter(color: Colors.redAccent, fontSize: 12),
                    ),
                  ),
                  const SizedBox(height: 10),
                ],
                Text('Contraseña Actual', style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary)),
                const SizedBox(height: 4),
                TextField(
                  controller: oldPassController,
                  obscureText: obscure,
                  style: GoogleFonts.inter(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: 'Ingresa tu contraseña actual',
                    hintStyle: GoogleFonts.inter(color: Colors.white30, fontSize: 13),
                    filled: true,
                    fillColor: AppTheme.primaryDark,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                  ),
                ),
                const SizedBox(height: 12),
                Text('Nueva Contraseña', style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary)),
                const SizedBox(height: 4),
                TextField(
                  controller: newPassController,
                  obscureText: obscure,
                  style: GoogleFonts.inter(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: 'Mínimo 6 caracteres',
                    hintStyle: GoogleFonts.inter(color: Colors.white30, fontSize: 13),
                    filled: true,
                    fillColor: AppTheme.primaryDark,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                  ),
                ),
                const SizedBox(height: 12),
                Text('Confirmar Nueva Contraseña', style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary)),
                const SizedBox(height: 4),
                TextField(
                  controller: confirmPassController,
                  obscureText: obscure,
                  style: GoogleFonts.inter(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: 'Repite la contraseña',
                    hintStyle: GoogleFonts.inter(color: Colors.white30, fontSize: 13),
                    filled: true,
                    fillColor: AppTheme.primaryDark,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Checkbox(
                      value: !obscure,
                      activeColor: AppTheme.accentBlue,
                      onChanged: (val) {
                        setModalState(() {
                          obscure = !obscure;
                        });
                      },
                    ),
                    Text('Mostrar contraseñas', style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 12)),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text('Cancelar', style: GoogleFonts.inter(color: Colors.white60)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accentBlue),
              onPressed: isLoading
                  ? null
                  : () async {
                      final oldP = oldPassController.text.trim();
                      final newP = newPassController.text.trim();
                      final confP = confirmPassController.text.trim();

                      if (oldP.isEmpty || newP.isEmpty) {
                        setModalState(() => error = 'Por favor completa todos los campos.');
                        return;
                      }
                      if (newP.length < 6) {
                        setModalState(() => error = 'La nueva contraseña debe tener al menos 6 caracteres.');
                        return;
                      }
                      if (newP != confP) {
                        setModalState(() => error = 'Las nuevas contraseñas no coinciden.');
                        return;
                      }

                      setModalState(() {
                        isLoading = true;
                        error = null;
                      });

                      final success = await _apiService.changePassword(oldP, newP);

                      if (success) {
                        Navigator.pop(ctx);
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Contraseña actualizada con éxito'),
                            backgroundColor: Color(0xFF10B981),
                          ),
                        );
                      } else {
                        setModalState(() {
                          isLoading = false;
                          error = 'Contraseña actual incorrecta o error de servidor.';
                        });
                      }
                    },
              child: isLoading
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Text('Guardar', style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }

  void _showEditProfileDialog() {
    final user = _apiService.currentUser;
    final nameController = TextEditingController(text: user?.name ?? '');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.cardDark,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text('Editar Perfil', style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Nombre Completo', style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary)),
            const SizedBox(height: 4),
            TextField(
              controller: nameController,
              style: GoogleFonts.inter(color: Colors.white),
              decoration: InputDecoration(
                filled: true,
                fillColor: AppTheme.primaryDark,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Cancelar', style: GoogleFonts.inter(color: Colors.white60)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accentBlue),
            onPressed: () async {
              final newName = nameController.text.trim();
              if (newName.isNotEmpty) {
                await _apiService.updateProfile(name: newName);
                setState(() {});
                Navigator.pop(ctx);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Perfil actualizado'),
                    backgroundColor: Color(0xFF10B981),
                  ),
                );
              }
            },
            child: Text('Actualizar', style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = _apiService.currentUser;
    final role = user?.role ?? 'admin';
    final roleName = RolePermissionData.getRoleDisplayName(role);
    final roleColor = RolePermissionData.getRoleBadgeColor(role);

    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(
        title: Text(
          'Perfil & Ajustes de Cuenta',
          style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        backgroundColor: AppTheme.cardDark,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Tarjeta de Usuario
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppTheme.cardDark,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white.withOpacity(0.08)),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 32,
                    backgroundColor: roleColor.withOpacity(0.2),
                    child: Text(
                      user != null && user.name.isNotEmpty ? user.name[0].toUpperCase() : 'U',
                      style: GoogleFonts.inter(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: roleColor,
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user?.name ?? 'Ing. Alejandro Melgar',
                          style: GoogleFonts.inter(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          user?.email ?? 'admin@classforge.io',
                          style: GoogleFonts.inter(
                            fontSize: 13,
                            color: AppTheme.textSecondary,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: roleColor.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: roleColor.withOpacity(0.4)),
                          ),
                          child: Text(
                            roleName,
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: roleColor,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.edit_outlined, color: AppTheme.accentBlue),
                    onPressed: _showEditProfileDialog,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Acceso Rápido a Privilegios y Seguridad
            Text(
              'SEGURIDAD & ACCESO',
              style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppTheme.textSecondary,
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 10),

            _buildActionTile(
              icon: Icons.lock_reset_outlined,
              title: 'Cambiar Contraseña',
              subtitle: 'Actualiza tu clave de acceso al backend',
              onTap: _showChangePasswordDialog,
            ),
            const SizedBox(height: 10),
            _buildActionTile(
              icon: Icons.admin_panel_settings_outlined,
              title: 'Ver Matriz de Privilegios por Rol',
              subtitle: 'Consulta las capacidades de Admin, Scrum Master y Dev',
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const PermissionsMatrixScreen()),
                );
              },
            ),

            const SizedBox(height: 24),
            Text(
              'CONEXIÓN AL BACKEND & BASE DE DATOS',
              style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppTheme.textSecondary,
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 10),

            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.cardDark,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white.withOpacity(0.08)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.cloud_sync_outlined, color: AppTheme.accentBlue, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        'URL del Backend FastAPI',
                        style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Ingresa la URL pública de Cloudflare Tunnel o la IP de tu servidor desplegado:',
                    style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _serverController,
                    style: GoogleFonts.inter(color: Colors.white, fontSize: 13),
                    decoration: InputDecoration(
                      hintText: 'https://xxxx.trycloudflare.com/api/v1',
                      hintStyle: GoogleFonts.inter(color: Colors.white30, fontSize: 12),
                      filled: true,
                      fillColor: AppTheme.primaryDark,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: BorderSide.none,
                      ),
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.check, color: AppTheme.accentBlue),
                        onPressed: _testServerConnection,
                      ),
                    ),
                  ),
                  if (_serverPingResult != null) ...[
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Icon(
                          _isServerOk ? Icons.check_circle : Icons.error_outline,
                          size: 16,
                          color: _isServerOk ? const Color(0xFF10B981) : Colors.redAccent,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            _serverPingResult!,
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              color: _isServerOk ? const Color(0xFF10B981) : Colors.redAccent,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.accentBlue,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      onPressed: _isTestingServer ? null : _testServerConnection,
                      icon: _isTestingServer
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : const Icon(Icons.wifi_tethering, size: 18, color: Colors.white),
                      label: Text(
                        _isTestingServer ? 'Probando Conexión...' : 'Probar & Guardar Endpoint',
                        style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: Colors.redAccent.withOpacity(0.5)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                icon: const Icon(Icons.logout, color: Colors.redAccent, size: 18),
                label: Text(
                  'Cerrar Sesión',
                  style: GoogleFonts.inter(
                    fontWeight: FontWeight.bold,
                    color: Colors.redAccent,
                  ),
                ),
                onPressed: () async {
                  await _apiService.logout();
                  if (mounted) {
                    Navigator.pushReplacementNamed(context, '/login');
                  }
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.cardDark,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withOpacity(0.06)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppTheme.accentBlue.withOpacity(0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: AppTheme.accentBlue, size: 20),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: AppTheme.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: Colors.white30),
          ],
        ),
      ),
    );
  }
}
