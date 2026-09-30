# -*- coding: utf-8 -*-
import json
import logging
import re
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("classforge.codegen.prompt")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

def _get_type_info(raw_type: str) -> Dict[str, str]:
    cleaned = str(raw_type).lower().strip()
    mapping = {
        "string": {"ts": "string", "dart": "String", "sample": '"ejemplo"'},
        "str": {"ts": "string", "dart": "String", "sample": '"ejemplo"'},
        "text": {"ts": "string", "dart": "String", "sample": '"texto descriptivo"'},
        "varchar": {"ts": "string", "dart": "String", "sample": '"ejemplo"'},
        "int": {"ts": "number", "dart": "int", "sample": "10"},
        "integer": {"ts": "number", "dart": "int", "sample": "10"},
        "long": {"ts": "number", "dart": "int", "sample": "100"},
        "bigint": {"ts": "number", "dart": "int", "sample": "100"},
        "double": {"ts": "number", "dart": "double", "sample": "99.99"},
        "float": {"ts": "number", "dart": "double", "sample": "49.50"},
        "decimal": {"ts": "number", "dart": "double", "sample": "150.00"},
        "bool": {"ts": "boolean", "dart": "bool", "sample": "true"},
        "boolean": {"ts": "boolean", "dart": "bool", "sample": "true"},
        "date": {"ts": "string (YYYY-MM-DD)", "dart": "DateTime", "sample": '"2026-05-15"'},
        "datetime": {"ts": "string (ISO-8601)", "dart": "DateTime", "sample": '"2026-05-15T10:30:00"'},
        "timestamp": {"ts": "string (ISO-8601)", "dart": "DateTime", "sample": '"2026-05-15T10:30:00"'}
    }
    return mapping.get(cleaned, {"ts": "string", "dart": "String", "sample": '"ejemplo"'})

def get_plural_name(name: str) -> str:
    lower = name.lower()
    if lower.endswith("s"):
        return lower
    if lower.endswith("y") and len(lower) > 1 and lower[-2] not in "aeiou":
        return lower[:-1] + "ies"
    if lower.endswith("z"):
        return lower[:-1] + "ces"
    if lower.endswith("dad") or lower.endswith("cion") or lower.endswith("sion") or lower.endswith("tad"):
        return lower + "es"
    return lower + "s"

