from datetime import date

from backend.credisense.odeme_asistani import answer_payment_question


def test_payment_assistant_returns_summary() -> None:
    answer = answer_payment_question(_payment_plan(), "summary")

    assert answer["intent"] == "summary"
    assert answer["data"]["principal"] == 250000
    assert answer["requires_bank_support"] is False


def test_payment_assistant_returns_next_payment() -> None:
    answer = answer_payment_question(
        _payment_plan(),
        "next_payment",
        today=date(2026, 6, 1),
    )

    assert answer["intent"] == "next_payment"
    assert answer["data"]["installment_no"] == 1
    assert answer["data"]["due_date"] == "2026-06-15"
    assert "payment_screen_open" in answer["allowed_actions"]


def test_payment_assistant_early_payment_requires_bank_support() -> None:
    answer = answer_payment_question(_payment_plan(), "early_payment")

    assert answer["intent"] == "early_payment"
    assert answer["requires_bank_support"] is True
    assert "early_payment_request" in answer["allowed_actions"]


def test_payment_assistant_unknown_question_is_safe() -> None:
    answer = answer_payment_question(_payment_plan(), "change_due_date")

    assert answer["intent"] == "unknown"
    assert answer["requires_bank_support"] is True
    assert "summary" in answer["data"]["supported_questions"]


def _payment_plan() -> dict:
    return {
        "loan_id": "LOAN-20260512-TEST0001",
        "principal": 250000,
        "term_months": 36,
        "monthly_payment": 9810.55,
        "total_payment": 353179.8,
        "total_interest": 103179.8,
        "schedule": [
            {
                "installment_no": 1,
                "due_date": "2026-06-15",
                "payment_amount": 9810.55,
                "principal_amount": 4810.55,
                "interest_amount": 5000,
                "remaining_principal": 245189.45,
                "status": "pending",
            }
        ],
    }
