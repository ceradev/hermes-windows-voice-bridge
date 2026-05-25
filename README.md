# Hermes Windows Voice Bridge

> **Plugin oficial de voz nativa para Hermes Agent en Windows.**
>
> Cliente Windows de escritorio que permite interactuar con Hermes mediante voz: wake word, hotkey, transcripción local, envío al webhook de Hermes, y lectura de respuestas con TTS.

---

## Índice

- [Resumen](#resumen)
- [Arquitectura](#arquitectura)
- [Integración con Hermes](#integración-con-hermes)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Flujo de Datos](#flujo-de-datos)
- [Sesión Persistente](#sesión-persistente)
- [Empaquetado y Distribución](#empaquetado-y-distribución)
- [Desarrollo y Tests](#desarrollo-y-tests)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## Resumen

Hermes Windows Voice Bridge es un cliente nativo de Windows para [Hermes Agent](https://github.com/nousresearch/hermes-agent). Transforma tu PC en un asistente de voz local que:

1. **Escucha** continuamente una wake phrase (ej: "Hermes", "Oye Hermes")
2. **Activa** por hotkey configurable (default: `Ctrl+Shift+H`)
3. **Graba** tu comando de voz hasta detectar silencio
4. **Transcribe** localmente con [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (modelos Whisper de OpenAI, ejecutados on-device)
5. **Envía** el texto al webhook de Hermes en tu VPS
6. **Recibe** la respuesta de Hermes
7. **Lee en voz alta** la respuesta con TTS (pyttsx3 / SAPI5 en Windows)

Todo ocurre sin abrir Telegram ni tocar el móvil. Una experiencia desktop-native, silenciosa y persistente.

### Características principales

| Característica | Descripción |
|---------------|-------------|
| 🎙️ Wake Word | Detección local por STT en ventanas cortas ("Hermes", "Oye Hermes", "Hey Hermes") |
| ⌨️ Hotkey | Atajo global configurable con captura visual moderna |
| 🧠 STT Local | `faster-whisper` — no envía audio al servidor, solo texto |
| 🔊 TTS Local | pyttsx3 + SAPI5 — respuestas leídas en voz alta |
| 🔄 Sesión Persistente | Autenticación que sobrevive reinicios de app y de Windows |
| 🎯 Tray Native | Icono en bandeja del sistema con menú contextual |
| 🖥️ Desktop App | Aplicación de configuración con UX moderna (tkinter themed) |
| 📡 API Local | HTTP API en `localhost:8765` para control externo |
| 🎨 Overlay | Feedback visual compacto en pantalla (listening, transcribing, responding) |
| 📦 Autostart | Inicio automático con Windows vía Scheduled Task + Startup shortcut |
| 🛠️ Extensible | Arquitectura modular: core, services, platform, ui, storage, api |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WINDOWS DESKTOP                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │  Tray Icon  │    │ Desktop App │    │   Overlay   │    │   Hotkey    │    │
│  │  (pystray)  │    │  (tkinter)  │    │  (tkinter)  │    │  (ctypes)   │    │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    │
│         │                  │                  │                  │          │
│         └──────────────────┴──────────────────┴──────────────────┘          │
│                                    │                                         │
│                         ┌──────────▼──────────┐                              │
│                         │   EVENT BUS         │                              │
│                         │   (pub/sub interno) │                              │
│                         └──────────┬──────────┘                              │
│                                    │                                         │
│         ┌──────────────────────────┼──────────────────────────┐             │
│         │                          │                          │             │
│  ┌──────▼──────┐          ┌────────▼────────┐        ┌────────▼────────┐  │
│  │  Core       │          │  Services       │        │  Platform        │  │
│  │  ─────────  │          │  ─────────────  │        │  ──────────────  │  │
│  │  ConfigSvc  │◄────────►│  Audio (sd+whisper)      │  Windows        │  │
│  │  StateMgr   │◄────────►│  WakeWord (STT loop)     │  Notifications  │  │
│  │  SessionMgr │◄────────►│  Transcription           │  Shortcuts      │  │
│  │  Logger     │◄────────►│  TTS (pyttsx3)           │  SecureStore    │  │
│  │  Lifecycle  │          │  Hermes (webhook POST)   │  SingleInstance │  │
│  └─────────────┘          └──────────────────────────┘        └─────────────────┘  │
│                                                                         │  │
│                              ┌──────────────┐                           │  │
│                              │  Storage     │                           │  │
│                              │  ───────────  │                           │  │
│                              │  Session JSON │                           │  │
│                              │  Secrets      │                           │  │
│                              │  Runtime State│                           │  │
│                              │  Cache        │                           │  │
│                              └──────────────┘                           │  │
│                                                                         │  │
└─────────────────────────────────────────────────────────────────────────┘  │
                                     │                                         │
                                     │ HTTP POST + HMAC-SHA256                   │
                                     │                                         │
                              ┌──────▼──────┐                                  │
                              │   VPS        │                                  │
                              │  Hermes      │                                  │
                              │  Gateway     │                                  │
                              │  ───────────  │                                  │
                              │  Webhook     │                                  │
                              │  Route:voice │                                  │
                              │  Agent       │                                  │
                              │  Telegram    │                                  │
                              └─────────────┘                                  │
```

### Principios de diseño

- **Menos web, más nativo:** No es una web app empaquetada. Es Python nativo con tkinter, ctypes, pystray.
- **Background utility:** La experiencia principal ocurre via tray, overlays, y atajos. No necesitas abrir ventanas.
- **Single source of truth:** Un único `AppStateStore` centralizado. No hay estados duplicados.
- **Event-driven:** Todo flujo de audio → transcripción → webhook → TTS pasa por el event bus.
- **Seguridad:** Tokens de sesión en archivo separado (`session.secrets`), HMAC-SHA256 en cada POST al webhook.

---

## Integración con Hermes

### Requisitos en el VPS (Hermes Gateway)

1. **Webhook activo** en el gateway de Hermes
2. **Ruta `voice`** creada y configurada
3. **Secret compartido** entre VPS y cliente Windows

### Configurar el webhook en el VPS

```bash
# En tu VPS donde corre Hermes
hermes webhook subscribe voice --secret "$(openssl rand -hex 32)"
```

Esto genera un secreto aleatorio. Guárdalo — lo necesitarás en el cliente Windows.

### Payload enviado al webhook

Cada comando de voz envía un POST a `http://VPS_IP:8644/webhooks/voice`:

```json
{
  "text": "hola hermes, ¿qué hora es?",
  "source": "windows_voice_bridge",
  "event_type": "voice",
  "user_id": "cesar"
}
```

Headers:
```
Content-Type: application/json
X-Webhook-Signature: <hmac-sha256-del-body>
X-Request-ID: cesar
```

- **`user_id`** y **`X-Request-ID`**: Si hay sesión persistida, Hermes agrupa todos los mensajes del mismo usuario en el mismo thread. Sin esto, cada comando crearía un chat nuevo.
- **`X-Webhook-Signature`**: HMAC-SHA256 del body con el shared secret. El gateway de Hermes valida esto para rechazar requests no autorizados.

### Respuesta de Hermes (modo sync)

Si `HERMES_WEBHOOK_SYNC=1`, el bridge espera la respuesta HTTP del webhook:

```json
{
  "response": "Son las 3:15 PM. ¿Necesitas algo más?",
  "final_response": "Son las 3:15 PM. ¿Necesitas algo más?"
}
```

El bridge extrae el texto y lo pasa al motor TTS para leerlo en voz alta.

---

## Requisitos

### Sistema

- Windows 10/11 (64-bit)
- Python 3.11 o superior
- Micrófono funcional
- ~500MB espacio libre (para modelos Whisper)

### Dependencias Python

Instalación automática via `requirements.txt`:

```powershell
pip install -r requirements.txt
```

Principales dependencias:
- `faster-whisper` — STT local (modelos Whisper optimizados)
- `sounddevice` — Captura de audio del micrófono
- `numpy` — Procesamiento de audio
- `pystray` — Icono en bandeja del sistema
- `Pillow` — Iconos e imágenes para tray
- `pyttsx3` — TTS local (SAPI5 en Windows)

---

## Instalación

### 1. Clonar o descargar

```powershell
git clone https://github.com/ceradev/hermes-windows-voice-bridge.git
cd hermes-windows-voice-bridge
```

### 2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copia el archivo de ejemplo y edítalo:

```powershell
copy state\voice.env.example state\voice.env
notepad state\voice.env
```

Contenido mínimo de `state/voice.env`:

```env
HERMES_WEBHOOK_URL=http://TU_VPS_IP:8644/webhooks/voice
HERMES_WEBHOOK_SECRET=tu_secreto_del_vps_aqui
HERMES_HOTKEY=ctrl+shift+h
HERMES_FEEDBACK_MODE=both
HERMES_WEBHOOK_SYNC=1
HERMES_STT_LANGUAGE=es
```

### 4. Ejecutar

**Opción A: Solo el bridge de voz**
```powershell
python .\src\windows_hermes_voice.py
```

**Opción B: Tray con supervisión (recomendado)**
```powershell
.\scripts\run_voice_tray.ps1
```

**Opción C: Desktop app**
```powershell
python -B .\src\windows_hermes_voice_desktop.py
```

---

## Configuración

### Variables de entorno completas

| Variable | Default | Descripción |
|----------|---------|-------------|
| `HERMES_WEBHOOK_URL` | (requerido) | URL del webhook en tu VPS |
| `HERMES_WEBHOOK_SECRET` | (requerido) | Secreto compartido para HMAC |
| `HERMES_WEBHOOK_SYNC` | `1` | Esperar respuesta de Hermes (1=sí, 0=no) |
| `HERMES_WEBHOOK_TIMEOUT` | `120` | Timeout en segundos para respuesta sync |
| `HERMES_HOTKEY` | `ctrl+shift+h` | Atajo global para activar escucha |
| `HERMES_WAKE_PHRASES` | `hermes,oye hermes,hey hermes` | Frases de activación por voz |
| `HERMES_STT_MODEL` | `base` | Modelo Whisper: tiny/base/small/medium/large |
| `HERMES_STT_LANGUAGE` | (auto) | Código idioma STT: `es`, `en`, etc. |
| `HERMES_MIC_DEVICE` | (default) | Índice del micrófono a usar |
| `HERMES_FEEDBACK_MODE` | `both` | Feedback: `off`, `beep`, `voice`, `both` |
| `HERMES_FEEDBACK_VOICE` | (default) | Nombre de voz SAPI5 para TTS |
| `HERMES_PERSIST_SESSION` | `1` | Mantener sesión iniciada entre reinicios |
| `HERMES_AUTH_REFRESH_URL` | (vacío) | Endpoint HTTP para refresh de tokens |
| `HERMES_AUTH_TIMEOUT` | `10` | Timeout para llamadas de auth |

### Configuración por archivo

Todas las variables también se pueden editar desde la **Desktop App** (pestañas General, Audio, Shortcuts, Hermes, Session).

Los cambios se guardan en `state/voice.env` automáticamente.

---

## Uso

### Activar por voz (Wake Word)

1. El bridge escucha continuamente en segundo plano
2. Di una wake phrase: **"Hermes"**, **"Oye Hermes"**, o **"Hey Hermes"**
3. Escucharás un beep + "Escuchando..." (si feedback=both)
4. Habla tu comando
5. Al detectar silencio, transcribe y envía automáticamente
6. Hermes responde en Telegram y (si sync=1) se lee en voz alta

### Activar por hotkey

1. Presiona `Ctrl+Shift+H` (o tu hotkey configurado)
2. El bridge entra en modo escucha inmediatamente
3. Habla tu comando
4. El resto es igual que con wake word

### Desktop App

```powershell
python -B .\src\windows_hermes_voice_desktop.py
```

**Pestañas:**
- **General:** Wake phrases, feedback, autostart
- **Audio:** Selección de micrófono, dispositivo de entrada
- **Shortcuts:** Editor visual de hotkey (captura en tiempo real con pills animadas)
- **Hermes:** Endpoint del webhook, configuración de auth refresh
- **Session:** Login/logout, persistencia de sesión, refresh de tokens
- **Logs:** Logs en tiempo real con filtros

### Tray Icon

Click derecho en el icono de Hermes en la bandeja del sistema:

```
● Ready
─────────────────
Start Listening
Stop Listening
Open Hermes (Desktop)
View Logs
Settings
Restart Services
Quit
```

---

## Flujo de Datos

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Usuario   │     │   Audio     │     │   Bridge    │     │   Hermes    │
│   habla     │────►│   Capture   │────►│   Engine    │────►│   Gateway   │
└─────────────┘     └─────────────┘     └──────┬──────┘     └──────┬──────┘
                                               │                    │
                                               │ 1. Wake detect     │
                                               │ 2. Record command  │
                                               │ 3. Transcribe (whisper)
                                               │ 4. POST to webhook │
                                               │ 5. Await response  │
                                               │ 6. TTS speak       │
                                               │                    │
                                        ┌──────▼──────┐     ┌──────▼──────┐
                                        │   Event Bus │     │  Telegram   │
                                        │   Signals   │────►│  (user)     │
                                        └─────────────┘     └─────────────┘
```

### Estados del sistema (Event Bus)

| Señal | Disparador | Descripción |
|-------|-----------|-------------|
| `audio.started` | Wake word detectada o hotkey presionado | Inicio de grabación |
| `audio.stopped` | Silencio detectado | Fin de grabación |
| `transcription.completed` | Whisper devuelve texto | Texto transcrito listo |
| `hermes.response` | Webhook devuelve 200 | Respuesta recibida de Hermes |
| `tts.started` | Inicio de síntesis de voz | Leyendo respuesta en voz alta |
| `session.restored` | Al iniciar con sesión guardada | Sesión recuperada del disco |
| `shortcut.updated` | Al cambiar hotkey | Nueva combinación guardada |

---

## Sesión Persistente

### ¿Por qué?

Hermes asigna un `chat_id` a cada interacción. Sin identificación persistente, cada comando de voz crea un **chat nuevo** en Telegram. La sesión persistente agrupa todos tus comandos en el mismo thread.

### ¿Cómo funciona?

1. El usuario guarda credenciales en la Desktop App (pestaña Session)
2. `SessionManager` guarda en `state/session.json` (datos públicos) y `state/session.secrets` (tokens)
3. Al iniciar, `SessionManager.restore()` recupera la sesión
4. En cada POST al webhook, se envía `user_id` + header `X-Request-ID`
5. Hermes reconoce al usuario y continúa la conversación previa

### Backend de refresh extensible

```python
# Local (default): extiende expiración localmente
LocalRefreshBackend()

# HTTP: llama a endpoint real de tu backend
HttpRefreshBackend(
    refresh_url="https://auth.hermes.example/refresh",
    timeout=10,
    extra_headers={"Authorization": "Bearer ..."},
)
```

Configura via env vars:
```env
HERMES_AUTH_REFRESH_URL=https://tu-backend.com/api/refresh
HERMES_AUTH_TIMEOUT=10
HERMES_AUTH_HEADER=Authorization: Bearer static-token
```

---

## Empaquetado y Distribución

### ZIP portable

```powershell
.\scripts\package_voice_bridge.ps1
```

Genera `dist/HermesVoiceBridge-windows.zip` — listo para descomprimir y ejecutar.

### Instalador Windows (Inno Setup)

Requisito: [Inno Setup](https://jrsoftware.org/isdl.php) instalado (`ISCC.exe` en PATH).

```powershell
.\scripts\build_installer.ps1
```

Genera `dist/HermesVoiceBridge-setup.exe` — instalador profesional con:
- Shortcut en Start Menu
- Registro de desinstalación en Panel de Control
- Icono de app

### Autostart con Windows

```powershell
.\scripts\install_autostart.ps1
```

Crea:
- Scheduled Task "Hermes Voice Bridge" (logon)
- Shortcut en Startup folder
- Persistencia de `voice.env` entre reinicios

### Desinstalar

```powershell
.\scripts\uninstall_voice_bridge.ps1
```

Elimina:
- Scheduled Task y shortcuts
- Archivos de estado (`voice.env`, sesión, logs)
- Procesos en ejecución

---

## Desarrollo y Tests

### Ejecutar tests

```powershell
python -m pytest tests/ -v
```

**Resultado actual:** 46 tests passing.

### Estructura de tests

```
tests/
├── test_refactor_foundations.py      # Core: state, config, events, session
├── test_windows_voice.py             # Bridge: post_json, submit_command, TTS
├── test_windows_voice_control.py     # Mutex, tray process control
├── test_windows_voice_desktop_models.py  # Desktop: theme, models
├── test_windows_voice_desktop_support.py # Desktop: API client, palette
├── test_windows_voice_overlay.py     # Overlays: signal mapping
└── test_windows_voice_panel_api.py   # API local: endpoints, state, session
```

### Arquitectura de paquetes

```
src/hermes_voice_bridge/
├── core/           # Lógica de negocio central
│   ├── config/     # ConfigService (voice.env)
│   ├── events/     # EventBus pub/sub
│   ├── lifecycle/  # AppLifecycle (start, stop, restart)
│   ├── logging/    # BridgeLogger (user, debug, crash logs)
│   ├── session/    # SessionManager + auth backends
│   └── state/      # AppStateStore (single source of truth)
├── platform/       # Abstracciones de plataforma
│   └── windows/    # SecureValueStore, single-instance mutex
├── services/       # (próximamente: audio, wake, transcription, tts)
├── storage/        # Persistencia
│   ├── cache/      # RuntimeSignalStore, RuntimeStateStore
│   └── repositories/  # JsonSessionRepository
├── ui/             # Interfaz de usuario
│   ├── desktop/    # ApiClient, theme, widgets
│   ├── overlays/   # Status overlay (listening, transcribing, responding)
│   └── settings/   # Models de configuración
└── api/            # (próximamente: endpoints HTTP)
```

---

## Estructura del Proyecto

```
hermes-windows-voice-bridge/
├── docs/
│   └── plans/
│       └── 2026-05-24-native-refactor-plan.md   # Plan de refactorización
├── panel-web/                                   # Legacy web panel (deprecated)
│   ├── index.html
│   ├── package.json
│   └── src/
├── scripts/
│   ├── build_installer.ps1                      # Build Inno Setup installer
│   ├── install_autostart.ps1                    # Configurar autostart Windows
│   ├── package_voice_bridge.ps1                 # Generar ZIP portable
│   ├── run_voice.ps1                            # Launch bridge directo
│   ├── run_voice_desktop.ps1                    # Launch desktop app
│   ├── run_voice_tray.ps1                       # Launch tray supervisor
│   ├── run_voice_watchdog.ps1                   # Launch con auto-restart
│   └── uninstall_voice_bridge.ps1               # Desinstalar completamente
├── src/
│   ├── hermes_voice_bridge/                     # Paquete Python principal
│   │   ├── core/
│   │   ├── platform/
│   │   ├── storage/
│   │   └── ui/
│   ├── windows_hermes_voice.py                  # Bridge de voz principal
│   ├── windows_hermes_voice_control.py          # Mutex, process control
│   ├── windows_hermes_voice_desktop.py          # Desktop app (tkinter)
│   ├── windows_hermes_voice_panel_api.py        # API local HTTP
│   └── windows_hermes_voice_tray.py             # Tray supervisor
├── state/                                       # Estado local (no commitear)
│   ├── voice.env.example                        # Plantilla de configuración
│   ├── logs/                                    # Logs de ejecución
│   ├── session.json                             # Sesión persistida (generado)
│   └── session.secrets                          # Tokens seguros (generado)
├── tests/                                       # Suite de tests pytest
├── .gitignore                                   # Excluye state/, node_modules/
├── README.md                                    # Este archivo
└── requirements.txt                             # Dependencias Python
```

---

## Troubleshooting

### "Set HERMES_WEBHOOK_SECRET to the route secret"

No has configurado el secreto del webhook. Obténlo del VPS:
```bash
hermes webhook list  # en el VPS
```

### "No se pudo enviar" (TTS feedback)

El bridge falló al hacer POST al webhook. Verifica:
- `HERMES_WEBHOOK_URL` apunta a tu VPS correctamente
- El gateway de Hermes está corriendo en el VPS
- No hay firewall bloqueando el puerto 8644

### "Port 8765 already in use"

Otra instancia del panel API ya está corriendo. Mata el proceso:
```powershell
Get-Process python | Where-Object {$_.MainWindowTitle -like "*Hermes*"} | Stop-Process
```

### Tray icon no aparece

Verifica que `state/voice.env` existe y tiene `HERMES_WEBHOOK_URL` y `HERMES_WEBHOOK_SECRET`. Sin ellos, el bridge muere antes de que el tray se muestre.

### Modelo Whisper no descarga

La primera ejecución descarga el modelo Whisper desde HuggingFace. Si falla:
```powershell
$env:HF_HUB_OFFLINE=0
python .\src\windows_hermes_voice.py
```

### Wake word no detecta

- Sube `HERMES_WAKE_ENERGY` (default 0.008) si es muy sensible
- Verifica que `HERMES_MIC_DEVICE` apunta al micrófono correcto
- Lista dispositivos: `python .\src\windows_hermes_voice.py --list-devices`

---

## Roadmap

- [x] Wake word por STT local
- [x] Hotkey global configurable
- [x] Transcripción con faster-whisper
- [x] TTS local con pyttsx3/SAPI5
- [x] Tray icon con menú contextual
- [x] Desktop app con pestañas
- [x] Sesión persistente con refresh backend
- [x] API local HTTP
- [x] Overlay de estado visual
- [x] Tests automatizados (46 passing)
- [x] ZIP portable + Inno Setup installer
- [x] Autostart con Windows
- [ ] Wake word engine dedicado (Porcupine/OpenWakeWord)
- [ ] Separación de voces por idioma (español/inglés nativo)
- [ ] Soporte para múltiples perfiles de usuario
- [ ] Plugin de acciones del sistema (abrir apps, controlar volumen, etc.)

---

## Licencia

MIT © César Suárez / ceradev

Este es un plugin no oficial para [Hermes Agent](https://github.com/nousresearch/hermes-agent) de Nous Research. No está afiliado ni respaldado oficialmente por Nous Research.
