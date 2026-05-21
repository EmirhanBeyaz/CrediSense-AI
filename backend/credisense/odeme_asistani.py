from __future__ import annotations

"""Kredi sonrası ödeme asistanı

Bu modül gerçek bir sohbet modeli değildir. Ürün mimarisi için kontrollü bir asistan katmanıdır.
Kullanıcının ödeme planı hakkındaki temel sorularını ödeme planındaki veriye bakarak cevaplar.
"""

from datetime import date


SUPPORTED_QUESTIONS = {
    "summary",
    "next_payment",
    "pending_installments",
    "payment_status",
    "remaining_debt",
    "early_payment",
    "late_payment",
    "overdue_payments",
    "change_due_date",
    "monthly_payment",
    "total_cost",
    "installment_count",
    "wallet_balance",
    "bank_support",
}


def answer_payment_message(
    payment_plan: dict,
    message: str,
    today: date | None = None,
    wallet: dict | None = None,
) -> dict:
    """Serbest metin kullanıcı sorusunu basit kurallarla desteklenen soru tipine çevirir."""

    question_type = _detect_question_type(message)
    answer = answer_payment_question(payment_plan, question_type, today=today, wallet=wallet)
    answer["original_message"] = message
    return answer


def answer_payment_question(
    payment_plan: dict,
    question_type: str,
    today: date | None = None,
    wallet: dict | None = None,
) -> dict:
    """Ödeme planına göre kullanıcı sorusuna kontrollü cevap üretir."""

    current_date = today or date.today()

    if question_type == "summary":
        return _summary_answer(payment_plan, wallet=wallet)

    if question_type == "next_payment":
        return _next_payment_answer(payment_plan, current_date, wallet=wallet)

    if question_type == "pending_installments":
        return _pending_installments_answer(payment_plan)

    if question_type == "payment_status":
        return _payment_status_answer(payment_plan, current_date)

    if question_type == "remaining_debt":
        return _remaining_debt_answer(payment_plan)

    if question_type == "early_payment":
        return _early_payment_answer(payment_plan, wallet=wallet)

    if question_type == "late_payment":
        return _late_payment_answer(payment_plan)

    if question_type == "overdue_payments":
        return _overdue_payments_answer(payment_plan, current_date)

    if question_type == "change_due_date":
        return _change_due_date_answer(payment_plan)

    if question_type == "monthly_payment":
        return _monthly_payment_answer(payment_plan)

    if question_type == "total_cost":
        return _total_cost_answer(payment_plan)

    if question_type == "installment_count":
        return _installment_count_answer(payment_plan)

    if question_type == "wallet_balance":
        return _wallet_balance_answer(payment_plan, wallet=wallet)

    if question_type == "bank_support":
        return _bank_support_answer(payment_plan)

    return _unknown_answer(question_type)


def _summary_answer(payment_plan: dict, wallet: dict | None = None) -> dict:
    """Kredi ödeme planının kısa özetini verir."""

    wallet_balance = _wallet_balance(wallet)
    wallet_text = f" Cüzdan bakiyen {_format_money(wallet_balance)}." if wallet is not None else ""
    return {
        "intent": "summary",
        "message": (
            f"Kredi tutarın {payment_plan.get('principal', 0):.2f} TL, "
            f"vaden {payment_plan.get('term_months', 0)} ay ve tahmini aylık taksitin "
            f"{payment_plan.get('monthly_payment', 0):.2f} TL.{wallet_text}"
        ),
        "data": {
            "principal": payment_plan.get("principal", 0),
            "term_months": payment_plan.get("term_months", 0),
            "monthly_payment": payment_plan.get("monthly_payment", 0),
            "total_payment": payment_plan.get("total_payment", 0),
            "total_interest": payment_plan.get("total_interest", 0),
            "wallet_balance": wallet_balance if wallet is not None else None,
        },
        "requires_bank_support": False,
        "allowed_actions": ["payment_plan_view", "wallet_view"],
    }


