import json

import pytest

from backend.credisense.terminal import _read_application_form


def test_read_application_form_returns_empty_dict_without_path() -> None:
    assert _read_application_form("") == {}


def test_read_application_form_requires_existing_file(tmp_path) -> None:
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        _read_application_form(str(missing_path))


def test_read_application_form_requires_json_object(tmp_path) -> None:
    form_path = tmp_path / "form.json"
    form_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    with pytest.raises(ValueError):
        _read_application_form(str(form_path))


def test_read_application_form_reads_valid_json(tmp_path) -> None:
    form_path = tmp_path / "form.json"
    form_path.write_text(json.dumps({"ad_soyad": "Deniz Kaya"}), encoding="utf-8")

    assert _read_application_form(str(form_path)) == {"ad_soyad": "Deniz Kaya"}

