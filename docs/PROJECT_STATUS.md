# Hermes Windows Voice Bridge - estado del proyecto

Actualizado: 2026-06-23
Rama auditada: `development`
Estado: snapshot de trabajo **sin commitear** con cambios amplios en backend, runtime Windows y UI React.

## 1. Qué es este repositorio

Hermes Windows Voice Bridge es el plugin/aplicación nativa de Windows para usar Hermes Agent por voz. La visión del producto es que funcione como un programa normal de Windows: instalable con un `package.exe`/instalador, icono en bandeja, autostart opcional, panel gráfico, overlay flotante, configuración persistente, sesiones locales/remotas y atajos globales.

Flujo buscado: activación por wake phrase/hotkey/botón, captura de audio local, STT local, envío a Hermes/VPS, guardado de sesiones/mensajes, respuesta por TTS cuando proceda y sincronización entre dashboard, tray, overlay, estado runtime y configuración.

## 2. Arquitectura actual observada

### Backend/runtime Python

- `src/platform/windows/desktop_app.py`: entrypoint desktop pywebview actual. Inicializa AppData, logging, configuración, SQLite, estado runtime, bridge, audio, TTS, wakeword, shortcuts, tray y overlay.
- `src/platform/windows/voice_loop.py`: bucle de voz en background. Gestiona escucha, wake phrase, grabación, STT, envío a Hermes, TTS, pausa/restart y actualización de overlay/tray.
- `src/api/webview_bridge.py`: bridge Python expuesto a React por `window.pywebview.api`. Gestiona config, sesiones, mensajes, salud, actividad reciente, audio devices, overlay, tray, shortcuts y comandos personalizados.
- `src/core/state/app_state.py`: `AppStateStore`, fuente thread-safe de estado runtime compartido: lifecycle, overlay, sesión, shortcut, servicios (`tray`, `bridge`, `api`, `hermes`, `tts`) y runtime (`connection_status`, micrófono, hotkey, overlay, listening state).
- `src/core/session/session_manager.py`: sesiones locales SQLite, mensajes, remote session id, token VPS vía keyring y auto-titulado de sesiones en inglés/español.
- `src/platform/tray/tray_manager.py`: tray nativo con pystray, icono con estado, tooltip, menú de micrófono, comandos rápidos, actividad reciente, pausa, settings, restart y quit.
- `src/platform/windows/overlay_service.py`: overlay/pill transparente con tkinter, drag, persistencia de posición, botones dashboard/mic/cerrar y estados activos. Riesgo: `set_mode()` todavía está vacío aunque la UI expone modo mini/full.
- `src/services/*`: audio, Hermes client, TTS, wakeword, comandos personalizados, herramientas locales/RAG/proactivo.
- `src/storage/database.py`: SQLite local para sesiones/mensajes y datos persistentes.

### Frontend React/Vite

La UI actual vive en `src/ui/app` y usa React 18 + Vite + Tailwind + Framer Motion + Lucide.

Rutas actuales en `src/ui/app/src/App.tsx`: `/` -> `Home.tsx`, `/chat` -> `Chat.tsx`, `/configure` -> `Configure.tsx`, `/settings` -> `Settings.tsx`, `/commands` -> `Commands.tsx`.

Páginas anteriores (`Voice`, `Shortcuts`, `Sessions`, `History`, `Notifications`) fueron eliminadas del working tree y sus conceptos se han plegado en `Chat`, `Configure`, `Settings`, `Commands` y componentes/layout nuevos.

Servicios/contextos importantes:

- `src/ui/app/src/services/api.ts`: wrapper seguro de `window.pywebview.api` con fallbacks si pywebview no existe. Expone config/runtime/sesiones/mensajes/audio/health/window/tray/overlay/pause/restart/custom commands.
- `HermesContext`: estado global de salud, pausa, runtime/config y sincronización con backend.
- `ToastContext`: toasts de éxito/error/warning.
- `LanguageContext`, `ThemeContext`: idioma/tema.

## 3. Funcionalidades añadidas o trabajadas hasta ahora

### UI y experiencia visual

