from pathlib import Path

from backend.credisense.analiz_akisi import analyze_documents


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DOCUMENTS = [
    PROJECT_ROOT / "ornek_belgeler" / "Sentetik Kimlik Belgesi Ornegi.pdf",
    PROJECT_ROOT / "ornek_belgeler" / "Sentetik Maas Bordrosu Ornegi.pdf",
    PROJECT_ROOT / "ornek_belgeler" / "Sentetik Banka Hesap Dokumu Ornegi.pdf",
]
SAMPLE_DATASET = PROJECT_ROOT / "veri" / "sentetik_kredi_basvuru_veri_seti.csv"


def test_sample_documents_produce_expected_risk_summary() -> None:
    result = analyze_documents(SAMPLE_DOCUMENTS, dataset_path=SAMPLE_DATASET)

    assert result["documents"]["identity"]["full_name"] == "Deniz Kaya"
    assert result["documents"]["bank_statement"]["transaction_count"] == 18
    assert len(result["document_quality"]) == 3
    assert {item["document_type"] for item in result["document_quality"]} == {
        "identity",
        "payroll",
        "bank_statement",
    }
    assert all(item["missing_fields"] == [] for item in result["document_quality"])
    assert all(item["pdf_extraction"]["ok"] is True for item in result["document_quality"])
    assert result["features"]["document_confidence_score"] == 1.0
    assert result["consistency"]["consistency_score"] == 1.0
    assert result["risk"]["decision_source"] == "baseline_formula"
    assert result["risk"]["decision_summary"]["decision_code"] in {
        "PRE_APPROVED",
        "MANUAL_REVIEW",
        "DEEP_REVIEW",
    }
