import json
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

class ConfigService:
    """Service to manage application configuration in %APPDATA%."""

    DEFAULT_CONFIG = {
        "webhook_url": "",
        "webhook_secret": "",
        "webhook_sync": True,
        "webhook_timeout": 120,
        "webhook_user_id": "",
        "api_base_url": "http://91.98.36.55:8642",
        "api_token": "",
        "app_language": "es",
        "app_platform": "windows",
        "app_version": "1.0.0",
        "wake_phrases": ["hermes", "oye hermes", "hey hermes"],
        "hotkey": "ctrl+shift+h",
        "mic_device": None,
        "mic_device_name": "",
        "mic_device_hostapi": None,
        "tts_enabled": True,
        "feedback_mode": "both",
        "feedback_voice": "",
        "autostart": True,
        "theme": "dark",
        "minimize_to_tray": True,
        "notifications": True,
        "stt_language": "es",
        "stt_model": "small",
        "stt_beam_size": 5,
        "wake_energy": 0.007,
        "silence_rms": 0.015,
        "block_seconds": 0.25,
        "wake_window_seconds": 1.25,
        "wake_hangover_seconds": 0.35,
        "wake_min_speech_seconds": 0.45,
        "wake_speech_ratio_min": 0.55,
        "wake_cooldown_seconds": 1.2,
        "initial_timeout_seconds": 2.5,
        "silence_timeout_seconds": 2.5,
        "max_command_seconds": 15.0,
        "custom_commands": [],
        "overlay_enabled": True,
        "overlay_mode": "mini",
        "overlay_x": None,
        "overlay_y": None,
        "notifications_enabled": True,
    }

    def __init__(self, app_name: str = "HermesVoiceBridge"):
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = str(Path.home() / "AppData" / "Roaming")

        self.config_dir = Path(appdata) / app_name
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self._lock = threading.RLock()

        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        if not self.config_file.exists():
            self._config = self.DEFAULT_CONFIG.copy()
            self.save()
        else:
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self._config = {**self.DEFAULT_CONFIG, **loaded}
            except Exception:
                self._config = self.DEFAULT_CONFIG.copy()

        # Force migration of old local URL to the VPS URL if they haven't changed it
        if self._config.get("api_base_url") in {"http://127.0.0.1:8642", "http://100.109.108.31:8642"}:
            self._config["api_base_url"] = "http://91.98.36.55:8642"
            self.save()

        # Environment variables only fill missing webhook settings (config file wins).
        env_webhook_url = os.environ.get("HERMES_WEBHOOK_URL", "").strip()
        if env_webhook_url and not str(self._config.get("webhook_url", "") or "").strip():
            self._config["webhook_url"] = env_webhook_url

        env_webhook_secret = os.environ.get("HERMES_WEBHOOK_SECRET", "").strip()
        if env_webhook_secret and not str(self._config.get("webhook_secret", "") or "").strip():
            self._config["webhook_secret"] = env_webhook_secret

        env_webhook_sync = os.environ.get("HERMES_WEBHOOK_SYNC", "").strip()
        if env_webhook_sync:
            self._config["webhook_sync"] = env_webhook_sync not in {"0", "false", "False", "no", "off"}

        env_webhook_timeout = os.environ.get("HERMES_WEBHOOK_TIMEOUT", "").strip()
        if env_webhook_timeout.isdigit():
            self._config["webhook_timeout"] = int(env_webhook_timeout)

        env_user_id = os.environ.get("HERMES_USER_ID", "").strip()
        if env_user_id:
            self._config["webhook_user_id"] = env_user_id

        # Load API token from environment if not already configured
        env_token = os.environ.get("HERMES_API_TOKEN", "").strip()
        if env_token and not self._config.get("api_token"):
            self._config["api_token"] = env_token

        # Back-compat: secret stored in api_token while webhook_url is set
        if self._config.get("webhook_url") and not self._config.get("webhook_secret"):
            legacy_secret = str(self._config.get("api_token", "") or "").strip()
            if legacy_secret:
                self._config["webhook_secret"] = legacy_secret

        # Enforce adjusted silence timeout to 2.5
        if self._config.get("silence_timeout_seconds") in (0.85, 1.8, 1.3):
            self._config["silence_timeout_seconds"] = 2.5
            self.save()

        # Enforce lower initial timeout to 2.5
        if self._config.get("initial_timeout_seconds") == 5.0:
            self._config["initial_timeout_seconds"] = 2.5
            self.save()

        # Softer defaults for better mic pickup (one-time tune for old installs).
        if self._config.get("wake_window_seconds") == 2.0:
            self._config["wake_window_seconds"] = 1.25
            self.save()

        if self._config.get("stt_model") == "base":
            self._config["stt_model"] = "small"
            self.save()

        if self._config.get("silence_rms") == 0.025:
            self._config["silence_rms"] = 0.015
            self.save()

        if self._config.get("wake_energy") in (0.005, 0.008):
            self._config["wake_energy"] = 0.007
            self.save()

        if self._config.get("wake_cooldown_seconds") == 0.8:
            self._config["wake_cooldown_seconds"] = 1.2
            self.save()

        if self._config.get("wake_min_speech_seconds") == 0.35:
            self._config["wake_min_speech_seconds"] = 0.45
            self.save()

        if self._config.get("wake_hangover_seconds") == 0.45:
            self._config["wake_hangover_seconds"] = 0.35
            self.save()

        return self._config

    def save(self) -> None:
        with self._lock:
            snapshot = self._config.copy()
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, ensure_ascii=False)
        try:
            import stat
            os.chmod(self.config_file, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._config.get(key, default)

    def update(self, updates: Dict[str, Any]) -> None:
        with self._lock:
            for key, value in updates.items():
                if key in self.DEFAULT_CONFIG:
                    self._config[key] = value
        self.save()

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return self._config.copy()

