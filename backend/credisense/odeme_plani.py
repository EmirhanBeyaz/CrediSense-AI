from __future__ import annotations

"""Kredi ödeme planı üretimi

Bu modül, banka uzmanı tarafından onaylanmış bir başvuru kaydından örnek ödeme planı üretir.
Gerçek bankacılık ürününde faiz oranı, masraf, sigorta ve kampanya gibi alanlar bankanın ana
sisteminden gelmelidir. Buradaki amaç ürün mimarisi için anlaşılır bir ödeme planı katmanı kurmaktır.
"""

import calendar
import re
from datetime import date


MIN_MONTHLY_INTEREST_RATE = 0.0185
MAX_MONTHLY_INTEREST_RATE = 0.0425
DEFAULT_MONTHLY_INTEREST_RATE = 0.025
INSTALLMENT_STATUSES = {"pending", "paid", "overdue"}


def build_payment_plan(
    application_record: dict,
    monthly_interest_rate: float | None = None,
    first_due_date: date | None = None,
) -> dict:
    """Onaylanmış başvuru kaydından taksitli ödeme planı üretir."""

    _ensure_application_is_approved(application_record)

    credit_terms = _credit_terms(application_record, monthly_interest_rate=monthly_interest_rate)
    principal = credit_terms["principal"]
    term_months = credit_terms["term_months"]
    effective_interest_rate = credit_terms["monthly_interest_rate"]

    if principal <= 0:
        raise ValueError("Ödeme planı için kredi tutarı 0'dan büyük olmalıdır.")

    if term_months <= 0:
        raise ValueError("Ödeme planı için vade 0'dan büyük olmalıdır.")

    if effective_interest_rate < 0:
        raise ValueError("Aylık faiz oranı negatif olamaz.")

    due_date = first_due_date or _add_months(date.today(), 1)
    monthly_payment = _monthly_payment(
        principal=principal,
        term_months=term_months,
        monthly_interest_rate=effective_interest_rate,
    )
    schedule = _build_schedule(
        principal=principal,
        term_months=term_months,
        monthly_interest_rate=effective_interest_rate,
        monthly_payment=monthly_payment,
        first_due_date=due_date,
    )

    total_payment = round(sum(item["payment_amount"] for item in schedule), 2)
    total_interest = round(sum(item["interest_amount"] for item in schedule), 2)

    return {
        "loan_id": _loan_id(application_record.get("application_id", "")),
        "application_id": application_record.get("application_id", ""),
        "customer_user_id": application_record.get("owner_user_id", ""),
        "principal": round(principal, 2),
        "term_months": term_months,
        "monthly_interest_rate": round(effective_interest_rate, 4),
        "annual_interest_rate": round(((1 + effective_interest_rate) ** 12) - 1, 4),
        "monthly_payment": monthly_payment,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "first_due_date": due_date.isoformat(),
        "interest_policy": credit_terms["interest_policy"],
        "credit_offer": credit_terms["credit_offer"],
        "schedule": schedule,
        "payment_summary": _payment_summary(schedule, principal=principal),
    }


def suggest_interest_offer(application_record: dict) -> dict:
    """Basvuru riski, tutari ve vadesine gore sistem faiz teklifini uretir."""

    credit_request = application_record.get("credit_request", {})
    principal = _repair_small_requested_amount(_to_float(credit_request.get("requested_amount")), credit_request)
    term_months = int(_to_float(credit_request.get("term_months")))
    risk_score = _risk_score(application_record)
    risk_level = _risk_level(application_record)

    risk_adjustment = _risk_adjustment(risk_level=risk_level, risk_score=risk_score)
    amount_adjustment = 0.003 if principal >= 500_000 else 0.0015 if principal >= 250_000 else 0.0
    term_adjustment = 0.004 if term_months >= 48 else 0.002 if term_months >= 36 else 0.0
    assigned_rate = _clamp_interest_rate(DEFAULT_MONTHLY_INTEREST_RATE + risk_adjustment + amount_adjustment + term_adjustment)

    return {
        "min_monthly_interest_rate": MIN_MONTHLY_INTEREST_RATE,
        "max_monthly_interest_rate": MAX_MONTHLY_INTEREST_RATE,
        "assigned_monthly_interest_rate": round(assigned_rate, 4),
        "assigned_annual_interest_rate": round(((1 + assigned_rate) ** 12) - 1, 4),
        "rate_source": "system",
        "risk_level": risk_level or "Belirsiz",
        "risk_score": round(risk_score, 4),
        "basis": {
            "base_monthly_interest_rate": DEFAULT_MONTHLY_INTEREST_RATE,
            "risk_adjustment": round(risk_adjustment, 4),
            "amount_adjustment": round(amount_adjustment, 4),
            "term_adjustment": round(term_adjustment, 4),
        },
        "reason": (
            "Faiz oranı başvurunun risk seviyesi, talep edilen kredi tutarı ve vade uzunluğu "
            "birlikte değerlendirilerek sistem tarafından atanmıştır."
        ),
    }


