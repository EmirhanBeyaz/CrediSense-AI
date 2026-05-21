from __future__ import annotations

"""Ek belge taleplerinde yuklenen PDF'in istenen belgeyle uyumunu kontrol eder."""

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

from .katman_01_pdf_okuma import extract_pdf
from .katman_02_belge_anlama import parse_bank_statement, parse_payroll, understand_document_text


CURRENT_PAYROLL_MAX_AGE_MONTHS = 2

DOCUMENT_TYPE_LABELS = {
    "identity": "kimlik belgesi",
    "payroll": "gelir belgesi/maas bordrosu",
    "bank_statement": "banka hesap dokumu",
    "consent": "KVKK/acik riza belgesi",
    "unknown": "turu belirlenemeyen belge",
}


@dataclass
class RequestedDocumentRequirement:
    """Istenen ek belgenin makine tarafindaki beklentisi."""

    requested_document: str
    expected_document_type: str
    min_statement_months: int = 0
    max_payroll_age_months: int | None = None


@dataclass
class RequestedDocumentValidation:
    """Ek belge dogrulama sonucu."""

    checked: bool
    is_valid: bool
    requested_document: str
    expected_document_type: str = ""
    detected_document_type: str = ""
    message: str = ""
    errors: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def validate_requested_document_upload(
    path: str | Path,
    requested_document_name: str,
    document_type_hint: str = "",
    source_file_name: str = "",
    today: date | None = None,
) -> RequestedDocumentValidation:
    """Yuklenen PDF'in ek belge talebiyle uyumlu olup olmadigini kontrol eder.

    Kontrol, yalnizca ek belge/ozel nitelikli talepler icin devreye girer. Ornek:
    "Guncel gelir belgesi" ve "Son 6 aylik hesap dokumu".
    """

    requirement = infer_requested_document_requirement(requested_document_name, document_type_hint)
    if not requirement:
        return RequestedDocumentValidation(
            checked=False,
            is_valid=True,
            requested_document=requested_document_name,
            message="Ek belgeye ozel bir icerik kontrolu gerekmiyor.",
        )

    document_path = Path(path)
    pdf_result = extract_pdf(document_path)
    text = pdf_result.text or ""
    understanding = understand_document_text(text)
    detected_type = _resolved_document_type(
        detected_type=understanding.document_type,
        text=text,
        file_name=source_file_name or document_path.name,
        document_type_hint=document_type_hint,
    )

    details = {
        "file_name": source_file_name or document_path.name,
        "confidence": understanding.confidence,
        "pdf_extraction_ok": pdf_result.extraction_ok,
        "pdf_warnings": pdf_result.warnings,
    }
    errors: list[str] = []

    if detected_type != requirement.expected_document_type:
        errors.append(
            _wrong_type_message(
                requested_document=requirement.requested_document,
                expected_type=requirement.expected_document_type,
                detected_type=detected_type,
            )
        )
    elif requirement.expected_document_type == "bank_statement" and requirement.min_statement_months:
        details.update(_bank_statement_period_details(text, source_file_name or document_path.name))
        covered_months = int(details.get("covered_months") or 0)
        if covered_months < requirement.min_statement_months:
            if covered_months:
                errors.append(
                    f"{requirement.requested_document} icin en az "
                    f"{requirement.min_statement_months} aylik hesap dokumu bekleniyor; "
                    f"yuklenen belge {covered_months} aylik gorunuyor."
                )
            else:
                errors.append(
                    f"{requirement.requested_document} icin donem araligi okunamadi; "
                    f"en az {requirement.min_statement_months} aylik hesap dokumu yukleyin."
                )
    elif requirement.expected_document_type == "payroll" and requirement.max_payroll_age_months is not None:
        details.update(_payroll_period_details(text, today=today or date.today()))
        age_months = details.get("payroll_age_months")
        if age_months is None:
            errors.append(
                f"{requirement.requested_document} icin bordro/gelir donemi okunamadi; "
                "son 3 ay icinde duzenlenmis gelir belgesi yukleyin."
            )
        elif int(age_months) > requirement.max_payroll_age_months:
            errors.append(
                f"{requirement.requested_document} guncel olmali; yuklenen gelir belgesi "
                f"{age_months} ay onceki doneme ait gorunuyor."
            )

    is_valid = not errors
    message = (
        "Yuklenen belge istenen ek belgeyle uyumlu."
        if is_valid
        else " ".join(errors)
    )
    return RequestedDocumentValidation(
        checked=True,
        is_valid=is_valid,
        requested_document=requirement.requested_document,
        expected_document_type=requirement.expected_document_type,
        detected_document_type=detected_type,
        message=message,
        errors=errors,
        details=details,
    )


def infer_requested_document_requirement(
    requested_document_name: str,
    document_type_hint: str = "",
) -> RequestedDocumentRequirement | None:
    """Serbest metin ek belge adini dogrulanabilir belge beklentisine cevirir."""

    requested_document = str(requested_document_name or "").strip()
    combined = _normalize_text(f"{document_type_hint} {requested_document}")
    is_extra_document = combined.startswith("extra ") or "ek belge" in combined
    asks_current_document = "guncel" in combined
    asks_recent_period = "son " in combined or _requested_month_count(combined) > 0

    expected_type = ""
    if any(keyword in combined for keyword in ["gelir", "maas", "bordro", "payroll", "income"]):
        expected_type = "payroll"
    elif any(keyword in combined for keyword in ["hesap dokumu", "banka", "bank statement", "bank"]):
        expected_type = "bank_statement"
    elif any(keyword in combined for keyword in ["kimlik", "identity"]):
        expected_type = "identity"

    if not expected_type:
        return None
    if not (is_extra_document or asks_current_document or asks_recent_period):
        return None

    min_statement_months = 0
    max_payroll_age_months: int | None = None
    if expected_type == "bank_statement":
        min_statement_months = _requested_month_count(combined)
    if expected_type == "payroll" and asks_current_document:
        max_payroll_age_months = CURRENT_PAYROLL_MAX_AGE_MONTHS

    return RequestedDocumentRequirement(
        requested_document=requested_document or document_type_hint,
        expected_document_type=expected_type,
        min_statement_months=min_statement_months,
        max_payroll_age_months=max_payroll_age_months,
    )


