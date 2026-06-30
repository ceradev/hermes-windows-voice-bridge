import hashlib
import hmac
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from src.core.config.config_service import ConfigService


class HermesClientError(Exception):
    def __init__(self, message: str, status: int = 500):
        self.message = message
        self.status = status
        super().__init__(f"[{status}] {message}")


class HermesClient:
    def __init__(self, config: ConfigService):
        self.config = config

    def is_webhook_mode(self) -> bool:
        if not (self._get_webhook_url() and self._get_webhook_secret()):
            return False
        api_token = str(self.config.get("api_token", "") or "").strip()
        if api_token:
            return False
        return True

    def _get_api_token(self) -> str:
        return str(self.config.get("api_token", "") or "").strip()

    def _can_use_api(self) -> bool:
        return bool(self._get_base_url() and self._get_api_token())

    def _get_webhook_url(self) -> str:
        return str(self.config.get("webhook_url", "") or "").strip()

    def _get_webhook_secret(self) -> str:
        return str(self.config.get("webhook_secret", "") or "").strip()

    def _get_base_url(self) -> str:
        url = self.config.get("api_base_url", "http://127.0.0.1:8642")
        return str(url).rstrip("/")

    def _get_user_id(self) -> str:
        user_id = str(self.config.get("webhook_user_id", "") or "").strip()
        if user_id:
            return user_id
        env_user = str(os.environ.get("HERMES_USER_ID", "") or "").strip()
        if env_user:
            return env_user
        return "windows_voice_bridge"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        token = self._get_api_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["x-hermes-client-key"] = token
        return headers

    def _request(
        self,
        path: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Any]:
        url = f"{self._get_base_url()}{path}"
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        headers = self._get_headers()
        if extra_headers:
            headers.update(extra_headers)

        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )

        ssl_context = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
                status = resp.status
                response_text = resp.read().decode("utf-8", errors="replace")
                try:
                    return status, json.loads(response_text)
                except json.JSONDecodeError:
                    return status, {"error": "Invalid JSON response", "raw": response_text}

        except urllib.error.HTTPError as exc:
            response_text = exc.read().decode("utf-8", errors="replace")
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

    def _webhook_request(self, payload: Dict[str, Any], timeout: int) -> Tuple[int, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        secret = self._get_webhook_secret().encode("utf-8")
        signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
        user_id = self._get_user_id()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Webhook-Signature": signature,
            "X-Request-ID": user_id,
        }

        req = urllib.request.Request(
            self._get_webhook_url(),
            data=body,
            headers=headers,
            method="POST",
        )

        ssl_context = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
                status = resp.status
                response_text = resp.read().decode("utf-8", errors="replace")
                if not response_text.strip():
                    return status, {}
                try:
                    return status, json.loads(response_text)
                except json.JSONDecodeError:
                    return status, {"response": response_text}
        except urllib.error.HTTPError as exc:
            response_text = exc.read().decode("utf-8", errors="replace")
            try:
                err_data = json.loads(response_text)
            except json.JSONDecodeError:
                err_data = {"error": response_text or exc.reason}
            return exc.code, err_data
        except urllib.error.URLError as exc:
            return 503, {"error": f"Connection failed: {str(exc.reason)}"}
        except TimeoutError:
            return 504, {"error": "Request timed out"}
        except Exception as exc:
            return 500, {"error": str(exc)}

    def _get_metadata(self) -> Dict[str, Any]:
        return {
            "client": "hermes-voice-bridge",
            "platform": self.config.get("app_platform", "windows"),
            "appVersion": self.config.get("app_version", "1.0.0"),
            "language": self.config.get("app_language", "es"),
        }

    def _extract_response_text(self, data: Any) -> str:
        if isinstance(data, str) and data.strip():
            return data.strip()
        if not isinstance(data, dict):
            return str(data or "")

        for key in (
            "response",
            "final_response",
            "message",
            "text",
            "content",
            "reply",
            "output",
            "answer",
            "assistant_response",
        ):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0] if isinstance(choices[0], dict) else {}
            message = first.get("message") if isinstance(first, dict) else {}
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()

        for nested_key in ("data", "result", "payload", "body"):
            nested = data.get(nested_key)
            if nested is not None:
                nested_text = self._extract_response_text(nested)
                if nested_text:
                    return nested_text
        return ""

    def _poll_latest_assistant_response(self, session_id: str, *, attempts: int = 12, delay: float = 0.9) -> str:
        def _coerce_messages(payload: Any) -> list[dict[str, Any]]:
            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]
            if isinstance(payload, dict):
                for key in ("messages", "data", "items", "results"):
                    value = payload.get(key)
                    if isinstance(value, list):
                        return [item for item in value if isinstance(item, dict)]
                    if isinstance(value, dict):
                        nested = value.get("messages")
                        if isinstance(nested, list):
                            return [item for item in nested if isinstance(item, dict)]
            return []

        for _ in range(attempts):
            try:
                raw_messages = self.get_session_messages(session_id)
            except Exception:
                raw_messages = []
            messages = _coerce_messages(raw_messages)
            for message in reversed(messages):
                role = str(message.get("role", "")).lower()
                if role and role not in {"assistant", "hermes", "system_assistant", "ai", "model"}:
                    continue
                for key in ("content", "text", "response", "message", "reply", "answer", "output"):
                    value = message.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                nested = message.get("data")
                if isinstance(nested, dict):
                    for key in ("content", "text", "response", "message", "reply", "answer", "output"):
                        value = nested.get(key)
                        if isinstance(value, str) and value.strip():
                            return value.strip()
            time.sleep(delay)
        return ""

    def _interpret_webhook_response(
        self,
        status: int,
        data: Any,
        *,
        latency_ms: int,
        user_id: str,
        session_id: str,
        webhook_sync: bool,
    ) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise HermesClientError("Invalid webhook response", status)

        if data.get("error"):
            raise HermesClientError(str(data["error"]), status)

        webhook_status = str(data.get("status", "")).lower()
        if webhook_status == "ignored":
            event = data.get("event", "unknown")
            raise HermesClientError(
                "Webhook ignored this event "
                f"('{event}'). On the VPS, ensure route 'voice' accepts event_type 'voice' "
                "(hermes webhook list — add --events voice or clear the events filter).",
                422,
            )

        response_text = self._extract_response_text(data)

        # Hermes gateway may acknowledge quickly while the real assistant reply
        # appears a moment later in the session history. Prefer the local answer
        # if we can recover it from the remote session.
        if webhook_status in {"accepted", "duplicate"} and not response_text:
            candidate_session_ids = []
            for candidate in (data.get("sessionId"), data.get("session_id"), session_id, user_id):
                candidate = str(candidate or "").strip()
                if candidate and candidate not in candidate_session_ids:
                    candidate_session_ids.append(candidate)

            for candidate in candidate_session_ids:
                recovered = self._poll_latest_assistant_response(candidate)
                if recovered:
                    response_text = recovered
                    break
            else:
                return {
                    "success": False,
                    "response": "",
                    "speak": False,
                    "async_delivery": True,
                    "latencyMs": latency_ms,
                    "sessionId": user_id,
                    "delivery_id": data.get("delivery_id"),
                    "error": (
                        "El webhook aceptó el mensaje pero no devolvió texto. "
                        "Añade api_token en Settings (API :8642) para recibir la respuesta en la app."
                    ),
                }

        if not response_text:
            print(
                "[WEBHOOK] Empty response body — "
                f"status={webhook_status or status} payload={json.dumps(data, ensure_ascii=False)[:400]}"
            )

        return {
            "success": True,
            "response": response_text,
            "speak": bool(response_text),
            "latencyMs": latency_ms,
            "sessionId": user_id,
        }

    # --- Endpoints ---

    def health(self) -> bool:
        if self._can_use_api():
            for path in ("/health", "/api/health"):
                status, _ = self._request(path, timeout=3)
                if 200 <= status < 300:
                    return True
        if self._get_webhook_url():
            return self._webhook_health()
        if self._get_base_url():
            status, _ = self._request("/health", timeout=3)
            return 200 <= status < 300
        return False

    def _webhook_health(self) -> bool:
        url = self._get_webhook_url()
        req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        ssl_context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, timeout=3, context=ssl_context) as resp:
                return resp.status < 500
        except urllib.error.HTTPError as exc:
            return exc.code < 500
        except Exception:
            return False

    def create_session(self, name: str) -> Dict[str, Any]:
        if self.is_webhook_mode():
            return {"session": {"id": self._get_user_id(), "name": name}}
        import uuid

        unique_name = f"{name}_{uuid.uuid4().hex[:6]}"
        payload = {"name": unique_name}
        status, data = self._request("/api/sessions", method="POST", payload=payload)
        if 200 <= status < 300:
            return data
        raise HermesClientError(data.get("error", "Failed to create session"), status)

    def get_sessions(self) -> List[Dict[str, Any]]:
        if self.is_webhook_mode():
            return []
        status, data = self._request("/api/sessions", method="GET")
        if 200 <= status < 300:
            return data if isinstance(data, list) else data.get("data", [])
        return []

    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        status, data = self._request(f"/api/sessions/{session_id}/messages", method="GET", timeout=15)
        if 200 <= status < 300:
            return data if isinstance(data, list) else data.get("data", [])
        return []

    def rename_session(self, session_id: str, new_name: str) -> bool:
        if self.is_webhook_mode():
            return True
        status, _ = self._request(
            f"/api/sessions/{session_id}",
            method="PATCH",
            payload={"name": new_name},
        )
        return 200 <= status < 300

    def delete_session(self, session_id: str) -> bool:
        if self.is_webhook_mode():
            return True
        status, _ = self._request(f"/api/sessions/{session_id}", method="DELETE")
        return 200 <= status < 300

    def send_message(
        self,
        session_id: str,
        text: str,
        source: str = "voice",
        image_base64: str | None = None,
    ) -> Dict[str, Any]:
        if text is None:
            text = ""

        try:
            from src.services.agent.rag_service import LocalRAGService

            text_with_rag = LocalRAGService.inject_local_files(text)
        except Exception:
            text_with_rag = text

        trigger_words = [
            "abre",
            "abrir",
            "busca",
            "buscar",
            "volumen",
            "sube",
            "baja",
            "mutea",
            "aplicación",
            "programa",
            "avísame",
            "alarma",
            "temporizador",
            "recuérdame",
        ]
        needs_tools = any(word in text.lower() for word in trigger_words)

        final_message = text_with_rag
        if needs_tools:
            system_instruction = (
                '\n[SYSTEM: You are on Windows. To execute the user\'s command, output strictly: `<execute tool="open_app|web_search|system_volume|set_timer">ARG</execute>`. '
                "For set_timer, ARG must be `seconds|prompt` (e.g. `300|Saca la pizza`)]"
            )
            final_message += system_instruction

        api_token = str(self.config.get("api_token", "") or "").strip()
        if api_token:
            return self._send_api_chat_message(session_id, final_message, source, image_base64=image_base64)

        if self._get_webhook_url() and self._get_webhook_secret():
            return self._send_webhook_message(session_id, final_message, source, image_base64=image_base64)

        if self._can_use_api():
            return self._send_api_chat_message(session_id, final_message, source, image_base64=image_base64)

        raise HermesClientError(
            "Configure API base URL + token in Settings (recommended), or webhook URL + secret.",
            401,
        )

    def _send_api_chat_message(
        self,
        session_id: str,
        text: str,
        source: str,
        image_base64: str | None = None,
    ) -> Dict[str, Any]:
        if not self._can_use_api():
            raise HermesClientError(
                "Falta api_token en Settings. El webhook no devuelve la respuesta en el cuerpo HTTP; "
                "necesitas el token de la API Hermes (puerto 8642) para ver y escuchar respuestas aquí.",
                401,
            )

        hermes_result = self._send_hermes_native_message(session_id, text, source, image_base64=image_base64)
        if str(hermes_result.get("response", "")).strip():
            return hermes_result

        openai_result = self._send_openai_chat_message(session_id, text, source, image_base64=image_base64)
        if str(openai_result.get("response", "")).strip():
            return openai_result

        raise HermesClientError(
            "La API respondió sin texto. Revisa api_base_url, api_token y que el agente esté activo en el VPS.",
            502,
        )

    def _send_hermes_native_message(
        self,
        session_id: str,
        text: str,
        source: str,
        image_base64: str | None = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "sessionId": session_id,
            "message": text,
            "source": source,
            "metadata": self._get_metadata(),
        }
        if image_base64:
            payload["image_base64"] = image_base64
            payload["imageBase64"] = image_base64
            payload["image"] = image_base64

        start_time = time.time()
        status, data = self._request("/api/hermes/message", method="POST", payload=payload, timeout=120)
        latency_ms = int((time.time() - start_time) * 1000)

        if not (200 <= status < 300):
            return {"success": False, "response": "", "latencyMs": latency_ms}

        if isinstance(data, dict):
            extracted = self._extract_response_text(data)
            if extracted:
                data = {
                    "success": data.get("success", True),
                    "response": extracted,
                    "speak": data.get("speak", True),
                    "latencyMs": latency_ms,
                    "sessionId": session_id,
                }
            elif "latencyMs" not in data:
                data["latencyMs"] = latency_ms
            return self._post_process_agent_response(data)

        return {"success": False, "response": "", "latencyMs": latency_ms}

    def _send_openai_chat_message(
        self,
        session_id: str,
        text: str,
        source: str,
        image_base64: str | None = None,
    ) -> Dict[str, Any]:
        payload = {
            "model": self.config.get("api_model", "hermes-agent"),
            "messages": [{"role": "user", "content": text}],
            "stream": False,
        }

        if image_base64:
            payload["messages"][0]["content"] = [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
            ]

        start_time = time.time()
        status, data = self._request(
            "/v1/chat/completions",
            method="POST",
            payload=payload,
            timeout=120,
            extra_headers={"X-Hermes-Session-Id": session_id},
        )
        latency_ms = int((time.time() - start_time) * 1000)

        if not (200 <= status < 300):
            error_message = data.get("error", "Failed to send message") if isinstance(data, dict) else "Failed to send message"
            if isinstance(error_message, dict):
                error_message = error_message.get("message", str(error_message))
            if status == 401 and "invalid" in str(error_message).lower():
                raise HermesClientError(
                    "API key inválida. En el VPS usa API_SERVER_KEY (puerto 8642), "
                    "no webhook_secret (puerto 8644). Son credenciales distintas.",
                    status,
                )
            raise HermesClientError(str(error_message), status)

        if isinstance(data, dict):
            extracted = self._extract_response_text(data)
            if extracted:
                data = {"response": extracted, "latencyMs": latency_ms, "sessionId": session_id}
            elif "latencyMs" not in data:
                data["latencyMs"] = latency_ms
        return self._post_process_agent_response(data if isinstance(data, dict) else {"response": str(data)})

    def _send_webhook_message(
        self,
        session_id: str,
        text: str,
        source: str,
        image_base64: str | None = None,
    ) -> Dict[str, Any]:
        user_id = self._get_user_id()
        payload: Dict[str, Any] = {
            "text": text,
            "source": "windows_voice_bridge",
            "event_type": "voice",
            "user_id": user_id,
            "session_id": session_id,
            "sessionId": session_id,
        }
        if source:
            payload["client_source"] = source
        if image_base64:
            payload["image_base64"] = image_base64

        webhook_sync = bool(self.config.get("webhook_sync", True))
        timeout = int(self.config.get("webhook_timeout", 120) or 120)
        if not webhook_sync:
            timeout = min(timeout, 15)

        start_time = time.time()
        status, data = self._webhook_request(payload, timeout=timeout)
        latency_ms = int((time.time() - start_time) * 1000)

        if not (200 <= status < 300):
            error_message = data.get("error", "Webhook request failed") if isinstance(data, dict) else "Webhook request failed"
            raise HermesClientError(str(error_message), status)

        if not webhook_sync:
            return {
                "success": True,
                "response": "",
                "speak": False,
                "latencyMs": latency_ms,
                "sessionId": user_id,
            }

        result = self._interpret_webhook_response(
            status,
            data,
            latency_ms=latency_ms,
            user_id=user_id,
            session_id=session_id,
            webhook_sync=webhook_sync,
        )
        processed = self._post_process_agent_response(result)
        if str(processed.get("response", "")).strip():
            return processed

        if processed.get("error"):
            raise HermesClientError(str(processed["error"]), 422)

        if self._can_use_api():
            try:
                print("[WEBHOOK] Empty inline response — falling back to API chat for sync reply.")
                return self._send_api_chat_message(session_id, text, source, image_base64=image_base64)
            except HermesClientError as exc:
                print(f"[WEBHOOK] API fallback failed: {exc}")

        raise HermesClientError(
            "El webhook aceptó el mensaje pero no devolvió respuesta. "
            "Configura api_token en Settings (API :8642) — no es el mismo valor que webhook_secret.",
            422,
        )

    def _post_process_agent_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
        if str(data.get("response", "")).strip() and "speak" not in data:
            data["speak"] = True
        return data
