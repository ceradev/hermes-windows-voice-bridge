# Build y distribución (Windows)

Guía para generar el ejecutable y el **instalador oficial** de Hermes Windows Voice Bridge.

## Requisitos

- Windows 10/11 (64-bit)
- Python 3.11+
- Node.js 18+ y npm en `PATH`
- [Inno Setup](https://jrsoftware.org/isdl.php) (`ISCC.exe` en `PATH`) para el instalador
- Micrófono y ~500 MB libres (modelos Whisper se descargan en el primer uso)

## Instalación de dependencias (desarrollo)

Desde la raíz del repositorio:

```powershell
python -m pip install -r requirements.txt
cd src\ui\app
npm install
cd ..\..\..
```

## Build del ejecutable (PyInstaller)

`build.py` compila la UI React y empaqueta la app con PyInstaller:

```powershell
python build.py
```

Pasos internos:

1. `npm run build` en `src/ui/app`
2. `python -m PyInstaller --noconfirm HermesVoiceBridge.spec`

Salida esperada:

```text
dist/HermesVoiceBridge/HermesVoiceBridge.exe
```

### Notas sobre `HermesVoiceBridge.spec`

- El archivo `.spec` puede estar en `.gitignore` (generado localmente).
- Si falta, créalo en la raíz del repo o copíalo desde una máquina que ya haya hecho build con éxito.
- El spec empaqueta `src/ui/app/dist` dentro del bundle one-dir.

### Modo desarrollo UI (sin rebuild)

```powershell
# Terminal 1
cd src\ui\app
npm run dev

# Terminal 2 (desde la raíz)
$env:HERMES_UI_DEV = "1"
python -B src\platform\windows\desktop_app.py
```

Atajo: `.\scripts\run_desktop_app.ps1` (build + launch en un solo paso).

## Instalador (entregable principal)

El instalador oficial usa **`setup.iss`** en la raíz del repo. Empaqueta el output de PyInstaller (`dist/HermesVoiceBridge/*`).

### Flujo completo

```powershell
# 1. Generar el .exe
python build.py

# 2. Generar el instalador
.\scripts\build_installer.ps1
```

O manualmente:

```powershell
ISCC.exe setup.iss
```

Salida esperada:

```text
Output/HermesVoiceBridge_Installer.exe
```

(o `dist/HermesVoiceBridge-setup.exe` según la configuración activa del `.iss`)

### Qué incluye el instalador (`setup.iss`)

- Copia recursiva de `dist\HermesVoiceBridge\*` a `{app}`
- Acceso directo en el menú Inicio
- Acceso directo en el escritorio (opcional)
- Autostart con Windows (opcional, tarea de instalación)
- Entrada de desinstalación en Panel de control

### Legacy: `scripts/HermesVoiceBridge.iss`

Ese spec antiguo instalaba scripts PowerShell + fuentes Python (sin PyInstaller). **No usar** para distribución actual. El flujo oficial es `build.py` → `setup.iss`.

## Verificación post-build

Checklist mínimo antes de publicar un instalador:

- [ ] `python -m pytest tests/` — 43 tests passing
- [ ] `cd src/ui/app && npx tsc --noEmit` — sin errores TypeScript
- [ ] `HermesVoiceBridge.exe` arranca y muestra icono en bandeja
- [ ] Dashboard abre desde tray u overlay
- [ ] Hotkey global activa escucha
- [ ] Overlay visible y posición persiste
- [ ] Config y sesiones persisten en `%APPDATA%\HermesVoiceBridge\`
- [ ] Desinstalación elimina archivos de `{app}`

## Scripts auxiliares

| Script | Uso |
|--------|-----|
| `scripts/run_desktop_app.ps1` | Dev: build UI + lanzar desktop |
| `scripts/build_installer.ps1` | Build exe (si falta) + Inno Setup |
| `scripts/install_autostart.ps1` | Autostart manual (dev / legacy) |
| `scripts/uninstall_voice_bridge.ps1` | Limpieza manual de tareas y estado |

## Troubleshooting de build

**`HermesVoiceBridge.spec` not found**  
Ejecuta PyInstaller una vez en la máquina de build o restaura el spec desde backup. `build.py` lo requiere.

**`ISCC.exe` not found**  
Instala Inno Setup y añade su carpeta `ISC` al `PATH`.

**UI en blanco al abrir el .exe**  
Falta el build de Vite. Ejecuta `npm run build` en `src/ui/app` antes de PyInstaller.

**Modelo Whisper no descarga en máquina nueva**  
Primera ejecución necesita red. Verifica que Hugging Face no esté bloqueado por firewall.