def _resolved_document_type(
    detected_type: str,
    text: str,
    file_name: str,
    document_type_hint: str,
) -> str:
    detected = str(detected_type or "").strip()
    if detected in DOCUMENT_TYPE_LABELS and detected != "unknown":
        return detected

    normalized = _normalize_text(f"{document_type_hint} {file_name} {text[:500]}")
    if any(keyword in normalized for keyword in ["kimlik", "identity"]):
        return "identity"
    if any(keyword in normalized for keyword in ["gelir", "maas", "bordro", "payroll", "income"]):
        return "payroll"
    if any(keyword in normalized for keyword in ["banka", "hesap dokumu", "bank statement", "bank"]):
        return "bank_statement"
    if any(keyword in normalized for keyword in ["kvkk", "acik riza", "veri isleme"]):
        return "consent"
    return detected or "unknown"


def _bank_statement_period_details(text: str, file_name: str) -> dict:
    bank_statement = parse_bank_statement(text) if text.strip() else None
    period = bank_statement.period if bank_statement else ""
    dates = _dates_from_text(period or text)
    covered_months = _covered_months(dates)

    if not covered_months:
        covered_months = _requested_month_count(_normalize_text(f"{period} {file_name} {text[:300]}"))

    return {
        "period": period,
        "covered_months": covered_months,
    }


def _payroll_period_details(text: str, today: date) -> dict:
    payroll = parse_payroll(text) if text.strip() else None
    period = payroll.period if payroll else ""
    period_month = _parse_payroll_period_month(period or text)
    age_months = None
    if period_month:
        age_months = max(0, (today.year - period_month.year) * 12 + today.month - period_month.month)

    return {
        "period": period,
        "payroll_age_months": age_months,
    }


def _wrong_type_message(requested_document: str, expected_type: str, detected_type: str) -> str:
    expected_label = DOCUMENT_TYPE_LABELS.get(expected_type, expected_type)
    detected_label = DOCUMENT_TYPE_LABELS.get(detected_type, detected_type or "bilinmeyen belge")
    return (
        f"Yanlis belge yuklendi: {requested_document} icin {expected_label} bekleniyor; "
        f"yuklenen belge {detected_label} olarak okundu."
    )


def _dates_from_text(text: str) -> list[date]:
    dates: list[date] = []
    for value in re.findall(r"\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}", text):
        parsed = _parse_date(value)
        if parsed:
            dates.append(parsed)
    return dates


def _covered_months(dates: list[date]) -> int:
    if len(dates) < 2:
        return 0

    start = min(dates)
    end = max(dates)
    return max(1, (end.year - start.year) * 12 + end.month - start.month + 1)


def _parse_date(value: str) -> date | None:
    for date_format in ["%d.%m.%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None


def _parse_payroll_period_month(text: str) -> date | None:
    normalized = _normalize_text(text)

    numeric_match = re.search(r"\b(20\d{2})\s+(0?[1-9]|1[0-2])\b", normalized)
    if numeric_match:
        return _safe_month_date(int(numeric_match.group(1)), int(numeric_match.group(2)))

    month_names = {
        "ocak": 1,
        "subat": 2,
        "mart": 3,
        "nisan": 4,
        "mayis": 5,
        "haziran": 6,
        "temmuz": 7,
        "agustos": 8,
        "eylul": 9,
        "ekim": 10,
        "kasim": 11,
        "aralik": 12,
    }
    for month_name, month_number in month_names.items():
        year_after = re.search(rf"\b{month_name}\s+(20\d{{2}})\b", normalized)
        year_before = re.search(rf"\b(20\d{{2}})\s+{month_name}\b", normalized)
        year = year_after.group(1) if year_after else year_before.group(1) if year_before else ""
        if year:
            return _safe_month_date(int(year), month_number)

    compact_match = re.search(r"\b(0?[1-9]|1[0-2])[./-](20\d{2})\b", normalized)
    if compact_match:
        return _safe_month_date(int(compact_match.group(2)), int(compact_match.group(1)))

    return None


def _safe_month_date(year: int, month: int) -> date | None:
    if month < 1 or month > 12:
        return None
    return date(year, month, 1)


def _requested_month_count(normalized_text: str) -> int:
    text = _normalize_text(normalized_text)
    number_match = re.search(r"\b(?:son\s+)?(\d{1,2})\s*(?:aylik|ay)\b", text)
    if number_match:
        return int(number_match.group(1))

    word_months = {
        "uc": 3,
        "alti": 6,
        "on iki": 12,
        "oniki": 12,
    }
    for word, month_count in word_months.items():
        if re.search(rf"\b(?:son\s+)?{word}\s*(?:aylik|ay)\b", text):
            return month_count
    return 0


def _normalize_text(value: str) -> str:
    text = str(value or "").replace("İ", "I").replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
    return " ".join(text.split())
