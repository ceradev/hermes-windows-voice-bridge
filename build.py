from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], cwd: Path) -> None:
    """Run a build command without invoking a shell."""
    print(f"> {' '.join(command)}")
    _ = subprocess.run(command, cwd=cwd, shell=False, check=True)


def resolve_executable(name: str) -> str:
    """Resolve an executable on PATH and fail with a clear message if missing."""
    executable = shutil.which(name)
    if executable is None:
        raise FileNotFoundError(f"Required executable not found on PATH: {name}")
    return executable


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    ui_app_dir = base_dir / "src" / "ui" / "app"
    spec_file = base_dir / "HermesVoiceBridge.spec"

    if not spec_file.is_file():
        raise FileNotFoundError(f"Missing PyInstaller spec file: {spec_file}")

    npm = resolve_executable("npm")

    print("Building React app...")
    run_command([npm, "run", "build"], cwd=ui_app_dir)

    print("Running PyInstaller...")
    run_command(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec_file)],
        cwd=base_dir,
    )

    exe_path = base_dir / "dist" / "HermesVoiceBridge" / "HermesVoiceBridge.exe"
    if not exe_path.is_file():
        raise FileNotFoundError(f"Expected executable was not created: {exe_path}")

    print(f"Build complete: {exe_path}")


if __name__ == "__main__":
    main()
