import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:speech_to_text/speech_recognition_error.dart';
import 'package:speech_to_text/speech_recognition_result.dart';

class VoiceRecognitionService extends ChangeNotifier {
  static final VoiceRecognitionService _instance = VoiceRecognitionService._internal();
  factory VoiceRecognitionService() => _instance;
  VoiceRecognitionService._internal();

  final stt.SpeechToText _speech = stt.SpeechToText();

  bool _isInitialized = false;
  bool _isListening = false;
  bool _speechAvailable = false;
  String _recognizedWords = '';
  double _soundLevel = 0.0;
  String? _lastError;

  bool get isListening => _isListening;
  bool get speechAvailable => _speechAvailable;
  String get recognizedWords => _recognizedWords;
  double get soundLevel => _soundLevel;
  String? get lastError => _lastError;

  Future<bool> initialize() async {
    if (_isInitialized && _speechAvailable) return true;

    try {
      _speechAvailable = await _speech.initialize(
        onError: _handleError,
        onStatus: _handleStatus,
        debugLogging: kDebugMode,
      );
      _isInitialized = true;
      notifyListeners();
      return _speechAvailable;
    } catch (e) {
      debugPrint('Error inicializando SpeechToText: $e');
      _speechAvailable = false;
      _isInitialized = true;
      notifyListeners();
      return false;
    }
  }

  void _handleError(SpeechRecognitionError error) {
    debugPrint('Speech recognition error: ${error.errorMsg} (${error.permanent})');
    _lastError = error.errorMsg;
    _isListening = false;
    notifyListeners();
  }

  void _handleStatus(String status) {
    debugPrint('Speech recognition status: $status');
    if (status == 'listening') {
      _isListening = true;
    } else if (status == 'notListening' || status == 'done') {
      _isListening = false;
    }
    notifyListeners();
  }

  /// Inicia la escucha física del micrófono en español
  Future<bool> startListening({
    required Function(String words, bool isFinal) onResult,
  }) async {
    if (!_isInitialized) {
      await initialize();
    }

    _lastError = null;
    _recognizedWords = '';

    try {
      HapticFeedback.mediumImpact();
    } catch (_) {}

    if (!_speechAvailable) {
      debugPrint('SpeechToText no disponible en este dispositivo.');
      return false;
    }

    try {
      // Intentar usar español latinoamericano o de España
      final locales = await _speech.locales();
      String selectedLocale = 'es_ES';
      for (var loc in locales) {
        if (loc.localeId.startsWith('es')) {
          selectedLocale = loc.localeId;
          break;
        }
      }

      await _speech.listen(
        onResult: (SpeechRecognitionResult result) {
          _recognizedWords = result.recognizedWords;
          onResult(result.recognizedWords, result.finalResult);
          notifyListeners();
        },
        onSoundLevelChange: (level) {
          _soundLevel = level;
          notifyListeners();
        },
        localeId: selectedLocale,
        listenFor: const Duration(seconds: 30),
        pauseFor: const Duration(seconds: 3),
        partialResults: true,
        cancelOnError: false,
        listenMode: stt.ListenMode.confirmation,
      );

      _isListening = true;
      notifyListeners();
      return true;
    } catch (e) {
      debugPrint('Error iniciando escucha por voz: $e');
      _isListening = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> stopListening() async {
    try {
      await _speech.stop();
      _isListening = false;
      try {
        HapticFeedback.lightImpact();
      } catch (_) {}
      notifyListeners();
    } catch (e) {
      debugPrint('Error deteniendo SpeechToText: $e');
    }
  }

  Future<void> cancelListening() async {
    try {
      await _speech.cancel();
      _isListening = false;
      notifyListeners();
    } catch (e) {
      debugPrint('Error cancelando SpeechToText: $e');
    }
  }
}
