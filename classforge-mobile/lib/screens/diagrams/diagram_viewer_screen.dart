import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/services/api_service.dart';
import '../../core/services/websocket_service.dart';
import '../../core/services/offline_nlu_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/diagram_model.dart';
import '../../widgets/uml_class_card.dart';
import '../../widgets/uml_relationship_painter.dart';

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
          // Diagram was updated remotely; fetch updated model
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
                      style: GoogleFonts.jetBrainsMono(fontSize: 12, color: AppTheme.textSecondary),
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

  void _showOfflineNluBottomSheet() {
    final textController = TextEditingController();
    NluResult? result;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surface2,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) {
        return StatefulBuilder(
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
                          const Icon(Icons.bolt, color: AppTheme.accent, size: 20),
                          const SizedBox(width: 6),
                          Text(
                            'Consulta NLU Offline',
                            style: GoogleFonts.inter(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppTheme.accent.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppTheme.accent.withOpacity(0.3)),
                        ),
                        child: Text(
                          '100% Offline (<1ms)',
                          style: GoogleFonts.inter(
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.accent,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: textController,
                    autofocus: true,
                    decoration: InputDecoration(
                      hintText: 'Ej: buscar clase Usuario, contar clases...',
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.send, color: AppTheme.primary),
                        onPressed: () {
                          if (textController.text.trim().isNotEmpty) {
                            final parsed = _nluService.parse(textController.text.trim());
                            setModalState(() => result = parsed);
                          }
                        },
                      ),
                    ),
                    onSubmitted: (val) {
                      if (val.trim().isNotEmpty) {
                        final parsed = _nluService.parse(val.trim());
                        setModalState(() => result = parsed);
                      }
                    },
                  ),
                  if (result != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.surface1,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                'Acción: ${result!.action}',
                                style: GoogleFonts.inter(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.primaryLight,
                                ),
                              ),
                              Text(
                                '${result!.latencyMs}ms',
                                style: GoogleFonts.jetBrainsMono(
                                  fontSize: 11,
                                  color: AppTheme.accent,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            result!.explanation,
                            style: GoogleFonts.inter(fontSize: 13, color: AppTheme.textPrimary),
                          ),
                          if (result!.queryTarget != null && _diagram != null) ...[
                            const SizedBox(height: 10),
                            Builder(
                              builder: (ctx) {
                                final targetNode = _diagram!.nodes.firstWhere(
                                  (n) => n.name.toLowerCase() == result!.queryTarget!.toLowerCase(),
                                  orElse: () => DiagramNodeModel(
                                    id: '',
                                    type: '',
                                    name: '',
                                    attributes: [],
                                    methods: [],
                                    x: 0,
                                    y: 0,
                                  ),
                                );
                                if (targetNode.id.isNotEmpty) {
                                  return ElevatedButton.icon(
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: AppTheme.primary,
                                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                    ),
                                    onPressed: () {
                                      Navigator.pop(context);
                                      _showNodeDetails(targetNode);
                                    },
                                    icon: const Icon(Icons.visibility, size: 16),
                                    label: Text('Ver clase ${targetNode.name}'),
                                  );
                                } else {
                                  return Text(
                                    'La clase "${result!.queryTarget}" no existe en este diagrama.',
                                    style: GoogleFonts.inter(
                                      fontSize: 12,
                                      color: AppTheme.warning,
                                      fontStyle: FontStyle.italic,
                                    ),
                                  );
                                }
                              },
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final ws = Provider.of<WebSocketService>(context);

    return Scaffold(
      backgroundColor: AppTheme.surface1,
      appBar: AppBar(
        backgroundColor: AppTheme.surface2,
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
                    color: ws.isConnected ? AppTheme.accent : AppTheme.danger,
                  ),
                ),
                const SizedBox(width: 5),
                Text(
                  ws.isConnected
                      ? 'En Vivo (${ws.onlineUsersCount} conectado${ws.onlineUsersCount > 1 ? "s" : ""})'
                      : 'Desconectado',
                  style: GoogleFonts.inter(fontSize: 11, color: AppTheme.textSecondary),
                ),
              ],
            ),
          ],
        ),
        actions: [
          // Readonly badge
          Container(
            margin: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppTheme.surface3,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: AppTheme.border),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.lock, size: 12, color: AppTheme.textSecondary),
                const SizedBox(width: 4),
                Text(
                  'Solo Lectura',
                  style: GoogleFonts.inter(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Recargar Diagrama',
            onPressed: _loadDiagram,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppTheme.primary),
            )
          : _diagram == null || _diagram!.nodes.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.account_tree_outlined, size: 54, color: AppTheme.textMuted),
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
                        'Agrega clases y relaciones desde la versión web.',
                        style: GoogleFonts.inter(fontSize: 13, color: AppTheme.textMuted),
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
                          color: AppTheme.surface1,
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
                          color: AppTheme.surface2.withOpacity(0.9),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: AppTheme.border),
                        ),
                        child: Row(
                          children: [
                            Text(
                              '${_diagram!.nodes.length} Clases',
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.primaryLight,
                              ),
                            ),
                            const SizedBox(width: 8),
                            const Text('•', style: TextStyle(color: AppTheme.textMuted)),
                            const SizedBox(width: 8),
                            Text(
                              '${_diagram!.edges.length} Relaciones',
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.accent,
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
                            backgroundColor: AppTheme.surface2,
                            foregroundColor: AppTheme.textPrimary,
                            onPressed: _zoomIn,
                            child: const Icon(Icons.add),
                          ),
                          const SizedBox(height: 8),
                          FloatingActionButton.small(
                            heroTag: 'zoom_out',
                            backgroundColor: AppTheme.surface2,
                            foregroundColor: AppTheme.textPrimary,
                            onPressed: _zoomOut,
                            child: const Icon(Icons.remove),
                          ),
                          const SizedBox(height: 8),
                          FloatingActionButton.small(
                            heroTag: 'reset_zoom',
                            backgroundColor: AppTheme.surface2,
                            foregroundColor: AppTheme.textPrimary,
                            onPressed: _resetZoom,
                            child: const Icon(Icons.crop_free),
                          ),
                        ],
                      ),
                    ),

                    // Offline NLU Search Button
                    Positioned(
                      bottom: 20,
                      left: 16,
                      child: FloatingActionButton.extended(
                        heroTag: 'nlu_search',
                        backgroundColor: AppTheme.primary,
                        foregroundColor: Colors.white,
                        icon: const Icon(Icons.bolt, size: 18),
                        label: Text(
                          'Asistente NLU',
                          style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600),
                        ),
                        onPressed: _showOfflineNluBottomSheet,
                      ),
                    ),
                  ],
                ),
    );
  }
}
