from __future__ import annotations

"""Başvuru kayıt deposu

Bu modül küçük ve anlaşılır bir dosya tabanlı kayıt deposudur. Gerçek üründe burası PostgreSQL,
MS SQL veya benzer bir veritabanına taşınabilir. Prototip aşamasında JSON dosyası, başvuru
kayıtlarını takip etmek için yeterlidir.
"""

import json
import sqlite3
from pathlib import Path

from .yol_ayarlari import data_path


DEFAULT_APPLICATION_STORE = data_path("basvuru_kayitlari.db")
SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}


def save_application_record(
    application_record: dict,
    store_path: str | Path = DEFAULT_APPLICATION_STORE,
) -> dict:
    """Başvuru kaydını dosyaya ekler veya mevcut kaydı günceller."""

    application_id = str(application_record.get("application_id", "")).strip()
    if not application_id:
        raise ValueError("Başvuru kaydında application_id bulunmalı.")

    if _is_sqlite_store(store_path):
        _save_to_sqlite(application_record, store_path)
        return application_record

    records = _read_records(store_path)
    records[application_id] = application_record
    _write_records(records, store_path)
    return application_record


def get_application_record(
    application_id: str,
    store_path: str | Path = DEFAULT_APPLICATION_STORE,
) -> dict | None:
    """Başvuru ID değerine göre kayıt döndürür."""

    if _is_sqlite_store(store_path):
        return _get_from_sqlite(application_id, store_path)

    records = _read_records(store_path)
    return records.get(application_id)


def list_application_records(
    store_path: str | Path = DEFAULT_APPLICATION_STORE,
    limit: int = 50,
) -> list[dict]:
    """Son eklenen başvuru kayıtlarını listeler."""

    if _is_sqlite_store(store_path):
        return _list_from_sqlite(store_path, limit=limit)

    records = list(_read_records(store_path).values())
    records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return records[:limit]


def _is_sqlite_store(store_path: str | Path) -> bool:
    """Dosya uzantısına bakarak SQLite deposu kullanılıp kullanılmayacağını belirler."""

    return Path(store_path).suffix.lower() in SQLITE_SUFFIXES


def _save_to_sqlite(application_record: dict, store_path: str | Path) -> None:
    """Başvuru kaydını SQLite tablosuna ekler veya günceller."""

    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(application_record, ensure_ascii=False)

    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        connection.execute(
            """
            INSERT OR REPLACE INTO applications (
                application_id,
                created_at,
                current_status_code,
                payload
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                application_record.get("application_id", ""),
                application_record.get("created_at", ""),
                application_record.get("current_status", {}).get("status_code", ""),
                payload,
            ),
        )


def _get_from_sqlite(application_id: str, store_path: str | Path) -> dict | None:
    """SQLite tablosundan tek başvuru kaydını okur."""

    path = Path(store_path)
    if not path.exists():
        return None

    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        row = connection.execute(
            "SELECT payload FROM applications WHERE application_id = ?",
            (application_id,),
        ).fetchone()

    return json.loads(row[0]) if row else None


def _list_from_sqlite(store_path: str | Path, limit: int) -> list[dict]:
    """SQLite tablosundaki son başvuru kayıtlarını listeler."""

    path = Path(store_path)
    if not path.exists():
        return []

    safe_limit = max(1, min(int(limit), 100))
    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        rows = connection.execute(
            """
            SELECT payload
            FROM applications
            ORDER BY created_at DESC, application_id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    return [json.loads(row[0]) for row in rows]


def _create_table_if_needed(connection: sqlite3.Connection) -> None:
    """Başvuru tablosu yoksa oluşturur."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            application_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            current_status_code TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )


def _read_records(store_path: str | Path) -> dict[str, dict]:
    """Kayıt dosyasını okur. Dosya yoksa boş sözlük döndürür."""

    path = Path(store_path)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Başvuru kayıt dosyası geçerli JSON değil: {path}") from error

    if not isinstance(data, dict):
        raise ValueError(f"Başvuru kayıt dosyası sözlük yapısında olmalı: {path}")

    return data


def _write_records(records: dict[str, dict], store_path: str | Path) -> None:
    """Kayıt sözlüğünü JSON dosyasına yazar."""

    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
