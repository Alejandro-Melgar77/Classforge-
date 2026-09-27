import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/team_model.dart';

class TeamsScreen extends StatefulWidget {
  const TeamsScreen({Key? key}) : super(key: key);

  @override
  State<TeamsScreen> createState() => _TeamsScreenState();
}

class _TeamsScreenState extends State<TeamsScreen> {
  final ApiService _apiService = ApiService();
  List<TeamModel> _teams = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadTeams();
  }

  Future<void> _loadTeams() async {
    setState(() => _isLoading = true);
    final teams = await _apiService.getTeams();
    if (mounted) {
      setState(() {
        _teams = teams;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surface1,
      appBar: AppBar(
        title: Text(
          'Equipos de Desarrollo Scrum',
          style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _loadTeams,
        color: AppTheme.primary,
        backgroundColor: AppTheme.surface2,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
            : ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                itemCount: _teams.length,
                itemBuilder: (context, index) {
                  final team = _teams[index];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 14),
                    color: AppTheme.surface2,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: const BorderSide(color: AppTheme.border),
                    ),
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
                                  team.name,
                                  style: GoogleFonts.inter(
                                    fontSize: 15,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.textPrimary,
                                  ),
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: AppTheme.primary.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(color: AppTheme.primary.withOpacity(0.4)),
                                ),
                                child: Text(
                                  '${team.membersCount} Miembros',
                                  style: GoogleFonts.inter(
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.primaryLight,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            team.description,
                            style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary),
                          ),
                          const SizedBox(height: 12),
                          Row(
                            children: [
                              const Icon(Icons.manage_accounts_outlined, size: 16, color: AppTheme.accent),
                              const SizedBox(width: 6),
                              Text(
                                'Scrum Master: ',
                                style: GoogleFonts.inter(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: AppTheme.textPrimary,
                                ),
                              ),
                              Text(
                                team.scrumMasterName,
                                style: GoogleFonts.inter(
                                  fontSize: 12,
                                  color: AppTheme.accent,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 6,
                            runSpacing: 6,
                            children: team.memberNames.map((m) {
                              return Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: AppTheme.surface3,
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  m,
                                  style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textSecondary),
                                ),
                              );
                            }).toList(),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }
}