def update_installment_status(
    payment_plan: dict,
    installment_no: int,
    status: str,
    paid_date: str = "",
    note: str = "",
) -> dict:
    """Odeme planindaki tek taksitin durumunu gunceller.

    Bu fonksiyon gercek para tahsilati yapmaz. Sadece urun akisinda taksit durumunu takip etmek
    icin plan verisini gunceller.
    """

    if status not in INSTALLMENT_STATUSES:
        valid_statuses = ", ".join(sorted(INSTALLMENT_STATUSES))
        raise ValueError(f"Gecersiz taksit durumu: {status}. Gecerli durumlar: {valid_statuses}")

    updated_plan = dict(payment_plan)
    updated_schedule: list[dict] = []
    installment_found = False

    for installment in payment_plan.get("schedule", []):
        updated_installment = dict(installment)
        if int(updated_installment.get("installment_no", 0)) == int(installment_no):
            installment_found = True
            updated_installment["status"] = status
            updated_installment["paid_date"] = paid_date if status == "paid" else ""
            updated_installment["note"] = note

        updated_schedule.append(updated_installment)

    if not installment_found:
        raise ValueError(f"Taksit bulunamadi: {installment_no}")

    updated_plan["schedule"] = updated_schedule
    updated_plan["payment_summary"] = _payment_summary(
        updated_schedule,
        principal=_to_float(updated_plan.get("principal")),
    )
    return updated_plan


def close_plan_with_principal_payoff(
    payment_plan: dict,
    paid_date: str,
    note: str = "Ana para tek seferde kapatıldı",
) -> dict:
    """Kalan ana parayi faizsiz tek odemeyle kapatir.

    Gelecek vadelerdeki faizler tahsil edilmez. Ilk bekleyen taksit kalan ana para kadar
    kapama odemesi olarak isaretlenir; sonraki taksitler 0 TL ile kapatilmis gorunur.
    """

    remaining_principal = remaining_principal_for_plan(payment_plan)
    if remaining_principal <= 0:
        raise ValueError("Kapatılacak kalan ana para bulunmuyor.")

    updated_plan = dict(payment_plan)
    updated_schedule: list[dict] = []
    payoff_applied = False
    waived_future_interest = 0.0

    for installment in payment_plan.get("schedule", []):
        updated_installment = dict(installment)
        if updated_installment.get("status") == "paid":
            updated_schedule.append(updated_installment)
            continue

        waived_future_interest += _to_float(updated_installment.get("interest_amount"))
        updated_installment["status"] = "paid"
        updated_installment["paid_date"] = paid_date
        updated_installment["note"] = note if not payoff_applied else "Erken ana para kapama ile kapandı"
        updated_installment["interest_amount"] = 0.0
        updated_installment["remaining_principal"] = 0.0

        if not payoff_applied:
            updated_installment["payment_amount"] = round(remaining_principal, 2)
            updated_installment["principal_amount"] = round(remaining_principal, 2)
            updated_installment["payoff_type"] = "principal_only"
            payoff_applied = True
        else:
            updated_installment["payment_amount"] = 0.0
            updated_installment["principal_amount"] = 0.0
            updated_installment["payoff_type"] = "future_installment_closed"

        updated_schedule.append(updated_installment)

    if not payoff_applied:
        raise ValueError("Kapatılacak bekleyen taksit bulunmuyor.")

    updated_plan["schedule"] = updated_schedule
    updated_plan["total_payment"] = round(sum(_to_float(item.get("payment_amount")) for item in updated_schedule), 2)
    updated_plan["total_interest"] = round(sum(_to_float(item.get("interest_amount")) for item in updated_schedule), 2)
    updated_plan["payment_summary"] = _payment_summary(
        updated_schedule,
        principal=_to_float(updated_plan.get("principal")),
    )
    updated_plan["early_payoff"] = {
        "status": "closed",
        "paid_date": paid_date,
        "principal_amount": round(remaining_principal, 2),
        "waived_future_interest": round(waived_future_interest, 2),
        "note": note,
    }
    return updated_plan


def remaining_principal_for_plan(payment_plan: dict) -> float:
    """Odeme planinda tahmini kalan ana parayi bulur."""

    summary_remaining = _to_float(payment_plan.get("payment_summary", {}).get("remaining_principal_after_last_payment"))
    if summary_remaining > 0:
        return round(summary_remaining, 2)

    schedule = payment_plan.get("schedule", [])
    paid_installments = [item for item in schedule if item.get("status") == "paid"]
    if paid_installments:
        return round(_to_float(paid_installments[-1].get("remaining_principal")), 2)

    return round(_to_float(payment_plan.get("principal")), 2)


