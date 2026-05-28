import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

class ConfigService:
    """Service to manage application configuration in %APPDATA%."""

    DEFAULT_CONFIG = {
        "api_base_url": "http://91.98.36.55:8642",
        "api_token": "",
        "app_language": "es",
        "app_platform": "windows",
        "app_version": "1.0.0",
        "wake_phrases": ["hermes", "oye hermes", "hey hermes"],
        "hotkey": "ctrl+shift+h",
        "mic_device": None,
        "tts_enabled": True,
        "feedback_mode": "both",
        "feedback_voice": "",
        "autostart": True,
        "theme": "dark",
        "minimize_to_tray": True,
        "notifications": True,
        "stt_language": "es",
        "stt_model": "base",
        "wake_energy": 0.008,
        "silence_rms": 0.025,
        "block_seconds": 0.25,
        "wake_window_seconds": 2.0,
        "initial_timeout_seconds": 2.5,
        "silence_timeout_seconds": 2.5,
        "max_command_seconds": 15.0,
        "custom_commands": [],
    }

    def __init__(self, app_name: str = "HermesVoiceBridge"):
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = str(Path.home() / "AppData" / "Roaming")
        
        self.config_dir = Path(appdata) / app_name
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        
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
        if self._config.get("api_base_url") == "http://127.0.0.1:8642":
            self._config["api_base_url"] = "http://91.98.36.55:8642"
            self.save()
            
        # Load API token from environment if not already configured
        env_token = os.environ.get("HERMES_API_TOKEN", "").strip()
        if env_token and not self._config.get("api_token"):
            self._config["api_token"] = env_token
            self.save()

        # Clean up old webhook_url if present
        if "webhook_url" in self._config:
            del self._config["webhook_url"]
            self.save()
            
        # Enforce adjusted silence timeout to 2.5
        if self._config.get("silence_timeout_seconds") in (0.85, 1.8, 1.3):
            self._config["silence_timeout_seconds"] = 2.5
            self.save()
            
        # Enforce lower initial timeout to 2.5
        if self._config.get("initial_timeout_seconds") == 5.0:
            self._config["initial_timeout_seconds"] = 2.5
            self.save()

        # Enforce higher silence_rms to ignore background noise
        if self._config.get("silence_rms") == 0.008:
            self._config["silence_rms"] = 0.025
            self.save()

        return self._config

    def save(self) -> None:
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def update(self, updates: Dict[str, Any]) -> None:
        for key, value in updates.items():
            if key in self.DEFAULT_CONFIG:
                self._config[key] = value
        self.save()

    def get_all(self) -> Dict[str, Any]:
        return self._config.copy()
