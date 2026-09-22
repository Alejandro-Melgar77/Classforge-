# ClassForge Mobile 📱

App móvil oficial de **ClassForge** construida en **Flutter 3.x** con arquitectura limpia y diseño **Forge Dark Professional**. Diseñada específicamente para **consulta en tiempo real, métricas ejecutivas, notificaciones colaborativas in-app y asistente NLU 100% on-device (offline)**.

---

## 🎯 Principios y Restricciones Arquitectónicas

1. **Visor de Diagramas 100% Solo Lectura (Readonly)**:
   - Los diagramas UML se editan en la versión web (Angular 17 + AntV X6). En el móvil, el usuario puede explorar, hacer pinch-to-zoom (60 FPS vía `InteractiveViewer`), inspeccionar atributos/métodos y revisar relaciones sin riesgo de alterar accidentalmente el modelo.
2. **Notificaciones Colaborativas In-App por WebSockets Nativos**:
   - Sin dependencias pesadas de Firebase Cloud Messaging (FCM) ni servicios de terceros. Las notificaciones se reciben en tiempo real mediante la conexión WebSocket nativa a `/api/v1/ws/diagrams/{id}`.
3. **Motor NLU On-Device 100% Offline (<1ms, 0MB memoria)**:
   - Algoritmo determinista portado a Dart con latencia `<1ms`. Permite interpretar comandos de voz y texto en lenguaje natural en el dispositivo sin conexión a internet y sin necesidad de descargar pesados LLMs de varios gigabytes.
4. **Paleta "Forge Dark Professional"**:
   - Fondo principal: `#0F172A`
   - Superficies y tarjetas: `#1E293B`
   - Primario: `#2D6BE4`
   - Acento / éxito: `#00C896`
   - Advertencia: `#F5A623`
   - Peligro: `#E74C3C`
   - Texto principal: `#F1F5F9`

---

## 🚀 Estructura del Proyecto

```
classforge-mobile/
├── lib/
│   ├── core/
│   │   ├── constants/
│   │   │   └── api_constants.dart       # Endpoints HTTP y WebSocket
│   │   ├── services/
│   │   │   ├── api_service.dart         # Cliente REST con token JWT en SharedPreferences
│   │   │   ├── websocket_service.dart   # Conexión WS nativa y gestor de notificaciones
│   │   │   └── offline_nlu_service.dart # Motor NLU Dart offline (<1ms)
│   │   └── theme/
│   │       └── app_theme.dart           # Forge Dark ThemeData y tipografía GoogleFonts
│   ├── models/
│   │   ├── user_model.dart              # Usuario, roles y token
│   │   ├── project_model.dart           # Proyectos y estadísticas de Dashboard
│   │   ├── diagram_model.dart           # Diagrama UML, nodos, atributos, métodos y aristas
│   │   └── notification_model.dart      # Notificaciones colaborativas en tiempo real
│   ├── widgets/
│   │   ├── uml_class_card.dart          # Caja UML con estereotipo, visibilidad y métodos
│   │   └── uml_relationship_painter.dart # CustomPainter para líneas, flechas y diamantes UML
│   ├── screens/
│   │   ├── auth/login_screen.dart       # Inicio de sesión con accesos rápidos demo
│   │   ├── dashboard/dashboard_screen.dart # Métricas (Total, Activos, Completados, Equipos)
│   │   ├── projects/projects_screen.dart   # Repertorio de proyectos con filtros
│   │   ├── diagrams/diagram_viewer_screen.dart # Visor interactivo 60fps solo lectura
│   │   ├── notifications/notifications_screen.dart # Centro de notificaciones in-app
│   │   ├── assistant/offline_assistant_screen.dart # Asistente NLU con simulación de voz
│   │   └── home/home_screen.dart        # Shell con BottomNavigationBar y badge de avisos
│   └── main.dart                        # MultiProvider y configuración inicial
├── test/
│   ├── offline_nlu_test.dart            # Pruebas unitarias del motor NLU en Dart
│   └── diagram_model_test.dart          # Pruebas de deserialización JSON de UML
├── pubspec.yaml
└── README.md
```

---

## 🛠️ Instalación y Ejecución

### Prerrequisitos
- Flutter SDK `>=3.0.0`
- Emulador Android (Android Studio) o Dispositivo físico
- Backend ClassForge corriendo en el puerto `8000`

### 1. Obtener dependencias
```bash
cd classforge-mobile
flutter pub get
```

### 2. Configurar la URL del Backend
Por defecto en `lib/core/constants/api_constants.dart`:
- Para **Emulador Android**: `http://10.0.2.2:8000/api/v1` (ya configurado)
- Para **Dispositivo Físico**: Cambiar a la IP local de tu máquina de desarrollo, ej: `http://192.168.1.100:8000/api/v1`.

### 3. Ejecutar la Aplicación
```bash
# Ejecutar en el dispositivo conectado o emulador
flutter run
```

### 4. Ejecutar Pruebas Unitarias
```bash
flutter test
```

---

## 🔑 Credenciales de Prueba (Demo)
El `LoginScreen` incluye botones de un solo toque para iniciar sesión inmediatamente con:
- **Administrador**: `admin@classforge.io` / `Admin123!`
- **Scrum Master**: `scrum@classforge.io` / `Scrum123!`
- **Desarrollador**: `dev@classforge.io` / `Dev12345!`
