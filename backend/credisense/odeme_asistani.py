from __future__ import annotations

"""Kredi sonrası ödeme asistanı

Bu modül gerçek bir sohbet modeli değildir. İlk ürün mimarisi için kontrollü bir asistan
katmanıdır. Kullanıcının ödeme planı hakkında sorabileceği temel sorulara, ödeme planındaki
verilere bakarak cevap verir.
"""

from datetime import date


SUPPORTED_QUESTIONS = {
    "summary",
    "next_payment",
    "remaining_debt",
    "early_payment",
    "late_payment",
}


def answer_payment_question(
    payment_plan: dict,
    question_type: str,
    today: date | None = None,
) -> dict:
    """Ödeme planına göre kullanıcı sorusuna kontrollü cevap üretir."""

    current_date = today or date.today()

    if question_type == "summary":
        return _summary_answer(payment_plan)

    if question_type == "next_payment":
        return _next_payment_answer(payment_plan, current_date)

    if question_type == "remaining_debt":
        return _remaining_debt_answer(payment_plan)

    if question_type == "early_payment":
        return _early_payment_answer(payment_plan)

    if question_type == "late_payment":
        return _late_payment_answer(payment_plan)

    return _unknown_answer(question_type)


def _summary_answer(payment_plan: dict) -> dict:
    """Kredi ödeme planının kısa özetini verir."""

    return {
        "intent": "summary",
        "message": (
            f"Kredi tutarın {payment_plan.get('principal', 0):.2f} TL, "
            f"vaden {payment_plan.get('term_months', 0)} ay ve tahmini aylık taksitin "
            f"{payment_plan.get('monthly_payment', 0):.2f} TL."
        ),
        "data": {
            "principal": payment_plan.get("principal", 0),
            "term_months": payment_plan.get("term_months", 0),
            "monthly_payment": payment_plan.get("monthly_payment", 0),
            "total_payment": payment_plan.get("total_payment", 0),
            "total_interest": payment_plan.get("total_interest", 0),
        },
        "requires_bank_support": False,
        "allowed_actions": ["payment_plan_view"],
    }


def _next_payment_answer(payment_plan: dict, today: date) -> dict:
    """Ödenmemiş ilk taksiti bulur ve kullanıcıya söyler."""

    next_installment = _next_pending_installment(payment_plan, today)
    if not next_installment:
        return {
            "intent": "next_payment",
            "message": "Ödeme planında bekleyen taksit görünmüyor.",
            "data": {},
            "requires_bank_support": False,
            "allowed_actions": ["payment_history_view"],
        }

    return {
        "intent": "next_payment",
        "message": (
            f"Sıradaki taksitin {next_installment['due_date']} tarihinde "
            f"{next_installment['payment_amount']:.2f} TL olarak görünüyor."
        ),
        "data": next_installment,
        "requires_bank_support": False,
        "allowed_actions": ["payment_screen_open", "payment_plan_view"],
    }


def _remaining_debt_answer(payment_plan: dict) -> dict:
    """Plan üzerindeki kalan ana para bilgisini verir."""

    remaining_debt = _remaining_principal(payment_plan)
    return {
        "intent": "remaining_debt",
        "message": f"Plan üzerindeki tahmini kalan ana para {remaining_debt:.2f} TL görünüyor.",
        "data": {
            "remaining_principal": remaining_debt,
        },
        "requires_bank_support": False,
        "allowed_actions": ["payment_plan_view"],
    }


def _early_payment_answer(payment_plan: dict) -> dict:
    """Erken kapama hakkında güvenli bilgilendirme yapar."""

    remaining_debt = _remaining_principal(payment_plan)
    return {
        "intent": "early_payment",
        "message": (
            f"Erken ödeme için plan üzerindeki tahmini kalan ana para {remaining_debt:.2f} TL. "
            "Net erken kapama tutarı günlük faiz, masraf ve banka politikasına göre değişebilir."
        ),
        "data": {
            "estimated_remaining_principal": remaining_debt,
        },
        "requires_bank_support": True,
        "allowed_actions": ["bank_support_request", "early_payment_request"],
    }


def _late_payment_answer(payment_plan: dict) -> dict:
    """Gecikme durumunda kullanıcıyı banka desteğine yönlendirir."""

    return {
        "intent": "late_payment",
        "message": (
            "Taksit gecikirse gecikme faizi ve kredi kayıtlarına bildirim gibi sonuçlar oluşabilir. "
            "Kesin bilgi ve çözüm seçenekleri için banka desteğine yönlendirilmen gerekir."
        ),
        "data": {
            "loan_id": payment_plan.get("loan_id", ""),
        },
        "requires_bank_support": True,
        "allowed_actions": ["bank_support_request", "payment_screen_open"],
    }


def _unknown_answer(question_type: str) -> dict:
    """Desteklenmeyen soru tipleri için güvenli cevap üretir."""

    return {
        "intent": "unknown",
        "message": f"Bu ödeme sorusu henüz desteklenmiyor: {question_type}",
        "data": {
            "supported_questions": sorted(SUPPORTED_QUESTIONS),
        },
        "requires_bank_support": True,
        "allowed_actions": ["bank_support_request"],
    }


def _next_pending_installment(payment_plan: dict, today: date) -> dict | None:
    """Bugünden sonraki ilk bekleyen taksiti bulur."""

    for installment in payment_plan.get("schedule", []):
        if installment.get("status") == "paid":
            continue

        due_date = date.fromisoformat(installment["due_date"])
        if due_date >= today:
            return installment

    return None


def _remaining_principal(payment_plan: dict) -> float:
    """Ödenmiş taksit bilgisine göre kalan ana parayı tahmin eder."""

    schedule = payment_plan.get("schedule", [])
    if not schedule:
        return 0.0

    paid_installments = [item for item in schedule if item.get("status") == "paid"]
    if not paid_installments:
        return round(float(payment_plan.get("principal", 0)), 2)

    last_paid = paid_installments[-1]
    return round(float(last_paid.get("remaining_principal", 0)), 2)
