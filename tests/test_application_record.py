from datetime import datetime

from backend.credisense.basvuru_kaydi import (
    append_status_event,
    build_application_record,
    create_application_id,
)


def test_create_application_id_uses_product_format() -> None:
    application_id = create_application_id(datetime(2026, 5, 12, 10, 30))

    assert application_id.startswith("APP-20260512-")
    assert len(application_id) == 21


def test_build_application_record_summarizes_analysis_result() -> None:
    record = build_application_record(_analysis_result(), application_id="APP-20260512-TEST0001")

    assert record["application_id"] == "APP-20260512-TEST0001"
    assert record["current_status"]["status_code"] == "MANUAL_REVIEW"
    assert record["applicant"]["full_name"] == "Deniz Kaya"
    assert record["credit_request"]["requested_amount"] == 250000
    assert record["risk_summary"]["risk_level"] == "Orta"
    assert record["status_history"][0]["actor"] == "system"


def test_append_status_event_adds_new_history_item() -> None:
    record = build_application_record(_analysis_result(), application_id="APP-20260512-TEST0001")

    updated_record = append_status_event(
        record,
        status_code="PRE_APPROVED",
        note="Uzman ön onayı verdi.",
        actor="bank_user",
    )

    assert updated_record["current_status"]["status_code"] == "PRE_APPROVED"
    assert len(updated_record["status_history"]) == 2
    assert updated_record["status_history"][1]["actor"] == "bank_user"


def _analysis_result() -> dict:
    return {
        "documents": {
            "identity": {
                "full_name": "Deniz Kaya",
                "test_id": "11111111110",
                "birth_date": "12.04.1992",
            }
        },
        "application_form": {
            "talep_edilen_kredi_tutari": 250000,
            "vade_ay": 36,
            "beyan_edilen_aylik_gelir": 42350.75,
        },
        "features": {
            "requested_credit_amount": 250000,
            "current_total_debt": 153000,
        },
        "application_status": {
            "status_code": "MANUAL_REVIEW",
            "next_action": "Banka uzmanının başvuruyu incelemesini bekle.",
        },
        "bank_view": {
            "recommended_action": "Risk gerekçelerini ve anomalileri manuel incele.",
        },
        "risk": {
            "risk_score": 0.51,
            "risk_level": "Orta",
            "decision_source": "trained_model",
        },
    }
