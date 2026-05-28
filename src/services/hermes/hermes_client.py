import json
import ssl
import urllib.request
import urllib.error
import time
from typing import Dict, Any, Tuple, Optional, List
from src.core.config.config_service import ConfigService

class HermesClientError(Exception):
    def __init__(self, message: str, status: int = 500):
        self.message = message
        self.status = status
        super().__init__(f"[{status}] {message}")

class HermesClient:
    def __init__(self, config: ConfigService):
        self.config = config
        
    def _get_base_url(self) -> str:
        url = self.config.get("api_base_url", "http://127.0.0.1:8642")
        return url.rstrip('/')

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        token = self.config.get("api_token", "").strip()
        if token:
            # Send both depending on server configuration
            headers["Authorization"] = f"Bearer {token}"
            headers["x-hermes-client-key"] = token
        return headers
        
    def _request(self, path: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Tuple[int, Any]:
        url = f"{self._get_base_url()}{path}"
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=data,
            headers=self._get_headers(),
            method=method
        )

        # Explicit SSL context with certificate verification enabled
        ssl_context = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
                status = resp.status
                response_text = resp.read().decode('utf-8', errors='replace')
                try:
                    return status, json.loads(response_text)
                except json.JSONDecodeError:
                    return status, {"error": "Invalid JSON response", "raw": response_text}

        except urllib.error.HTTPError as exc:
            response_text = exc.read().decode('utf-8', errors='replace')
            try:
                err_data = json.loads(response_text)
            except json.JSONDecodeError:
                err_data = {"error": response_text}
            return exc.code, err_data
        except urllib.error.URLError as exc:
            return 503, {"error": f"Connection failed: {str(exc.reason)}"}
        except ssl.SSLError as exc:
            return 525, {"error": f"SSL verification failed: {str(exc)}"}
        except TimeoutError:
            return 504, {"error": "Request timed out"}
        except Exception as exc:
            return 500, {"error": str(exc)}

    def _get_metadata(self) -> Dict[str, Any]:
        return {
            "client": "hermes-voice-bridge",
            "platform": self.config.get("app_platform", "windows"),
            "appVersion": self.config.get("app_version", "1.0.0"),
            "language": self.config.get("app_language", "es")
        }

    # --- Endpoints ---

    def health(self) -> bool:
        """Check API health with short timeout."""
        status, _ = self._request("/api/health", timeout=3)
        return 200 <= status < 300

    def create_session(self, name: str) -> Dict[str, Any]:
        """Create a new session on the VPS."""
        import uuid
        unique_name = f"{name}_{uuid.uuid4().hex[:6]}"
        payload = {
            "name": unique_name
        }
        status, data = self._request("/api/sessions", method="POST", payload=payload)
        if 200 <= status < 300:
            return data
        raise HermesClientError(data.get("error", "Failed to create session"), status)

    def get_sessions(self) -> List[Dict[str, Any]]:
        status, data = self._request("/api/sessions", method="GET")
        if 200 <= status < 300:
            return data if isinstance(data, list) else data.get("data", [])
        return []

    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        status, data = self._request(f"/api/sessions/{session_id}/messages", method="GET")
        if 200 <= status < 300:
            return data if isinstance(data, list) else data.get("data", [])
        return []

    def rename_session(self, session_id: str, new_name: str) -> bool:
        status, _ = self._request(f"/api/sessions/{session_id}", method="PATCH", payload={"name": new_name})
        return 200 <= status < 300

    def delete_session(self, session_id: str) -> bool:
        status, _ = self._request(f"/api/sessions/{session_id}", method="DELETE")
        return 200 <= status < 300

    def send_message(self, session_id: str, text: str, source: str = "voice", image_base64: str | None = None) -> Dict[str, Any]:
        """
        Sends a message to the hermes agent.
        Expected return format from server:
        { "success": true, "sessionId": "...", "messageId": "...", "response": "...", "speak": true, "latencyMs": 820 }
        """
        if text is None:
            text = ""
            
        # RAG Local: Escanear texto en busca de rutas e inyectar archivos
        try:
            from src.services.agent.rag_service import LocalRAGService
            text_with_rag = LocalRAGService.inject_local_files(text)
        except Exception:
            text_with_rag = text

        # Agentic System: Only inject tool instructions if user mentions trigger words
        trigger_words = ["abre", "abrir", "busca", "buscar", "volumen", "sube", "baja", "mutea", "aplicación", "programa", "avísame", "alarma", "temporizador", "recuérdame"]
        needs_tools = any(word in text.lower() for word in trigger_words)
        
        final_message = text_with_rag
        if needs_tools:
            system_instruction = (
                "\n[SYSTEM: You are on Windows. To execute the user's command, output strictly: `<execute tool=\"open_app|web_search|system_volume|set_timer\">ARG</execute>`. "
                "For set_timer, ARG must be `seconds|prompt` (e.g. `300|Saca la pizza`)]"
            )
            final_message += system_instruction

        payload = {
            "sessionId": session_id,
            "message": final_message,
            "source": source,
            "metadata": self._get_metadata()
        }
        
        if image_base64:
            payload["image_base64"] = image_base64
            payload["imageBase64"] = image_base64
            payload["image"] = image_base64 # Just in case
        
        start_time = time.time()
        status, data = self._request("/api/hermes/message", method="POST", payload=payload, timeout=120)
        end_time = time.time()
        
        latency_ms = int((end_time - start_time) * 1000)
        
        if 200 <= status < 300:
            # Inject locally calculated latency if server didn't provide it
            if "latencyMs" not in data:
                data["latencyMs"] = latency_ms
                
            # Intercept and execute tools
            if "response" in data and isinstance(data["response"], str):
                from src.services.agent.command_executor import CommandExecutor
                executor = CommandExecutor()
                clean_text, results = executor.parse_and_execute(data["response"])
                confirmation = next((result for result in results if result.startswith("CONFIRM_REQUIRED|")), "")
                if confirmation:
                    data["response"] = confirmation
                    data["speak"] = True
                    data["confirmationRequired"] = True
                else:
                    data["response"] = clean_text
                    if results:
                        data["localActionResults"] = results
                 
                # We could log or send the results back in a future iteration, 
                # but for now, executing them silently is exactly what we need!
                
            return data
            
        raise HermesClientError(data.get("error", "Failed to send message"), status)
