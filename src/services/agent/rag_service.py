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
    
    @classmethod
    def inject_local_files(cls, user_message: str) -> str:
        matches = re.finditer(cls.PATH_PATTERN, user_message)
        appended_context = []
        
        for match in matches:
            file_path = match.group(1).strip()
            
            try:
                path_obj = Path(file_path)
                if path_obj.exists() and path_obj.is_file():
                    if path_obj.suffix.lower() in cls.SUPPORTED_EXTENSIONS:
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
