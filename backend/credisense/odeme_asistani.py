from __future__ import annotations

"""Kredi sonrası ödeme asistanı

Bu modül gerçek bir sohbet modeli değildir. Ürün mimarisi için kontrollü bir asistan katmanıdır.
Kullanıcının ödeme planı hakkındaki temel sorularını ödeme planındaki veriye bakarak cevaplar.
"""

from datetime import date


SUPPORTED_QUESTIONS = {
    "summary",
    "next_payment",
    "payment_status",
    "remaining_debt",
    "early_payment",
    "late_payment",
    "overdue_payments",
    "change_due_date",
}


def answer_payment_message(
    payment_plan: dict,
    message: str,
    today: date | None = None,
) -> dict:
    """Serbest metin kullanıcı sorusunu basit kurallarla desteklenen soru tipine çevirir."""

    question_type = _detect_question_type(message)
    answer = answer_payment_question(payment_plan, question_type, today=today)
    answer["original_message"] = message
    return answer


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

    if question_type == "payment_status":
        return _payment_status_answer(payment_plan, current_date)

    if question_type == "remaining_debt":
        return _remaining_debt_answer(payment_plan)

    if question_type == "early_payment":
        return _early_payment_answer(payment_plan)

    if question_type == "late_payment":
        return _late_payment_answer(payment_plan)

    if question_type == "overdue_payments":
        return _overdue_payments_answer(payment_plan, current_date)

    if question_type == "change_due_date":
        return _change_due_date_answer(payment_plan)

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

    next_installment = _next_pending_installment(payment_plan)
    if not next_installment:
        return {
            "intent": "next_payment",
            "message": "Ödeme planında bekleyen taksit görünmüyor.",
            "data": {},
            "requires_bank_support": False,
            "allowed_actions": ["payment_history_view"],
        }

    due_date = date.fromisoformat(next_installment["due_date"])
    if due_date < today:
        day_count = (today - due_date).days
        message = (
            f"{next_installment['installment_no']}. taksitin {next_installment['due_date']} tarihinde "
            f"{next_installment['payment_amount']:.2f} TL idi ve {day_count} gün gecikmiş görünüyor."
        )
        allowed_actions = ["payment_screen_open", "bank_support_request"]
        requires_bank_support = True
    else:
        message = (
            f"Sıradaki taksitin {next_installment['due_date']} tarihinde "
            f"{next_installment['payment_amount']:.2f} TL olarak görünüyor."
        )
        allowed_actions = ["payment_screen_open", "payment_plan_view"]
        requires_bank_support = False

    return {
        "intent": "next_payment",
        "message": message,
        "data": next_installment,
        "requires_bank_support": requires_bank_support,
        "allowed_actions": allowed_actions,
    }


def _payment_status_answer(payment_plan: dict, today: date) -> dict:
    """Ödeme planının genel durumunu özetler."""

    schedule = payment_plan.get("schedule", [])
    paid_count = len([item for item in schedule if item.get("status") == "paid"])
    overdue_items = _overdue_installments(payment_plan, today)
    pending_count = len(schedule) - paid_count
    remaining_debt = _remaining_principal(payment_plan)

    if overdue_items:
        message = (
            f"{len(overdue_items)} taksit gecikmiş görünüyor. "
            f"Tahmini kalan ana para {remaining_debt:.2f} TL."
        )
        allowed_actions = ["payment_screen_open", "bank_support_request"]
    else:
        message = (
            f"{paid_count} taksit ödenmiş, {pending_count} taksit bekliyor. "
            f"Tahmini kalan ana para {remaining_debt:.2f} TL."
        )
        allowed_actions = ["payment_plan_view", "payment_history_view"]

    return {
        "intent": "payment_status",
        "message": message,
        "data": {
            "paid_installment_count": paid_count,
            "pending_installment_count": pending_count,
            "overdue_installment_count": len(overdue_items),
            "remaining_principal": remaining_debt,
        },
        "requires_bank_support": bool(overdue_items),
        "allowed_actions": allowed_actions,
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


def _overdue_payments_answer(payment_plan: dict, today: date) -> dict:
    """Gecikmiş taksitleri listeler."""

    overdue_items = _overdue_installments(payment_plan, today)
    if not overdue_items:
        return {
            "intent": "overdue_payments",
            "message": "Bugün itibarıyla gecikmiş taksit görünmüyor.",
            "data": {"overdue_installments": []},
            "requires_bank_support": False,
            "allowed_actions": ["payment_plan_view"],
        }

    total_overdue_amount = round(sum(item.get("payment_amount", 0) for item in overdue_items), 2)
    return {
        "intent": "overdue_payments",
        "message": (
            f"{len(overdue_items)} gecikmiş taksit ve toplam {total_overdue_amount:.2f} TL "
            "ödenmemiş tutar görünüyor."
        ),
        "data": {
            "overdue_installments": overdue_items,
            "total_overdue_amount": total_overdue_amount,
        },
        "requires_bank_support": True,
        "allowed_actions": ["payment_screen_open", "bank_support_request"],
    }


def _change_due_date_answer(payment_plan: dict) -> dict:
    """Taksit tarihi değişikliği için güvenli yönlendirme yapar."""

    return {
        "intent": "change_due_date",
        "message": (
            "Taksit tarihi değişikliği banka onayı gerektirir. Talep oluşturabilirsin; "
            "banka uygunluk ve sözleşme koşullarına göre değerlendirme yapar."
        ),
        "data": {
            "loan_id": payment_plan.get("loan_id", ""),
        },
        "requires_bank_support": True,
        "allowed_actions": ["bank_support_request", "due_date_change_request"],
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


def _next_pending_installment(payment_plan: dict) -> dict | None:
    """İlk ödenmemiş taksiti bulur. Gecikmiş taksit varsa önce onu döndürür."""

    for installment in payment_plan.get("schedule", []):
        if installment.get("status") == "paid":
            continue
        return installment

    return None


def _overdue_installments(payment_plan: dict, today: date) -> list[dict]:
    """Bugüne göre gecikmiş taksitleri bulur."""

    overdue_items: list[dict] = []
    for installment in payment_plan.get("schedule", []):
        if installment.get("status") == "paid":
            continue

        due_date = date.fromisoformat(installment["due_date"])
        if due_date < today or installment.get("status") == "overdue":
            item = dict(installment)
            item["overdue_day_count"] = max(0, (today - due_date).days)
            overdue_items.append(item)

    return overdue_items


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


def _detect_question_type(message: str) -> str:
    """Basit anahtar kelimelerle kullanıcı sorusunu sınıflandırır."""

    text = _normalize_text(message)

    if any(word in text for word in ["ozet", "plan", "taksitler", "summary"]):
        return "summary"
    if any(word in text for word in ["siradaki", "sonraki", "ne zaman", "next", "tarih"]):
        return "next_payment"
    if any(word in text for word in ["durum", "status", "odemelerim"]):
        return "payment_status"
    if any(word in text for word in ["kalan", "borc", "remaining"]):
        return "remaining_debt"
    if any(word in text for word in ["erken", "kapama", "early"]):
        return "early_payment"
    if any(word in text for word in ["gecik", "odenmedi", "late", "overdue"]):
        return "overdue_payments"
    if any(word in text for word in ["ertele", "degistir", "gunu", "change"]):
        return "change_due_date"

    return "unknown"


def _normalize_text(value: str) -> str:
    """Türkçe karakter ve boşluk farklarını azaltır."""

    translation_table = str.maketrans("ÇĞİÖŞÜçğıöşü", "CGIOSUcgiosu")
    normalized = value.translate(translation_table).lower()
    return " ".join(normalized.split())
