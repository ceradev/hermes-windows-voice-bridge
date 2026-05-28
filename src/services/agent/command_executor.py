import subprocess
import webbrowser
import logging
import urllib.parse
import shutil
from importlib import import_module
from typing import Any

logger = logging.getLogger(__name__)

SAFE_APP_TARGETS = {
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "spotify": "spotify.exe",
}

SHELL_METACHARACTERS = {"&", "|", ";", ">", "<", "^", "`", "\"", "'", "\n", "\r"}

class CommandExecutor:
    """
    Handles local OS command execution and exposes a schema of available tools
    that can be sent to the remote LLM VPS.
    """
    def __init__(self, custom_command_service: Any = None):
        custom_command_module = import_module("src.services.custom_commands.custom_command_service")
        self.custom_command_service = custom_command_service or custom_command_module.CustomCommandService()
        self.sensitive_apps: set[str] = {
            "cmd",
            "powershell",
            "pwsh",
            "regedit",
            "taskmgr",
            "control",
            "settings",
            "windows terminal",
            "terminal",
        }
        self.available_tools: list[dict[str, Any]] = [
            {
                "name": "open_app",
                "description": "Abre una aplicación local o programa en Windows.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {"type": "string", "description": "Nombre del ejecutable o programa (ej. 'spotify', 'notepad', 'calc', 'chrome')"}
                    },
                    "required": ["app_name"]
                }
            },
            {
                "name": "web_search",
                "description": "Abre el navegador por defecto y busca la información solicitada en Google.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Término de búsqueda."}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "system_volume",
                "description": "Sube, baja o mutea el volumen del sistema Windows.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["up", "down", "mute"]}
                    },
                    "required": ["action"]
                }
            }
        ]

    def get_tool_schemas(self):
        return self.available_tools + self.custom_command_service.get_tool_schemas()

    def execute_tool(self, tool_name: str, args: dict[str, Any], confirmed: bool = False) -> str:
        logger.info(f"Ejecutando herramienta: {tool_name} con argumentos: {args}")
        try:
            custom_result = self.custom_command_service.execute_tool(tool_name)
            if custom_result is not None:
                return custom_result

            if not confirmed:
                action_description = self._get_confirmation_description(tool_name, args)
                if action_description:
                    logger.info(f"Confirmación requerida para: {action_description}")
                    return f"CONFIRM_REQUIRED|{action_description}"

            if tool_name == "open_app":
                app_name = str(args.get("app_name", "")).lower().strip()
                executable = self._resolve_safe_app(app_name)
                if not executable:
                    return f"Aplicación no permitida o desconocida: {app_name}"

                _ = subprocess.Popen([executable], shell=False)
                return f"Aplicación {app_name} lanzada."
                
            elif tool_name == "web_search":
                query = str(args.get("query", "")).strip()
                url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                webbrowser.open(url)
                return f"Búsqueda abierta en el navegador para: {query}"
                
            elif tool_name == "system_volume":
                action = str(args.get("action", ""))
                # Media keys mapping for SendKeys
                keys = {"up": "175", "down": "174", "mute": "173"}
                if action in keys:
                    cmd = f"(new-object -com wscript.shell).SendKeys([char]{keys[action]})"
                    _ = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-Command", cmd], shell=False)
                    return f"Volumen del sistema modificado: {action}"
                return "Acción de volumen desconocida."
                
            elif tool_name == "set_timer":
                try:
                    timer_data = str(args.get("timer_data", ""))
                    parts = timer_data.split("|", 1)
                    if len(parts) == 2:
                        seconds = int(parts[0])
                        prompt = parts[1]
                        
                        import src.platform.windows.desktop_app as desktop_app
                        proactive = getattr(desktop_app, "proactive", None)
                        if proactive:
                            proactive.add_timer(seconds, prompt)
                            logger.info(f"Timer set for {seconds}s: {prompt}")
                            return f"Temporizador configurado en {seconds} segundos."
                except Exception as e:
                    logger.error(f"Error setting timer: {e}")
                    return f"Error configurando temporizador: {str(e)}"
                
            return f"Herramienta '{tool_name}' no soportada por el sistema cliente."
            
        except Exception as e:
            logger.error(f"Error al ejecutar {tool_name}: {e}")
            return f"Error ejecutando comando local: {str(e)}"

    def _get_confirmation_description(self, tool_name: str, args: dict[str, Any]) -> str:
        if tool_name == "system_volume":
            action = str(args.get("action", ""))
            return f"Cambiar el volumen del sistema ({action})"

        if tool_name == "open_app":
            app_name = str(args.get("app_name", "")).lower().strip()
            if app_name in self.sensitive_apps:
                return f"Abrir la aplicación sensible '{app_name}'"

        if self._is_destructive_operation(tool_name, args):
            return f"Ejecutar operación destructiva '{tool_name}'"

        return ""

    def _resolve_safe_app(self, app_name: str) -> str:
        if not app_name or any(character in app_name for character in SHELL_METACHARACTERS):
            return ""

        target = SAFE_APP_TARGETS.get(app_name)
        if not target:
            return ""

        return shutil.which(target) or target

    def _is_destructive_operation(self, tool_name: str, args: dict[str, Any]) -> bool:
        destructive_terms = {
            "delete",
            "remove",
            "rm",
            "del",
            "erase",
            "format",
            "shutdown",
            "restart",
            "reboot",
            "kill",
            "terminate",
            "wipe",
        }
        haystack = " ".join([tool_name, *(str(value) for value in args.values())]).lower()
        return any(term in haystack for term in destructive_terms)

    def parse_and_execute(self, response_text: str) -> tuple[str, list[str]]:
        """
        Busca etiquetas <execute tool="X">ARG</execute> en el texto de respuesta,
        las extrae, ejecuta la herramienta correspondiente y devuelve el texto limpio
        (para que el TTS no lea el código de la etiqueta) y una lista con los resultados.
        """
        import re
        pattern = r'<execute tool="([^"]+)">([^<]+)</execute>'
        matches = list(re.finditer(pattern, response_text))
        
        results = []
        clean_text = response_text
        
        for match in matches:
            tool_name = match.group(1)
            arg_str = match.group(2).strip()
            
            # Mapeo rápido de argumento único (ya que nuestras 3 tools solo requieren 1 param)
            args: dict[str, Any] = {}
            if tool_name == "open_app":
                args["app_name"] = arg_str
            elif tool_name == "web_search":
                args["query"] = arg_str
            elif tool_name == "system_volume":
                args["action"] = arg_str
            elif tool_name == "set_timer":
                args["timer_data"] = arg_str
            elif tool_name.startswith("custom_command_"):
                args["command_id"] = tool_name.replace("custom_command_", "", 1)
                
            res = self.execute_tool(tool_name, args)
            results.append(res)
            
            # Borrar la etiqueta del texto para que no se escuche
            clean_text = clean_text.replace(match.group(0), "")
            
        return clean_text.strip(), results
