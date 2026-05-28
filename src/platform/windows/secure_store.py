from __future__ import annotations

import base64
import os
import sys
from pathlib import Path


def _dpapi_encrypt(plaintext: str) -> bytes:
    """Encrypt plaintext using Windows DPAPI (user-scoped)."""
    import ctypes
    from ctypes import wintypes

    _crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", wintypes.LPBYTE)]

    _crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        wintypes.LPCWSTR,
        ctypes.POINTER(DATA_BLOB),
        wintypes.HWND,
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    _crypt32.CryptProtectData.restype = wintypes.BOOL

    blob_in = DATA_BLOB()
    blob_in.cbData = len(plaintext.encode("utf-8"))
    blob_in.pbData = ctypes.cast(plaintext.encode("utf-8"), wintypes.LPBYTE)

    blob_out = DATA_BLOB()

    if not _crypt32.CryptProtectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError(ctypes.get_last_error())

    size = blob_out.cbData
    buf = ctypes.string_at(blob_out.pbData, size)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return buf


def _dpapi_decrypt(ciphertext: bytes) -> str:
    """Decrypt ciphertext using Windows DPAPI (user-scoped)."""
    import ctypes
    from ctypes import wintypes

    _crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", wintypes.LPBYTE)]

    _crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(DATA_BLOB),
        wintypes.HWND,
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    _crypt32.CryptUnprotectData.restype = wintypes.BOOL

    blob_in = DATA_BLOB()
    blob_in.cbData = len(ciphertext)
    blob_in.pbData = ctypes.cast(ciphertext, wintypes.LPBYTE)

    blob_out = DATA_BLOB()

    if not _crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError(ctypes.get_last_error())

    size = blob_out.cbData
    buf = ctypes.string_at(blob_out.pbData, size)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return buf.decode("utf-8")


class SecureValueStore:
    """Small secret store.

    On Windows uses real DPAPI (user-scoped). On non-Windows falls back to an
    opaque base64 payload with file permissions limited by the current umask.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._use_dpapi = sys.platform == "win32"

    def set_secret(self, name: str, value: str) -> None:
        data = self._read_all()
        payload = value.encode("utf-8")
        if self._use_dpapi:
            payload = _dpapi_encrypt(value)
        data[name] = base64.b64encode(payload).decode("ascii")
        self._write_all(data)

    def get_secret(self, name: str) -> str:
        raw = self._read_all().get(name, "")
        if not raw:
            return ""
        try:
            payload = base64.b64decode(raw.encode("ascii"))
        except Exception:
            return ""
        if self._use_dpapi:
            try:
                return _dpapi_decrypt(payload)
            except Exception:
                # Fallback: if it was stored as plain base64 before migration
                try:
                    return payload.decode("utf-8")
                except Exception:
                    return ""
        return payload.decode("utf-8")

    def delete_secret(self, name: str) -> None:
        data = self._read_all()
        if name in data:
            del data[name]
            self._write_all(data)

    def _read_all(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        pairs: dict[str, str] = {}
        for line in raw.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            pairs[key.strip()] = value.strip()
        return pairs

    def _write_all(self, data: dict[str, str]) -> None:
        lines = [f"{key}={value}" for key, value in sorted(data.items())]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        if os.name != "nt":
            os.chmod(self.path, 0o600)
