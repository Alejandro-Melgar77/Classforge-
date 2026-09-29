import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/project_model.dart';
import '../diagrams/diagram_viewer_screen.dart';
import 'create_project_screen.dart';

class ProjectsScreen extends StatefulWidget {
  const ProjectsScreen({Key? key}) : super(key: key);

  @override
  State<ProjectsScreen> createState() => _ProjectsScreenState();
}

class _ProjectsScreenState extends State<ProjectsScreen> {
  final ApiService _apiService = ApiService();
  List<ProjectModel> _projects = [];
  String _selectedStatus = 'all';
  String _searchQuery = '';
  bool _isLoading = true;

  final List<Map<String, String>> _statusFilters = [
    {'key': 'all', 'label': 'Todos'},
    {'key': 'in_progress', 'label': 'En Progreso'},
    {'key': 'completed', 'label': 'Completados'},
    {'key': 'review', 'label': 'Revisión'},
    {'key': 'archived', 'label': 'Archivados'},
  ];

  @override
  void initState() {
    super.initState();
    _loadProjects();
  }

  Future<void> _loadProjects() async {
    setState(() => _isLoading = true);
    final list = await _apiService.getProjects(
      status: _selectedStatus == 'all' ? null : _selectedStatus,
    );
    if (mounted) {
      setState(() {
        _projects = list;
        _isLoading = false;
      });
    }
  }

  List<ProjectModel> get _filteredProjects {
    if (_searchQuery.isEmpty) return _projects;
    return _projects
        .where((p) =>
            p.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
            p.description.toLowerCase().contains(_searchQuery.toLowerCase()))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surface1,
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppTheme.accentBlue,
        icon: const Icon(Icons.add, color: Colors.white),
        label: Text(
          'Nuevo Proyecto',
          style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: Colors.white),
        ),
        onPressed: () async {
          final res = await Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const CreateProjectScreen()),
          );
          if (res == true) {
            _loadProjects();
          }
        },
      ),
      body: Column(
        children: [
          // Search & Filter Header
          Container(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            color: AppTheme.surface2,
            child: Column(
              children: [
                TextField(
                  style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 14),
                  decoration: InputDecoration(
                    hintText: 'Buscar proyectos...',
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
                const SizedBox(height: 10),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: _statusFilters.map((f) {
                      final isSelected = _selectedStatus == f['key'];
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          label: Text(f['label']!),
                          selected: isSelected,
                          selectedColor: AppTheme.primary,
                          backgroundColor: AppTheme.surface3,
                          labelStyle: GoogleFonts.inter(
                            fontSize: 12,
                            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                            color: isSelected ? Colors.white : AppTheme.textSecondary,
                          ),
                          onSelected: (selected) {
                            if (selected) {
                              setState(() => _selectedStatus = f['key']!);
                              _loadProjects();
                            }
                          },
                        ),
                      );
                    }).toList(),
                  ),
                ),
              ],
            ),
          ),

          // Projects List
          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadProjects,
              color: AppTheme.primary,
              backgroundColor: AppTheme.surface2,
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
                  : _filteredProjects.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.folder_open, size: 48, color: AppTheme.textMuted),
                              const SizedBox(height: 12),
                              Text(
                                'No se encontraron proyectos',
                                style: GoogleFonts.inter(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                  color: AppTheme.textSecondary,
                                ),
                              ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _filteredProjects.length,
                          itemBuilder: (context, index) {
                            final project = _filteredProjects[index];
                            return _buildProjectItem(project);
                          },
                        ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProjectItem(ProjectModel project) {
    Color statusColor;
    switch (project.status) {
      case 'completed':
        statusColor = const Color(0xFF10B981);
        break;
      case 'review':
        statusColor = AppTheme.warning;
        break;
      case 'in_progress':
      default:
        statusColor = AppTheme.primary;
        break;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _openProjectDiagrams(project),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      project.name,
                      style: GoogleFonts.inter(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: statusColor.withOpacity(0.3)),
                    ),
                    child: Text(
                      project.status.toUpperCase(),
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: statusColor,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                project.description.isNotEmpty ? project.description : 'Sin descripción',
                style: GoogleFonts.inter(fontSize: 13, color: AppTheme.textSecondary),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.group_outlined, size: 14, color: AppTheme.textMuted),
                      const SizedBox(width: 4),
                      Text(
                        project.teamName ?? 'Personal',
                        style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textMuted),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      Text(
                        'Explorar Diagramas',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: AppTheme.primaryLight,
                          fontWeight: FontWeight.w600,
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

  Future<void> _openProjectDiagrams(ProjectModel project) async {
    final diagrams = await _apiService.getDiagrams(projectId: project.id);
    if (!mounted) return;

    if (diagrams.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Este proyecto aún no contiene diagramas UML.'),
          backgroundColor: AppTheme.surface3,
        ),
      );
      return;
    }

    if (diagrams.length == 1) {
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => DiagramViewerScreen(
            diagramId: diagrams.first.id,
            initialName: diagrams.first.name,
          ),
        ),
      );
      return;
    }

    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.surface2,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Diagramas UML en ${project.name}',
                style: GoogleFonts.inter(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 12),
              ...diagrams.map((d) {
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.account_tree_outlined, color: AppTheme.primary),
                  title: Text(d.name, style: GoogleFonts.inter(color: AppTheme.textPrimary)),
                  subtitle: Text('Versión ${d.version} • ${d.status}',
                      style: GoogleFonts.inter(color: AppTheme.textMuted, fontSize: 12)),
                  trailing: const Icon(Icons.chevron_right, color: AppTheme.textSecondary),
                  onTap: () {
                    Navigator.pop(context);
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => DiagramViewerScreen(
                          diagramId: d.id,
                          initialName: d.name,
                        ),
                      ),
                    );
                  },
                );
              }),
            ],
          ),
        );
      },
    );
  }
}