def generate_frontend_meta_prompt(
    graph_data: dict, 
    target_framework: str = "flutter", 
    theme: str = "dark"
) -> str:
    """
    Generates an exhaustive, high-precision, production-grade Meta-Prompt in Markdown
    for external LLMs (Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro, Cursor)
    to generate a complete Mobile Application (Flutter / React Native) or Web SPA.
    
    Includes:
    - 100% Responsive CRUD Components for all UML Entities.
    - Native Microphone Permissions and Voice Assistant UI.
    - Anti-Blank Screen Hybrid Architecture Flow (App -> FastAPI Cloud -> Local Backend -> Cloud DB).
    - Natural Language Voice processing flow with Gemini.
    - Automatic Folder Scaffolding & 1-Click APK Compilation.
    """
    nodes = list(graph_data.get("nodes", [])) if isinstance(graph_data, dict) else []
    edges = list(graph_data.get("edges", [])) if isinstance(graph_data, dict) else []
    
    if not nodes and not edges and isinstance(graph_data, dict) and "cells" in graph_data:
        cells = graph_data.get("cells", [])
        for cell in cells:
            shape = (cell.get("shape") or cell.get("type") or "").lower()
            if "edge" in shape or cell.get("source") or cell.get("target"):
                edges.append(cell)
            else:
                nodes.append(cell)
    
    classes: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        node_type = (node.get("type") or node.get("shape") or "").lower().replace("uml-", "").replace("-", "")
        if node_type in ["class", "abstract", "entity", "classnode"] or "class" in node_type or "entity" in node_type:
            data = node.get("data", {})
            raw_name = data.get("name") or "Entity"
            clean_name = re.sub(r'[^a-zA-Z0-9_]', '', str(raw_name))
            if not clean_name or not clean_name[0].isalpha():
                clean_name = f"Entity{clean_name}"
            clean_name = clean_name[0].upper() + clean_name[1:]
            
            raw_attrs = data.get("attributes", [])
            parsed_attrs = []
            for attr in raw_attrs:
                if isinstance(attr, dict):
                    aname = attr.get("name", "")
                    atype = attr.get("type", "string")
                elif isinstance(attr, str):
                    cleaned = attr.lstrip("+-#~ ").strip()
                    if ":" in cleaned:
                        parts = cleaned.split(":", 1)
                        aname = parts[0].strip()
                        atype = parts[1].strip()
                    else:
                        aname = cleaned
                        atype = "string"
                else:
                    continue
                aname = re.sub(r'[^a-zA-Z0-9_]', '', str(aname))
                if not aname or aname.lower() in ["id", "_id", "createdat", "updatedat", "created_at", "updated_at"]:
                    continue
                aname = aname[0].lower() + aname[1:]
                type_info = _get_type_info(atype)
                parsed_attrs.append({
                    "name": aname,
                    "ts_type": type_info["ts"],
                    "dart_type": type_info["dart"],
                    "sample": type_info["sample"]
                })
            
            plural_path = get_plural_name(clean_name)
            classes[str(node.get("id"))] = {
                "name": clean_name,
                "endpoint_path": plural_path,
                "attributes": parsed_attrs,
                "relations": [],
                "parent_name": None
            }
            
    for edge in edges:
        source_val = edge.get("source")
        target_val = edge.get("target")
        source_id = str(source_val if isinstance(source_val, str) else (source_val.get("cell") if isinstance(source_val, dict) else str(source_val or "")))
        target_id = str(target_val if isinstance(target_val, str) else (target_val.get("cell") if isinstance(target_val, dict) else str(target_val or "")))
        
        edge_data = edge.get("data", {})
        edge_type = (edge_data.get("type") or edge.get("shape") or "association").lower()
        
        if source_id in classes and target_id in classes:
            source_cls = classes[source_id]
            target_cls = classes[target_id]
            
            if edge_type in ["generalization", "inheritance"]:
                source_cls["parent_name"] = target_cls["name"]
            else:
                s_mult = edge_data.get("sourceMultiplicity", "1")
                t_mult = edge_data.get("targetMultiplicity", "*")
                
                if "*" in t_mult or "n" in t_mult.lower():
                    source_cls["relations"].append({
                        "type": "OneToMany",
                        "target_name": target_cls["name"],
                        "target_endpoint": target_cls["endpoint_path"],
                        "field_name": target_cls["endpoint_path"]
                    })
                    target_cls["relations"].append({
                        "type": "ManyToOne",
                        "target_name": source_cls["name"],
                        "target_endpoint": source_cls["endpoint_path"],
                        "field_name": source_cls["name"][0].lower() + source_cls["name"][1:],
                        "foreign_key": f"{source_cls['name'][0].lower() + source_cls['name'][1:]}Id"
                    })
                else:
                    source_cls["relations"].append({
                        "type": "OneToOne",
                        "target_name": target_cls["name"],
                        "target_endpoint": target_cls["endpoint_path"],
                        "field_name": target_cls["name"][0].lower() + target_cls["name"][1:],
                        "foreign_key": f"{target_cls['name'][0].lower() + target_cls['name'][1:]}Id"
                    })

    framework_normalized = target_framework.lower().replace(" ", "").replace("_", "-")
    theme_normalized = theme.lower()
    
    if framework_normalized == "flutter":
        framework_title = "Flutter 3.x (Dart 3) Aplicación Móvil Híbrida & Offline-First con Asistente de Voz"
        framework_instructions = """- **Stack Tecnológico**: Flutter 3.x (Flutter 3.22+), Dart 3.4+, flutter_riverpod (Riverpod 2.5), dio (Cliente HTTP con interceptores y reintentos), speech_to_text, permission_handler, flutter_animate, google_fonts.
- **Permisos Nativos en `android/app/src/main/AndroidManifest.xml`**:
  ```xml
  <uses-permission android:name="android.permission.RECORD_AUDIO" />
  <uses-permission android:name="android.permission.INTERNET" />
  <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
  <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
  ```
- **Configuración de URLs Adaptativas en `lib/core/constants/api_constants.dart`**:
  ```dart
  class ApiConstants {
    // 1. Backend Nube FastAPI (Hidratación inmediata y Asistente de Voz Gemini)
    static const String cloudBaseUrl = 'https://classforge-backend.onrender.com';
    
    // 2. Backend Local (Spring Boot puerto 8080 o FastAPI puerto 8000)
    static String get localBaseUrl {
      if (Platform.isAndroid) return 'http://10.0.2.2:8080/api/v1'; // Emulador Android
      return 'http://localhost:8080/api/v1'; // iOS / Web
    }
  }
  ```
- **Estructura Modular de Archivos**:
  ```text
  lib/
  ├── core/
  │   ├── constants/api_constants.dart
  │   ├── network/api_client.dart           # Dio con fallback Nube -> Local
  │   ├── theme/app_theme.dart
  │   └── voice/voice_assistant_service.dart # Servicio acústico de micrófono y STT
  ├── features/
  │   ├── voice_assistant/
  │   │   ├── widgets/floating_voice_button.dart # Botón pulsante flotante de micrófono
  │   │   └── screens/voice_chat_sheet.dart      # BottomSheet con feedback de voz en vivo
  │   ├── [Entidad]/
  │   │   ├── models/[entidad]_model.dart
  │   │   ├── providers/[entidad]_provider.dart
  │   │   ├── repositories/[entidad]_repository.dart
  │   │   └── screens/
  │   │       ├── [entidad]_list_screen.dart     # Responsive List / Grid con Pull-to-Refresh
  │   │       ├── [entidad]_form_screen.dart     # Formulario validado con pickers
  │   │       └── [entidad]_detail_screen.dart
  │   └── home/
  │       └── screens/main_dashboard_screen.dart # Dashboard con accesos y estado
  └── main.dart
  ```
- **Script de Creación y Compilación Automática del APK**:
  ```bash
  # 1. Crear proyecto y obtener dependencias
  flutter create . --org com.classforge.app
  flutter pub get

  # 2. Compilar APK Release listo para instalación inmediata en Android
  flutter build apk --release

  # El binario ejecutable final se genera en:
  # build/app/outputs/flutter-apk/app-release.apk
  ```"""
    elif framework_normalized == "react-native":
        framework_title = "React Native (Expo SDK 51 & TypeScript) con Reconocimiento de Voz"
        framework_instructions = """- **Stack Tecnológico**: React Native (Expo SDK 51), TypeScript, TanStack React Query v5, Zustand, Axios, Expo AV / Expo Speech Recognition, NativeWind/Tailwind.
- **Permisos en `app.json`**:
  ```json
  {
    "expo": {
      "plugins": [
        [
          "expo-speech-recognition",
          {
            "microphonePermission": "ClassForge requiere acceso al micrófono para comandos de voz con IA."
          }
        ]
      ]
    }
  }
  ```
- **URLs de Conexión Híbrida**:
  ```ts
  export const API_CONFIG = {
    cloudUrl: 'https://classforge-backend.onrender.com',
    localUrl: Platform.OS === 'android' ? 'http://10.0.2.2:8080/api/v1' : 'http://localhost:8080/api/v1'
  };
  ```
- **Comandos de Creación y Build del APK**:
  ```bash
  npx create-expo-app --template blank-typescript .
  npx expo install expo-speech expo-av @tanstack/react-query axios zustand lucide-react-native
  npx eas-cli build -p android --profile preview
  ```"""
    elif framework_normalized == "angular":
        framework_title = "Angular 17+ (Standalone Signals & RxJS) Enterprise SPA"
        framework_instructions = """- **Stack Tecnológico**: Angular 17+ (Standalone Components, Signals), ReactiveFormsModule (`FormGroup`, `FormControl`, `Validators`), Tailwind CSS, HttpClient con interceptores, Web Speech API (`webkitSpeechRecognition`).
- **Arquitectura Híbrida**: Servicio `CloudSyncService` para hidratación inicial desde FastAPI en la nube y proxy local para operaciones CRUD."""
    elif framework_normalized == "vue":
        framework_title = "Vue 3 (Composition API / Pinia) Modern Web App"
        framework_instructions = """- **Stack Tecnológico**: Vue 3 (Vite), `<script setup>` syntax, TypeScript, Tailwind CSS, Pinia, Axios, Web Speech API."""
    elif framework_normalized == "vanilla":
        framework_title = "Vanilla HTML5 / JavaScript (ES Modules) Lightweight Web App"
        framework_instructions = """- **Stack Tecnológico**: HTML5 Semántico, JavaScript ES Modules, Tailwind CDN, Fetch API, Web Speech API nativa."""
    else:
        framework_title = "React 18+ (Vite / TypeScript / Tailwind) Professional Web SPA"
        framework_instructions = """- **Stack Tecnológico**: React 18+ (Vite), TypeScript, Tailwind CSS, TanStack Query, Lucide Icons, Axios, Web Speech API."""

    palette_instructions = """- **Tema Visual**: Modo Oscuro Enterprise (ClassForge Dark Aesthetic).
  - Fondo Principal: `#0F172A` (Slate 900)
  - Superficies y Tarjetas: `#1E293B` (Slate 800)
  - Bordes e Inputs: `#334155` (Slate 700)
  - Acento Primario: `#256BE4` (Electric Blue) con hover/active `#1A4FB0`
  - Micrófono / Voz Activa: `#8B5CF6` (Vibrant Purple) con pulso animado
  - Éxito / Confirmación: `#10B981` (Emerald Green)
  - Peligro / Eliminación: `#EF4444` (Ruby Red)
  - Textos: `#F1F5F9` (Slate 100) primario, `#94A3B8` (Slate 400) secundario.""" if theme_normalized == "dark" else """- **Tema Visual**: Modo Claro Limpio y Moderno.
  - Fondo Principal: `#F8FAFC` (Slate 50)
  - Superficies y Tarjetas: `#FFFFFF` (Pure White) con sombras suaves `shadow-sm`
  - Bordes e Inputs: `#E2E8F0` (Slate 200)
  - Acento Primario: `#2563EB` (Royal Blue)
  - Micrófono / Voz Activa: `#7C3AED` (Purple)
  - Éxito / Confirmación: `#10B981` (Emerald)
  - Peligro / Eliminación: `#EF4444` (Red)
  - Textos: `#0F172A` (Slate 900) primario, `#64748B` (Slate 500) secundario."""

    entities_doc = []
    for cls in classes.values():
        name = cls["name"]
        endpoint = cls["endpoint_path"]
        attrs = cls["attributes"]
        relations = cls["relations"]
        parent = cls.get("parent_name")
        
        sample_request_fields = {}
        sample_response_fields = {"id": 1}
        for a in attrs:
            val_sample = "ejemplo" if "string" in a["ts_type"] else (10 if "number" in a["ts_type"] else True)
            sample_request_fields[a["name"]] = val_sample
            sample_response_fields[a["name"]] = val_sample
            
        rel_specs = []
        for r in relations:
            if r["type"] == "ManyToOne":
                sample_request_fields[r["foreign_key"]] = 1
                sample_response_fields[r["field_name"]] = {"id": 1, "name": f"Parent {r['target_name']}"}
                rel_specs.append(f"  - **Pertenece a `{r['target_name']}` (@ManyToOne)**: El formulario de `{name}` DEBE incluir un selector (Dropdown o BottomSheet) cargado dinámicamente desde `GET /api/v1/{r['target_endpoint']}` para seleccionar `{r['foreign_key']}`.")
            elif r["type"] == "OneToMany":
                sample_response_fields[r["field_name"]] = []
                rel_specs.append(f"  - **Tiene muchos `{r['target_name']}` (@OneToMany)**: En la vista de detalle de `{name}`, mostrar sub-lista con tarjetas hijas `{r['field_name']}`.")
                
        rel_str = "\n".join(rel_specs) if rel_specs else "  - *Sin relaciones foráneas directas.*"
        parent_str = f"\n  - *Hereda de*: `{parent}`" if parent else ""
        
        entity_section = f"""### Entidad: `{name}`
- **Endpoint Base**: http://localhost:8080/api/v1/{endpoint} (/api/v1/{endpoint}){parent_str}
- **Atributos**:
{chr(10).join([f"  - `{a['name']}`: `{a['ts_type']}` (Dart: `{a['dart_type']}`)" for a in attrs]) or "  - *(Solo ID autogenerado)*"}
- **Relaciones**:
{rel_str}
- **Operaciones CRUD**:
  - `GET /api/v1/{endpoint}` ➔ Listar todos los registros
  - `GET /api/v1/{endpoint}/{{id}}` ➔ Obtener registro por ID
  - `POST /api/v1/{endpoint}` ➔ Crear nuevo registro (Payload: `{name}RequestDTO`, HTTP 201)
  - `PUT /api/v1/{endpoint}/{{id}}` ➔ Actualizar registro (Payload: `{name}RequestDTO`, HTTP 200)
  - `DELETE /api/v1/{endpoint}/{{id}}` ➔ Eliminar registro (HTTP 204)
- **Ejemplo JSON Request Payload (`POST`/`PUT`)**:
```json
{json.dumps(sample_request_fields, indent=2)}
```
- **Ejemplo JSON Response Payload (`GET`)**:
```json
{json.dumps(sample_response_fields, indent=2)}
```"""
        entities_doc.append(entity_section)
        
    all_entities_str = "\n\n".join(entities_doc) if entities_doc else "*(No se definieron clases en el diagrama)*"
    
    prompt = f"""# Prompt para Generación de Aplicación Frontend / Mobile Profesional
## Objetivo: Construir {framework_title}

Actúa como un **Lead Mobile & Frontend Architect y Senior AI/UX Specialist**. Tu misión es construir la aplicación móvil o frontend COMPLETO, modular, responsivo y 100% operativo basado en el diagrama conceptual modelado en ClassForge.

---

## 🏛️ 1. Arquitectura de Flujo Híbrido (Garantía Anti-Pantalla en Blanco)
La aplicación debe implementar el siguiente flujo arquitectónico de alta disponibilidad:

```text
App Móvil / Web ➔ Backend Nube FastAPI (ClassForge Cloud) ➔ Backend Local (Spring Boot/FastAPI) ➔ Base de Datos Nube (MongoDB / PostgreSQL)
```

1. **Hidratación Inmediata de Recursos**: Al arrancar, la aplicación consulta inmediatamente a la URL en la nube (`https://classforge-backend.onrender.com/health` y `/api/v1/...`) para precargar catálogos, datos iniciales y estado, asegurando que el usuario **NUNCA vea una pantalla en blanco**.
2. **Sincronización Local**: Si el usuario está ejecutando el backend local (en `http://10.0.2.2:8080` en Android o `http://localhost:8080`), la app realiza las operaciones CRUD rápidas contra el backend local y sincroniza en segundo plano.

---

## 🎙️ 2. Módulo de Asistente de Voz & Micrófono Integrado
La aplicación DEBE incluir una interfaz nativa de control por voz:

1. **Permisos de Audio**: Solicitar en tiempo de ejecución permiso de micrófono (`RECORD_AUDIO`).
2. **Botón Flotante de Micrófono (Floating Voice Button)**:
   - Botón flotante accesible en todas las pantallas con animación de pulsación (*pulse effect*) al hablar.
   - Panel inferior (*Voice Chat BottomSheet*) con transcripción en tiempo real del habla del usuario.
3. **Flujo de Ejecución por Voz con Gemini**:
   - `Micrófono en la App` ➔ Captura texto dictado (ej. *"Registrar nueva venta de 2 laptops al cliente Juan"*).
   - `Envío a FastAPI Nube` ➔ Envía la orden a `POST /api/v1/ai/generate`.
   - `Procesamiento con Gemini API` ➔ NLU extrae la intención, entidad y parámetros.
   - `Ejecución & Persistencia` ➔ Actualiza la Base de Datos y sincroniza la lista en la App.
   - `Feedback Sonoro / Visual` ➔ Muestra alerta de éxito y actualiza la pantalla sin recargar toda la app.

---

## 🛠️ 3. Stack Técnico y Configuración
{framework_instructions}

---

## 🎨 4. Paleta de Diseño y Guía de Estilo Visual Responsive
{palette_instructions}
- **Diseño 100% Responsive**:
  - En móviles: Navegación inferior (Bottom Navigation Bar), listas en tarjetas con Pull-to-Refresh y acciones deslizables (Swipe-to-delete).
  - En tablets/desktop: Barra lateral colapsable (Navigation Rail) y vistas en Grid / Data Tables de alta densidad.

---

## 📡 5. Especificación de Entidades y Contratos API REST
{all_entities_str}

---

## 📦 6. Pipeline de Scaffolding y Compilación Automática del APK
Genera el proyecto completo con los siguientes comandos automatizados:

```bash
# 1. Crear estructura y dependencias
flutter create . --org com.classforge.app
flutter pub get

# 2. Compilar APK Release listo para producción
flutter build apk --release

# APK generado en:
# build/app/outputs/flutter-apk/app-release.apk
```

Entrega todos los archivos con su código **COMPLETO**, sin omitir ninguna clase, método o widget.
"""
    return prompt


