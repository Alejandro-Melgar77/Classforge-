# ClassForge 🚀

**ClassForge** es una plataforma integral de modelado conceptual UML 2.5+, generación de código backend y colaboración en tiempo real con asistencia offline basada en NLU y comandos por voz.

---

## 🏗️ Arquitectura del Sistema

El ecosistema se compone de 3 módulos principales:

1. **`classforge-backend` (FastAPI / Python 3.11)**
   - API REST asíncrona y servidor WebSocket para colaboración multi-usuario.
   - Motor heurístico NLU para procesamiento de lenguaje natural y comandos por voz.
   - Generador de código Clean Architecture (Spring Boot 3 / Flutter).
   - Base de datos MongoDB con soporte para proyectos, carpetas, equipos y diagramas.

2. **`classforge-frontend` (Angular 17 / TailwindCSS)**
   - Diagramador interactivo SVG/Canvas UML 2.5+.
   - Asistente de IA por voz con Web Speech API y ejecución reactiva de comandos in-canvas.
   - Drawer de previsualización de código generado en vivo.
   - Presencia multi-cursor, bloqueo optimista de nodos y chat colaborativo.

3. **`classforge-mobile` (Flutter / Dart)**
   - Visor y modelador móvil offline/online.
   - Motor de comandos NLU en el dispositivo (<1ms latencia, 0MB consumo adicional de memoria).
   - Reconocimiento de voz y centro de notificaciones push / locales.
   - Gestión de equipos, proyectos y diagnóstico en panel de control.

---

## 🚀 Despliegue Rápido con Docker Compose

La forma recomendada para desplegar el entorno completo de producción o pruebas es mediante Docker:

```bash
# 1. Clonar el repositorio
git clone https://github.com/Alejandro-Melgar77/Classforge-.git
cd Classforge-

# 2. Levantar los servicios (MongoDB, Backend, Frontend NGINX)
docker compose up -d --build
```

Una vez levantados los contenedores:
- **Frontend Web:** `http://localhost`
- **Backend API Docs:** `http://localhost:8000/docs`
- **MongoDB:** `localhost:27017`

---

## 💻 Ejecución Local para Desarrollo

### Backend
```bash
cd classforge-backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd classforge-frontend
npm install
npm run start
# Abre en http://localhost:4200
```

### Mobile (Flutter)
```bash
cd classforge-mobile
flutter pub get
flutter run
```

---

## ⚙️ Variables de Entorno (Backend)

| Variable | Descripción | Valor por Defecto |
|---|---|---|
| `PROJECT_NAME` | Nombre de la aplicación | `ClassForge` |
| `API_V1_STR` | Prefijo de rutas del API | `/api/v1` |
| `SECRET_KEY` | Clave secreta para JWT | `super-secret-key-change-me` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración token de acceso | `60` |
| `MONGODB_URL` | URL de conexión MongoDB | `mongodb://localhost:27017` |
| `DATABASE_NAME` | Nombre de base de datos | `classforge` |
| `CORS_ORIGINS` | Orígenes permitidos (CORS) | `http://localhost:4200,http://localhost` |
