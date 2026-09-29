import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import '../../core/services/api_service.dart';
import '../../core/services/push_notification_service.dart';
import '../../core/theme/app_theme.dart';

class ImageDiagramDialog extends StatefulWidget {
  final String diagramId;

  const ImageDiagramDialog({Key? key, required this.diagramId}) : super(key: key);

  @override
  State<ImageDiagramDialog> createState() => _ImageDiagramDialogState();
}

class _ImageDiagramDialogState extends State<ImageDiagramDialog> {
  final ImagePicker _picker = ImagePicker();
  final ApiService _apiService = ApiService();

  Uint8List? _selectedImageBytes;
  String? _imageMimeType;
  bool _isProcessing = false;
  String? _statusText;

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? file = await _picker.pickImage(
        source: source,
        maxWidth: 1920,
        maxHeight: 1920,
        imageQuality: 85,
      );

      if (file != null) {
        final bytes = await file.readAsBytes();
        setState(() {
          _selectedImageBytes = bytes;
          _imageMimeType = file.mimeType ?? 'image/jpeg';
          _statusText = null;
        });
      }
    } catch (e) {
      debugPrint('Error picking image: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error al capturar imagen: $e'), backgroundColor: Colors.redAccent),
        );
      }
    }
  }

  Future<void> _processImageWithGemini() async {
    if (_selectedImageBytes == null) return;

    setState(() {
      _isProcessing = true;
      _statusText = 'Analizando imagen con Google Gemini Vision (Extrayendo clases y relaciones UML)...';
    });

    final result = await _apiService.generateFromImage(
      diagramId: widget.diagramId,
      imageBytes: _selectedImageBytes!,
      mimeType: _imageMimeType ?? 'image/jpeg',
    );

    if (mounted) {
      setState(() => _isProcessing = false);

      if (result != null) {
        PushNotificationService().triggerInstantPush(
          title: '📸 Diagrama Digitalizado con Éxito',
          message: result['summary'] ?? 'Se reconocieron las entidades UML desde la fotografía.',
          type: 'diagram_update',
          diagramId: widget.diagramId,
        );

        Navigator.pop(context, result);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('No se pudo procesar el diagrama a partir de la imagen.'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppTheme.cardDark,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.accentBlue.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.document_scanner_outlined, color: AppTheme.accentBlue, size: 22),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Digitalizar Diagrama desde Foto',
                      style: GoogleFonts.inter(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                'Toma una foto o selecciona una imagen de un diagrama UML (pizarra, cuaderno o captura). La IA de Google Gemini extraerá clases, atributos, métodos y cardinalidades.',
                style: GoogleFonts.inter(fontSize: 12, color: AppTheme.textSecondary, height: 1.3),
              ),
              const SizedBox(height: 16),

              if (_selectedImageBytes != null) ...[
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    height: 180,
                    width: double.infinity,
                    color: Colors.black26,
                    child: Image.memory(
                      _selectedImageBytes!,
                      fit: BoxFit.cover,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
              ],

              if (_isProcessing) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.accentBlue.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.accentBlue.withOpacity(0.3)),
                  ),
                  child: Row(
                    children: [
                      const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.5, color: AppTheme.accentBlue),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _statusText ?? 'Procesando con Gemini Vision...',
                          style: GoogleFonts.inter(fontSize: 12, color: Colors.white70),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        side: BorderSide(color: AppTheme.accentBlue.withOpacity(0.5)),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      icon: const Icon(Icons.camera_alt_outlined, color: AppTheme.accentBlue, size: 18),
                      label: Text(
                        'Cámara',
                        style: GoogleFonts.inter(fontSize: 13, color: Colors.white, fontWeight: FontWeight.w600),
                      ),
                      onPressed: _isProcessing ? null : () => _pickImage(ImageSource.camera),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        side: BorderSide(color: AppTheme.accentBlue.withOpacity(0.5)),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      icon: const Icon(Icons.photo_library_outlined, color: AppTheme.accentBlue, size: 18),
                      label: Text(
                        'Galería',
                        style: GoogleFonts.inter(fontSize: 13, color: Colors.white, fontWeight: FontWeight.w600),
                      ),
                      onPressed: _isProcessing ? null : () => _pickImage(ImageSource.gallery),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              if (_selectedImageBytes != null && !_isProcessing) ...[
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.accentBlue,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    icon: const Icon(Icons.auto_awesome, color: Colors.white, size: 18),
                    label: Text(
                      'Replicar Diagrama con Gemini AI',
                      style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                    onPressed: _processImageWithGemini,
                  ),
                ),
                const SizedBox(height: 8),
              ],

              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: _isProcessing ? null : () => Navigator.pop(context),
                  child: Text('Cerrar', style: GoogleFonts.inter(color: Colors.white60)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
