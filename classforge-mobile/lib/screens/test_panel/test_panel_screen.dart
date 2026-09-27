import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/services/api_service.dart';
import '../../core/services/offline_nlu_service.dart';
import '../../core/services/push_notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../diagrams/diagram_viewer_screen.dart';

class TestPanelScreen extends StatefulWidget {
  const TestPanelScreen({Key? key}) : super(key: key);

  @override
  State<TestPanelScreen> createState() => _TestPanelScreenState();
}

class _TestPanelScreenState extends State<TestPanelScreen> with SingleTickerProviderStateMixin {
  final OfflineNluService _nluService = OfflineNluService();
  final TextEditingController _voiceInputController = TextEditingController();

  bool _isListening = false;
  String _activeSpeechTranscript = '';
  NluResult? _lastNluResult;
  bool _appliedToDiagram = false;
  int _scheduledCountdown = 0;
  Timer? _countdownTimer;

  late AnimationController _pulseController;

  final List<Map<String, String>> _voicePresets = [
    {
      'label': 'Factura (id, monto, fecha)',
      'command': 'crear clase Factura con id:long, monto:double, fecha:datetime',
      'category': 'Clase',
    },
    {
      'label': 'Cliente (id, nombre, nit)',
      'command': 'crear clase Cliente con id:int, nombre:string, nit:string',
      'category': 'Clase',
    },
    {
      'label': 'Herencia: Admin hereda de Usuario',
      'command': 'hacer que Administrador herede de Usuario',
      'category': 'Relación',
    },
    {
      'label': 'Composición: Factura y Detalle',
      'command': 'relacionar Factura con DetallePedido por composicion',
      'category': 'Relación',
    },
    {
      'label': 'Atributo: saldo a CuentaBancaria',
      'command': 'agregar atributo saldo:double a CuentaBancaria',
      'category': 'Atributo',
    },
    {
      'label': 'Método: pagar() a Factura',
      'command': 'agregar metodo pagar(monto:double):boolean a Factura',
      'category': 'Método',
    },
    {
      'label': 'Buscar clase Usuario',
      'command': 'buscar clase Usuario',
      'category': 'Consulta',
    },
    {
      'label': 'Resumen del diagrama',
      'command': 'resumen del diagrama',
      'category': 'Consulta',
    },
  ];

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _countdownTimer?.cancel();
    _voiceInputController.dispose();
    super.dispose();
  }

  void _enterOfflineApp() async {
    final apiService = Provider.of<ApiService>(context, listen: false);
    await apiService.enableOfflineDemoMode();
    if (mounted) {
      Navigator.pushReplacementNamed(context, '/home');
    }
  }

  void _simulateVoiceRecognition(String command) {
    setState(() {
      _isListening = true;
      _activeSpeechTranscript = 'Capturando audio fonético local...';
      _appliedToDiagram = false;
    });

    try {
      HapticFeedback.mediumImpact();
    } catch (_) {}

    // Simular procesamiento de ondas fonéticas en 1.2 segundos
    Future.delayed(const Duration(milliseconds: 600), () {
      if (mounted && _isListening) {
        setState(() {
          _activeSpeechTranscript = '"$command"';
        });
      }
    });

    Future.delayed(const Duration(milliseconds: 1200), () {
      if (mounted) {
        final result = _nluService.parse(command);
        setState(() {
          _isListening = false;
          _voiceInputController.text = command;
          _lastNluResult = result;
        });
        try {
          HapticFeedback.lightImpact();
        } catch (_) {}
      }
    });
  }

  void _executeVoiceCommand(String text) {
    if (text.trim().isEmpty) return;
    setState(() {
      _appliedToDiagram = false;
      _lastNluResult = _nluService.parse(text.trim());
    });
    try {
      HapticFeedback.selectionClick();
    } catch (_) {}
  }

  void _applyToDiagram() {
    if (_lastNluResult == null) return;
    final apiService = Provider.of<ApiService>(context, listen: false);
    final success = apiService.applyNluResultToDiagram('diag-01', _lastNluResult!);

    if (success) {
      setState(() => _appliedToDiagram = true);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '✓ ¡Cambios aplicados al modelo UML en memoria!',
            style: GoogleFonts.inter(fontWeight: FontWeight.w600),
          ),
          backgroundColor: const Color(0xFF10B981),
          duration: const Duration(seconds: 2),
          action: SnackBarAction(
            label: 'Ver Lienzo',
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

  void _triggerScheduledPush(PushNotificationService pushService, int seconds) {
    setState(() => _scheduledCountdown = seconds);
    _countdownTimer?.cancel();

    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_scheduledCountdown <= 1) {
        timer.cancel();
        setState(() => _scheduledCountdown = 0);
        pushService.triggerInstantPush(
          title: '⏱️ Notificación Programada Recibida',
          message: 'La alerta programada de $seconds segundos se ejecutó con éxito en segundo plano.',
          type: 'backend_generated',
          diagramId: 'diag-01',
        );
      } else {
        setState(() => _scheduledCountdown--);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final pushService = Provider.of<PushNotificationService>(context);

    return Scaffold(
      backgroundColor: AppTheme.surface1,
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: AppTheme.primary,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.hub_outlined, color: Colors.white, size: 20),
            ),
            const SizedBox(width: 10),
            Text(
              'ClassForge Demo Hub',
              style: GoogleFonts.inter(fontSize: 17, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.login, size: 20, color: AppTheme.textSecondary),
            tooltip: 'Iniciar Sesión (Cloud)',
            onPressed: () => Navigator.pushNamed(context, '/login'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
        children: [
          // Banner de Estado Autónomo
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppTheme.primary.withOpacity(0.2),
                  const Color(0xFF10B981).withOpacity(0.15),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.primary.withOpacity(0.4)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF10B981).withOpacity(0.2),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: const Color(0xFF10B981).withOpacity(0.5)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 6,
                            height: 6,
                            decoration: const BoxDecoration(
                              shape: BoxShape.circle,
                              color: Color(0xFF10B981),
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'MODO DEMOSTRACIÓN OFFLINE',
                            style: GoogleFonts.inter(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: const Color(0xFF10B981),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Text(
                      '100% On-Device',
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 11,
                        color: AppTheme.accent,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  'Bienvenido al Panel de Pruebas de ClassForge Mobile',
                  style: GoogleFonts.inter(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Este panel permite evaluar la IA de voz local y el sistema de notificaciones push de forma autónoma sin depender de conexión a base de datos ni servidor localhost.',
                  style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary, height: 1.3),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  height: 46,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    icon: const Icon(Icons.rocket_launch, size: 18),
                    label: Text(
                      'Ingresar a la App Completa (Modo Demo)',
                      style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.bold),
                    ),
                    onPressed: _enterOfflineApp,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // SECCIÓN 1: LABORATORIO DE IA DE VOZ LOCAL
          _buildSectionHeader(
            icon: Icons.mic_none,
            title: 'Laboratorio de IA de Voz Local',
            tag: '0MB • <0.5ms',
            tagColor: AppTheme.accent,
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.surface2,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Prueba del Motor NLU Fonético Offline',
                  style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                ),
                const SizedBox(height: 4),
                Text(
                  'Toca el micrófono para simular captura de voz o selecciona un comando de prueba para ver el reconocimiento instantáneo en el dispositivo.',
                  style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary),
                ),
                const SizedBox(height: 16),

                // Micrófono con ondas visuales de audio
                Center(
                  child: Column(
                    children: [
                      GestureDetector(
                        onTap: () {
                          _simulateVoiceRecognition('crear clase Factura con id:long, monto:double');
                        },
                        child: AnimatedBuilder(
                          animation: _pulseController,
                          builder: (context, child) {
                            return Container(
                              width: 80,
                              height: 80,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: _isListening
                                    ? AppTheme.danger.withOpacity(0.2 + (_pulseController.value * 0.3))
                                    : AppTheme.primary.withOpacity(0.15),
                                border: Border.all(
                                  color: _isListening ? AppTheme.danger : AppTheme.primary,
                                  width: _isListening ? 2.5 : 1.5,
                                ),
                                boxShadow: _isListening
                                    ? [
                                        BoxShadow(
                                          color: AppTheme.danger.withOpacity(0.4),
                                          blurRadius: 18 * _pulseController.value,
                                          spreadRadius: 4 * _pulseController.value,
                                        )
                                      ]
                                    : [],
                              ),
                              child: Icon(
                                _isListening ? Icons.mic : Icons.mic_none,
                                size: 36,
                                color: _isListening ? AppTheme.danger : AppTheme.primaryLight,
                              ),
                            );
                          },
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        _isListening ? 'Escuchando audio local...' : 'Tocar para prueba de voz',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: _isListening ? AppTheme.danger : AppTheme.textMuted,
                        ),
                      ),
                      if (_isListening) ...[
                        const SizedBox(height: 8),
                        // Espectro de ondas sonoras animado (Ecualizador)
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: List.generate(7, (i) {
                            return AnimatedBuilder(
                              animation: _pulseController,
                              builder: (context, _) {
                                final height = 8.0 + ((i % 2 == 0 ? _pulseController.value : 1.0 - _pulseController.value) * 20.0);
                                return Container(
                                  margin: const EdgeInsets.symmetric(horizontal: 2),
                                  width: 3,
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
                        const SizedBox(height: 6),
                        Text(
                          _activeSpeechTranscript,
                          style: GoogleFonts.jetBrainsMono(
                            fontSize: 11,
                            color: AppTheme.textPrimary,
                            fontStyle: FontStyle.italic,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // Banco de Comandos Rápidos por Voz
                Text(
                  'Banco de Comandos Pregrabados:',
                  style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textMuted),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: _voicePresets.map((preset) {
                    return ActionChip(
                      label: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                            decoration: BoxDecoration(
                              color: AppTheme.surface1,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              preset['category']!,
                              style: const TextStyle(fontSize: 9, color: AppTheme.accent),
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(preset['label']!),
                        ],
                      ),
                      backgroundColor: AppTheme.surface3,
                      labelStyle: GoogleFonts.inter(fontSize: 11, color: AppTheme.textPrimary),
                      onPressed: () => _simulateVoiceRecognition(preset['command']!),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 14),

                // Campo de entrada manual de voz/texto
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _voiceInputController,
                        style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 13),
                        decoration: InputDecoration(
                          hintText: 'Escribe o dicta comando UML...',
                          isDense: true,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                            borderSide: const BorderSide(color: AppTheme.border),
                          ),
                        ),
                        onSubmitted: _executeVoiceCommand,
                      ),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.surface3,
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      ),
                      onPressed: () => _executeVoiceCommand(_voiceInputController.text),
                      child: const Icon(Icons.send, size: 16, color: AppTheme.primaryLight),
                    ),
                  ],
                ),

                // Tarjeta de Resultado NLU si existe
                if (_lastNluResult != null) ...[
                  const SizedBox(height: 14),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.surface1,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: AppTheme.primary.withOpacity(0.4)),
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
                                  _lastNluResult!.action.toUpperCase(),
                                  style: GoogleFonts.inter(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.accent,
                                  ),
                                ),
                              ],
                            ),
                            Text(
                              '⚡ ${_lastNluResult!.latencyMs}ms (0 MB RAM)',
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 10,
                                color: const Color(0xFF10B981),
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          _lastNluResult!.explanation,
                          style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textPrimary),
                        ),
                        if (_lastNluResult!.classes.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          ..._lastNluResult!.classes.map((c) => Text(
                                '• Clase ${c.name} (${c.attributes.length} attrs, ${c.methods.length} métodos)',
                                style: GoogleFonts.jetBrainsMono(fontSize: 11, color: AppTheme.primaryLight),
                              )),
                        ],
                        if (_lastNluResult!.relations.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          ..._lastNluResult!.relations.map((r) => Text(
                                '• Relación: ${r.source} ──(${r.type})──▶ ${r.target}',
                                style: GoogleFonts.jetBrainsMono(fontSize: 11, color: AppTheme.accent),
                              )),
                        ],
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            Expanded(
                              child: ElevatedButton.icon(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: _appliedToDiagram ? const Color(0xFF10B981) : AppTheme.primary,
                                  padding: const EdgeInsets.symmetric(vertical: 8),
                                ),
                                icon: Icon(_appliedToDiagram ? Icons.check : Icons.auto_awesome, size: 16),
                                label: Text(
                                  _appliedToDiagram ? '¡Aplicado al Modelo!' : 'Aplicar al Diagrama en Vivo',
                                  style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold),
                                ),
                                onPressed: _applyToDiagram,
                              ),
                            ),
                            const SizedBox(width: 8),
                            OutlinedButton.icon(
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 10),
                                side: const BorderSide(color: AppTheme.border),
                              ),
                              icon: const Icon(Icons.remove_red_eye, size: 16),
                              label: const Text('Ver Visor', style: TextStyle(fontSize: 11)),
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
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 24),

          // SECCIÓN 2: LABORATORIO DE NOTIFICACIONES PUSH
          _buildSectionHeader(
            icon: Icons.notifications_active,
            title: 'Laboratorio de Notificaciones Push',
            tag: 'Heads-Up & Háptica',
            tagColor: const Color(0xFF10B981),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.surface2,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Prueba de Alertas en Tiempo Real',
                  style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                ),
                const SizedBox(height: 4),
                Text(
                  'Dispara notificaciones push inmediatas con banner flotante heads-up y vibración o programa una alerta con retardo.',
                  style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary),
                ),
                const SizedBox(height: 16),

                // Botones de disparo rápido de push
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _buildPushTriggerButton(
                      label: 'Colaborador Unido',
                      icon: Icons.person_add_alt_1,
                      color: AppTheme.accent,
                      onPressed: () {
                        pushService.triggerInstantPush(
                          title: '👤 Colaborador en Línea',
                          message: 'Carlos Mendoza ha ingresado al Diagrama Bancario.',
                          type: 'team_member_added',
                          diagramId: 'diag-01',
                        );
                      },
                    ),
                    _buildPushTriggerButton(
                      label: 'Clase Modificada',
                      icon: Icons.edit_note,
                      color: AppTheme.primaryLight,
                      onPressed: () {
                        pushService.triggerInstantPush(
                          title: '✏️ Modificación en Tiempo Real',
                          message: 'Ana Torres añadió el método procesarPago() a Factura.',
                          type: 'diagram_modified',
                          diagramId: 'diag-01',
                        );
                      },
                    ),
                    _buildPushTriggerButton(
                      label: 'Spring Boot 3 Generado',
                      icon: Icons.auto_awesome,
                      color: const Color(0xFF10B981),
                      onPressed: () {
                        pushService.triggerInstantPush(
                          title: '⚡ Backend Spring Boot Listo',
                          message: 'Entidades JPA Java 17 y Repositorios Maven listos para descarga.',
                          type: 'backend_generated',
                          diagramId: 'diag-01',
                        );
                      },
                    ),
                    _buildPushTriggerButton(
                      label: 'Bloqueo Concurrente',
                      icon: Icons.lock_clock,
                      color: const Color(0xFFF59E0B),
                      onPressed: () {
                        pushService.triggerInstantPush(
                          title: '🔒 Nodo Bloqueado',
                          message: 'David Rojas está editando la clase Transaccion (Edición simultánea).',
                          type: 'warning',
                          diagramId: 'diag-01',
                        );
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Notificación programada (con retardo)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.surface1,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.timer_outlined, color: AppTheme.accent, size: 22),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Notificación Programada (4 seg)',
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.textPrimary,
                              ),
                            ),
                            Text(
                              _scheduledCountdown > 0
                                  ? 'Disparando en $_scheduledCountdown segundo(s)...'
                                  : 'Presiona para probar recepción diferida',
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                color: _scheduledCountdown > 0 ? AppTheme.accent : AppTheme.textMuted,
                              ),
                            ),
                          ],
                        ),
                      ),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _scheduledCountdown > 0 ? AppTheme.surface3 : AppTheme.primary,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        ),
                        onPressed: _scheduledCountdown > 0
                            ? null
                            : () => _triggerScheduledPush(pushService, 4),
                        child: Text(
                          _scheduledCountdown > 0 ? '$_scheduledCountdown s' : 'Programar',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // Switch de simulación continua en segundo plano
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(
                    'Simulador de Eventos de Equipo Continuo',
                    style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                  ),
                  subtitle: Text(
                    'Dispara notificaciones push periódicas cada 8 segundos simulando trabajo en equipo.',
                    style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textMuted),
                  ),
                  value: pushService.isSimulationActive,
                  activeColor: const Color(0xFF10B981),
                  onChanged: (val) {
                    pushService.toggleBackgroundSimulation(val);
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // SECCIÓN 3: CONECTIVIDAD NUBE / LOGIN
          _buildSectionHeader(
            icon: Icons.cloud_outlined,
            title: 'Despliegue y Conexión Cloud',
            tag: 'Para Producción',
            tagColor: AppTheme.textMuted,
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.surface2,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Conexión a Servidor Remoto / VPS',
                  style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                ),
                const SizedBox(height: 4),
                Text(
                  'Cuando el backend FastAPI y MongoDB se desplieguen en la nube o en una IP local compartida, puedes iniciar sesión con credenciales reales.',
                  style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                    side: const BorderSide(color: AppTheme.border),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  icon: const Icon(Icons.login, size: 16),
                  label: const Text('Abrir Pantalla de Inicio de Sesión Cloud'),
                  onPressed: () => Navigator.pushNamed(context, '/login'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 30),
        ],
      ),
    );
  }

  Widget _buildSectionHeader({
    required IconData icon,
    required String title,
    required String tag,
    required Color tagColor,
  }) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(
          children: [
            Icon(icon, size: 18, color: AppTheme.primaryLight),
            const SizedBox(width: 8),
            Text(
              title,
              style: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
            ),
          ],
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: tagColor.withOpacity(0.15),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: tagColor.withOpacity(0.3)),
          ),
          child: Text(
            tag,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 10,
              fontWeight: FontWeight.bold,
              color: tagColor,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPushTriggerButton({
    required String label,
    required IconData icon,
    required Color color,
    required VoidCallback onPressed,
  }) {
    return ElevatedButton.icon(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppTheme.surface3,
        foregroundColor: AppTheme.textPrimary,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: BorderSide(color: color.withOpacity(0.4)),
        ),
      ),
      icon: Icon(icon, size: 16, color: color),
      label: Text(label, style: GoogleFonts.inter(fontSize: 12)),
      onPressed: onPressed,
    );
  }
}
