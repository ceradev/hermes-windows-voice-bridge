# Plan de trabajo — Hermes Windows Voice Bridge

Actualizado: 2026-06-29  
Rama: `development`

## Decisiones acordadas

| Tema | Decisión |
|------|----------|
| Entregable principal | **Instalador Windows** (Inno Setup → `HermesVoiceBridge-setup.exe`) |
| Orden de ejecución | Empezar por **documentación (Fase 1)**, luego limpieza, UI, packaging |
| `api_base_url` por defecto | Mantener la IP del VPS real en `ConfigService.DEFAULT_CONFIG` |
| Dashboard `Home` | Implementar **estadísticas reales** desde SQLite (no mocks) |
| Código legacy tkinter | **Eliminar** `src/ui/desktop/` y `src/ui/overlays/` si no hay imports activos |

## Fases

### Fase 1 — Documentación y alineación ✅ completada

- [x] Resolver conflictos de merge en `README.md`
- [x] README alineado con arquitectura actual (pywebview + React + API Hermes)
- [x] Actualizar `docs/PROJECT_STATUS.md` y `docs/BUILD_NOTES.md`
- [x] Crear `docs/PLAN.md` con decisiones acordadas
- [x] Alinear `scripts/build_installer.ps1` → `setup.iss` + `build.py`

**Criterio de salida:** un desarrollador puede clonar, desarrollar y generar el instalador siguiendo solo la documentación.

### Fase 2 — Limpieza arquitectónica ✅ completada

- [x] Eliminar `src/ui/desktop/`, `src/ui/overlays/`, `src/ui/settings/`
- [x] Eliminar session manager legacy JSON (`core/session/__init__.py` antiguo, `auth_backend`, `storage/repositories`, `storage/cache`)
- [x] Eliminar `core/events`, `core/lifecycle`, `core/logging` sin uso
- [x] Tests en verde

### Fase 3 — Contrato frontend ↔ backend ✅ completada

- [x] Stats reales en `Home.tsx` (`get_message_stats`, `get_recent_messages`)
- [x] Nuevos métodos en `webview_bridge.py` y `api.ts`
- [x] Corregir fallback 404 en `App.tsx`

### Fase 4 — Packaging reproducible

- Versionar o documentar `HermesVoiceBridge.spec`
- Unificar en un solo `.iss` oficial (`setup.iss`)
- Checklist de smoke post-instalación (tray, dashboard, hotkey, overlay, autostart, desinstalación)

### Fase 5 — Mejoras de producto (después de estabilizar)

- Wake engine dedicado (Porcupine / OpenWakeWord)
- Voces TTS por idioma
- Múltiples perfiles de usuario
- Ampliar acciones de sistema en `Commands`

## Entrypoint oficial

| Contexto | Comando / artefacto |
|----------|---------------------|
| Desarrollo | `.\scripts\run_desktop_app.ps1` |
| Python directo | `python -B src\platform\windows\desktop_app.py` (requiere `npm run build` previo) |
| Producción | `dist\HermesVoiceBridge\HermesVoiceBridge.exe` |
| Distribución | `dist\HermesVoiceBridge-setup.exe` (Inno Setup) |

## Configuración y datos

| Recurso | Ubicación |
|---------|-----------|
| Config | `%APPDATA%\HermesVoiceBridge\config.json` |
| Base de datos | `%APPDATA%\HermesVoiceBridge\database.sqlite` |
| Logs | `%APPDATA%\HermesVoiceBridge\app.log` |
