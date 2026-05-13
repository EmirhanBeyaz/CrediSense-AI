from datetime import date

import pytest

from backend.credisense.banka_kararlari import apply_bank_decision
from backend.credisense.odeme_plani import build_payment_plan, update_installment_status


def test_payment_plan_is_created_for_approved_application() -> None:
    approved_record = apply_bank_decision(_application_record(), decision_type="approve")

    payment_plan = build_payment_plan(
        approved_record,
        monthly_interest_rate=0.02,
        first_due_date=date(2026, 6, 15),
    )

    assert payment_plan["loan_id"] == "LOAN-20260512-TEST0001"
    assert payment_plan["principal"] == 250000
    assert payment_plan["term_months"] == 36
    assert len(payment_plan["schedule"]) == 36
    assert payment_plan["schedule"][0]["due_date"] == "2026-06-15"
    assert payment_plan["schedule"][-1]["remaining_principal"] == 0.0
    assert payment_plan["monthly_payment"] > 0
    assert payment_plan["total_interest"] > 0
    assert payment_plan["payment_summary"]["pending_installment_count"] == 36


def test_payment_plan_rejects_not_approved_application() -> None:
    with pytest.raises(ValueError):
        build_payment_plan(_application_record())


def test_payment_plan_rejects_invalid_values() -> None:
    approved_record = apply_bank_decision(_application_record(), decision_type="approve")
    approved_record["credit_request"]["requested_amount"] = 0

    with pytest.raises(ValueError):
        build_payment_plan(approved_record)


def test_payment_plan_updates_installment_status() -> None:
    approved_record = apply_bank_decision(_application_record(), decision_type="approve")
    payment_plan = build_payment_plan(
        approved_record,
        monthly_interest_rate=0.02,
        first_due_date=date(2026, 6, 15),
    )

    updated_plan = update_installment_status(
        payment_plan,
        installment_no=1,
        status="paid",
        paid_date="2026-06-14",
        note="Mobil bankacilik odemesi",
    )

    assert updated_plan["schedule"][0]["status"] == "paid"
    assert updated_plan["schedule"][0]["paid_date"] == "2026-06-14"
    assert updated_plan["payment_summary"]["paid_installment_count"] == 1


def _application_record() -> dict:
    return {
        "application_id": "APP-20260512-TEST0001",
        "current_status": {
            "status_code": "MANUAL_REVIEW",
            "status_text": "Uzman incelemesinde",
            "is_final": False,
        },
        "credit_request": {
            "requested_amount": 250000,
            "term_months": 36,
        },
        "status_history": [],
    }
