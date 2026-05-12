from __future__ import annotations

"""Kredi ödeme planı üretimi

Bu modül, banka uzmanı tarafından onaylanmış bir başvuru kaydından örnek ödeme planı üretir.
Gerçek bankacılık ürününde faiz oranı, masraf, sigorta ve kampanya gibi alanlar bankanın ana
sisteminden gelmelidir. Buradaki amaç ürün mimarisi için anlaşılır bir ödeme planı katmanı kurmaktır.
"""

import calendar
from datetime import date


DEFAULT_MONTHLY_INTEREST_RATE = 0.025


def build_payment_plan(
    application_record: dict,
    monthly_interest_rate: float = DEFAULT_MONTHLY_INTEREST_RATE,
    first_due_date: date | None = None,
) -> dict:
    """Onaylanmış başvuru kaydından taksitli ödeme planı üretir."""

    _ensure_application_is_approved(application_record)

    credit_request = application_record.get("credit_request", {})
    principal = _to_float(credit_request.get("requested_amount"))
    term_months = int(_to_float(credit_request.get("term_months")))

    if principal <= 0:
        raise ValueError("Ödeme planı için kredi tutarı 0'dan büyük olmalıdır.")

    if term_months <= 0:
        raise ValueError("Ödeme planı için vade 0'dan büyük olmalıdır.")

    if monthly_interest_rate < 0:
        raise ValueError("Aylık faiz oranı negatif olamaz.")

    due_date = first_due_date or _add_months(date.today(), 1)
    monthly_payment = _monthly_payment(
        principal=principal,
        term_months=term_months,
        monthly_interest_rate=monthly_interest_rate,
    )
    schedule = _build_schedule(
        principal=principal,
        term_months=term_months,
        monthly_interest_rate=monthly_interest_rate,
        monthly_payment=monthly_payment,
        first_due_date=due_date,
    )

    total_payment = round(sum(item["payment_amount"] for item in schedule), 2)
    total_interest = round(sum(item["interest_amount"] for item in schedule), 2)

    return {
        "loan_id": _loan_id(application_record.get("application_id", "")),
        "application_id": application_record.get("application_id", ""),
        "principal": round(principal, 2),
        "term_months": term_months,
        "monthly_interest_rate": round(monthly_interest_rate, 4),
        "monthly_payment": monthly_payment,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "first_due_date": due_date.isoformat(),
        "schedule": schedule,
    }


def _ensure_application_is_approved(application_record: dict) -> None:
    """Sadece onaylı başvurular için ödeme planı oluşturulmasını sağlar."""

    status_code = application_record.get("current_status", {}).get("status_code", "")
    if status_code != "APPROVED":
        raise ValueError("Ödeme planı yalnızca onaylanmış başvuru için oluşturulabilir.")


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


def _to_float(value) -> float:
    """Boş veya hatalı değeri 0.0 kabul ederek sayıya çevirir."""

    if value is None or str(value).strip() == "":
        return 0.0

    try:
        return float(str(value).replace(",", ".").strip())
    except ValueError:
        return 0.0
