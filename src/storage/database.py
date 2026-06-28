import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._run_migrations()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _run_migrations(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create migrations table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        current_version = cursor.execute('SELECT MAX(version) FROM _migrations').fetchone()[0] or 0

        migrations = self._get_migrations()
        for version, sql in sorted(migrations.items()):
            if version > current_version:
                cursor.executescript(sql)
                cursor.execute('INSERT INTO _migrations (version) VALUES (?)', (version,))

        conn.commit()
        conn.close()

    def _get_migrations(self) -> Dict[int, str]:
        # Migrations are defined here or loaded from a folder. We'll define them inline for simplicity.
        return {
            1: '''
                CREATE TABLE sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 0
                );

                CREATE TABLE messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,
                    status TEXT,
                    latency_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
            ''',
            2: '''
                ALTER TABLE sessions ADD COLUMN remote_session_id TEXT;
            ''',
            3: '''
                ALTER TABLE sessions ADD COLUMN title_source TEXT NOT NULL DEFAULT 'manual';

                UPDATE sessions
                SET title_source = 'system'
                WHERE TRIM(name) IN ('New Session', 'Default Session');

                UPDATE sessions
                SET title_source = 'manual'
                WHERE title_source = 'system'
                  AND TRIM(name) NOT IN ('New Session', 'Default Session');
            ''',
        }
