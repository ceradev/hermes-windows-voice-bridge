# Hermes Windows Voice Bridge

> Cliente nativo de Windows para [Hermes Agent](https://github.com/nousresearch/hermes-agent).
>
> Asistente de voz de escritorio: wake phrase, hotkey global, STT local, envío a Hermes en tu VPS y respuestas por TTS.

---

## Índice

- [Resumen](#resumen)
- [Arquitectura](#arquitectura)
- [Integración con Hermes](#integración-con-hermes)
- [Requisitos](#requisitos)
- [Instalación para usuarios](#instalación-para-usuarios)
- [Desarrollo](#desarrollo)
- [Configuración](#configuración)
- [Uso](#uso)
- [Flujo de datos](#flujo-de-datos)
- [Build e instalador](#build-e-instalador)
- [Tests](#tests)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## Resumen

Hermes Windows Voice Bridge convierte tu PC en un asistente de voz que funciona en segundo plano:

1. **Escucha** wake phrases ("Hermes", "Oye Hermes", "Hey Hermes")
2. **Activa** con hotkey global (por defecto `Ctrl+Shift+H`)
3. **Graba** hasta detectar silencio
4. **Transcribe** localmente con [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
5. **Envía** el texto a la API de Hermes en tu VPS
6. **Guarda** sesiones y mensajes en SQLite local
7. **Lee** la respuesta con TTS (pyttsx3 / SAPI5 o edge-tts)

La experiencia principal es **nativa de Windows**: icono en bandeja, overlay flotante y panel de configuración React embebido con pywebview.

### Características

| Característica | Descripción |
|---------------|-------------|
| Wake phrase | Detección local por STT en ventanas cortas |
| Hotkey global | Atajo configurable con captura visual |
| STT local | faster-whisper — el audio no sale del PC |
| TTS local | Respuestas leídas en voz alta |
| Sesiones SQLite | Historial local + `remote_session_id` para VPS |
| Tray nativo | Menú contextual con micrófonos, pausa y comandos rápidos |
| Dashboard React | Home, Chat, Configure, Settings, Commands |
| Overlay | Pill flotante con estados listening / thinking / speaking |
| Autostart | Opcional al instalar o desde Settings |
| Comandos custom | Abrir apps, búsqueda web, volumen, TTS, hotkeys |

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           WINDOWS DESKTOP                               │
│  ┌────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ Tray       │  │ pywebview   │  │ Overlay     │  │ Hotkeys         │ │
│  │ (pystray)  │  │ + React UI  │  │ (tkinter)   │  │ (ShortcutMgr)   │ │
│  └─────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘ │
│        │                │                │                   │          │
│        └────────────────┴────────────────┴───────────────────┘          │
│                                    │                                     │
│                         ┌──────────▼──────────┐                          │
│                         │   WebviewBridge     │                          │
│                         │   (Python ↔ React)  │                          │
│                         └──────────┬──────────┘                          │
│                                    │                                     │
│         ┌──────────────────────────┼──────────────────────────┐          │
│         │                          │                          │          │
│  ┌──────▼──────┐          ┌────────▼────────┐        ┌────────▼────────┐│
│  │ Core        │          │ Services        │        │ Platform        ││
│  │ ConfigSvc   │◄────────►│ Audio + Whisper │        │ VoiceLoop       ││
│  │ AppState    │◄────────►│ WakePhrase      │        │ OverlayService  ││
│  │ SessionMgr  │◄────────►│ TTS             │        │ Autostart       ││
│  │ EventBus    │          │ HermesClient    │        │ SecureStore     ││
│  └──────┬──────┘          └─────────────────┘        └─────────────────┘│
│         │                                                                │
│  ┌──────▼──────┐                                                         │
│  │ SQLite      │  %APPDATA%\HermesVoiceBridge\database.sqlite            │
│  └─────────────┘                                                         │
└──────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ HTTPS / HTTP + Bearer token
                                     ▼
                          ┌─────────────────────┐
                          │ Hermes API (VPS)    │
                          │ /api/health         │
                          │ /api/hermes/message │
                          │ /api/sessions       │
                          └─────────────────────┘
```

### Principios de diseño

- **Entrypoint único:** `src/platform/windows/desktop_app.py`
- **Single source of truth:** `AppStateStore` centraliza el estado runtime
- **Background-first:** tray, overlay y hotkeys son la experiencia principal
- **Persistencia en AppData:** config, DB y logs fuera del directorio de instalación
- **Seguridad:** tokens vía keyring/DPAPI; SSL verificado en cliente HTTP

---

## Integración con Hermes

### Requisitos en el VPS

1. Hermes Agent / gateway accesible desde tu PC
2. API HTTP habilitada (puerto por defecto del despliegue, ej. `8642`)
3. Token de cliente válido (`api_token`)

### Configuración en el cliente

Desde **Settings** en el dashboard o editando `%APPDATA%\HermesVoiceBridge\config.json`:

```json
{
  "api_base_url": "http://TU_VPS:8642",
  "api_token": "tu-token-de-cliente"
}
```

También puedes inyectar el token por entorno antes del primer arranque:

```powershell
$env:HERMES_API_TOKEN = "tu-token"
python -B src\platform\windows\desktop_app.py
```

### Envío de mensajes

`HermesClient.send_message()` hace `POST /api/hermes/message` con:

```json
{
  "sessionId": "uuid-remoto",
  "message": "texto transcrito o escrito",
  "source": "voice",
  "metadata": {
    "client": "hermes-voice-bridge",
    "platform": "windows",
    "appVersion": "1.0.0",
    "language": "es"
  }
}
```

Respuesta esperada (simplificada):

```json
{
  "success": true,
  "response": "Texto de Hermes",
  "speak": true,
  "latencyMs": 820
}
```

Si `speak` es verdadero, `TTSService` lee la respuesta en voz alta.

### Sesiones

- **Locales:** SQLite en AppData (lista en Chat)
- **Remotas:** `remote_session_id` sincroniza con `/api/sessions` del VPS
- **Auto-titulado:** sesiones genéricas se renombran desde el primer mensaje (ES/EN)

---

## Requisitos

### Sistema

- Windows 10/11 (64-bit)
- Micrófono
- ~500 MB libres (modelos Whisper)

### Desarrollo

- Python 3.11+
- Node.js 18+ y npm
- Inno Setup (solo para generar el instalador)

---

## Instalación para usuarios

**Distribución oficial:** instalador Windows generado con Inno Setup.

1. Ejecuta `HermesVoiceBridge-setup.exe` (o el nombre de salida de `setup.iss`)
2. Sigue el asistente (escritorio y autostart son opcionales)
3. Abre la app desde el menú Inicio o la bandeja del sistema
4. En **Settings**, configura `api_base_url` y `api_token`
5. En **Configure**, elige micrófono y hotkey

Datos de usuario (config, sesiones, logs) viven en:

```text
%APPDATA%\HermesVoiceBridge\
├── config.json
├── database.sqlite
└── app.log
```

---

## Desarrollo

### 1. Clonar e instalar

```powershell
git clone https://github.com/ceradev/hermes-windows-voice-bridge.git
cd hermes-windows-voice-bridge
python -m pip install -r requirements.txt
cd src\ui\app
npm install
cd ..\..\..
```

### 2. Arrancar (recomendado)

```powershell
.\scripts\run_desktop_app.ps1
```

Compila la UI y lanza `desktop_app.py`.

### 3. Modo dev UI (hot reload)

```powershell
# Terminal 1
cd src\ui\app
npm run dev

# Terminal 2
$env:HERMES_UI_DEV = "1"
python -B src\platform\windows\desktop_app.py
```

Documentación detallada de build: [docs/BUILD_NOTES.md](docs/BUILD_NOTES.md)  
Plan de trabajo: [docs/PLAN.md](docs/PLAN.md)

---

## Configuración

Archivo: `%APPDATA%\HermesVoiceBridge\config.json`

| Clave | Default | Descripción |
|-------|---------|-------------|
| `api_base_url` | VPS configurado | URL base de la API Hermes |
| `api_token` | `""` | Token Bearer / client key |
| `hotkey` | `ctrl+shift+h` | Atajo global de voz |
| `wake_phrases` | `["hermes", ...]` | Frases de activación |
| `stt_model` | `base` | Modelo Whisper: tiny/base/small/… |
| `stt_language` | `es` | Idioma STT |
| `mic_device` | `null` | Índice de micrófono sounddevice |
| `feedback_mode` | `both` | `off`, `beep`, `voice`, `both` |
| `feedback_voice` | `""` | Voz SAPI5 para TTS |
| `overlay_enabled` | `true` | Mostrar overlay flotante |
| `overlay_mode` | `mini` | `mini` o `full` |
| `autostart` | `true` | Inicio con Windows |
| `custom_commands` | `[]` | Comandos personalizados |

La mayoría de opciones se editan desde **Configure** y **Settings** sin tocar el JSON a mano.

---

## Uso

### Por voz (wake phrase)

1. La app escucha en background
2. Di **"Hermes"**, **"Oye Hermes"** o **"Hey Hermes"**
3. Habla tu comando tras el feedback (beep/voz según config)
4. Al detectar silencio: transcribe → envía → TTS si aplica

### Por hotkey

1. Pulsa `Ctrl+Shift+H` (o tu combinación)
2. Habla el comando
3. Mismo flujo que con wake phrase

### Dashboard (React)

| Página | Función |
|--------|---------|
| **Home** | Estado de conexión, escucha, hotkey, actividad reciente |
| **Chat** | Sesiones, mensajes, envío manual |
| **Configure** | Wake phrases, micrófono, hotkeys, TTS |
| **Settings** | API Hermes, overlay, autostart, idioma |
| **Commands** | Biblioteca de comandos personalizados |

### Bandeja del sistema

- Click izquierdo → abre dashboard
- Click derecho → micrófonos, pausa, comandos rápidos, settings, restart, quit

### Overlay

Pill flotante siempre visible (si está habilitado): estados idle, listening, thinking, speaking. Botones para abrir dashboard y activar micrófono.

---

## Flujo de datos

```
Usuario habla
    → AudioService (sounddevice)
    → WakePhraseManager / VoiceLoop (faster-whisper)
    → WebviewBridge.send_message()
    → HermesClient → VPS
    → SQLite (mensaje usuario + respuesta)
    → Evento hermes_new_message → React
    → TTSService (si speak=true)
    → Overlay + Tray actualizan estado
```

Estados de escucha en runtime (`listening_state`): `idle`, `listening`, `thinking`, `processing`, `speaking`, `responding`.

---

## Build e instalador

### Ejecutable portable (PyInstaller)

```powershell
python build.py
# → dist/HermesVoiceBridge/HermesVoiceBridge.exe
```

### Instalador (distribución oficial)

```powershell
python build.py
.\scripts\build_installer.ps1
```

Usa `setup.iss` en la raíz del repo. Requiere [Inno Setup](https://jrsoftware.org/isdl.php).

Ver [docs/BUILD_NOTES.md](docs/BUILD_NOTES.md) para requisitos, troubleshooting y checklist post-build.

---

## Tests

```powershell
python -m pytest tests/ -v
```

**Estado actual:** 44 tests passing.

```
tests/
├── test_phase1_smoke_pipeline.py
├── test_voice_loop_concurrency.py
├── test_webview_bridge_config_sync.py
├── test_audio_service.py
├── test_wake_phrase_manager.py
├── test_tts_service_shutdown.py
├── test_session_naming.py
└── test_message_stats.py
```

---

## Estructura del proyecto

```
hermes-windows-voice-bridge/
├── docs/
│   ├── PLAN.md                 # Plan por fases
│   ├── PROJECT_STATUS.md       # Estado actual
│   ├── BUILD_NOTES.md          # Build + instalador
│   └── PHASE1_VERIFICATION.md
├── scripts/
│   ├── run_desktop_app.ps1     # Dev: build UI + launch
│   ├── build_installer.ps1     # PyInstaller + Inno Setup
│   ├── install_autostart.ps1
│   └── uninstall_voice_bridge.ps1
├── src/
│   ├── api/
│   │   └── webview_bridge.py   # Bridge Python ↔ React
│   ├── core/                   # config, state, session, events
│   ├── platform/
│   │   ├── windows/
│   │   │   ├── desktop_app.py  # ★ Entrypoint oficial
│   │   │   ├── voice_loop.py
│   │   │   └── overlay_service.py
│   │   ├── tray/
│   │   └── shortcuts/
│   ├── services/               # audio, hermes, tts, wakeword, agent
│   ├── storage/                # SQLite + cache
│   └── ui/app/                 # React + Vite frontend
├── tests/
├── build.py                    # Build PyInstaller
├── setup.iss                   # ★ Spec Inno Setup oficial
├── requirements.txt
└── README.md
```

---

## Troubleshooting

### Hermes aparece offline en Home

- Verifica `api_base_url` y `api_token` en Settings
- Comprueba que el VPS responde: `GET {api_base_url}/api/health`
- Revisa firewall entre tu PC y el puerto del API

### No hay icono en bandeja

- La app puede estar arrancando (descarga del modelo Whisper la primera vez)
- Revisa `%APPDATA%\HermesVoiceBridge\app.log`

### UI en blanco

- Falta build de React: `cd src\ui\app && npm run build`
- O usa `HERMES_UI_DEV=1` con `npm run dev` en paralelo

### Wake phrase no detecta

- Ajusta `wake_energy` en config (default `0.008`)
- Confirma el micrófono correcto en Configure
- Prueba activación por hotkey para aislar el problema

### Hotkey no responde

- Otra app puede tener la misma combinación
- Guarda de nuevo en Configure; el bridge reinicia el registro de shortcuts
- Revisa toasts de error en la UI

### Modelo Whisper no descarga

```powershell
$env:HF_HUB_OFFLINE = "0"
python -B src\platform\windows\desktop_app.py
```

### Build falla: `HermesVoiceBridge.spec` not found

El spec puede estar en `.gitignore`. Consulta [docs/BUILD_NOTES.md](docs/BUILD_NOTES.md).

---

## Roadmap

### Completado

- [x] Wake phrase por STT local
- [x] Hotkey global configurable
- [x] Transcripción faster-whisper
- [x] TTS local
- [x] Tray + overlay + dashboard React
- [x] Sesiones SQLite + sync VPS
- [x] Comandos personalizados
- [x] Build PyInstaller + spec Inno Setup
- [x] 43 tests automatizados

### En progreso / planificado

- [x] Documentación alineada (Fase 1)
- [x] Limpieza código legacy tkinter (Fase 2)
- [x] Stats reales en dashboard Home (Fase 3)
- [ ] Instalador reproducible end-to-end (Fase 4)
- [ ] Wake engine dedicado (Porcupine / OpenWakeWord)
- [ ] Voces TTS nativas por idioma
- [ ] Múltiples perfiles de usuario

---

## Licencia

MIT © César Suárez / ceradev

Plugin no oficial para [Hermes Agent](https://github.com/nousresearch/hermes-agent) (Nous Research). Sin afiliación ni respaldo oficial.
