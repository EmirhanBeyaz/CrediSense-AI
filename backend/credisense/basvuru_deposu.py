from __future__ import annotations

"""Başvuru kayıt deposu

Bu modül küçük ve anlaşılır bir dosya tabanlı kayıt deposudur. Gerçek üründe burası PostgreSQL,
MS SQL veya benzer bir veritabanına taşınabilir. Prototip aşamasında JSON dosyası, başvuru
kayıtlarını takip etmek için yeterlidir.
"""

import json
from pathlib import Path


DEFAULT_APPLICATION_STORE = Path("veri") / "basvuru_kayitlari.json"


def save_application_record(
    application_record: dict,
    store_path: str | Path = DEFAULT_APPLICATION_STORE,
) -> dict:
    """Başvuru kaydını dosyaya ekler veya mevcut kaydı günceller."""

    application_id = str(application_record.get("application_id", "")).strip()
    if not application_id:
        raise ValueError("Başvuru kaydında application_id bulunmalı.")

    records = _read_records(store_path)
    records[application_id] = application_record
    _write_records(records, store_path)
    return application_record


def get_application_record(
    application_id: str,
    store_path: str | Path = DEFAULT_APPLICATION_STORE,
) -> dict | None:
    """Başvuru ID değerine göre kayıt döndürür."""

    records = _read_records(store_path)
    return records.get(application_id)


def list_application_records(
    store_path: str | Path = DEFAULT_APPLICATION_STORE,
    limit: int = 50,
) -> list[dict]:
    """Son eklenen başvuru kayıtlarını listeler."""

    records = list(_read_records(store_path).values())
    records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return records[:limit]


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
