from __future__ import annotations

"""Odeme asistani mesaj deposu."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .yol_ayarlari import data_path


DEFAULT_ASSISTANT_STORE = data_path("asistan_mesajlari.db")


def save_assistant_exchange(
    user_id: str,
    loan_id: str,
    user_message: str,
    assistant_response: dict,
    store_path: str | Path = DEFAULT_ASSISTANT_STORE,
) -> dict:
    """Kullanici sorusunu ve asistan cevabini SQLite'a kaydeder."""

    record = {
        "message_id": f"MSG-{uuid.uuid4().hex[:12].upper()}",
        "user_id": user_id,
        "loan_id": loan_id,
        "user_message": user_message,
        "assistant_response": assistant_response,
        "created_at": _now_iso(),
    }

    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        connection.execute(
            """
            INSERT INTO assistant_messages (
                message_id, user_id, loan_id, created_at, payload
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record["message_id"],
                user_id,
                loan_id,
                record["created_at"],
                json.dumps(record, ensure_ascii=False),
            ),
        )

    return record


def _create_table_if_needed(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS assistant_messages (
            message_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            loan_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
