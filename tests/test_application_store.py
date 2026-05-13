from backend.credisense.basvuru_deposu import get_application_record, list_application_records, save_application_record


def test_application_store_saves_and_reads_record(tmp_path) -> None:
    store_path = tmp_path / "applications.json"
    record = {
        "application_id": "APP-20260513-TEST0001",
        "created_at": "2026-05-13T12:00:00",
        "current_status": {"status_code": "MANUAL_REVIEW"},
    }

    save_application_record(record, store_path=store_path)

    assert get_application_record("APP-20260513-TEST0001", store_path=store_path) == record
    assert list_application_records(store_path=store_path) == [record]


def test_application_store_updates_existing_record(tmp_path) -> None:
    store_path = tmp_path / "applications.json"
    first_record = {
        "application_id": "APP-20260513-TEST0001",
        "created_at": "2026-05-13T12:00:00",
        "current_status": {"status_code": "MANUAL_REVIEW"},
    }
    updated_record = {
        "application_id": "APP-20260513-TEST0001",
        "created_at": "2026-05-13T12:00:00",
        "current_status": {"status_code": "APPROVED"},
    }

    save_application_record(first_record, store_path=store_path)
    save_application_record(updated_record, store_path=store_path)

    assert get_application_record("APP-20260513-TEST0001", store_path=store_path) == updated_record


def test_application_store_supports_sqlite_files(tmp_path) -> None:
    store_path = tmp_path / "applications.db"
    first_record = {
        "application_id": "APP-20260513-TEST0001",
        "created_at": "2026-05-13T12:00:00",
        "current_status": {"status_code": "MANUAL_REVIEW"},
    }
    second_record = {
        "application_id": "APP-20260513-TEST0002",
        "created_at": "2026-05-13T13:00:00",
        "current_status": {"status_code": "APPROVED"},
    }

    save_application_record(first_record, store_path=store_path)
    save_application_record(second_record, store_path=store_path)

    assert get_application_record("APP-20260513-TEST0001", store_path=store_path) == first_record
    assert list_application_records(store_path=store_path, limit=1) == [second_record]
