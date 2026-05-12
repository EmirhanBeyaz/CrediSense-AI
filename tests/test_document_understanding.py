from backend.credisense.katman_02_belge_anlama import (
    detect_document_type,
    parse_money,
    understand_document_text,
)


def test_parse_money_supports_turkish_format() -> None:
    assert parse_money("42.350,75 TL") == 42350.75
    assert parse_money("0,00") == 0.0


def test_detect_document_type_with_expected_keywords() -> None:
    identity_text = "Kimlik Bilgileri Test Kimlik No Dogum Tarihi"
    payroll_text = "Maas Bordrosu Brut Ucret Net Odenecek Kesinti Bilgileri"
    bank_text = "Hesap Hareketleri Hesap Sahibi Toplam Gelen Toplam Giden"

    assert detect_document_type(identity_text) == "identity"
    assert detect_document_type(payroll_text) == "payroll"
    assert detect_document_type(bank_text) == "bank_statement"
    assert detect_document_type("ilgili anahtar kelime yok") == "unknown"


def test_understand_document_text_reports_missing_fields_for_unknown_text() -> None:
    result = understand_document_text("ilgili anahtar kelime yok")

    assert result.document_type == "unknown"
    assert result.confidence == 0.0
    assert result.missing_fields == ["document_type"]
    assert result.warnings == ["Belge türü belirlenemedi."]


def test_understand_document_text_reports_missing_identity_fields() -> None:
    result = understand_document_text("Kimlik Bilgileri Test Kimlik No")

    assert result.document_type == "identity"
    assert result.missing_fields == ["full_name", "test_id", "birth_date"]
    assert result.warnings == ["Eksik alanlar: full_name, test_id, birth_date"]
