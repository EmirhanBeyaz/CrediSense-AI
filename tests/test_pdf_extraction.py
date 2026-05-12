from pathlib import Path

from backend.credisense.katman_01_pdf_okuma import extract_pdf, extract_pdf_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IDENTITY_PDF = PROJECT_ROOT / "ornek_belgeler" / "Sentetik Kimlik Belgesi Ornegi.pdf"


def test_extract_pdf_uses_available_reader_for_sample_pdf() -> None:
    result = extract_pdf(IDENTITY_PDF)

    assert result.extraction_ok is True
    assert result.page_count == 1
    assert result.extractor in {"pymupdf", "builtin"}
    assert "Deniz Kaya" in result.text
    assert result.warnings == []


def test_extract_pdf_text_returns_only_text() -> None:
    text = extract_pdf_text(IDENTITY_PDF)

    assert "Test Kimlik No" in text


def test_extract_pdf_reports_missing_file_without_raising(tmp_path) -> None:
    result = extract_pdf(tmp_path / "missing.pdf")

    assert result.extraction_ok is False
    assert result.extractor == "none"
    assert "FileNotFoundError" in result.error

