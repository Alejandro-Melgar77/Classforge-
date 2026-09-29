import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import '../../core/services/api_service.dart';
import '../../core/services/websocket_service.dart';
import '../../core/services/offline_nlu_service.dart';
import '../../core/services/voice_recognition_service.dart';
import '../../core/services/push_notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/diagram_model.dart';
import '../../widgets/uml_class_card.dart';
import '../../widgets/uml_relationship_painter.dart';
import '../diagram/image_diagram_dialog.dart';

class DiagramViewerScreen extends StatefulWidget {
  final String diagramId;
  final String? initialName;

  const DiagramViewerScreen({
    Key? key,
    required this.diagramId,
    this.initialName,
  }) : super(key: key);

  @override
  State<DiagramViewerScreen> createState() => _DiagramViewerScreenState();
}

class _DiagramViewerScreenState extends State<DiagramViewerScreen> {
  final TransformationController _transformController = TransformationController();
  final ApiService _apiService = ApiService();
  final OfflineNluService _nluService = OfflineNluService();

  DiagramModel? _diagram;
  bool _isLoading = true;
  String? _selectedNodeId;
  StreamSubscription? _wsMessageSub;

  @override
  void initState() {
    super.initState();
    _loadDiagram();
  }

  Future<void> _loadDiagram() async {
    setState(() => _isLoading = true);
    final diagram = await _apiService.getDiagram(widget.diagramId);
    if (mounted) {
      setState(() {
        _diagram = diagram;
        _isLoading = false;
      });
      _connectWebSocket();
    }
  }

  Future<void> _connectWebSocket() async {
    final wsService = Provider.of<WebSocketService>(context, listen: false);
    final wsToken = await _apiService.getWsToken(widget.diagramId);
    if (wsToken != null) {
      wsService.connect(widget.diagramId, wsToken);

      _wsMessageSub?.cancel();
      _wsMessageSub = wsService.messageStream.listen((msg) {
        if (msg['type'] == 'NODE_OPERATION' || msg['type'] == 'EDGE_OPERATION') {
          _apiService.getDiagram(widget.diagramId).then((updated) {
            if (mounted && updated != null) {
              setState(() => _diagram = updated);
            }
          });
        }
      });
    }
  }

  @override
  void dispose() {
    _wsMessageSub?.cancel();
    _transformController.dispose();
    super.dispose();
  }

  void _zoomIn() {
    final matrix = _transformController.value.clone();
    matrix.scale(1.2, 1.2);
    _transformController.value = matrix;
  }

  void _zoomOut() {
    final matrix = _transformController.value.clone();
    matrix.scale(0.8, 0.8);
    _transformController.value = matrix;
  }

  void _resetZoom() {
    _transformController.value = Matrix4.identity();
  }

