import logging
import re
import subprocess
import urllib.parse
import uuid
import webbrowser
from typing import Any, Dict, List, Optional

from src.core.config.config_service import ConfigService

logger = logging.getLogger(__name__)


class CustomCommandService:
    """Manages user-defined commands stored in ConfigService."""

    VALID_ACTION_TYPES = {"open_app", "web_search", "system_volume", "tts_speak", "hotkey"}

    def __init__(self, config: Optional[ConfigService] = None, tts_service: Any = None):
        self.config = config or ConfigService()
        self.tts_service = tts_service

    def get_all(self) -> List[Dict[str, Any]]:
        commands = self.config.get("custom_commands", [])
        if not isinstance(commands, list):
            return []
        return [self._normalize_command(command) for command in commands if isinstance(command, dict)]

    def get_by_id(self, command_id: str) -> Optional[Dict[str, Any]]:
        for command in self.get_all():
            if command.get("id") == command_id:
                return command
        return None

    def add(self, command: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize_command(command)
        if not normalized["id"]:
            normalized["id"] = uuid.uuid4().hex

        commands = self.get_all()
        commands.append(normalized)
        self._save(commands)
        return normalized

    def update(self, command_id: str, command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        commands = self.get_all()
        for index, existing in enumerate(commands):
            if existing.get("id") == command_id:
                updated = self._normalize_command({**existing, **command, "id": command_id})
                commands[index] = updated
                self._save(commands)
                return updated
        return None

    def delete(self, command_id: str) -> bool:
        commands = self.get_all()
        remaining = [command for command in commands if command.get("id") != command_id]
        if len(remaining) == len(commands):
            return False
        self._save(remaining)
        return True

    def match_command(self, text: str) -> Optional[Dict[str, Any]]:
        text_normalized = self._normalize_text(text)
        if not text_normalized:
            return None

        for command in self.get_all():
            for phrase in command.get("trigger_phrases", []):
                phrase_normalized = self._normalize_text(str(phrase))
                if phrase_normalized and phrase_normalized in text_normalized:
                    return command
        return None

    def execute(self, command_id: str) -> bool:
        command = self.get_by_id(command_id)
        if not command:
            return False

        for action in command.get("actions", []):
            self._execute_action(action)
        return True

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [self._command_to_tool_schema(command) for command in self.get_all()]

    def execute_tool(self, tool_name: str) -> Optional[str]:
        prefix = "custom_command_"
        if not tool_name.startswith(prefix):
            return None

        command_id = tool_name[len(prefix):]
        command = self.get_by_id(command_id)
        if not command:
            return f"Comando personalizado '{command_id}' no encontrado."

        self.execute(command_id)
        return f"Comando personalizado ejecutado: {command.get('name', command_id)}"

    def _save(self, commands: List[Dict[str, Any]]) -> None:
        self.config.update({"custom_commands": commands})

    def _normalize_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        trigger_phrases = command.get("trigger_phrases", [])
        if not isinstance(trigger_phrases, list):
            trigger_phrases = []

        actions = command.get("actions", [])
        if not isinstance(actions, list):
            actions = []

        return {
            "id": str(command.get("id", "")).strip(),
            "name": str(command.get("name", "")).strip(),
            "trigger_phrases": [str(phrase).strip() for phrase in trigger_phrases if str(phrase).strip()],
            "actions": [self._normalize_action(action) for action in actions if isinstance(action, dict)],
        }

    def _normalize_action(self, action: Dict[str, Any]) -> Dict[str, str]:
        action_type = str(action.get("type", "")).strip()
        target = str(action.get("target", "")).strip()
        if action_type not in self.VALID_ACTION_TYPES:
            action_type = "tts_speak"
        return {"type": action_type, "target": target}

    def _command_to_tool_schema(self, command: Dict[str, Any]) -> Dict[str, Any]:
        name = command.get("name") or command.get("id")
        triggers = ", ".join(command.get("trigger_phrases", []))
        description = f"Ejecuta el comando personalizado '{name}'."
        if triggers:
            description += f" Frases de activación: {triggers}."

        return {
            "name": f"custom_command_{command.get('id')}",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }

    def _execute_action(self, action: Dict[str, str]) -> None:
        action_type = action.get("type", "")
        target = action.get("target", "")

        if action_type == "open_app":
            subprocess.Popen(f"start {target}", shell=True)
        elif action_type == "web_search":
            url = f"https://www.google.com/search?q={urllib.parse.quote(target)}"
            webbrowser.open(url)
        elif action_type == "system_volume":
            self._execute_volume_action(target)
        elif action_type == "tts_speak":
            self._speak(target)
        elif action_type == "hotkey":
            self._send_hotkey(target)
        else:
            logger.warning("Unknown custom command action type: %s", action_type)

    def _execute_volume_action(self, action: str) -> None:
        keys = {"up": "175", "down": "174", "mute": "173"}
        key = keys.get(action.lower().strip())
        if not key:
            return
        cmd = f"powershell -WindowStyle Hidden -Command \"(new-object -com wscript.shell).SendKeys([char]{key})\""
        subprocess.Popen(cmd, shell=True)

    def _speak(self, text: str) -> None:
        if not text:
            return
        if self.tts_service:
            self.tts_service.say(text)
            return
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as exc:
            logger.error("Failed to speak custom command text: %s", exc)

    def _send_hotkey(self, hotkey: str) -> None:
        send_keys = self._to_send_keys(hotkey)
        if not send_keys:
            return
        escaped = send_keys.replace("'", "''")
        cmd = f"powershell -WindowStyle Hidden -Command \"(new-object -com wscript.shell).SendKeys('{escaped}')\""
        subprocess.Popen(cmd, shell=True)

    def _to_send_keys(self, hotkey: str) -> str:
        parts = [part.strip().lower() for part in hotkey.split("+") if part.strip()]
        if not parts:
            return ""

        modifiers = ""
        key = parts[-1]
        for modifier in parts[:-1]:
            if modifier in {"ctrl", "control"}:
                modifiers += "^"
            elif modifier == "shift":
                modifiers += "+"
            elif modifier in {"alt", "option"}:
                modifiers += "%"

        special_keys = {
            "enter": "{ENTER}",
            "esc": "{ESC}",
            "escape": "{ESC}",
            "tab": "{TAB}",
            "space": " ",
            "backspace": "{BACKSPACE}",
            "delete": "{DELETE}",
        }
        key_value = special_keys.get(key, key)
        return f"{modifiers}{key_value}"

    def _normalize_text(self, text: str) -> str:
        text_lower = text.lower().strip()
        replacements = str.maketrans("áéíóúüñ", "aeiouun")
        text_lower = text_lower.translate(replacements)
        return re.sub(r"[^\w\s]", "", text_lower)
