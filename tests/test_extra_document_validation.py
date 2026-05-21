from datetime import date
from pathlib import Path

from backend.credisense.ek_belge_dogrulama import validate_requested_document_upload


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_IDENTITY = PROJECT_ROOT / "ornek_belgeler" / "Sentetik Kimlik Belgesi Ornegi.pdf"
SAMPLE_PAYROLL = PROJECT_ROOT / "ornek_belgeler" / "Sentetik Maas Bordrosu Ornegi.pdf"
SAMPLE_BANK_STATEMENT = PROJECT_ROOT / "ornek_belgeler" / "Sentetik Banka Hesap Dokumu Ornegi.pdf"


def test_six_month_statement_request_rejects_three_month_statement() -> None:
    result = validate_requested_document_upload(
        SAMPLE_BANK_STATEMENT,
        requested_document_name="Son 6 aylik hesap dokumu",
        document_type_hint="extra-son-6-aylik-hesap-dokumu",
        today=date(2026, 5, 21),
    )

    assert result.checked is True
    assert result.is_valid is False
    assert result.expected_document_type == "bank_statement"
    assert result.detected_document_type == "bank_statement"
    assert result.details["covered_months"] == 3
    assert "en az 6 aylik hesap dokumu" in result.message


def test_current_income_document_accepts_recent_payroll() -> None:
    result = validate_requested_document_upload(
        SAMPLE_PAYROLL,
        requested_document_name="Guncel gelir belgesi",
        document_type_hint="extra-guncel-gelir-belgesi",
        today=date(2026, 5, 21),
    )

    assert result.checked is True
    assert result.is_valid is True
    assert result.expected_document_type == "payroll"
    assert result.detected_document_type == "payroll"
    assert result.details["payroll_age_months"] == 2


def test_income_document_request_rejects_identity_document() -> None:
    result = validate_requested_document_upload(
        SAMPLE_IDENTITY,
        requested_document_name="Guncel gelir belgesi",
        document_type_hint="extra-guncel-gelir-belgesi",
        today=date(2026, 5, 21),
    )

    assert result.checked is True
    assert result.is_valid is False
    assert result.expected_document_type == "payroll"
    assert result.detected_document_type == "identity"
    assert "Yanlis belge yuklendi" in result.message
