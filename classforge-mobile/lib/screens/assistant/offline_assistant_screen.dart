import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/services/api_service.dart';
import '../../core/services/offline_nlu_service.dart';
import '../../core/services/voice_recognition_service.dart';
import '../../core/theme/app_theme.dart';
import '../diagrams/diagram_viewer_screen.dart';

class OfflineAssistantScreen extends StatefulWidget {
  const OfflineAssistantScreen({Key? key}) : super(key: key);

  @override
  State<OfflineAssistantScreen> createState() => _OfflineAssistantScreenState();
}

class _OfflineAssistantScreenState extends State<OfflineAssistantScreen> with SingleTickerProviderStateMixin {
  final TextEditingController _textController = TextEditingController();
  final OfflineNluService _nluService = OfflineNluService();
  final VoiceRecognitionService _voiceService = VoiceRecognitionService();

  final List<Map<String, dynamic>> _history = [];
  bool _isListening = false;
  String _liveTranscription = '';
  late AnimationController _waveController;

  final List<String> _quickSuggestions = [
    'crear clase Factura con id:long, monto:double',
    'crear clase Pedido con atributos total:double',
    'relacionar Usuario con CuentaBancaria por composicion',
    'hacer que Administrador herede de Usuario',
    'agregar atributo saldo:double a CuentaBancaria',
    'agregar metodo pagar(monto):boolean a Factura',
    'buscar clase Usuario',
    'resumen del diagrama',
  ];

  @override
  void initState() {
    super.initState();
    _waveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    )..repeat(reverse: true);
    _voiceService.initialize();
  }

  @override
  void dispose() {
    _waveController.dispose();
    _textController.dispose();
    _voiceService.cancelListening();
    super.dispose();
  }

  void _executeCommand(String text) {
    if (text.trim().isEmpty) return;

    final result = _nluService.parse(text.trim());
    setState(() {
      _history.insert(0, {
        'input': text.trim(),
        'result': result,
        'timestamp': DateTime.now(),
        'applied': false,
      });
      _textController.clear();
      _liveTranscription = '';
    });

    try {
      HapticFeedback.selectionClick();
    } catch (_) {}
  }

  Future<void> _toggleMicListening() async {
    if (_isListening) {
      await _voiceService.stopListening();
      setState(() => _isListening = false);
      if (_liveTranscription.trim().isNotEmpty) {
        _executeCommand(_liveTranscription);
      }
      return;
    }

    setState(() {
      _isListening = true;
      _liveTranscription = 'Escuchando tu voz...';
    });

    final success = await _voiceService.startListening(
      onResult: (words, isFinal) {
        if (mounted) {
          setState(() {
            _liveTranscription = words.isNotEmpty ? words : 'Escuchando...';
            _textController.text = words;
          });
          if (isFinal && words.trim().isNotEmpty) {
            setState(() => _isListening = false);
            _executeCommand(words);
          }
        }
      },
    );

    if (!success) {
      if (mounted) {
        setState(() {
          _isListening = false;
          _liveTranscription = '';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              _voiceService.lastError != null
                  ? 'Micrófono: ${_voiceService.lastError}. Puedes escribir o seleccionar un comando rápido.'
                  : 'Reconocimiento de voz no disponible en este dispositivo. Puedes usar los comandos rápidos o escribir.',
              style: GoogleFonts.inter(fontSize: 12),
            ),
            backgroundColor: AppTheme.danger,
            duration: const Duration(seconds: 4),
          ),
        );
      }
    }
  }

  void _applyResultToDiagram(int index, NluResult res) {
    final apiService = Provider.of<ApiService>(context, listen: false);
    final success = apiService.applyNluResultToDiagram('diag-01', res);

    if (success) {
      setState(() {
        _history[index]['applied'] = true;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '✓ ¡Cambios aplicados al lienzo conceptual!',
            style: GoogleFonts.inter(fontWeight: FontWeight.w600),
          ),
          backgroundColor: const Color(0xFF10B981),
          duration: const Duration(seconds: 3),
          action: SnackBarAction(
            label: 'Ver en Lienzo',
            textColor: Colors.white,
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const DiagramViewerScreen(
                    diagramId: 'diag-01',
                    initialName: 'Diagrama Conceptual Bancario',
                  ),
                ),
              );
            },
          ),
        ),
      );
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
              'Asistente de Modelado IA',
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
                  '<0.5ms • On-Device',
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
                            child: const Icon(Icons.mic, size: 48, color: AppTheme.primaryLight),
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Modelado UML por Voz y Texto',
                            style: GoogleFonts.inter(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Presiona el micrófono inferior y dicta comandos en lenguaje natural para generar clases, métodos, atributos y relaciones UML.',
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
                      final isApplied = item['applied'] as bool? ?? false;
                      return _buildHistoryItem(index, input, res, isApplied);
                    },
                  ),
          ),

          // Voice active indicator with real-time waveform equalizer
          if (_isListening)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
              color: AppTheme.danger.withOpacity(0.18),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.mic, color: AppTheme.danger, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        'Grabando audio del micrófono...',
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          color: AppTheme.danger,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(width: 14),
                      // Animated sound wave bars
                      Row(
                        children: List.generate(6, (i) {
                          return AnimatedBuilder(
                            animation: _waveController,
                            builder: (context, _) {
                              final height = 6.0 +
                                  ((i % 2 == 0 ? _waveController.value : 1.0 - _waveController.value) *
                                      18.0);
                              return Container(
                                margin: const EdgeInsets.symmetric(horizontal: 1.5),
                                width: 3.5,
                                height: height,
                                decoration: BoxDecoration(
                                  color: AppTheme.danger,
                                  borderRadius: BorderRadius.circular(2),
                                ),
                              );
                            },
                          );
                        }),
                      ),
                    ],
                  ),
                  if (_liveTranscription.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      _liveTranscription,
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: AppTheme.textPrimary,
                        fontWeight: FontWeight.w500,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
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
                    _isListening ? Icons.stop_circle : Icons.mic,
                    color: _isListening ? AppTheme.danger : AppTheme.accent,
                    size: 28,
                  ),
                  tooltip: _isListening ? 'Detener grabación' : 'Hablar por micrófono',
                  onPressed: _toggleMicListening,
                ),
                Expanded(
                  child: TextField(
                    controller: _textController,
                    style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 14),
                    decoration: InputDecoration(
                      hintText: 'Comando UML ej: crear clase Factura...',
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

  Widget _buildHistoryItem(int index, String input, NluResult res, bool isApplied) {
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
                            color: const Color(0xFF10B981),
                            fontWeight: FontWeight.bold,
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

                  // Botón de aplicación directa al diagrama UML
                  if (res.classes.isNotEmpty || res.relations.isNotEmpty || res.deletedElements.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: isApplied ? const Color(0xFF10B981) : AppTheme.primary,
                              padding: const EdgeInsets.symmetric(vertical: 8),
                            ),
                            icon: Icon(isApplied ? Icons.check : Icons.auto_awesome, size: 16),
                            label: Text(
                              isApplied ? '¡Aplicado al Diagrama!' : 'Aplicar al Diagrama en Vivo',
                              style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold),
                            ),
                            onPressed: () => _applyResultToDiagram(index, res),
                          ),
                        ),
                      ],
                    ),
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
