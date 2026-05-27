import base64
from io import BytesIO

def capture_screen_base64() -> str:
    """
    Captures the primary screen, resizes it to a maximum of 720p to save bandwidth,
    and returns it as a base64 encoded JPEG string.
    """
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.thumbnail((1280, 720))
        
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=75)
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Prepend the data URI prefix so the backend knows the mime type
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"Failed to capture screen: {e}")
        return ""