def _ensure_application_is_approved(application_record: dict) -> None:
    """Sadece onaylı başvurular için ödeme planı oluşturulmasını sağlar."""

    status_code = application_record.get("current_status", {}).get("status_code", "")
    if status_code != "APPROVED":
        raise ValueError("Ödeme planı yalnızca onaylanmış başvuru için oluşturulabilir.")


def _credit_terms(application_record: dict, monthly_interest_rate: float | None = None) -> dict:
    """Sistem veya uzman teklifinden ödeme planı koşullarını seçer."""

    credit_request = application_record.get("credit_request", {})
    decision_offer = application_record.get("bank_decision", {}).get("credit_offer", {})
    interest_policy = suggest_interest_offer(application_record)

    principal = _to_float(decision_offer.get("approved_amount"))
    if principal <= 0:
        principal = _repair_small_requested_amount(_to_float(credit_request.get("requested_amount")), credit_request)

    term_months = int(_to_float(decision_offer.get("term_months")))
    if term_months <= 0:
        term_months = int(_to_float(credit_request.get("term_months")))

    expert_rate = _to_rate(decision_offer.get("monthly_interest_rate"))
    if monthly_interest_rate is not None:
        effective_rate = float(monthly_interest_rate)
        rate_source = "manual_request"
    elif expert_rate > 0:
        effective_rate = expert_rate
        rate_source = "expert_offer"
    else:
        effective_rate = float(interest_policy["assigned_monthly_interest_rate"])
        rate_source = "system"

    _validate_interest_rate(effective_rate)
    interest_policy = dict(interest_policy)
    interest_policy["rate_source"] = rate_source
    interest_policy["effective_monthly_interest_rate"] = round(effective_rate, 4)
    interest_policy["effective_annual_interest_rate"] = round(((1 + effective_rate) ** 12) - 1, 4)
    interest_policy["expert_editable"] = _is_medium_or_high_risk(application_record)

    return {
        "principal": principal,
        "term_months": term_months,
        "monthly_interest_rate": effective_rate,
        "interest_policy": interest_policy,
        "credit_offer": {
            "approved_amount": round(principal, 2),
            "term_months": term_months,
            "monthly_interest_rate": round(effective_rate, 4),
            "source": rate_source,
        },
    }


def _validate_interest_rate(monthly_interest_rate: float) -> None:
    """Faiz oranının ürün bandında kalmasını sağlar."""

    if monthly_interest_rate < 0:
        raise ValueError("Aylık faiz oranı negatif olamaz.")
    if monthly_interest_rate < MIN_MONTHLY_INTEREST_RATE or monthly_interest_rate > MAX_MONTHLY_INTEREST_RATE:
        min_rate = MIN_MONTHLY_INTEREST_RATE * 100
        max_rate = MAX_MONTHLY_INTEREST_RATE * 100
        raise ValueError(f"Aylık faiz oranı %{min_rate:.2f} ile %{max_rate:.2f} aralığında olmalı.")


def _risk_adjustment(risk_level: str, risk_score: float) -> float:
    """Risk seviyesini aylık faiz ek puanına çevirir."""

    normalized_level = _normalize_text(risk_level)
    if "yuksek" in normalized_level or risk_score >= 0.67:
        return 0.011
    if "orta" in normalized_level or risk_score >= 0.34:
        return 0.0055
    return 0.0


def _risk_score(application_record: dict) -> float:
    """Kayittaki risk skorunu 0-1 araliginda okur."""

    candidates = [
        application_record.get("risk_score"),
        application_record.get("analysis_result", {}).get("risk_score"),
        application_record.get("risk_summary", {}).get("risk_score"),
        application_record.get("risk", {}).get("risk_score"),
        application_record.get("bank_view", {}).get("risk_score"),
    ]
    for candidate in candidates:
        score = _to_float(candidate)
        if score <= 0:
            continue
        return score / 100 if score > 1 else score
    return 0.0


def _risk_level(application_record: dict) -> str:
    """Kayittaki risk seviyesi metnini bulur."""

    candidates = [
        application_record.get("risk_level"),
        application_record.get("analysis_result", {}).get("risk_level"),
        application_record.get("risk_summary", {}).get("risk_level"),
        application_record.get("risk", {}).get("risk_level"),
        application_record.get("bank_view", {}).get("risk_level"),
    ]
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    return ""


def _is_medium_or_high_risk(application_record: dict) -> bool:
    risk_level = _normalize_text(_risk_level(application_record))
    return "orta" in risk_level or "yuksek" in risk_level or _risk_score(application_record) >= 0.34


