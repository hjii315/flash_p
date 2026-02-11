from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from typing import Optional

from flash_proto.types import Requirements


class Storage:
    def __init__(self, db_path: str, runs_dir: str) -> None:
        self.db_path = db_path
        self.runs_dir = Path(runs_dir)
        self._init_db()

    def _sanitize_component(self, value: str) -> str:
        value = value.strip().replace(" ", "_")
        for ch in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
            value = value.replace(ch, "_")
        while "__" in value:
            value = value.replace("__", "_")
        return value.strip("_ ") or "data"

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    requirements_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    content TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )

    def create_session(self, requirements: Requirements) -> str:
        session_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        requirements_json = json.dumps(asdict(requirements), ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (id, created_at, requirements_json) VALUES (?, ?, ?)",
                (session_id, created_at, requirements_json),
            )

        (self.runs_dir / session_id).mkdir(parents=True, exist_ok=True)
        return session_id

    def save_artifact(
        self,
        session_id: str,
        kind: str,
        content: str,
        filename: str,
        *,
        data_name: Optional[str] = None,
        run_stamp: Optional[str] = None,
    ) -> str:
        artifact_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        session_dir = self.runs_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(filename).suffix or ".md"
        if data_name and run_stamp:
            base = f"{self._sanitize_component(data_name)}_{run_stamp}_{kind}{suffix}"
        else:
            base = filename

        safe_filename = base.replace("..", "_").replace("/", "_").replace("\\", "_")
        file_path = session_dir / safe_filename
        file_path.write_text(content, encoding="utf-8")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (id, session_id, kind, created_at, content, file_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (artifact_id, session_id, kind, created_at, content, os.fspath(file_path)),
            )

        return artifact_id
