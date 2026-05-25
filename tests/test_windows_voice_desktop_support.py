from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_voice_bridge.ui.desktop import ApiClient, PALETTE


def test_release_scripts_exist():
    assert (ROOT / "scripts" / "package_voice_bridge.ps1").exists()
    assert (ROOT / "scripts" / "build_installer.ps1").exists()
    assert (ROOT / "scripts" / "HermesVoiceBridge.iss").exists()


def test_desktop_palette_exposes_expected_tokens():
    assert PALETTE["app_bg"] == "#0B1020"
    assert PALETTE["accent"] == "#2563EB"


def test_api_client_get_parses_json(monkeypatch):
    client = ApiClient("http://127.0.0.1:8765")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true, "path": "/api/status"}'

    def fake_urlopen(request, timeout=0):
        assert request.full_url == "http://127.0.0.1:8765/api/status"
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    payload = client.get("/api/status")

    assert payload["ok"] is True
    assert payload["path"] == "/api/status"