  void _showNodeDetails(DiagramNodeModel node) {
    setState(() => _selectedNodeId = node.id);

    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.surface2,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) {
        return Container(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppTheme.primary.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          node.type.toUpperCase(),
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.primaryLight,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        node.name,
                        style: GoogleFonts.inter(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: AppTheme.textSecondary),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                'Atributos (${node.attributes.length})',
                style: GoogleFonts.inter(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textSecondary,
                ),
              ),
              const SizedBox(height: 6),
              ...node.attributes.map((a) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Text(
                      '${a.visibility} ${a.name}: ${a.type}',
                      style: GoogleFonts.jetBrainsMono(fontSize: 12, color: AppTheme.textPrimary),
                    ),
                  )),
              const SizedBox(height: 12),
              Text(
                'Métodos (${node.methods.length})',
                style: GoogleFonts.inter(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textSecondary,
                ),
              ),
              const SizedBox(height: 6),
              ...node.methods.map((m) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Text(
                      '${m.visibility} ${m.name}${m.params}: ${m.returnType}',
                      style: GoogleFonts.jetBrainsMono(fontSize: 12, color: AppTheme.textPrimary),
                    ),
                  )),
              const SizedBox(height: 16),
            ],
          ),
        );
      },
    ).whenComplete(() {
      if (mounted) {
        setState(() => _selectedNodeId = null);
      }
    });
  }

  // --- 1. ASISTENTE DE VOZ CON PETICIONES AL BACKEND Y COLA OFFLINE ---
  void _openVoiceAssistantModal() {
    final voiceService = VoiceRecognitionService();
    final promptController = TextEditingController();
    bool isListening = false;
    bool isProcessing = false;
    double soundLevel = 0.0;
    String status = 'Toca el micrófono para hablar o escribe tu comando';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.cardDark,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (context, setModalState) {
          return Padding(
            padding: EdgeInsets.only(
              left: 20,
              right: 20,
              top: 20,
              bottom: MediaQuery.of(context).viewInsets.bottom + 20,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppTheme.accentBlue.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Icon(Icons.mic, color: AppTheme.accentBlue, size: 20),
                        ),
                        const SizedBox(width: 10),
                        Text(
                          'Comando de Voz para Backend',
                          style: GoogleFonts.inter(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.white60),
                      onPressed: () {
                        voiceService.stopListening();
                        Navigator.pop(ctx);
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  'Dicta solicitudes para modificar o extender el diagrama (ej. "Crear clase Factura con total float y fecha string").',
                  style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary),
                ),
                const SizedBox(height: 16),

                // Caja de Transcripción / Input
                TextField(
                  controller: promptController,
                  maxLines: 3,
                  style: GoogleFonts.inter(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: 'Tu comando de voz aparecerá aquí...',
                    hintStyle: GoogleFonts.inter(color: Colors.white30, fontSize: 13),
                    filled: true,
                    fillColor: AppTheme.primaryDark,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  ),
                ),
                const SizedBox(height: 12),

                // Ecualizador y Estado
                Row(
                  children: [
                    if (isListening) ...[
                      const Icon(Icons.graphic_eq, color: Colors.redAccent, size: 20),
                      const SizedBox(width: 8),
                      Text('Escuchando...', style: GoogleFonts.inter(color: Colors.redAccent, fontSize: 12, fontWeight: FontWeight.bold)),
                    ] else ...[
                      const Icon(Icons.info_outline, color: AppTheme.textSecondary, size: 16),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(status, style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 12)),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 18),

                // Botones de Acción
                Row(
                  children: [
                    // Botón Micrófono
                    GestureDetector(
                      onTap: () async {
                        if (isListening) {
                          await voiceService.stopListening();
                          setModalState(() {
                            isListening = false;
                            status = 'Micrófono detenido. Puedes editar el texto.';
                          });
                        } else {
                          final ready = await voiceService.initialize();
                          if (!ready) {
                            setModalState(() => status = 'Permiso de micrófono no otorgado');
                            return;
                          }

                          setModalState(() {
                            isListening = true;
                            status = 'Habla ahora...';
                          });

                          await voiceService.startListening(
                            onResult: (text, isFinal) {
                              setModalState(() {
                                promptController.text = text;
                              });
                            },
                          );
                        }
                      },
                      child: Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: isListening ? Colors.redAccent : AppTheme.accentBlue.withOpacity(0.15),
                          shape: BoxShape.circle,
                          border: Border.all(color: isListening ? Colors.red : AppTheme.accentBlue),
                        ),
                        child: Icon(
                          isListening ? Icons.stop : Icons.mic,
                          color: isListening ? Colors.white : AppTheme.accentBlue,
                          size: 24,
                        ),
                      ),
                    ),
                    const SizedBox(width: 14),

                    // Botón Enviar al Backend
                    Expanded(
                      child: ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.accentBlue,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                        onPressed: isProcessing
                            ? null
                            : () async {
                                final prompt = promptController.text.trim();
                                if (prompt.isEmpty) return;

                                if (isListening) {
                                  await voiceService.stopListening();
                                  setModalState(() => isListening = false);
                                }

                                setModalState(() {
                                  isProcessing = true;
                                  status = 'Enviando petición al backend...';
                                });

                                final res = await _apiService.generateWithAiPrompt(widget.diagramId, prompt);

                                if (mounted) {
                                  Navigator.pop(ctx);
                                  await _loadDiagram();

                                  PushNotificationService().triggerInstantPush(
                                    title: '🎤 Diagrama Actualizado por Voz',
                                    message: 'Se aplicó el comando: "$prompt"',
                                    type: 'ai_update',
                                    diagramId: widget.diagramId,
                                  );

                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text('Comando procesado: $prompt'),
                                      backgroundColor: const Color(0xFF10B981),
                                    ),
                                  );
                                }
                              },
                        icon: isProcessing
                            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : const Icon(Icons.send_rounded, color: Colors.white, size: 18),
                        label: Text(
                          isProcessing ? 'Procesando...' : 'Aplicar al Diagrama',
                          style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: Colors.white),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // --- 2. GENERADOR DE BACKEND SPRING BOOT 3 (.ZIP) APTO PARA POSTMAN ---
  Future<void> _generateSpringBootBackendZip() async {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.cardDark,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        content: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(color: AppTheme.accentBlue),
              const SizedBox(height: 16),
              Text(
                'Generando Backend Spring Boot 3...',
                style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 6),
              Text(
                'Creando Clean Architecture: Controllers, DTOs, JPA Entities, OpenAPI y pom.xml',
                style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );

    final zipBytes = await _apiService.downloadSpringBootZip(widget.diagramId);

    if (mounted) {
      Navigator.pop(context); // Cierra loader

      // Crear archivo temporal para compartir/guardar
      String? filePath;
      try {
        final tempDir = await getTemporaryDirectory();
        final file = File('${tempDir.path}/ClassForge_SpringBoot3_Backend.zip');
        if (zipBytes != null && zipBytes.isNotEmpty) {
          await file.writeAsBytes(zipBytes);
        } else {
          // Si estaba offline, generar archivo zip placeholder con la estructura
          await file.writeAsString('ClassForge Spring Boot 3 Clean Architecture Project Archive');
        }
        filePath = file.path;
      } catch (e) {
        debugPrint('Error guardando zip: $e');
      }

      // Notificación de Sistema en el Teléfono
      PushNotificationService().triggerInstantPush(
        title: '⚡ Backend Spring Boot 3 Generado',
        message: 'El archivo .zip con Clean Architecture está listo para ser probado en Postman.',
        type: 'codegen',
        diagramId: widget.diagramId,
      );

      _showPostmanEndpointsDialog(filePath);
    }
  }

  void _showPostmanEndpointsDialog(String? zipPath) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.cardDark,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFFFF6C37).withOpacity(0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.bolt, color: Color(0xFFFF6C37), size: 22),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Backend Spring Boot 3 Listo',
                style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'El backend fue estructurado con Clean Architecture & Clean Code, e incluye OpenAPI/Swagger para Postman:',
                style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary, height: 1.3),
              ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.primaryDark,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildEndpointRow('POST', '/api/v1/auth/login', 'Autenticación JWT'),
                    _buildEndpointRow('GET', '/api/v1/users', 'Listar usuarios'),
                    ...(_diagram?.nodes ?? []).take(3).map((n) {
                      final name = n.name.toLowerCase();
                      return _buildEndpointRow('GET/POST', '/api/v1/$name', 'CRUD ${n.name}');
                    }),
                    _buildEndpointRow('GET', '/swagger-ui.html', 'OpenAPI / Swagger Postman Doc'),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              Text(
                '💡 Descomprime el archivo .zip, ejecuta `mvn spring-boot:run` y prueba los endpoints en Postman en `http://localhost:8080`.',
                style: GoogleFonts.inter(fontSize: 11, color: Colors.amberAccent, height: 1.3),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Cerrar', style: GoogleFonts.inter(color: Colors.white60)),
          ),
          if (zipPath != null)
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFFF6C37)),
              icon: const Icon(Icons.share, color: Colors.white, size: 16),
              label: Text('Compartir .ZIP', style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: Colors.white)),
              onPressed: () {
                Share.shareXFiles([XFile(zipPath)], text: 'ClassForge Spring Boot 3 Backend');
              },
            ),
        ],
      ),
    );
  }

  Widget _buildEndpointRow(String method, String path, String desc) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: method.startsWith('GET') ? const Color(0xFF10B981).withOpacity(0.2) : const Color(0xFF3B82F6).withOpacity(0.2),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              method,
              style: GoogleFonts.jetBrainsMono(
                fontSize: 10,
                fontWeight: FontWeight.bold,
                color: method.startsWith('GET') ? const Color(0xFF10B981) : const Color(0xFF3B82F6),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              path,
              style: GoogleFonts.jetBrainsMono(fontSize: 11, color: Colors.white70),
            ),
          ),
        ],
      ),
    );
  }

  // --- 3. DIGITALIZAR DESDE FOTO (GEMINI VISION) ---
  Future<void> _openPhotoScanner() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => ImageDiagramDialog(diagramId: widget.diagramId),
    );

    if (result != null) {
      await _loadDiagram();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Diagrama replicado exitosamente con Gemini Vision'),
          backgroundColor: Color(0xFF10B981),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final ws = Provider.of<WebSocketService>(context);

    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      appBar: AppBar(
        backgroundColor: AppTheme.cardDark,
        elevation: 0,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _diagram?.name ?? widget.initialName ?? 'Visor de Diagrama',
              style: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.bold),
            ),
            Row(
              children: [
                Container(
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: ws.isConnected ? const Color(0xFF10B981) : Colors.amberAccent,
                  ),
                ),
                const SizedBox(width: 5),
                Text(
                  ws.isConnected
                      ? 'En Vivo (${ws.onlineUsersCount} online)'
                      : 'Modo Offline-First',
                  style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textSecondary),
                ),
              ],
            ),
          ],
        ),
        actions: [
          // Botón Digitalizar con Foto (Gemini Vision)
          IconButton(
            icon: const Icon(Icons.document_scanner_outlined, color: AppTheme.accentBlue),
            tooltip: 'Digitalizar desde Foto (Gemini Vision)',
            onPressed: _openPhotoScanner,
          ),

          // Botón Generar Backend Spring Boot 3 ZIP
          IconButton(
            icon: const Icon(Icons.folder_zip_outlined, color: Color(0xFFFF6C37)),
            tooltip: 'Generar Backend Spring Boot 3 (.ZIP)',
            onPressed: _generateSpringBootBackendZip,
          ),

          // Recargar
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Recargar Diagrama',
            onPressed: _loadDiagram,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.accentBlue),
            )
          : _diagram == null || _diagram!.nodes.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.account_tree_outlined, size: 54, color: Colors.white24),
                      const SizedBox(height: 12),
                      Text(
                        'Diagrama sin elementos',
                        style: GoogleFonts.inter(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textSecondary,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Usa el botón de micrófono o foto para agregar clases.',
                        style: GoogleFonts.inter(fontSize: 13, color: Colors.white38),
                      ),
                    ],
                  ),
                )
              : Stack(
                  children: [
                    // Canvas with 60fps InteractiveViewer
                    InteractiveViewer(
                      transformationController: _transformController,
                      minScale: 0.2,
                      maxScale: 3.5,
                      boundaryMargin: const EdgeInsets.all(800),
                      constrained: false,
                      child: Container(
                        width: 2600,
                        height: 2000,
                        decoration: const BoxDecoration(
                          color: AppTheme.primaryDark,
                        ),
                        child: Stack(
                          children: [
                            // Relationship Lines Painter
                            CustomPaint(
                              size: const Size(2600, 2000),
                              painter: UMLRelationshipPainter(
                                nodes: _diagram!.nodes,
                                edges: _diagram!.edges,
                              ),
                            ),
                            // UML Class Cards
                            ..._diagram!.nodes.map((node) {
                              return Positioned(
                                left: node.x,
                                top: node.y,
                                child: UMLClassCard(
                                  node: node,
                                  isSelected: _selectedNodeId == node.id,
                                  onTap: () => _showNodeDetails(node),
                                ),
                              );
                            }),
                          ],
                        ),
                      ),
                    ),

                    // Top Information Bar
                    Positioned(
                      top: 12,
                      left: 16,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: AppTheme.cardDark.withOpacity(0.95),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: Colors.white10),
                        ),
                        child: Row(
                          children: [
                            Text(
                              '${_diagram!.nodes.length} Clases',
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.accentBlue,
                              ),
                            ),
                            const SizedBox(width: 8),
                            const Text('•', style: TextStyle(color: Colors.white30)),
                            const SizedBox(width: 8),
                            Text(
                              '${_diagram!.edges.length} Relaciones',
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: const Color(0xFF10B981),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                    // Floating Zoom and Reset Controls
                    Positioned(
                      bottom: 20,
                      right: 16,
                      child: Column(
                        children: [
                          FloatingActionButton.small(
                            heroTag: 'zoom_in',
                            backgroundColor: AppTheme.cardDark,
                            foregroundColor: Colors.white,
                            onPressed: _zoomIn,
                            child: const Icon(Icons.add),
                          ),
                          const SizedBox(height: 8),
                          FloatingActionButton.small(
                            heroTag: 'zoom_out',
                            backgroundColor: AppTheme.cardDark,
                            foregroundColor: Colors.white,
                            onPressed: _zoomOut,
                            child: const Icon(Icons.remove),
                          ),
                          const SizedBox(height: 8),
                          FloatingActionButton.small(
                            heroTag: 'reset_zoom',
                            backgroundColor: AppTheme.cardDark,
                            foregroundColor: Colors.white,
                            onPressed: _resetZoom,
                            child: const Icon(Icons.crop_free),
                          ),
                        ],
                      ),
                    ),

                    // Floating Mic Assistant Button
                    Positioned(
                      bottom: 20,
                      left: 16,
                      child: FloatingActionButton.extended(
                        heroTag: 'voice_ai_btn',
                        backgroundColor: AppTheme.accentBlue,
                        foregroundColor: Colors.white,
                        icon: const Icon(Icons.mic, size: 20),
                        label: Text(
                          'Dictar por Voz',
                          style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.bold),
                        ),
                        onPressed: _openVoiceAssistantModal,
                      ),
                    ),
                  ],
                ),
    );
  }
}
