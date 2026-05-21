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
    assert result["application_package_quality"]["can_continue"] is True
    assert result["application_package_quality"]["missing_required_documents"] == []
    assert result["application_form_quality"]["is_valid"] is False
    assert "talep_edilen_kredi_tutari" in result["application_form_quality"]["missing_required_fields"]
    assert result["consent_quality"]["is_valid"] is False
    assert result["application_status"]["status_code"] == "CONSENT_REQUIRED"
    assert result["user_view"]["show_risk_score"] is False
    assert result["application_id"].startswith("APP-")
    assert result["analysis_id"] == result["application_id"]
    assert result["application_record"]["application_id"] == result["application_id"]
    assert len(result["document_quality"]) == 3
    assert {item["document_type"] for item in result["document_quality"]} == {
        "identity",
        "payroll",
        "bank_statement",
    }
    assert all(item["missing_fields"] == [] for item in result["document_quality"])
    assert all(item["pdf_extraction"]["ok"] is True for item in result["document_quality"])
    assert 0.9 <= result["features"]["document_confidence_score"] < 1.0
    assert result["consistency"]["consistency_score"] == 1.0
    assert result["risk"]["decision_source"] == "baseline_formula"
    assert result["risk"]["decision_summary"]["decision_code"] in {
        "PRE_APPROVED",
        "MANUAL_REVIEW",
        "DEEP_REVIEW",
    }
