# Windows Build Notes

Build from the repository root on Windows:

```powershell
python -m pip install -r requirements.txt
cd src\ui\app
npm install
npm run build
cd ..\..\..
python build.py
```

`build.py` rebuilds the React UI and then runs PyInstaller with `HermesVoiceBridge.spec`.
The spec file uses paths relative to its own location and packages `src/ui/app/dist`
into the one-dir output.

Expected output:

```text
dist/HermesVoiceBridge/HermesVoiceBridge.exe
```

Caveats:

- Node.js/npm must be available on `PATH` before running the build.
- PyInstaller is included in `requirements.txt` because `build.py` invokes
  `python -m PyInstaller`.
- The optional UI icon path is used only if `src/ui/app/public/favicon.ico` exists.
