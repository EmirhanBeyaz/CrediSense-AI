from backend.credisense.rapor_uret import build_markdown_report


def test_markdown_report_includes_document_quality_section() -> None:
    report = build_markdown_report(
        {
            "documents": {},
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
    assert "Dosya: `ornek.pdf`" in report
    assert "PDF okuyucu: `pymupdf`" in report
    assert "Eksik alanlar: Yok" in report