def _next_payment_answer(payment_plan: dict, today: date, wallet: dict | None = None) -> dict:
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
    wallet_balance = _wallet_balance(wallet)
    can_pay_from_wallet = wallet is not None and wallet_balance >= float(next_installment.get("payment_amount", 0))
    wallet_text = ""
    if wallet is not None:
        wallet_text = (
            f" Cüzdan bakiyen {_format_money(wallet_balance)} ve bu taksiti ödemeye yeterli."
            if can_pay_from_wallet
            else f" Cüzdan bakiyen {_format_money(wallet_balance)}; bu taksit için bakiye yüklemen gerekiyor."
        )

    if due_date < today:
        day_count = (today - due_date).days
        message = (
            f"{next_installment['installment_no']}. taksitin {next_installment['due_date']} tarihinde "
            f"{next_installment['payment_amount']:.2f} TL idi ve {day_count} gün gecikmiş görünüyor.{wallet_text}"
        )
        allowed_actions = ["payment_screen_open", "bank_support_request"]
        requires_bank_support = True
    else:
        message = (
            f"Sıradaki taksitin {next_installment['due_date']} tarihinde "
            f"{next_installment['payment_amount']:.2f} TL olarak görünüyor.{wallet_text}"
        )
        allowed_actions = ["payment_screen_open", "payment_plan_view", "wallet_view"]
        requires_bank_support = False

    return {
        "intent": "next_payment",
        "message": message,
        "data": {
            **next_installment,
            "wallet_balance": wallet_balance if wallet is not None else None,
            "can_pay_from_wallet": can_pay_from_wallet,
        },
        "requires_bank_support": requires_bank_support,
        "allowed_actions": allowed_actions,
    }


