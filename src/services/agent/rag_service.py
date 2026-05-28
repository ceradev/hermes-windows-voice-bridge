import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class LocalRAGService:
    """
    Escanea los mensajes del usuario antes de enviarlos al VPS.
    Si detecta rutas de archivos locales válidas, lee su contenido
    y lo inyecta de forma invisible en el prompt.
    """

    # Patrón básico para detectar rutas de Windows (ej. C:\Users\... o D:/Datos/...)
    PATH_PATTERN = r'([a-zA-Z]:[\\/](?:[a-zA-Z0-9_\-\.\s]+[\\/])*([a-zA-Z0-9_\-\.\s]+\.[a-zA-Z0-9]+))'

    # Extensiones que podemos leer en texto plano sin usar librerías externas complejas
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.json', '.py', '.js', '.ts', '.html', '.css', '.csv'}

    # Archivos sensibles que nunca deben ser leídos
    SENSITIVE_FILENAMES = {
        "voice.env", "config.json", ".env", ".panel_token",
        "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
        "known_hosts", "authorized_keys", "credentials", "secrets",
    }

    _MAX_FILE_SIZE = 1024 * 1024  # 1 MB

    @classmethod
    def _allowed_dirs(cls) -> list[Path]:
        env_dirs = os.environ.get("HERMES_RAG_ALLOW_DIRS", "")
        if env_dirs:
            return [Path(d).resolve() for d in env_dirs.split(";") if d.strip()]
        defaults = [Path.home() / "Documents"]
        project_dir = Path(__file__).resolve().parent.parent.parent.parent
        defaults.append(project_dir)
        return defaults

    @classmethod
    def _is_path_allowed(cls, path: Path) -> bool:
        try:
            resolved = path.resolve()
        except Exception:
            return False
        # Reject hidden files/directories
        if any(part.startswith(".") for part in resolved.parts):
            return False
        # Reject known sensitive filenames
        if resolved.name.lower() in cls.SENSITIVE_FILENAMES:
            return False
        # Sandbox check
        allowed_dirs = cls._allowed_dirs()
        return any(
            resolved == allowed or allowed in resolved.parents
            for allowed in allowed_dirs
        )

    @classmethod
    def inject_local_files(cls, user_message: str) -> str:
        matches = re.finditer(cls.PATH_PATTERN, user_message)
        appended_context = []

        for match in matches:
            file_path = match.group(1).strip()

            try:
                path_obj = Path(file_path)
                if not cls._is_path_allowed(path_obj):
                    logger.warning(f"RAG Service: Rejected out-of-sandbox path -> {file_path}")
                    continue
                if path_obj.exists() and path_obj.is_file():
                    if path_obj.suffix.lower() not in cls.SUPPORTED_EXTENSIONS:
                        continue
                    # Size guard
                    if path_obj.stat().st_size > cls._MAX_FILE_SIZE:
                        logger.warning(f"RAG Service: File too large -> {file_path}")
                        continue
                    logger.info(f"RAG Service: Leyendo archivo detectado -> {file_path}")
                    # Leemos con cuidado de los encodings
                    try:
                        content = path_obj.read_text(encoding='utf-8')
                    except UnicodeDecodeError:
                        content = path_obj.read_text(encoding='latin-1')

                    # Limitamos a unos ~15k caracteres para no explotar el context window
                    if len(content) > 15000:
                        content = content[:15000] + "\n\n[... CONTENIDO TRUNCADO POR LONGITUD ...]"

                    appended_context.append(f"\n\n--- INICIO DEL ARCHIVO LOCAL: {file_path} ---\n{content}\n--- FIN DEL ARCHIVO ---")
            except Exception as e:
                logger.warning(f"RAG Service: Error leyendo {file_path}: {e}")

        if appended_context:
            return user_message + "".join(appended_context)

        return user_message
