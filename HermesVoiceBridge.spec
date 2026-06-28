import os


SPECPATH = os.path.abspath(os.path.dirname(SPEC))


def from_spec_root(*parts):
    return os.path.join(SPECPATH, *parts)


entry_script = from_spec_root("src", "platform", "windows", "desktop_app.py")
ui_dist_dir = from_spec_root("src", "ui", "app", "dist")
icon_file = from_spec_root("src", "ui", "app", "public", "favicon.ico")


a = Analysis(
    [entry_script],
    pathex=[SPECPATH],
    binaries=[],
    datas=[(ui_dist_dir, "src/ui/app/dist")],
    hiddenimports=["keyring.backends.Windows"],
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
    name="HermesVoiceBridge",
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
    icon=icon_file if os.path.exists(icon_file) else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="HermesVoiceBridge",
)
