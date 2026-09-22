import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/services/offline_nlu_service.dart';
import '../../core/theme/app_theme.dart';

class OfflineAssistantScreen extends StatefulWidget {
  const OfflineAssistantScreen({Key? key}) : super(key: key);

  @override
  State<OfflineAssistantScreen> createState() => _OfflineAssistantScreenState();
}

class _OfflineAssistantScreenState extends State<OfflineAssistantScreen> {
  final TextEditingController _textController = TextEditingController();
  final OfflineNluService _nluService = OfflineNluService();

  final List<Map<String, dynamic>> _history = [];
  bool _isListening = false;

  final List<String> _quickSuggestions = [
    'crear clase Usuario con atributos id:int, email:string',
    'crear clase Pedido con atributos total:double',
    'relacionar Usuario con Pedido por composicion',
    'hacer que Cliente herede de Persona',
    'agregar atributo activo:boolean a la clase Usuario',
    'agregar metodo login(email, pass):boolean a la clase Usuario',
    'buscar clase Usuario',
    'resumen del diagrama',
  ];

  void _executeCommand(String text) {
    if (text.trim().isEmpty) return;

    final result = _nluService.parse(text.trim());
    setState(() {
      _history.insert(0, {
        'input': text.trim(),
        'result': result,
        'timestamp': DateTime.now(),
      });
      _textController.clear();
    });
  }

  void _toggleVoiceSimulation() {
    setState(() => _isListening = !_isListening);

    if (_isListening) {
      // Simula captura de voz en dispositivo móvil
      Future.delayed(const Duration(milliseconds: 1500), () {
        if (mounted && _isListening) {
          setState(() {
            _isListening = false;
            _textController.text = 'crear clase Factura con atributos id:long, monto:double';
          });
          _executeCommand(_textController.text);
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surface1,
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.bolt, color: AppTheme.accent, size: 22),
            const SizedBox(width: 8),
            Text(
              'Asistente IA Offline',
              style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        actions: [
          Container(
            margin: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppTheme.accent.withOpacity(0.15),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.accent.withOpacity(0.4)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 6,
                  height: 6,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppTheme.accent,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  '0MB • <1ms',
                  style: GoogleFonts.inter(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.accent,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // Suggestions bar
          Container(
            height: 48,
            padding: const EdgeInsets.symmetric(vertical: 6),
            color: AppTheme.surface2,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              itemCount: _quickSuggestions.length,
              itemBuilder: (context, index) {
                final suggestion = _quickSuggestions[index];
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ActionChip(
                    label: Text(suggestion),
                    backgroundColor: AppTheme.surface3,
                    labelStyle: GoogleFonts.inter(
                      fontSize: 11,
                      color: AppTheme.textPrimary,
                    ),
                    onPressed: () {
                      _textController.text = suggestion;
                      _executeCommand(suggestion);
                    },
                  ),
                );
              },
            ),
          ),

          // Conversation / History log
          Expanded(
            child: _history.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 32),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: AppTheme.primary.withOpacity(0.1),
                              border: Border.all(color: AppTheme.primary.withOpacity(0.2)),
                            ),
                            child: const Icon(Icons.mic_none, size: 48, color: AppTheme.primaryLight),
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Motor NLU On-Device',
                            style: GoogleFonts.inter(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Comandos en lenguaje natural por texto o voz procesados 100% en tu dispositivo sin necesidad de conexión ni descargas pesadas.',
                            style: GoogleFonts.inter(
                              fontSize: 13,
                              color: AppTheme.textSecondary,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  )
                : ListView.builder(
                    reverse: true,
                    padding: const EdgeInsets.all(16),
                    itemCount: _history.length,
                    itemBuilder: (context, index) {
                      final item = _history[index];
                      final input = item['input'] as String;
                      final NluResult res = item['result'] as NluResult;
                      return _buildHistoryItem(input, res);
                    },
                  ),
          ),

          // Voice active indicator
          if (_isListening)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 8),
              color: AppTheme.danger.withOpacity(0.15),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.mic, color: AppTheme.danger, size: 18),
                  const SizedBox(width: 8),
                  Text(
                    'Escuchando comando de voz offline...',
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: AppTheme.danger,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),

          // Bottom Input bar
          Container(
            padding: const EdgeInsets.all(12),
            color: AppTheme.surface2,
            child: Row(
              children: [
                IconButton(
                  icon: Icon(
                    _isListening ? Icons.mic : Icons.mic_none,
                    color: _isListening ? AppTheme.danger : AppTheme.accent,
                  ),
                  tooltip: 'Comando por voz offline',
                  onPressed: _toggleVoiceSimulation,
                ),
                Expanded(
                  child: TextField(
                    controller: _textController,
                    style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 14),
                    decoration: InputDecoration(
                      hintText: 'Comando UML ej: crear clase Cuenta...',
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(20),
                        borderSide: const BorderSide(color: AppTheme.border),
                      ),
                    ),
                    onSubmitted: _executeCommand,
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.send, color: AppTheme.primaryLight),
                  onPressed: () => _executeCommand(_textController.text),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHistoryItem(String input, NluResult res) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // User input bubble
          Align(
            alignment: Alignment.centerRight,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: AppTheme.primary,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Text(
                input,
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),

          // Assistant / NLU Result bubble
          Align(
            alignment: Alignment.centerLeft,
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.surface2,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppTheme.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.bolt, color: AppTheme.accent, size: 16),
                          const SizedBox(width: 4),
                          Text(
                            res.action.toUpperCase(),
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.accent,
                            ),
                          ),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.surface1,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppTheme.border),
                        ),
                        child: Text(
                          '⚡ ${res.latencyMs}ms',
                          style: GoogleFonts.jetBrainsMono(
                            fontSize: 10,
                            color: AppTheme.textSecondary,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    res.explanation,
                    style: GoogleFonts.inter(fontSize: 13, color: AppTheme.textPrimary),
                  ),

                  // Structured classes preview
                  if (res.classes.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    ...res.classes.map((c) => Container(
                          margin: const EdgeInsets.only(top: 6),
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: AppTheme.surface1,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.primary.withOpacity(0.3)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Clase: ${c.name}',
                                  style: GoogleFonts.inter(
                                      fontWeight: FontWeight.bold,
                                      color: AppTheme.primaryLight,
                                      fontSize: 12)),
                              if (c.attributes.isNotEmpty)
                                Text(
                                  'Atributos: ${c.attributes.map((a) => "${a.name}:${a.type}").join(", ")}',
                                  style: GoogleFonts.jetBrainsMono(
                                      fontSize: 11, color: AppTheme.textSecondary),
                                ),
                              if (c.methods.isNotEmpty)
                                Text(
                                  'Métodos: ${c.methods.map((m) => "${m.name}${m.params}").join(", ")}',
                                  style: GoogleFonts.jetBrainsMono(
                                      fontSize: 11, color: AppTheme.textSecondary),
                                ),
                            ],
                          ),
                        )),
                  ],

                  // Structured relations preview
                  if (res.relations.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    ...res.relations.map((r) => Container(
                          margin: const EdgeInsets.only(top: 4),
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: AppTheme.surface1,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            '${r.source} ──(${r.type})──▶ ${r.target}',
                            style: GoogleFonts.jetBrainsMono(
                                fontSize: 11, color: AppTheme.accent),
                          ),
                        )),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
