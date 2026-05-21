import pytest

from backend.credisense.banka_kararlari import allowed_bank_decisions, apply_bank_decision


def test_bank_decision_approves_application_record() -> None:
    updated_record = apply_bank_decision(
        _application_record(),
        decision_type="approve",
        note="Gelir ve belge kontrolleri uygun.",
        actor="bank_user_1",
    )

    assert updated_record["current_status"]["status_code"] == "APPROVED"
    assert updated_record["current_status"]["is_final"] is True
    assert updated_record["bank_decision"]["decision_type"] == "approve"
    assert updated_record["bank_decision"]["actor"] == "bank_user_1"
    assert updated_record["user_notification"]["allowed_actions"] == [
        "loan_terms_view",
        "payment_plan_view",
    ]
    assert len(updated_record["status_history"]) == 2


def test_bank_decision_requests_extra_document() -> None:
    updated_record = apply_bank_decision(
        _application_record(),
        decision_type="request_extra_document",
        requested_documents=["Güncel gelir belgesi"],
    )

    assert updated_record["current_status"]["status_code"] == "EXTRA_DOCUMENT_REQUESTED"
    assert updated_record["current_status"]["is_final"] is False
    assert updated_record["bank_decision"]["requested_documents"] == ["Güncel gelir belgesi"]
    assert updated_record["user_notification"]["allowed_actions"] == ["document_upload"]


def test_bank_decision_stores_expert_credit_offer_on_approval() -> None:
    updated_record = apply_bank_decision(
        _application_record(),
        decision_type="approve",
        credit_offer={
            "approved_amount": 210000,
            "term_months": 24,
            "monthly_interest_rate": 0.031,
        },
    )

    assert updated_record["bank_decision"]["credit_offer"] == {
        "approved_amount": 210000,
        "term_months": 24,
        "monthly_interest_rate": 0.031,
    }


def test_bank_decision_rejects_invalid_decision_type() -> None:
    with pytest.raises(ValueError):
        apply_bank_decision(_application_record(), decision_type="unknown")


def test_final_application_cannot_receive_new_bank_decision() -> None:
    approved_record = apply_bank_decision(_application_record(), decision_type="approve")

    with pytest.raises(ValueError):
        apply_bank_decision(approved_record, decision_type="reject")


def test_allowed_bank_decisions_depend_on_status() -> None:
    assert allowed_bank_decisions("CONSENT_REQUIRED") == []
    assert allowed_bank_decisions("APPROVED") == []
    assert allowed_bank_decisions("DOCUMENT_REVISION_REQUIRED") == ["request_extra_document", "reject"]
    assert "send_to_deep_review" in allowed_bank_decisions("MANUAL_REVIEW")


def _application_record() -> dict:
    return {
        "application_id": "APP-20260512-TEST0001",
        "current_status": {
            "status_code": "MANUAL_REVIEW",
            "status_text": "Uzman incelemesinde",
            "is_final": False,
            "next_action": "Banka uzmanının başvuruyu incelemesini bekle.",
        },
        "status_history": [
            {
                "status_code": "MANUAL_REVIEW",
                "note": "Banka uzmanının başvuruyu incelemesini bekle.",
                "actor": "system",
                "created_at": "2026-05-12T22:05:46",
            }
        ],
    }
