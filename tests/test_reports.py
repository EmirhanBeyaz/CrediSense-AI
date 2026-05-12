from backend.credisense.rapor_uret import build_markdown_report


def test_markdown_report_includes_document_quality_section() -> None:
    report = build_markdown_report(
        {
            "application_id": "APP-20260512-TEST0001",
            "application_record": {
                "application_id": "APP-20260512-TEST0001",
            },
            "documents": {},
            "application_package_quality": {
                "is_complete": True,
                "can_continue": True,
                "quality_score": 1.0,
                "missing_required_documents": [],
                "duplicate_document_types": [],
                "missing_required_form_fields": [],
            },
            "application_form_quality": {
                "is_valid": True,
                "quality_score": 1.0,
                "missing_required_fields": [],
                "invalid_fields": [],
                "warnings": [],
            },
            "consent_quality": {
                "is_valid": True,
                "missing_consents": [],
                "rejected_consents": [],
                "warnings": [],
            },
            "application_status": {
                "status_code": "MANUAL_REVIEW",
                "status_text": "Uzman incelemesinde",
                "next_action": "Banka uzmanının başvuruyu incelemesini bekle.",
            },
            "user_view": {
                "message": "Başvurun uzman incelemesine alındı.",
            },
            "bank_view": {
                "recommended_action": "Risk gerekçelerini ve anomalileri manuel incele.",
            },
            "document_quality": [
                {
                    "file_name": "ornek.pdf",
                    "document_type": "identity",
                    "confidence": 1.0,
                    "missing_fields": [],
                    "warnings": [],
                    "pdf_extraction": {"extractor": "pymupdf"},
                }
            ],
            "features": {},
            "consistency": {},
            "risk": {"decision_summary": {}},
        }
    )

    assert "## Belge Okuma Kalitesi" in report
    assert "Başvuru ID: `APP-20260512-TEST0001`" in report
    assert "## Başvuru Durumu" in report
    assert "## Başvuru Paketi Ön Kontrolü" in report
    assert "## Başvuru Formu Doğrulama" in report
    assert "## Onay Kontrolü" in report
    assert "Dosya: `ornek.pdf`" in report
    assert "PDF okuyucu: `pymupdf`" in report
    assert "Eksik alanlar: Yok" in report