- Rediseño minimalista tipo Apple/Windows glass oscuro.
- Eliminación de contenido falso o decorativo que confundía: perfil local falso, campanas/acciones sin utilidad, botones test falsos.
- Layout con `Titlebar`, `Sidebar`, `Header`, `PageHeader`, tema oscuro y estilo glass consistente.
- Dashboard `Home` orientado a estado real: salud Hermes, pausa/listening, micrófono activo, hotkey, actividad reciente y accesos rápidos.
- Consolidación de páginas: chat + sesiones + actividad en `Chat`, configuración de voz/shortcuts/TTS en `Configure`, backend/overlay/app behavior en `Settings`, comandos personalizados en `Commands`.
- Sistema de toasts para errores reales y avisos. Nota histórica: se probó lógica global de conexión dentro de `HermesProvider`, provocó pantalla en blanco en pywebview y se movió hacia un componente shell más seguro (`SystemAlerts`, actualmente untracked).

### Sesiones y chat

- Sesiones locales en SQLite con sesión activa por defecto.
- Crear, cambiar, eliminar y renombrar sesiones.
- Soporte de `remote_session_id` para sincronización con Hermes/VPS.
- Auto-titulado de sesiones genéricas a partir del primer mensaje del usuario, con limpieza de prefijos en inglés y español.
- `Chat.tsx` combina lista de sesiones, actividad del sistema y mensajes.
- Envío manual de mensajes desde UI, copia/exportación y eventos `hermes_new_message` para refrescar.

### Runtime state y sincronización

- `AppStateStore` centraliza el estado runtime: sesión, shortcut, servicios, overlay y micrófono.
- `webview_bridge.py` sincroniza config, tray, overlay, servicios y runtime state.
- `get_runtime_state()` expone snapshot completo al frontend.
- `send_message()` registra mensajes de usuario/Hermes, actualiza estado Hermes, mide latencia, dispara TTS si aplica y emite evento frontend.
- `check_health()` actualiza estado Hermes y tray.

### Tray nativo

- Tray con icono “H” y punto de estado: conectado, offline o pausado.
- Tooltip con app, estado, hotkey y micrófono.
- Menú con dashboard, micrófonos disponibles, comandos rápidos, actividad reciente, pausa/reanudar, settings, restart y quit.
- Click izquierdo abre dashboard.
- Integración con estado de pausa, conexión, micrófono activo, shortcut y actividad.

### Overlay

- Overlay flotante/pill siempre encima, transparente, arrastrable y con posición persistente.
- Estado idle compacto con “H”.
- Hover expandido con botones de dashboard, micrófono y cerrar.
- Estados activos con texto/dots animados.
- Configuración de enable/posición visible desde backend/UI.
- Pendiente: implementar de verdad `set_mode()` para modo mini/full o simplificar la UI si sólo existe un modo real.

### Configuración, audio y shortcuts

- `Configure.tsx` agrupa wake/audio, hotkeys y TTS feedback.
- Selección de micrófono vía `api.getAudioDevices()` y guardado por config.
- `HotkeyRecorder` para capturar hotkeys de voz, mute, pausa y visión.
- Bridge aplica cambios de micrófono resolviendo nombre/hostapi y pidiendo restart de stream al voice loop.
- Bridge reinicia shortcuts al cambiar configuración salvo si están pausados.

### Comandos personalizados

- `Commands.tsx` gestiona biblioteca de comandos.
- Acciones soportadas: abrir app, búsqueda web, volumen del sistema, TTS speak, hotkey.
- Validación de nombre, trigger phrase y acciones completas.
- Test, crear, editar y borrar comandos.
- Integración con quick commands en tray.

### Seguridad y limpieza histórica

Trabajo ya registrado en git/historial del repo:

- Eliminación de token hardcoded.
- Endurecimiento por fases: subprocess shell removal, hardening HTTP local, sandbox RAG, DPAPI secure store, guardas SSL/XSS, permisos seguros de env/static/config.
- Limpieza de helpers y entrypoints obsoletos en commits previos.
- Mejoras de packaging/build en iteraciones anteriores, aunque el estado actual debe verificarse antes de afirmar que el instalador está completo.

## 4. Estado actual del working tree

Hay muchos cambios sin commitear. Resumen observado con `git status --short`:

- Backend modificado: `src/api/webview_bridge.py`, config/session/state, tray, desktop app, overlay, voice loop, audio service, database.
- Frontend modificado: package files, `App.tsx`, layout, contexts, CSS, `Home`, `Settings`, `Commands`, `api.ts`, Tailwind.
- Frontend eliminado: `AudioVisualizer.tsx`, `History.tsx`, `Notifications.tsx`, `Sessions.tsx`, `Shortcuts.tsx`, `Voice.tsx`.
- Tests eliminado: `tests/test_windows_voice_desktop_support.py`.
- Untracked: `.agents/`, `skills-lock.json`, scripts de ejecución/installer, `SystemAlerts.tsx`, `Chat.tsx`, `Configure.tsx`, `build-output.txt`.

