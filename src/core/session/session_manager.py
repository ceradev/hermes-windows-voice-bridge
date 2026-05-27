import uuid
import keyring
from keyring.errors import PasswordDeleteError
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.storage.database import Database

class SessionManager:
    SERVICE_NAME = "HermesVoiceBridge"
    
    def __init__(self, db: Database):
        self.db = db
        self._ensure_default_session()
        
    def _ensure_default_session(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        active = cursor.execute('SELECT id FROM sessions WHERE is_active = 1').fetchone()
        if not active:
            session_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO sessions (id, name, is_active, remote_session_id)
                VALUES (?, ?, 1, NULL)
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

    def create_session(self, name: str, remote_session_id: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        conn = self.db.get_connection()
        cursor = conn.cursor()
        # Deactivate current
        cursor.execute('UPDATE sessions SET is_active = 0')
        # Create new
        cursor.execute('''
            INSERT INTO sessions (id, name, is_active, remote_session_id)
            VALUES (?, ?, 1, ?)
        ''', (session_id, name, remote_session_id))
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
                cursor.execute('INSERT INTO sessions (id, name, is_active) VALUES (?, ?, 1)', (new_id, "Default Session"))
            conn.commit()
        conn.close()

    def get_sessions(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        sessions = cursor.execute('SELECT * FROM sessions ORDER BY updated_at DESC').fetchall()
        conn.close()
        return [dict(row) for row in sessions]

    def rename_session(self, session_id: str, new_name: str) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE sessions SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_name, session_id))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0

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
        return msg_id

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
