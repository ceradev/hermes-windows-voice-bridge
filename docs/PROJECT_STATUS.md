# Estado del proyecto

Actualizado: 2026-06-29  
Rama: `development`  
Fase actual: **Fase 4 — Packaging reproducible** (Fases 1–3 completadas; ver [PLAN.md](./PLAN.md))

## Resumen

Hermes Windows Voice Bridge es el cliente nativo de Windows para usar Hermes Agent por voz. El runtime oficial es una app de escritorio con **pywebview + React**, bandeja del sistema, overlay flotante, bucle de voz en background y persistencia local en SQLite.

**Entregable de distribución acordado:** instalador Windows (Inno Setup).

## Arquitectura actual

### Entrypoint

`src/platform/windows/desktop_app.py` — único launcher de producción y desarrollo.

### Componentes principales

| Módulo | Rol |
|--------|-----|
| `desktop_app.py` | Orquesta config, DB, servicios, tray, overlay, voice loop y ventana pywebview |
| `voice_loop.py` | Wake phrase, hotkey, grabación, STT, envío a Hermes, TTS, estados de overlay |
| `webview_bridge.py` | API Python expuesta a React (`window.pywebview.api`) |
| `AppStateStore` | Estado runtime thread-safe compartido (servicios, overlay, mic, listening) |
| `ConfigService` | `%APPDATA%\HermesVoiceBridge\config.json` |
| `SessionManager` + `Database` | Sesiones y mensajes en SQLite |
| `HermesClient` | Cliente HTTP hacia API Hermes en VPS (`/api/health`, `/api/hermes/message`, …) |
| `TrayManager` | Bandeja pystray con menú contextual |
| `OverlayService` | Pill flotante tkinter (idle, listening, thinking, speaking) |

### Frontend (`src/ui/app`)

React 18 + Vite + TypeScript + Tailwind.

| Ruta | Página |
|------|--------|
| `/` | Home — dashboard de estado |
| `/chat` | Chat — sesiones y mensajes |
| `/configure` | Configure — voz, micrófono, hotkeys, TTS |
| `/settings` | Settings — API Hermes, overlay, app |
| `/commands` | Commands — comandos personalizados |

## Integración con Hermes

- **Modelo actual:** API REST con `api_base_url` + `api_token` (Bearer / `x-hermes-client-key`)
- **Default VPS:** IP configurada en `ConfigService.DEFAULT_CONFIG` (servidor real del mantenedor)
- **Legacy descartado:** webhooks `voice.env`, entrypoints `windows_hermes_voice*.py`, panel tkinter

## Calidad y verificación

| Check | Estado |
|-------|--------|
| `python -m pytest tests/` | **44 passing** |
| Fase 1 smoke (ver `PHASE1_VERIFICATION.md`) | **PASS** |
| `npm run build` / `tsc --noEmit` | PASS (última verificación 2026-06-28) |
| `python build.py` | PASS → `dist/HermesVoiceBridge/HermesVoiceBridge.exe` |

## Deuda técnica conocida

1. **README histórico** — reescrito en Fase 1; antes describía tkinter/webhook/78 tests.
2. **Dos specs Inno Setup** — `setup.iss` (oficial, PyInstaller) vs `scripts/HermesVoiceBridge.iss` (legacy PowerShell). Usar solo `setup.iss`.
3. ~~**Código legacy tkinter**~~ — eliminado en Fase 2
4. ~~**Stats mock en Home**~~ — reemplazados por consultas SQLite reales (Fase 3)
5. **`HermesVoiceBridge.spec` en `.gitignore`** — dificulta builds en máquinas nuevas (Fase 4).
6. **Warnings LSP** — funciones largas en bridge, voice_loop, overlay, desktop_app (no bloquean runtime).

## Próximos pasos (orden acordado)

1. ~~Fase 1 — Documentación~~ ✅
2. ~~Fase 2 — Limpieza legacy~~ ✅
3. ~~Fase 3 — Stats reales en Home~~ ✅
4. Fase 4 — Instalador reproducible end-to-end
5. Fase 5 — Features (wake engine dedicado, perfiles, TTS por idioma)

## Documentación relacionada

- [PLAN.md](./PLAN.md) — plan por fases y decisiones
- [BUILD_NOTES.md](./BUILD_NOTES.md) — build exe + instalador
- [PHASE1_VERIFICATION.md](./PHASE1_VERIFICATION.md) — reporte de verificación Fase 1
