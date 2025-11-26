import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

class ChatStore:
    def __init__(self, db_path: str = "./data/chat.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # 启用外键约束，确保 ON DELETE CASCADE 生效
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._setup()

    def _setup(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    api_key_id INTEGER NOT NULL,
                    name TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
                """
            )

    def create_session(self, api_key_id: int, name: Optional[str] = None) -> Dict:
        with self._lock:
            session_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            if not name:
                name = f"Session {now}"
            
            with self._conn:
                self._conn.execute(
                    "INSERT INTO chat_sessions (id, api_key_id, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (session_id, api_key_id, name, now, now)
                )
            return {
                "id": session_id,
                "api_key_id": api_key_id,
                "name": name,
                "created_at": now,
                "updated_at": now
            }

    def get_session(self, session_id: str, api_key_id: int) -> Optional[Dict]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM chat_sessions WHERE id = ? AND api_key_id = ?",
                (session_id, api_key_id)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_sessions(self, api_key_id: int) -> List[Dict]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM chat_sessions WHERE api_key_id = ? ORDER BY updated_at DESC",
                (api_key_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def delete_session(self, session_id: str, api_key_id: int) -> bool:
        with self._lock:
            with self._conn:
                cursor = self._conn.execute(
                    "DELETE FROM chat_sessions WHERE id = ? AND api_key_id = ?",
                    (session_id, api_key_id)
                )
                return cursor.rowcount > 0

    def add_message(self, session_id: str, role: str, content: str) -> Dict:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            with self._conn:
                cursor = self._conn.execute(
                    "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                    (session_id, role, content, now)
                )
                # Update session updated_at
                self._conn.execute(
                    "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                    (now, session_id)
                )
                message_id = cursor.lastrowid
            
            return {
                "id": message_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "created_at": now
            }

    def get_messages(self, session_id: str) -> List[Dict]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

chat_store = ChatStore()