def _clamp_interest_rate(monthly_interest_rate: float) -> float:
    return min(MAX_MONTHLY_INTEREST_RATE, max(MIN_MONTHLY_INTEREST_RATE, monthly_interest_rate))


def _monthly_payment(
    principal: float,
    term_months: int,
    monthly_interest_rate: float,
) -> float:
    """Eşit taksitli kredi için aylık ödeme tutarını hesaplar."""

    if monthly_interest_rate == 0:
        return round(principal / term_months, 2)

    growth = (1 + monthly_interest_rate) ** term_months
    payment = principal * monthly_interest_rate * growth / (growth - 1)
    return round(payment, 2)


def _build_schedule(
    principal: float,
    term_months: int,
    monthly_interest_rate: float,
    monthly_payment: float,
    first_due_date: date,
) -> list[dict]:
    """Taksit takvimini ay ay oluşturur."""

    remaining_principal = round(principal, 2)
    schedule: list[dict] = []

    for installment_no in range(1, term_months + 1):
        interest_amount = round(remaining_principal * monthly_interest_rate, 2)

        if installment_no == term_months:
            principal_amount = remaining_principal
            payment_amount = round(principal_amount + interest_amount, 2)
            remaining_principal = 0.0
        else:
            payment_amount = monthly_payment
            principal_amount = round(payment_amount - interest_amount, 2)
            remaining_principal = round(remaining_principal - principal_amount, 2)

        schedule.append(
            {
                "installment_no": installment_no,
                "due_date": _add_months(first_due_date, installment_no - 1).isoformat(),
                "payment_amount": payment_amount,
                "principal_amount": principal_amount,
                "interest_amount": interest_amount,
                "remaining_principal": remaining_principal,
                "status": "pending",
            }
        )

    return schedule


def _payment_summary(schedule: list[dict], principal: float = 0.0) -> dict:
    """Taksit listesi uzerinden kisa odeme ozeti uretir."""

    paid_count = 0
    overdue_count = 0
    pending_count = 0
    remaining_principal = 0.0

    for installment in schedule:
        status = installment.get("status", "pending")
        if status == "paid":
            paid_count += 1
            remaining_principal = _to_float(installment.get("remaining_principal"))
        elif status == "overdue":
            overdue_count += 1
        else:
            pending_count += 1

    if paid_count == 0:
        remaining_principal = principal

    total_count = len(schedule)
    progress_ratio = paid_count / total_count if total_count else 0.0

    return {
        "total_installment_count": total_count,
        "paid_installment_count": paid_count,
        "pending_installment_count": pending_count,
        "overdue_installment_count": overdue_count,
        "payment_progress_ratio": round(progress_ratio, 2),
        "remaining_principal_after_last_payment": round(remaining_principal, 2),
    }


def _repair_small_requested_amount(amount: float, credit_request: dict) -> float:
    """Eski kayitlarda 300.000 TL -> 300 gibi okunmus tutari duzeltir."""

    current_debt = _to_float(credit_request.get("current_total_debt"))
    declared_income = _to_float(credit_request.get("declared_monthly_income"))
    if 0 < amount < 1000 and (current_debt >= 10000 or declared_income >= 10000):
        return amount * 1000
    return amount


def _loan_id(application_id: str) -> str:
    """Başvuru ID'sinden kredi ID'si üretir."""

    clean_application_id = application_id.replace("APP-", "")
    return f"LOAN-{clean_application_id}" if clean_application_id else "LOAN-DRAFT"


def _add_months(start_date: date, month_count: int) -> date:
    """Standart kütüphane ile güvenli ay ekleme işlemi yapar."""

    month_index = start_date.month - 1 + month_count
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(start_date.day, last_day)
    return date(year, month, day)


def _normalize_text(value: str) -> str:
    translation_table = str.maketrans("ÇĞİÖŞÜçğıöşü", "CGIOSUcgiosu")
    return value.translate(translation_table).lower()


def _to_rate(value) -> float:
    """Faiz oranını para parserındaki binlik ayırıcı varsayımına takılmadan okur."""

    if isinstance(value, (int, float)):
        return float(value)
    if value is None or str(value).strip() == "":
        return 0.0

    text = str(value).strip().replace("%", "").replace(",", ".")
    try:
        rate = float(text)
    except ValueError:
        return 0.0
    return rate / 100 if rate > 1 else rate


def _to_float(value) -> float:
    """Bos veya hatali degeri 0.0 kabul ederek sayiya cevirir."""

    if value is None or str(value).strip() == "":
        return 0.0

    text = re.sub(r"[^0-9,.\-]", "", str(value).strip())
    if not text:
        return 0.0

    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif "." in text:
        parts = text.split(".")
        if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
            text = "".join(parts)

    try:
        return float(text)
    except ValueError:
        return 0.0
