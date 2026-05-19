from __future__ import annotations

"""Odeme plani deposu

Kredi onaylandiktan sonra olusan odeme plani ayri bir kayit olarak saklanir. Bu modul,
prototip icin SQLite tabanli basit bir odeme plani deposu saglar.
"""

import json
import sqlite3
from pathlib import Path

from .yol_ayarlari import data_path


DEFAULT_PAYMENT_STORE = data_path("odeme_planlari.db")


def save_payment_plan(payment_plan: dict, store_path: str | Path = DEFAULT_PAYMENT_STORE) -> dict:
    """Odeme planini SQLite deposuna ekler veya gunceller."""

    loan_id = str(payment_plan.get("loan_id", "")).strip()
    if not loan_id:
        raise ValueError("Odeme planinda loan_id bulunmali.")

    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(payment_plan, ensure_ascii=False)

    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        connection.execute(
            """
            INSERT OR REPLACE INTO payment_plans (
                loan_id,
                application_id,
                created_key,
                payload
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                payment_plan.get("loan_id", ""),
                payment_plan.get("application_id", ""),
                payment_plan.get("first_due_date", ""),
                payload,
            ),
        )

    return payment_plan


def get_payment_plan(loan_id: str, store_path: str | Path = DEFAULT_PAYMENT_STORE) -> dict | None:
    """Kredi ID degerine gore odeme planini dondurur."""

    path = Path(store_path)
    if not path.exists():
        return None

    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        row = connection.execute(
            "SELECT payload FROM payment_plans WHERE loan_id = ?",
            (loan_id,),
        ).fetchone()

    return json.loads(row[0]) if row else None


def get_payment_plan_by_application(
    application_id: str,
    store_path: str | Path = DEFAULT_PAYMENT_STORE,
) -> dict | None:
    """Basvuru ID degerine gore odeme planini dondurur."""

    path = Path(store_path)
    if not path.exists():
        return None

    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        row = connection.execute(
            """
            SELECT payload
            FROM payment_plans
            WHERE application_id = ?
            ORDER BY created_key DESC, loan_id DESC
            LIMIT 1
            """,
            (application_id,),
        ).fetchone()

    return json.loads(row[0]) if row else None


def list_payment_plans(store_path: str | Path = DEFAULT_PAYMENT_STORE, limit: int = 50) -> list[dict]:
    """Son olusturulan odeme planlarini listeler."""

    path = Path(store_path)
    if not path.exists():
        return []

    safe_limit = max(1, min(int(limit), 100))
    with sqlite3.connect(path) as connection:
        _create_table_if_needed(connection)
        rows = connection.execute(
            """
            SELECT payload
            FROM payment_plans
            ORDER BY created_key DESC, loan_id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    return [json.loads(row[0]) for row in rows]


def _create_table_if_needed(connection: sqlite3.Connection) -> None:
    """Odeme plani tablosu yoksa olusturur."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_plans (
            loan_id TEXT PRIMARY KEY,
            application_id TEXT NOT NULL,
            created_key TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