Este documento refleja el estado actual observado, pero antes de commit/release hay que estabilizar, revisar cada cambio y ejecutar verificación completa.

## 5. Riesgos e inconsistencias conocidas

1. **Packaging no verificado**
   - La visión es un programa instalable de Windows, pero el estado actual del installer/build no está validado en este snapshot.
   - Existe `scripts/HermesVoiceBridge.iss` untracked; hay que confirmar cuál es el spec/installer oficial.

2. **Rama desktop moderna vs rutas históricas**
   - Históricamente hubo rutas `windows_hermes_voice*`/`voice.env` y rutas `desktop_app.py`/`config.json` compitiendo.
   - En el estado actual indexado por CodeGraph no aparecen algunos archivos históricos de `src/windows_hermes_voice*.py` ni `src/hermes_voice_bridge/*`; no deben documentarse como actuales sin verificar.

3. **Overlay mode incompleto**
   - UI/backend exponen modo overlay, pero `OverlayService.set_mode()` está vacío.

4. **Tipos frontend débiles**
   - `Chat.tsx`, `Configure.tsx`, `Settings.tsx` usan `any` en varios puntos.
   - `api.ts` y Python bridge tienen posible mismatch: frontend tipa `add_custom_command()` como boolean, pero Python devuelve dict.

5. **Métricas/acciones parcialmente mock**
   - `Home.tsx` calcula algunas estadísticas con valores derivados simples (`week = msgs.length * 3`) y accesos rápidos que pueden ser placeholders.

6. **Fallback 404 confuso**
   - `App.tsx` fallback todavía comunica “This page is under construction” pese a que ahora actúa como 404.

7. **Cambios grandes sin commit**
   - Hay muchas modificaciones, eliminaciones y archivos nuevos sin commit. Riesgo alto de mezclar feature work, limpieza y packaging en un solo cambio.

## 6. Próximos pasos recomendados

### Paso 1 - Estabilizar snapshot actual

- Revisar diff por grupos: backend runtime, UI, scripts, tests eliminados.
- Confirmar qué archivos untracked deben entrar al repo.
- Restaurar o reemplazar tests eliminados si cubrían comportamiento importante.
- Ejecutar verificación completa: Python compile/tests relevantes, LSP/diagnostics en archivos tocados, `npm` build en `src/ui/app` y smoke manual pywebview/tray en Windows.

### Paso 2 - Resolver inconsistencias de contrato

- Alinear tipos de `api.ts` con retornos reales de `webview_bridge.py`.
- Quitar `any` críticos en páginas nuevas.
- Cambiar fallback 404.
- Implementar o retirar modo overlay mini/full.
- Revisar falsas métricas/acciones mock del dashboard.

### Paso 3 - Packaging Windows

- Elegir entrypoint oficial del producto instalable.
- Alinear script de ejecución, build, Inno Setup/spec y autostart a ese entrypoint.
- Definir directorios de AppData/logs/config/db.
- Probar instalación, ejecución, autostart, cierre/restart y desinstalación.

### Paso 4 - Limpieza arquitectónica segura

- Clasificar archivos como activo, legacy, migrar o borrar.
- No borrar legacy hasta comprobar imports, scripts, tests y packaging.
- Evitar gran reestructura de golpe: primero estabilizar runtime oficial y packaging, luego mover carpetas.

### Paso 5 - Commit por fases

Sugerencia de commits separados:

1. Runtime state/tray/overlay/backend sync.
2. UI React reorganizada (`Home`, `Chat`, `Configure`, `Settings`, `Commands`).
3. Scripts/packaging Windows.
4. Limpieza de páginas/tests obsoletos.
5. Documentación y status del proyecto.

## 7. Criterio de “listo para seguir”

Antes de añadir nuevas funcionalidades, el proyecto debería cumplir:

- Build frontend pasa.
- Tests backend relevantes pasan.
- Tray abre dashboard y refleja estado real.
- Micrófono seleccionado coincide en UI, tray y runtime.
- Hotkeys funcionan tras guardar configuración.
- Overlay se activa/desactiva y persiste posición.
- Sesiones/mensajes se crean y refrescan en `Chat`.
- Installer/launcher oficial arranca la misma app que se prueba en desarrollo.
