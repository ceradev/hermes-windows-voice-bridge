from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.session.session_manager import SessionManager
from src.storage.database import Database


def test_message_stats_and_recent_messages(tmp_path: Path) -> None:
    db = Database(tmp_path / "stats.sqlite")
    manager = SessionManager(db)
    session_id = manager.get_active_session_id()

    manager.add_message(session_id, "user", "hola hermes", source="voice")
    manager.add_message(session_id, "hermes", "hola", source="voice")
    manager.add_message(session_id, "user", "otra pregunta", source="manual")

    stats = manager.get_message_stats()
    assert stats["today"] == 2
    assert stats["week"] == 2

    recent = manager.get_recent_messages(limit=2)
    assert len(recent) == 2
    assert recent[0]["role"] == "user"
    assert recent[0]["content"] == "otra pregunta"
    assert recent[1]["role"] == "hermes"
