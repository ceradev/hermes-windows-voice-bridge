import os
import sys
import winreg

class AutostartService:
    def __init__(self, app_name="HermesVoiceBridge"):
        self.app_name = app_name
        self.script_path = os.path.abspath(sys.argv[0])
        # We need pythonw.exe instead of python.exe if we want to hide the console on startup
        # But if the user runs with python.exe, we'll just use that.
        self.python_exe = sys.executable

    def enable(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            command = f'"{self.python_exe}" "{self.script_path}"'
            winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Failed to enable autostart: {e}")
            return False

    def disable(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, self.app_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return True
        except Exception as e:
            print(f"Failed to disable autostart: {e}")
            return False
            
    def is_enabled(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, self.app_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False
