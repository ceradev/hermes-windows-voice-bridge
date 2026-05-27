import ctypes
import re
import time
import webbrowser
import subprocess
from importlib import import_module

# Windows Virtual Key Codes for media control
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

def _press_key(vk_code):
    # keybd_event(bVk, bScan, dwFlags, dwExtraInfo)
    # KEYEVENTF_EXTENDEDKEY = 0x0001
    # KEYEVENTF_KEYUP = 0x0002
    ctypes.windll.user32.keybd_event(vk_code, 0, 0x0001, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk_code, 0, 0x0001 | 0x0002, 0)

def process_local_command(text: str) -> bool:
    """
    Parses the transcribed text. If it matches a local command pattern,
    executes the command and returns True.
    If no match, returns False.
    """
    custom_command_module = import_module("src.services.custom_commands.custom_command_service")
    custom_command_service = custom_command_module.CustomCommandService()
    custom_command = custom_command_service.match_command(text)
    if custom_command:
        return custom_command_service.execute(custom_command["id"])

    text_lower = text.lower().strip()
    # Remove accents for easier matching
    text_lower = text_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
    text_clean = re.sub(r'[^\w\s]', '', text_lower)
    
    # --- MEDIA / SYSTEM ---
    if re.search(r'\b(silencia|mutea|calla|silencio|apaga el sonido)\b', text_clean):
        _press_key(VK_VOLUME_MUTE)
        return True
        
    if re.search(r'\b(baja|bajar|reduce|menos)( el)?( volumen| sonido| voz| audio)\b', text_clean):
        for _ in range(5):
            _press_key(VK_VOLUME_DOWN)
        return True
        
    if re.search(r'\b(sube|subir|aumenta|mas|mas)( el)?( volumen| sonido| voz| audio)\b', text_clean):
        for _ in range(5):
            _press_key(VK_VOLUME_UP)
        return True
        
    if re.search(r'\b(pausa|reproduce|play|para|deten|reanuda|continua|pon)( la)?( musica| cancion| video| audio)?\b', text_clean):
        _press_key(VK_MEDIA_PLAY_PAUSE)
        return True
        
    if re.search(r'\b(siguiente|pasa|avanza|otra)( la)?( cancion| pista| track| musica)?\b', text_clean):
        _press_key(VK_MEDIA_NEXT_TRACK)
        return True
        
    if re.search(r'\b(anterior|vuelve|retrocede)( a la)?( cancion| pista| track| musica)?\b', text_clean):
        _press_key(VK_MEDIA_PREV_TRACK)
        return True

    # --- BROWSER / SEARCH ---
    # "busca x en google", "busca en google x", "busca x"
    search_match = re.search(r'\bbusca\s+(?:en google\s+)?(.+?)(?:\s+en google)?$', text_clean)
    if search_match:
        query = search_match.group(1).strip()
        if query:
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(url)
            return True

    # --- OPEN APPS ---
    open_match = re.search(r'\b(abre|abrir|inicia|ejecuta)\s+(el |la |los |las )?(.+)$', text_clean)
    if open_match:
        app_name = open_match.group(3).strip()
        app_map = {
            "bloc de notas": "notepad",
            "notas": "notepad",
            "navegador": "chrome", 
            "google": "chrome",
            "calculadora": "calc",
            "explorador": "explorer",
            "archivos": "explorer",
            "terminal": "cmd",
            "consola": "cmd",
            "comandos": "cmd",
            "spotify": "spotify",
            "whatsapp": "whatsapp",
            "discord": "discord",
        }
        
        target = app_map.get(app_name, app_name.replace(" ", ""))
        try:
            if target == "chrome":
                webbrowser.open("https://google.com")
            else:
                subprocess.Popen(f"start {target}", shell=True)
            return True
        except Exception:
            pass # Fallback to False
            
    return False
