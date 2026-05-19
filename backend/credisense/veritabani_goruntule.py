from __future__ import annotations

"""SQLite veritabanlarini terminalden goruntuleme araci.

VS Code eklentisi kullanmadan tablolarin ve kayitlarin hizli kontrol edilmesi
icin yazildi. Sadece okuma yapar, veritabani uzerinde degisiklik yapmaz.
"""

import argparse
import json
import sqlite3
from pathlib import Path

from .yol_ayarlari import data_path

DATABASES = {
    "kullanicilar": data_path("credisense_kullanicilar.db"),
    "basvurular": data_path("basvuru_kayitlari.db"),
    "belgeler": data_path("belge_kayitlari.db"),
    "odemeler": data_path("odeme_planlari.db"),
    "asistan": data_path("asistan_mesajlari.db"),
    "raporlar": data_path("rapor_kayitlari.db"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="CrediSense SQLite veritabani goruntuleyici")
    parser.add_argument("database", choices=DATABASES.keys(), help="Goruntulenecek veritabani")
    parser.add_argument("--table", default="", help="Okunacak tablo adi")
    parser.add_argument("--limit", default=20, type=int, help="Gosterilecek maksimum kayit sayisi")
    parser.add_argument(
        "--show-sensitive",
        action="store_true",
        help="Hash, salt ve token gibi hassas alanlari gizlemeden gosterir. Duz metin sifre gostermez.",
    )
    args = parser.parse_args()

    database_path = DATABASES[args.database]
    if not database_path.exists():
        print(json.dumps({"error": f"Veritabani bulunamadi: {database_path}"}, ensure_ascii=False, indent=2))
        return

    if args.table:
        print(
            json.dumps(
                read_table(database_path, args.table, args.limit, show_sensitive=args.show_sensitive),
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print(json.dumps(database_summary(database_path), ensure_ascii=False, indent=2))


def database_summary(database_path: Path) -> dict:
    """Veritabani icindeki tablo listesini ve kayit sayilarini dondurur."""

    summary = {
        "database": str(database_path),
        "tables": [],
    }
    with sqlite3.connect(database_path) as connection:
        table_names = get_table_names(connection)
        for table_name in table_names:
            row_count = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            summary["tables"].append(
                {
                    "name": table_name,
                    "row_count": row_count,
                }
            )

    return summary


def read_table(database_path: Path, table_name: str, limit: int, show_sensitive: bool = False) -> dict:
    """Secilen tablodaki ilk kayitlari JSON olarak dondurur."""

    safe_limit = max(1, min(limit, 100))
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        table_names = get_table_names(connection)
        if table_name not in table_names:
            return {
                "database": str(database_path),
                "error": f"Tablo bulunamadi: {table_name}",
                "available_tables": table_names,
            }

        rows = connection.execute(f"SELECT * FROM {table_name} LIMIT ?", (safe_limit,)).fetchall()

    return {
        "database": str(database_path),
        "table": table_name,
        "sensitive_columns_visible": show_sensitive,
        "rows": [
            dict(row) if show_sensitive else mask_sensitive_columns(dict(row))
            for row in rows
        ],
    }


def get_table_names(connection: sqlite3.Connection) -> list[str]:
    """SQLite dosyasindaki tablo adlarini listeler."""

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def mask_sensitive_columns(row: dict) -> dict:
    """Sifre hash, salt ve token gibi hassas alanlari ekranda gizler."""

    sensitive_columns = {"password_hash", "salt", "token_hash", "token"}
    return {
        key: "[hidden]" if key in sensitive_columns else value
        for key, value in row.items()
    }


if __name__ == "__main__":
    main()
