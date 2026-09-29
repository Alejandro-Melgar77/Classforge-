import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/services/api_service.dart';
import '../../core/services/push_notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/team_model.dart';

class CreateProjectScreen extends StatefulWidget {
  const CreateProjectScreen({Key? key}) : super(key: key);

  @override
  State<CreateProjectScreen> createState() => _CreateProjectScreenState();
}

class _CreateProjectScreenState extends State<CreateProjectScreen> {
  final ApiService _apiService = ApiService();
  final _formKey = GlobalKey<FormState>();

  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _premiseController = TextEditingController();

  String _selectedType = 'team'; // team | personal
  String? _selectedTeamId;
  List<TeamModel> _teams = [];
  bool _isLoadingTeams = true;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _loadTeams();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _premiseController.dispose();
    super.dispose();
  }

  Future<void> _loadTeams() async {
    final teams = await _apiService.getTeams();
    if (mounted) {
      setState(() {
        _teams = teams;
        _isLoadingTeams = false;
        if (teams.isNotEmpty) {
          _selectedTeamId = teams.first.id;
        }
      });
    }
  }

  Future<void> _submitProject() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isSubmitting = true);

    final name = _nameController.text.trim();
    final description = _descriptionController.text.trim();
    final premise = _premiseController.text.trim();

    final project = await _apiService.createProject(
      name: name,
      description: description,
      premise: premise,
      type: _selectedType,
      teamId: _selectedType == 'team' ? _selectedTeamId : null,
    );

    if (mounted) {
      setState(() => _isSubmitting = false);

      if (project != null) {
        // Disparar notificación push en el teléfono
        PushNotificationService().triggerInstantPush(
          title: '📁 Nuevo Proyecto Creado',
          message: 'Se generó el proyecto "$name" con su diagrama conceptual inicial.',
          type: 'project_update',
        );

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Proyecto "$name" creado exitosamente'),
            backgroundColor: const Color(0xFF10B981),
          ),
        );

        Navigator.pop(context, true);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Error al crear el proyecto en el servidor'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(
        title: Text(
          'Nuevo Proyecto de Software',
          style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        backgroundColor: AppTheme.cardDark,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppTheme.accentBlue.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppTheme.accentBlue.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.architecture_outlined, color: AppTheme.accentBlue, size: 24),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Define la premisa y arquitectura del proyecto para que la IA genere el diagrama inicial editable en Web y Móvil.',
                        style: GoogleFonts.inter(fontSize: 12, color: Colors.white70, height: 1.3),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Nombre
              Text('Nombre del Proyecto', style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white)),
              const SizedBox(height: 6),
              TextFormField(
                controller: _nameController,
                style: GoogleFonts.inter(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Ej. Sistema de Pagos Core Banking',
                  hintStyle: GoogleFonts.inter(color: Colors.white30, fontSize: 13),
                  filled: true,
                  fillColor: AppTheme.cardDark,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
                validator: (val) => val == null || val.trim().isEmpty ? 'El nombre es obligatorio' : null,
              ),
              const SizedBox(height: 16),

              // Premisa / Prompt de Arquitectura
              Text('Premisa / Requerimientos de Arquitectura', style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white)),
              const SizedBox(height: 6),
              TextFormField(
                controller: _premiseController,
                maxLines: 3,
                style: GoogleFonts.inter(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Describe el dominio de negocio, entidades principales y reglas (ej. Microservicio de pagos con autenticación, clientes y pasarelas)',
                  hintStyle: GoogleFonts.inter(color: Colors.white30, fontSize: 12),
                  filled: true,
                  fillColor: AppTheme.cardDark,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
                validator: (val) => val == null || val.trim().isEmpty ? 'La premisa es requerida para el modelado' : null,
              ),
              const SizedBox(height: 16),

              // Tipo de Proyecto
              Text('Tipo de Proyecto', style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white)),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: _buildTypeOption('team', 'Célula Scrum (Equipo)', Icons.groups_outlined),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildTypeOption('personal', 'Personal', Icons.person_outline),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Asignación de Equipo
              if (_selectedType == 'team') ...[
                Text('Célula Scrum Asignada', style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white)),
                const SizedBox(height: 6),
                _isLoadingTeams
                    ? const Center(child: CircularProgressIndicator())
                    : Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        decoration: BoxDecoration(
                          color: AppTheme.cardDark,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<String>(
                            value: _selectedTeamId,
                            isExpanded: true,
                            dropdownColor: AppTheme.cardDark,
                            style: GoogleFonts.inter(color: Colors.white),
                            items: _teams.map((t) {
                              return DropdownMenuItem<String>(
                                value: t.id,
                                child: Text(t.name),
                              );
                            }).toList(),
                            onChanged: (val) {
                              setState(() => _selectedTeamId = val);
                            },
                          ),
                        ),
                      ),
                const SizedBox(height: 16),
              ],

              // Descripción Opcional
              Text('Descripción Adicional (Opcional)', style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.white)),
              const SizedBox(height: 6),
              TextFormField(
                controller: _descriptionController,
                maxLines: 2,
                style: GoogleFonts.inter(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Comentarios sobre el sprint o metas de entrega',
                  hintStyle: GoogleFonts.inter(color: Colors.white30, fontSize: 12),
                  filled: true,
                  fillColor: AppTheme.cardDark,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 28),

              // Botón Crear
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.accentBlue,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  onPressed: _isSubmitting ? null : _submitProject,
                  icon: _isSubmitting
                      ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.rocket_launch, color: Colors.white, size: 20),
                  label: Text(
                    _isSubmitting ? 'Creando e Inicializando...' : 'Generar Proyecto & Diagrama Inicial',
                    style: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTypeOption(String type, String label, IconData icon) {
    final isSelected = _selectedType == type;
    return InkWell(
      onTap: () => setState(() => _selectedType = type),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.accentBlue.withOpacity(0.18) : AppTheme.cardDark,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? AppTheme.accentBlue : Colors.white10,
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Column(
          children: [
            Icon(icon, color: isSelected ? AppTheme.accentBlue : Colors.white60, size: 22),
            const SizedBox(height: 6),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                color: isSelected ? Colors.white : Colors.white70,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
