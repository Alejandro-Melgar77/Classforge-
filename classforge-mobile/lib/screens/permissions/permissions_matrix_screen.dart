import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/theme/app_theme.dart';
import '../../models/role_permission_model.dart';

class PermissionsMatrixScreen extends StatelessWidget {
  const PermissionsMatrixScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(
        title: Text(
          'Matriz de Privilegios y Roles',
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
            // Resumen de Roles
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.cardDark,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.accentBlue.withOpacity(0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.shield_outlined, color: AppTheme.accentBlue, size: 24),
                      const SizedBox(width: 8),
                      Text(
                        'Control de Acceso Basado en Roles (RBAC)',
                        style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'ClassForge implementa un modelo de seguridad por capas donde cada rol cuenta con privilegios específicos sobre proyectos, equipos, diagramas y generación de código.',
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      color: AppTheme.textSecondary,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      _buildRoleBadge('Admin', const Color(0xFFEF4444)),
                      const SizedBox(width: 8),
                      _buildRoleBadge('Scrum Master', const Color(0xFFF59E0B)),
                      const SizedBox(width: 8),
                      _buildRoleBadge('Developer', const Color(0xFF3B82F6)),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'DETALLE DE PRIVILEGIOS POR CAPACIDAD',
              style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppTheme.textSecondary,
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 12),

            // Lista de Permisos
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: RolePermissionData.permissions.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final perm = RolePermissionData.permissions[index];
                return Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppTheme.cardDark,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: Colors.white.withOpacity(0.06)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: AppTheme.accentBlue.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Icon(perm.icon, color: AppTheme.accentBlue, size: 20),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              perm.title,
                              style: GoogleFonts.inter(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        perm.description,
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: AppTheme.textSecondary,
                        ),
                      ),
                      const SizedBox(height: 12),
                      const Divider(color: Colors.white10, height: 1),
                      const SizedBox(height: 10),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _buildPermissionCheck('Admin', perm.admin, const Color(0xFFEF4444)),
                          _buildPermissionCheck('Scrum Master', perm.scrumMaster, const Color(0xFFF59E0B)),
                          _buildPermissionCheck('Developer', perm.dev, const Color(0xFF3B82F6)),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRoleBadge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Text(
        label,
        style: GoogleFonts.inter(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: color,
        ),
      ),
    );
  }

  Widget _buildPermissionCheck(String roleName, bool isGranted, Color color) {
    return Row(
      children: [
        Icon(
          isGranted ? Icons.check_circle : Icons.cancel,
          size: 16,
          color: isGranted ? const Color(0xFF10B981) : Colors.white24,
        ),
        const SizedBox(width: 4),
        Text(
          roleName,
          style: GoogleFonts.inter(
            fontSize: 11,
            color: isGranted ? Colors.white70 : Colors.white30,
            fontWeight: isGranted ? FontWeight.w600 : FontWeight.normal,
          ),
        ),
      ],
    );
  }
}
