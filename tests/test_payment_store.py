from backend.credisense.odeme_deposu import (
    get_payment_plan,
    get_payment_plan_by_application,
    list_payment_plans,
    save_payment_plan,
)


def test_payment_store_saves_and_reads_payment_plan(tmp_path) -> None:
    store_path = tmp_path / "payment_plans.db"
    payment_plan = _payment_plan()

    save_payment_plan(payment_plan, store_path=store_path)

    assert get_payment_plan("LOAN-20260512-TEST0001", store_path=store_path) == payment_plan
    assert get_payment_plan_by_application("APP-20260512-TEST0001", store_path=store_path) == payment_plan
    assert list_payment_plans(store_path=store_path) == [payment_plan]


def _payment_plan() -> dict:
    return {
        "loan_id": "LOAN-20260512-TEST0001",
        "application_id": "APP-20260512-TEST0001",
        "first_due_date": "2026-06-15",
        "principal": 250000,
        "term_months": 36,
        "schedule": [],
    }
