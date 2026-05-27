import os
import subprocess
import shutil
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent
    src_dir = base_dir / "src"
    ui_app_dir = src_dir / "ui" / "app"
    dist_dir = ui_app_dir / "dist"
    
    # 1. Build React App
    print("Building React App...")
    subprocess.run(["npm", "run", "build"], cwd=ui_app_dir, shell=True, check=True)
    
    # 2. Run PyInstaller
    print("Running PyInstaller...")
    # Add dist folder to PyInstaller
    add_data = f"{dist_dir};src/ui/app/dist"
    
    import sys
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name", "HermesVoiceBridge",
        "--add-data", add_data,
        "--hidden-import", "keyring.backends.Windows",
        str(src_dir / "platform" / "windows" / "desktop_app.py")
    ]
    
    subprocess.run(pyinstaller_cmd, cwd=base_dir, shell=True, check=True)
    print("Build complete! Check the 'dist' folder for the executable.")

if __name__ == "__main__":
    main()
