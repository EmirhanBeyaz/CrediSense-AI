from datetime import date

import pytest

from backend.credisense.banka_kararlari import apply_bank_decision
from backend.credisense.odeme_plani import (
    build_payment_plan,
    close_plan_with_principal_payoff,
    remaining_principal_for_plan,
    suggest_interest_offer,
    update_installment_status,
)


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


def test_payment_plan_assigns_interest_from_application_risk() -> None:
    application = _application_record()
    application["analysis_result"] = {"risk_level": "Yüksek", "risk_score": 0.75}
    approved_record = apply_bank_decision(application, decision_type="approve")

    interest_offer = suggest_interest_offer(approved_record)
    payment_plan = build_payment_plan(approved_record, first_due_date=date(2026, 6, 15))

    assert 0.0185 <= interest_offer["assigned_monthly_interest_rate"] <= 0.0425
    assert payment_plan["monthly_interest_rate"] == interest_offer["assigned_monthly_interest_rate"]
    assert payment_plan["interest_policy"]["rate_source"] == "system"
    assert payment_plan["monthly_payment"] > 0


def test_payment_plan_uses_expert_credit_offer() -> None:
    approved_record = apply_bank_decision(
        _application_record(),
        decision_type="approve",
        credit_offer={
            "approved_amount": 200000,
            "term_months": 24,
            "monthly_interest_rate": 0.035,
        },
    )

    payment_plan = build_payment_plan(approved_record, first_due_date=date(2026, 6, 15))

    assert payment_plan["principal"] == 200000
    assert payment_plan["term_months"] == 24
    assert payment_plan["monthly_interest_rate"] == 0.035
    assert payment_plan["credit_offer"]["source"] == "expert_offer"


def test_payment_plan_closes_with_principal_only_payoff() -> None:
    approved_record = apply_bank_decision(_application_record(), decision_type="approve")
    payment_plan = build_payment_plan(
        approved_record,
        monthly_interest_rate=0.02,
        first_due_date=date(2026, 6, 15),
    )
    first_paid = update_installment_status(
        payment_plan,
        installment_no=1,
        status="paid",
        paid_date="2026-06-15",
        note="İlk taksit",
    )
    remaining_principal = remaining_principal_for_plan(first_paid)

    closed_plan = close_plan_with_principal_payoff(
        first_paid,
        paid_date="2026-07-01",
        note="Ana para kapama",
    )

    assert closed_plan["payment_summary"]["remaining_principal_after_last_payment"] == 0
    assert closed_plan["payment_summary"]["paid_installment_count"] == 36
    assert closed_plan["early_payoff"]["principal_amount"] == remaining_principal
    assert closed_plan["schedule"][1]["payment_amount"] == remaining_principal
    assert closed_plan["schedule"][1]["interest_amount"] == 0
    assert closed_plan["schedule"][2]["payment_amount"] == 0


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
