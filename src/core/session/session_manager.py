import uuid
import re
import keyring
from keyring.errors import PasswordDeleteError
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.storage.database import Database
from src.core.state import AppStateStore

class SessionManager:
    SERVICE_NAME = "HermesVoiceBridge"
    GENERIC_SESSION_NAMES = {"New Session", "Default Session"}

    AUTO_TITLE_PREFIX_PATTERNS = (
        r"^(?:please[\s,]+)?help\s+me[\s,]+(?:to\s+)?",
        r"^(?:please[\s,]+)?(?:can|could|would|will)\s+you(?:[\s,]+please)?[\s,]+",
        r"^(?:please[\s,]+)?i\s+need(?:\s+help)?[\s,]+(?:to\s+)?",
        r"^(?:por\s+favor[\s,]+)?ay[uú]dame[\s,]+(?:a\s+)?",
        r"^(?:por\s+favor[\s,]+)?(?:puedes|podr[ií]as)[\s,]+(?:ayudarme\s+a\s+)?",
        r"^(?:por\s+favor[\s,]+)?necesito\s+ayuda\s+para\s+",
    )

    def __init__(self, db: Database, app_state: AppStateStore | None = None):
        self.db = db
        self.app_state = app_state or AppStateStore()
        self._ensure_default_session()

    def _ensure_default_session(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        active = cursor.execute('SELECT id FROM sessions WHERE is_active = 1').fetchone()
        if not active:
            session_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO sessions (id, name, is_active, remote_session_id, title_source)
                VALUES (?, ?, 1, NULL, 'system')
            ''', (session_id, "Default Session"))
            conn.commit()
        conn.close()

    def get_active_session_id(self) -> str:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        active = cursor.execute('SELECT id FROM sessions WHERE is_active = 1').fetchone()
        conn.close()
        return active['id'] if active else ""

    def get_active_session(self) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        active = cursor.execute('SELECT * FROM sessions WHERE is_active = 1').fetchone()
        conn.close()
        return dict(active) if active else None

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        row = cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def create_session(self, name: str, remote_session_id: Optional[str] = None) -> str:
        normalized = self._normalize_name(name) or "New Session"
        session_id = str(uuid.uuid4())
        conn = self.db.get_connection()
        cursor = conn.cursor()
        # Deactivate current
        cursor.execute('UPDATE sessions SET is_active = 0')
        # Create new
        cursor.execute('''
            INSERT INTO sessions (id, name, is_active, remote_session_id, title_source)
            VALUES (?, ?, 1, ?, ?)
        ''', (session_id, normalized, remote_session_id, self._initial_title_source(normalized)))
        conn.commit()
        conn.close()
        return session_id

    def switch_session(self, session_id: str) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Check if exists
        exists = cursor.execute('SELECT id FROM sessions WHERE id = ?', (session_id,)).fetchone()
        if not exists:
            conn.close()
            return False

        cursor.execute('UPDATE sessions SET is_active = 0')
        cursor.execute('UPDATE sessions SET is_active = 1 WHERE id = ?', (session_id,))
        conn.commit()
        conn.close()
        return True

    def set_remote_session_id(self, session_id: str, remote_session_id: Optional[str]) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE sessions SET remote_session_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (remote_session_id, session_id),
        )
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0

    def delete_session(self, session_id: str):
        conn = self.db.get_connection()
        cursor = conn.cursor()

        is_active = cursor.execute('SELECT is_active FROM sessions WHERE id = ?', (session_id,)).fetchone()
        cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        conn.commit()

        # If deleted active, activate the most recent one
        if is_active and is_active['is_active']:
            recent = cursor.execute('SELECT id FROM sessions ORDER BY updated_at DESC LIMIT 1').fetchone()
            if recent:
                cursor.execute('UPDATE sessions SET is_active = 1 WHERE id = ?', (recent['id'],))
            else:
                new_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO sessions (id, name, is_active, remote_session_id, title_source)
                    VALUES (?, ?, 1, NULL, 'system')
                ''', (new_id, "Default Session"))
            conn.commit()
        conn.close()

    def get_sessions(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        sessions = cursor.execute('SELECT * FROM sessions ORDER BY updated_at DESC').fetchall()
        conn.close()
        return [dict(row) for row in sessions]

    def rename_session(self, session_id: str, new_name: str) -> bool:
        normalized = self._normalize_name(new_name)
        if not normalized:
            return False
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET name = ?, title_source = 'manual', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (normalized, session_id),
        )
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0

    def count_user_messages(self, session_id: str) -> int:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE session_id = ? AND role = 'user'",
            (session_id,),
        ).fetchone()
        conn.close()
        return int(row['c']) if row else 0

    def auto_title_session(self, session_id: str, message_text: str) -> Optional[str]:
        title = self.build_auto_title(message_text)
        if not title:
            return None

        conn = self.db.get_connection()
        cursor = conn.cursor()
        row = cursor.execute(
            'SELECT id, name, title_source FROM sessions WHERE id = ?',
            (session_id,),
        ).fetchone()
        if not row:
            conn.close()
            return None

        current_source = (row['title_source'] or 'manual').lower()
        if current_source != 'system':
            conn.close()
            return None

        existing_user_messages = cursor.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE session_id = ? AND role = 'user'",
            (session_id,),
        ).fetchone()
        existing_count = int(existing_user_messages['c']) if existing_user_messages else 0
        if existing_count > 0:
            conn.close()
            return None

        cursor.execute(
            "UPDATE sessions SET name = ?, title_source = 'auto', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, session_id),
        )
        conn.commit()
        conn.close()
        return title

    @classmethod
    def _normalize_name(cls, value: str) -> str:
        if value is None:
            return ""
        cleaned = re.sub(r"\s+", " ", str(value)).strip()
        return cleaned

    @classmethod
    def _is_generic_name(cls, name: str) -> bool:
        normalized = cls._normalize_name(name).casefold()
        return normalized in {n.casefold() for n in cls.GENERIC_SESSION_NAMES}

    @classmethod
    def _initial_title_source(cls, name: str) -> str:
        return "system" if cls._is_generic_name(name) else "manual"

    @classmethod
    def build_auto_title(cls, text: str, max_length: int = 60) -> str:
        first_non_empty_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        normalized = cls._normalize_name(first_non_empty_line)
        if not normalized:
            return ""

        normalized = normalized.lstrip("-•*#>\"'¿¡([{")
        normalized = cls._normalize_name(normalized)

        changed = True
        while changed:
            changed = False
            for pattern in cls.AUTO_TITLE_PREFIX_PATTERNS:
                cleaned = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
                cleaned = cls._normalize_name(cleaned)
                if cleaned and cleaned != normalized:
                    normalized = cleaned
                    changed = True
                    break

        normalized = normalized.strip(" .,!?:;'-–—")
        if normalized:
            normalized = normalized[0].upper() + normalized[1:]

        if len(normalized) <= max_length:
            return normalized

        truncated = normalized[:max_length].rsplit(" ", 1)[0].strip(" .,!?:;'-–—")
        if not truncated:
            truncated = normalized[:max_length]
        return truncated.rstrip() + "…"

    def add_message(self, session_id: str, role: str, content: str, source: str = "manual", status: str = "success", latency_ms: Optional[int] = None) -> str:
        msg_id = str(uuid.uuid4())
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (id, session_id, role, content, source, status, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (msg_id, session_id, role, content, source, status, latency_ms))
        cursor.execute('UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (session_id,))
        conn.commit()
        conn.close()
        self._sync_runtime_preview(role, content)
        return msg_id

    def _sync_runtime_preview(self, role: str, content: str) -> None:
        if role == "user":
            self.app_state.update(last_transcript=content or "")
        elif role == "hermes":
            preview = (content or "").strip()
            if len(preview) > 240:
                preview = preview[:239].rstrip() + "…"
            self.app_state.update(last_response_preview=preview)

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        messages = cursor.execute('SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC', (session_id,)).fetchall()
        conn.close()
        return [dict(row) for row in messages]

    # Token management via Keyring
    def save_vps_token(self, username: str, token: str):
        keyring.set_password(self.SERVICE_NAME, username, token)

    def get_vps_token(self, username: str) -> Optional[str]:
        return keyring.get_password(self.SERVICE_NAME, username)

    def delete_vps_token(self, username: str):
        try:
            keyring.delete_password(self.SERVICE_NAME, username)
        except PasswordDeleteError:
            pass
