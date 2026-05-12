from backend.credisense.katman_00_basvuru_paketi import evaluate_application_package
from backend.credisense.katman_02_belge_anlama import ParsedDocuments


def test_complete_application_package_can_continue() -> None:
    parsed = ParsedDocuments(
        document_quality=[
            _quality_item("identity.pdf", "identity"),
            _quality_item("payroll.pdf", "payroll"),
            _quality_item("bank.pdf", "bank_statement"),
        ]
    )
    form = {
        "talep_edilen_kredi_tutari": 250000,
        "vade_ay": 36,
    }

    result = evaluate_application_package(parsed, form)

    assert result.is_complete is True
    assert result.can_continue is True
    assert result.quality_score == 1.0
    assert result.missing_required_documents == []
    assert result.missing_required_form_fields == []


def test_missing_required_document_stops_package_flow() -> None:
    parsed = ParsedDocuments(
        document_quality=[
            _quality_item("identity.pdf", "identity"),
            _quality_item("bank.pdf", "bank_statement"),
        ]
    )

    result = evaluate_application_package(parsed, {})

    assert result.is_complete is False
    assert result.can_continue is False
    assert result.missing_required_documents == ["payroll"]
    assert "talep_edilen_kredi_tutari" in result.missing_required_form_fields
    assert result.quality_score < 1.0


def _quality_item(file_name: str, document_type: str) -> dict:
    return {
        "file_name": file_name,
        "document_type": document_type,
        "confidence": 1.0,
        "missing_fields": [],
        "warnings": [],
        "pdf_extraction": {"ok": True, "page_count": 1, "extractor": "pymupdf", "error": ""},
    }
