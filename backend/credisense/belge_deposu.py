from __future__ import annotations

"""Yuklenen belge deposu.

Bu modul PDF dosyalarini yerel klasore, belge metadatasini SQLite tablosuna
kaydeder. Boylece belge yukleme ekrani sadece tarayici state'inde kalmaz.
"""

import json
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

from .yol_ayarlari import data_folder, data_path


DEFAULT_DOCUMENT_STORE = data_path("belge_kayitlari.db")
DEFAULT_DOCUMENT_FOLDER = data_folder("yuklenen_belgeler")


def save_uploaded_document(
    file_name: str,
    file_stream: BinaryIO,
    owner_user_id: str,
    document_type: str,
    document_name: str,
    store_path: str | Path = DEFAULT_DOCUMENT_STORE,
    file_folder: str | Path = DEFAULT_DOCUMENT_FOLDER,
) -> dict:
    """PDF dosyasini kaydeder ve metadata kaydini SQLite'a yazar."""

    safe_file_name = Path(file_name or "document.pdf").name
    if not safe_file_name.lower().endswith(".pdf"):
        raise ValueError("Sadece PDF belgeleri kaydedilebilir.")

    document_id = f"DOC-{uuid.uuid4().hex[:12].upper()}"
    target_folder = Path(file_folder) / owner_user_id
    target_folder.mkdir(parents=True, exist_ok=True)
    target_path = target_folder / f"{document_id}.pdf"

    with target_path.open("wb") as output_file:
        shutil.copyfileobj(file_stream, output_file)

    record = {
        "document_id": document_id,
        "owner_user_id": owner_user_id,
        "document_type": document_type,
        "document_name": document_name,
        "original_file_name": safe_file_name,
        "stored_path": str(target_path),
        "status": "uploaded",
        "created_at": _now_iso(),
    }
    _save_record(record, store_path=store_path)
    return record


def list_user_documents(
    owner_user_id: str,
    store_path: str | Path = DEFAULT_DOCUMENT_STORE,
) -> list[dict]:
    """Kullaniciya ait belge kayitlarini listeler."""

    path = Path(store_path)
    if not path.exists():
        return []

    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        rows = connection.execute(
            """
            SELECT payload
            FROM documents
            WHERE owner_user_id = ?
            ORDER BY created_at DESC
            """,
            (owner_user_id,),
        ).fetchall()

    return [json.loads(row[0]) for row in rows]


def _save_record(record: dict, store_path: str | Path) -> None:
    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        connection.execute(
            """
            INSERT INTO documents (
                document_id, owner_user_id, document_type, status, created_at, payload
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["document_id"],
                record["owner_user_id"],
                record["document_type"],
                record["status"],
                record["created_at"],
                json.dumps(record, ensure_ascii=False),
            ),
        )


def _create_table_if_needed(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
