"""简单的 API Key 存储与校验服务，使用 SQLite 持久化。"""

import hashlib
import os
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Literal, TypedDict


Role = Literal["user", "admin", "super_admin"]


class APIKeyCreateResult(TypedDict):
    api_key: str
    role: Role
    label: str
    created_at: str


class APIKeyStore:
    def __init__(self, db_path: str = "./data/api_keys.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # 使用 RLock 以允许嵌套调用（get_or_create_super_admin -> create_key）
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._setup()

    def _setup(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL,
                    label TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def create_key(self, role: Role, label: Optional[str] = None) -> APIKeyCreateResult:
        """
        生成随机 API Key，存储哈希，返回明文 key 及基础信息。
        """
        with self._lock:
            raw_key = uuid.uuid4().hex
            key_hash = self._hash_key(raw_key)
            created_at = datetime.utcnow().isoformat()
            with self._conn:
                self._conn.execute(
                    "INSERT INTO api_keys (key_hash, role, label, created_at) VALUES (?, ?, ?, ?)",
                    (key_hash, role, label, created_at),
                )
        return {"api_key": raw_key, "role": role, "label": label or "", "created_at": created_at}

    def verify_key(self, raw_key: str) -> Optional[Dict[str, str]]:
        """
        校验明文 key，返回记录（不含明文）。
        """
        key_hash = self._hash_key(raw_key)
        cursor = self._conn.execute(
            "SELECT id, role, label, created_at FROM api_keys WHERE key_hash = ?", (key_hash,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def has_any_key(self) -> bool:
        cursor = self._conn.execute("SELECT 1 FROM api_keys LIMIT 1")
        return cursor.fetchone() is not None

    def get_or_create_super_admin(self) -> Optional[str]:
        """
        如果不存在 super_admin 则生成一个并返回明文 key，否则返回 None。
        """
        with self._lock:
            cursor = self._conn.execute("SELECT 1 FROM api_keys WHERE role = 'super_admin' LIMIT 1")
            if cursor.fetchone():
                return None
            created = self.create_key("super_admin", label="bootstrap")
            return created["api_key"]

    def list_keys(self) -> Dict[str, list]:
        cursor = self._conn.execute(
            "SELECT id, role, label, created_at FROM api_keys ORDER BY created_at DESC"
        )
        rows = [dict(row) for row in cursor.fetchall()]
        return {"items": rows}


# 创建全局实例，并在无 super_admin 时自动生成一个
key_store = APIKeyStore()
bootstrap_key = key_store.get_or_create_super_admin()
if bootstrap_key:
    bootstrap_path = Path("./data/initial_superadmin_key.txt")
    # 仅在首次生成时写入文件，方便运维取用
    bootstrap_path.write_text(bootstrap_key, encoding="utf-8")
    print(f"[bootstrap] Super admin API key generated and stored at {bootstrap_path}")
