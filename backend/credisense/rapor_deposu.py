from __future__ import annotations

"""Rapor metadata deposu."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .yol_ayarlari import data_path


DEFAULT_REPORT_STORE = data_path("rapor_kayitlari.db")


def save_report_record(
    application_id: str,
    owner_user_id: str,
    report_files: dict,
    store_path: str | Path = DEFAULT_REPORT_STORE,
    title: str = "",
    report_type: str = "",
    content: str = "",
    report_id: str = "",
) -> dict:
    """Uretilen rapor dosyalarini SQLite metadata olarak kaydeder."""

    record = {
        "report_id": report_id or f"RPT-{application_id}",
        "application_id": application_id,
        "owner_user_id": owner_user_id,
        "title": title or f"Basvuru raporu {application_id}",
        "report_type": report_type or "Analiz raporu",
        "content": content,
        "report_files": report_files,
        "created_at": _now_iso(),
    }

    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        connection.execute(
            """
            INSERT OR REPLACE INTO reports (
                report_id, application_id, owner_user_id, created_at, payload
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record["report_id"],
                application_id,
                owner_user_id,
                record["created_at"],
                json.dumps(record, ensure_ascii=False),
            ),
        )

    return record


def save_expert_report_record(
    application_id: str,
    owner_user_id: str,
    title: str,
    content: str,
    author: str,
    store_path: str | Path = DEFAULT_REPORT_STORE,
) -> dict:
    """Uzmanin yazdigi kanaat raporunu rapor deposuna kaydeder."""

    report_id = f"RPT-EXP-{application_id}-{uuid4().hex[:8].upper()}"
    full_content = content.strip()
    if author.strip():
        full_content = f"Uzman: {author.strip()}\n\n{full_content}"

    return save_report_record(
        application_id=application_id,
        owner_user_id=owner_user_id,
        report_files={},
        store_path=store_path,
        title=title or f"Uzman kanaat raporu {application_id}",
        report_type="Uzman kanaat raporu",
        content=full_content,
        report_id=report_id,
    )


def list_report_records(
    owner_user_id: str = "",
    store_path: str | Path = DEFAULT_REPORT_STORE,
    limit: int = 50,
) -> list[dict]:
    """Rapor metadata kayitlarini listeler."""

    path = Path(store_path)
    if not path.exists():
        return []

    safe_limit = max(1, min(int(limit), 100))
    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        if owner_user_id:
            rows = connection.execute(
                """
                SELECT payload
                FROM reports
                WHERE owner_user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (owner_user_id, safe_limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT payload
                FROM reports
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

    return [json.loads(row[0]) for row in rows]


def _create_table_if_needed(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            application_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
