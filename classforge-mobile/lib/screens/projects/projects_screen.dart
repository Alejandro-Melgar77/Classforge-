import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/diagram_model.dart';
import '../diagrams/diagram_viewer_screen.dart';

class ProjectsScreen extends StatefulWidget {
  const ProjectsScreen({Key? key}) : super(key: key);

  @override
  State<ProjectsScreen> createState() => _ProjectsScreenState();
}

class _ProjectsScreenState extends State<ProjectsScreen> {
  final ApiService _apiService = ApiService();
  List<DiagramModel> _diagrams = [];
  String _searchQuery = '';
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadDiagrams();
  }

  Future<void> _loadDiagrams() async {
    setState(() => _isLoading = true);
    final all = await _apiService.getDiagrams();
    final user = _apiService.currentUser;

    // Filtro estricto (Req 3): solo mostrar proyectos/diagramas en los que está incluido el usuario
    final filtered = all.where((d) {
      if (user == null) return true;
      if (user.role == 'admin') return true;
      final isCreator = (d.createdBy != null && (d.createdBy == user.id || d.createdBy == user.name || d.createdBy == user.email));
      final isMember = d.memberIds.contains(user.id);
      final isTeamMember = d.teamId != null && user.teamIds.contains(d.teamId);
      final isNamedTeam = d.teamName != null && user.name.isNotEmpty && d.teamName!.toLowerCase().contains(user.name.toLowerCase());
      return isCreator || isMember || isTeamMember || isNamedTeam;
    }).toList();

    if (mounted) {
      setState(() {
        _diagrams = filtered;
        _isLoading = false;
      });
    }
  }

  List<DiagramModel> get _filteredDiagrams {
    if (_searchQuery.isEmpty) return _diagrams;
    return _diagrams
        .where((d) =>
            d.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
            d.description.toLowerCase().contains(_searchQuery.toLowerCase()))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final user = _apiService.currentUser;

    return Scaffold(
      backgroundColor: AppTheme.surface1,
      body: Column(
        children: [
          // Header Informativo del Usuario y Filtro
          Container(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
            color: AppTheme.surface2,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Proyectos y Diagramas Asignados',
                          style: GoogleFonts.inter(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Usuario: ${user?.name ?? "Invitado"} (${user?.role.toUpperCase() ?? "USER"})',
                          style: GoogleFonts.inter(fontSize: 12, color: AppTheme.primaryLight),
                        ),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh, color: AppTheme.textSecondary),
                      tooltip: 'Actualizar en tiempo real',
                      onPressed: _loadDiagrams,
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                TextField(
                  style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 14),
                  decoration: InputDecoration(
                    hintText: 'Buscar por nombre o descripción...',
                    prefixIcon: const Icon(Icons.search, color: AppTheme.textSecondary, size: 20),
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: AppTheme.border),
                    ),
                  ),
                  onChanged: (val) {
                    setState(() => _searchQuery = val.trim());
                  },
                ),
              ],
            ),
          ),

          // Lista de Diagramas
          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadDiagrams,
              color: AppTheme.primary,
              backgroundColor: AppTheme.surface2,
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
                  : _filteredDiagrams.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(24.0),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Icon(Icons.account_tree_outlined, size: 54, color: AppTheme.textMuted),
                                const SizedBox(height: 14),
                                Text(
                                  'No tienes proyectos asignados',
                                  style: GoogleFonts.inter(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.textPrimary,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  'Solo se muestran los diagramas donde eres creador o miembro del equipo colaborativo.',
                                  style: GoogleFonts.inter(fontSize: 13, color: AppTheme.textSecondary),
                                  textAlign: TextAlign.center,
                                ),
                                const SizedBox(height: 16),
                                OutlinedButton.icon(
                                  onPressed: _loadDiagrams,
                                  icon: const Icon(Icons.refresh, size: 16),
                                  label: const Text('Reintentar sincronización'),
                                ),
                              ],
                            ),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _filteredDiagrams.length,
                          itemBuilder: (context, index) {
                            final diagram = _filteredDiagrams[index];
                            return _buildDiagramCard(diagram);
                          },
                        ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDiagramCard(DiagramModel diagram) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      color: AppTheme.surface2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppTheme.border),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => DiagramViewerScreen(
                diagramId: diagram.id,
                initialName: diagram.name,
              ),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppTheme.primary.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Icon(Icons.account_tree_rounded, color: AppTheme.primaryLight, size: 20),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            diagram.name,
                            style: GoogleFonts.inter(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.textPrimary,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withOpacity(0.15),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF10B981).withOpacity(0.3)),
                    ),
                    child: Text(
                      'v${diagram.version}',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: const Color(0xFF10B981),
                      ),
                    ),
                  ),
                ],
              ),
              if (diagram.description.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text(
                  diagram.description,
                  style: GoogleFonts.inter(fontSize: 13, color: AppTheme.textSecondary),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              const SizedBox(height: 14),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.crop_square_rounded, size: 15, color: AppTheme.accent),
                      const SizedBox(width: 4),
                      Text(
                        '${diagram.nodes.length} clases',
                        style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textMuted),
                      ),
                      const SizedBox(width: 12),
                      const Icon(Icons.timeline, size: 15, color: AppTheme.accentBlue),
                      const SizedBox(width: 4),
                      Text(
                        '${diagram.edges.length} relaciones',
                        style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textMuted),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      Text(
                        'Ver en Tiempo Real',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: AppTheme.primaryLight,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(width: 4),
                      const Icon(Icons.arrow_forward_ios, size: 11, color: AppTheme.primaryLight),
                    ],
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
