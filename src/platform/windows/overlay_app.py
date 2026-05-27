import webview
from typing import Optional

class OverlayWindow:
    def __init__(self, bridge):
        self.bridge = bridge
        self.window = None

    def show(self, text: str):
        if self.window is None:
            # We use a simple HTML string for the overlay to avoid external dependencies
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        margin: 0;
                        padding: 10px 20px;
                        background: rgba(0, 0, 0, 0.8);
                        color: white;
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                        font-size: 14px;
                        border-radius: 8px;
                        overflow: hidden;
                        user-select: none;
                        backdrop-filter: blur(8px);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                    }}
                    #content {{
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    }}
                </style>
            </head>
            <body>
                <div id="content">
                    <span id="text">{text}</span>
                </div>
                <script>
                    function updateText(newText) {{
                        document.getElementById('text').innerText = newText;
                    }}
                </script>
            </body>
            </html>
            """
            self.window = webview.create_window(
                'Hermes Overlay',
                html=html,
                transparent=True,
                frameless=True,
                on_top=True,
                width=300,
                height=50,
                x=50,  # Or center bottom
                y=50,
            )
        else:
            self.window.evaluate_js(f"updateText('{text}')")

    def hide(self):
        if self.window:
            self.window.destroy()
            self.window = None