def _pending_installments_answer(payment_plan: dict) -> dict:
    """Bekleyen taksit olup olmadigini net sekilde soyler."""

    pending_installments = [
        installment
        for installment in payment_plan.get("schedule", [])
        if installment.get("status") != "paid"
    ]
    if not pending_installments:
        return {
            "intent": "pending_installments",
            "message": "Ödeme planında bekleyen taksit görünmüyor. Tüm taksitler ödenmiş veya plan kapanmış görünüyor.",
            "data": {
                "pending_installment_count": 0,
                "next_installment": None,
            },
            "requires_bank_support": False,
            "allowed_actions": ["payment_history_view", "payment_plan_view"],
        }

    next_installment = pending_installments[0]
    return {
        "intent": "pending_installments",
        "message": (
            f"{len(pending_installments)} bekleyen taksit görünüyor. "
            f"Sıradaki taksit {next_installment['due_date']} tarihinde "
            f"{next_installment['payment_amount']:.2f} TL."
        ),
        "data": {
            "pending_installment_count": len(pending_installments),
            "next_installment": next_installment,
        },
        "requires_bank_support": False,
        "allowed_actions": ["payment_screen_open", "payment_plan_view"],
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


def _early_payment_answer(payment_plan: dict, wallet: dict | None = None) -> dict:
    """Kalan ana parayi tek seferde kapatma bilgisini verir."""

    remaining_debt = _remaining_principal(payment_plan)
    wallet_balance = _wallet_balance(wallet)
    if remaining_debt <= 0:
        return {
            "intent": "early_payment",
            "message": "Kapatılacak kalan ana para görünmüyor. Ödeme planı kapanmış durumda.",
            "data": {
                "estimated_remaining_principal": 0,
                "wallet_balance": wallet_balance if wallet is not None else None,
                "can_pay_from_wallet": False,
            },
            "requires_bank_support": False,
            "allowed_actions": ["payment_history_view"],
        }

    if wallet is not None:
        can_pay = wallet_balance >= remaining_debt
        missing_amount = round(max(0, remaining_debt - wallet_balance), 2)
        message = (
            f"Kalan ana para {_format_money(remaining_debt)}. "
            f"Cüzdan bakiyen {_format_money(wallet_balance)}. "
            f"{'Bu tutarı faiz eklenmeden tek seferde kapatabilirsin.' if can_pay else f'Kapatmak için {_format_money(missing_amount)} daha yüklemen gerekiyor.'}"
        )
        return {
            "intent": "early_payment",
            "message": message,
            "data": {
                "estimated_remaining_principal": remaining_debt,
                "wallet_balance": wallet_balance,
                "missing_amount": missing_amount,
                "can_pay_from_wallet": can_pay,
                "interest_policy": "future_interest_waived",
            },
            "requires_bank_support": False,
            "allowed_actions": ["wallet_view", "payment_screen_open"],
        }

    return {
        "intent": "early_payment",
        "message": (
            f"Erken ödeme için plan üzerindeki tahmini kalan ana para {remaining_debt:.2f} TL. "
            "Müşteri cüzdanı bağlıysa kalan ana para faiz eklenmeden tek seferde kapatılabilir."
        ),
        "data": {
            "estimated_remaining_principal": remaining_debt,
        },
        "requires_bank_support": False,
        "allowed_actions": ["payment_screen_open"],
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


def _monthly_payment_answer(payment_plan: dict) -> dict:
    """Aylik taksit tutarini ve vadeyi ozetler."""

    monthly_payment = float(payment_plan.get("monthly_payment", 0))
    term_months = int(float(payment_plan.get("term_months", 0) or 0))
    return {
        "intent": "monthly_payment",
        "message": (
            f"Bu kredi icin aylik taksit tutari {_format_money(monthly_payment)} olarak gorunuyor. "
            f"Plan vadesi {term_months} ay."
        ),
        "data": {
            "monthly_payment": monthly_payment,
            "term_months": term_months,
        },
        "requires_bank_support": False,
        "allowed_actions": ["payment_plan_view"],
    }


def _total_cost_answer(payment_plan: dict) -> dict:
    """Toplam geri odeme ve faiz bilgisini verir."""

    total_payment = float(payment_plan.get("total_payment", 0))
    total_interest = float(payment_plan.get("total_interest", 0))
    principal = float(payment_plan.get("principal", 0))
    if total_payment <= 0:
        schedule = payment_plan.get("schedule", [])
        total_payment = round(sum(float(item.get("payment_amount", 0)) for item in schedule), 2)
        total_interest = round(max(0, total_payment - principal), 2)

    return {
        "intent": "total_cost",
        "message": (
            f"Plan toplam geri odemeyi {_format_money(total_payment)} olarak gosteriyor. "
            f"Bunun yaklasik {_format_money(total_interest)} kismi faiz/maliyet kalemi olarak hesaplanmis."
        ),
        "data": {
            "principal": principal,
            "total_payment": total_payment,
            "total_interest": total_interest,
        },
        "requires_bank_support": False,
        "allowed_actions": ["payment_plan_view"],
    }


def _installment_count_answer(payment_plan: dict) -> dict:
    """Kalan, odenen ve gecikmis taksit sayilarini verir."""

    schedule = payment_plan.get("schedule", [])
    paid_count = len([item for item in schedule if item.get("status") == "paid"])
    overdue_count = len([item for item in schedule if item.get("status") == "overdue"])
    remaining_count = len(schedule) - paid_count
    return {
        "intent": "installment_count",
        "message": (
            f"Toplam {len(schedule)} taksitin {paid_count} tanesi odenmis gorunuyor. "
            f"Kalan taksit sayisi {remaining_count}. Gecikmis taksit sayisi {overdue_count}."
        ),
        "data": {
            "total_installment_count": len(schedule),
            "paid_installment_count": paid_count,
            "remaining_installment_count": remaining_count,
            "overdue_installment_count": overdue_count,
        },
        "requires_bank_support": overdue_count > 0,
        "allowed_actions": ["payment_plan_view", "payment_history_view"],
    }


def _wallet_balance_answer(payment_plan: dict, wallet: dict | None = None) -> dict:
    """Cuzdan bakiyesi ve siradaki taksiti odeme yeterliligini soyler."""

    balance = _wallet_balance(wallet)
    next_installment = _next_pending_installment(payment_plan)
    if not next_installment:
        return {
            "intent": "wallet_balance",
            "message": f"Cüzdan bakiyen {_format_money(balance)}. Bekleyen taksit görünmüyor.",
            "data": {
                "wallet_balance": balance,
                "can_pay_next_installment": False,
            },
            "requires_bank_support": False,
            "allowed_actions": ["wallet_view", "payment_history_view"],
        }

    next_amount = float(next_installment.get("payment_amount", 0))
    can_pay = balance >= next_amount
    if can_pay:
        message = (
            f"Cüzdan bakiyen {_format_money(balance)}. "
            f"Sıradaki {next_installment['installment_no']}. taksit {_format_money(next_amount)} ve bakiyen yeterli."
        )
    else:
        missing_amount = round(next_amount - balance, 2)
        message = (
            f"Cüzdan bakiyen {_format_money(balance)}. "
            f"Sıradaki taksit {_format_money(next_amount)}; ödeme için {_format_money(missing_amount)} daha yüklemen gerekiyor."
        )

    return {
        "intent": "wallet_balance",
        "message": message,
        "data": {
            "wallet_balance": balance,
            "next_installment_amount": next_amount,
            "can_pay_next_installment": can_pay,
        },
        "requires_bank_support": False,
        "allowed_actions": ["wallet_view", "payment_screen_open"],
    }


def _bank_support_answer(payment_plan: dict) -> dict:
    """Banka destegi gerektiren konular icin kontrollu yonlendirme yapar."""

    return {
        "intent": "bank_support",
        "message": (
            "Bu konu banka onayi veya musteri temsilcisi islemi gerektirebilir. "
            "Erken kapama, taksit tarihi degisikligi, yapilandirma ve itiraz gibi talepler icin banka destek kaydi acilmalidir."
        ),
        "data": {
            "loan_id": payment_plan.get("loan_id", ""),
        },
        "requires_bank_support": True,
        "allowed_actions": ["bank_support_request"],
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

    if any(phrase in text for phrase in ["bekleyen taksit", "bekleyen odeme", "taksitim var mi", "odeme var mi", "bekleyen borc"]):
        return "pending_installments"
    if any(word in text for word in ["cuzdan", "bakiye", "para yukle", "bakiyem", "kartla ode", "odeyebilir miyim", "yeterli mi"]):
        return "wallet_balance"
    if any(word in text for word in ["siradaki", "sonraki", "ne zaman", "next", "tarih"]):
        return "next_payment"
    if any(word in text for word in ["aylik", "taksitim ne kadar", "taksit tutari"]):
        return "monthly_payment"
    if any(word in text for word in ["toplam", "maliyet", "faiz", "geri odeme"]):
        return "total_cost"
    if any(word in text for word in ["kac taksit", "kac odeme", "kalan taksit", "taksitim kaldi", "taksit sayisi"]):
        return "installment_count"
    if any(word in text for word in ["ozet", "plan", "taksitler", "summary"]):
        return "summary"
    if any(word in text for word in ["durum", "status", "odemelerim"]):
        return "payment_status"
    if any(word in text for word in ["kalan", "borc", "remaining"]):
        return "remaining_debt"
    if any(word in text for word in ["erken", "kapama", "kapatma", "kapatabilir", "tek sefer", "tek odeme", "early"]):
        return "early_payment"
    if any(word in text for word in ["gecik", "odenmedi", "late", "overdue"]):
        return "overdue_payments"
    if any(word in text for word in ["ertele", "degistir", "gunu", "change"]):
        return "change_due_date"
    if any(word in text for word in ["destek", "temsilci", "itiraz", "yardim", "banka"]):
        return "bank_support"

    return "unknown"


def _normalize_text(value: str) -> str:
    """Türkçe karakter ve boşluk farklarını azaltır."""

    translation_table = str.maketrans("ÇĞİÖŞÜçğıöşü", "CGIOSUcgiosu")
    normalized = value.translate(translation_table).lower()
    return " ".join(normalized.split())


def _format_money(value: float) -> str:
    """TL tutarini arayuzde okunur sekilde bicimlendirir."""

    rounded_value = round(float(value), 2)
    if rounded_value.is_integer():
        formatted = f"{int(rounded_value):,}".replace(",", ".")
    else:
        formatted = f"{rounded_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} TL"


def _wallet_balance(wallet: dict | None) -> float:
    if not wallet:
        return 0.0
    try:
        return round(float(wallet.get("balance", 0) or 0), 2)
    except (TypeError, ValueError):
        return 0.0