async def generate_frontend_meta_prompt_with_gemini(
    graph_data: dict,
    target_framework: str = "flutter",
    theme: str = "dark",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synthesizes and enriches the frontend meta-prompt using Google Gemini API.
    Falls back gracefully to the deterministic generator.
    """
    base_prompt = generate_frontend_meta_prompt(graph_data, target_framework, theme)
    key = api_key or settings.GEMINI_API_KEY
    
    if not key:
        char_count = len(base_prompt)
        return {
            "prompt": base_prompt,
            "character_count": char_count,
            "estimated_tokens": max(1, char_count // 4),
            "target_framework": target_framework,
            "theme": theme,
            "engine_used": "deterministic"
        }

    target_model = model or getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash") or "gemini-3.8-flash"
    url = f"{GEMINI_API_BASE}/{target_model}:generateContent?key={key}"
    
    instruction = """You are a Senior Mobile & Frontend Architect.
Enrich and refine the following Meta-Prompt for code generation LLMs (Claude, GPT-4, Cursor).
Ensure it has:
1. Complete CRUD specs and responsive UI guidelines.
2. Native microphone permissions and voice assistant workflows.
3. Hybrid flow: App -> Cloud FastAPI -> Local Backend -> Cloud Database.
4. Voice flow: Mic -> FastAPI -> Gemini -> DB -> Real-time feedback.
5. Exact 1-click APK compilation script.
Output the complete, enriched Markdown prompt directly without backticks."""

    payload = {
        "contents": [
            {"parts": [{"text": f"Enrich this architecture prompt:\n\n{base_prompt}"}]}
        ],
        "systemInstruction": {
            "parts": [{"text": instruction}]
        },
        "generationConfig": {
            "temperature": 0.3
        }
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                char_count = len(text)
                return {
                    "prompt": text,
                    "character_count": char_count,
                    "estimated_tokens": max(1, char_count // 4),
                    "target_framework": target_framework,
                    "theme": theme,
                    "engine_used": f"Google Gemini ({target_model})"
                }
    except Exception as e:
        logger.warning(f"Gemini prompt generation failed ({e}). Using deterministic prompt.")

    char_count = len(base_prompt)
    return {
        "prompt": base_prompt,
        "character_count": char_count,
        "estimated_tokens": max(1, char_count // 4),
        "target_framework": target_framework,
        "theme": theme,
        "engine_used": "deterministic"
    }
