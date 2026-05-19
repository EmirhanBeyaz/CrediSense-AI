from datetime import date

from backend.credisense.odeme_asistani import answer_payment_message, answer_payment_question


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
    answer = answer_payment_question(_payment_plan(), "not_supported_yet")

    assert answer["intent"] == "unknown"
    assert answer["requires_bank_support"] is True
    assert "summary" in answer["data"]["supported_questions"]


def test_payment_assistant_returns_payment_status() -> None:
    plan = _payment_plan()
    plan["schedule"][0]["status"] = "paid"

    answer = answer_payment_question(plan, "payment_status", today=date(2026, 6, 20))

    assert answer["intent"] == "payment_status"
    assert answer["data"]["paid_installment_count"] == 1
    assert answer["requires_bank_support"] is False


def test_payment_assistant_detects_overdue_payment() -> None:
    answer = answer_payment_question(
        _payment_plan(),
        "overdue_payments",
        today=date(2026, 6, 20),
    )

    assert answer["intent"] == "overdue_payments"
    assert answer["data"]["total_overdue_amount"] == 9810.55
    assert answer["requires_bank_support"] is True


def test_payment_assistant_classifies_free_text_message() -> None:
    answer = answer_payment_message(
        _payment_plan(),
        "Kalan borcum ne kadar?",
        today=date(2026, 6, 1),
    )

    assert answer["intent"] == "remaining_debt"
    assert answer["original_message"] == "Kalan borcum ne kadar?"


def test_payment_assistant_returns_total_cost() -> None:
    answer = answer_payment_message(_payment_plan(), "Toplam geri odeme tutarim ne kadar?")

    assert answer["intent"] == "total_cost"
    assert answer["data"]["total_payment"] == 353179.8
    assert answer["requires_bank_support"] is False


def test_payment_assistant_returns_installment_count() -> None:
    answer = answer_payment_message(_payment_plan(), "Kac taksitim kaldi?")

    assert answer["intent"] == "installment_count"
    assert answer["data"]["remaining_installment_count"] == 1


def test_payment_assistant_returns_monthly_payment() -> None:
    answer = answer_payment_message(_payment_plan(), "Aylik taksitim ne kadar?")

    assert answer["intent"] == "monthly_payment"
    assert answer["data"]["monthly_payment"] == 9810.55


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
