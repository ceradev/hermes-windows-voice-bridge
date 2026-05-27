# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\cesar\\Desktop\\Files\\Work\\Projects\\Personal\\hermes-windows-voice-bridge\\src\\platform\\windows\\desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\cesar\\Desktop\\Files\\Work\\Projects\\Personal\\hermes-windows-voice-bridge\\src\\ui\\app\\dist', 'src/ui/app/dist')],
    hiddenimports=['keyring.backends.Windows'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HermesVoiceBridge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\cesar\\Desktop\\Files\\Work\\Projects\\Personal\\hermes-windows-voice-bridge\\src\\ui\\app\\public\\favicon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HermesVoiceBridge',
)
