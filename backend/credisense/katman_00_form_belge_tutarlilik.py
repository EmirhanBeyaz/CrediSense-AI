from __future__ import annotations

"""Katman 00.7 - Form ve Belge Tutarlılığı

Başvuru formu kullanıcının kendi beyanıdır. Kimlik, bordro ve banka dökümü ise bu beyanı
destekleyen belgelerdir. Bu katman formdaki temel alanların belgelerden çıkarılan alanlarla
uyumlu olup olmadığını kontrol eder.

Bu katman kredi kararı vermez. Sadece "formdaki bilgi belgelerle uyumlu mu?" sorusuna cevap verir.
"""

from dataclasses import dataclass, field
from datetime import datetime
import re

from .katman_02_belge_anlama import BankStatementInfo, IdentityInfo, PayrollInfo


@dataclass
class FormDocumentConsistency:
    """Form-belge tutarlılığı sonucudur."""

    is_consistent: bool
    score: float
    flags: list[str] = field(default_factory=list)
    positive_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def evaluate_form_document_consistency(
    application_form: dict | None,
    identity: IdentityInfo | None,
    payroll: PayrollInfo | None,
    bank: BankStatementInfo | None,
) -> FormDocumentConsistency:
    """Başvuru formundaki ana alanları belgelerle karşılaştırır."""

    form = application_form or {}
    if not form:
        return FormDocumentConsistency(
            is_consistent=False,
            score=0.0,
            flags=["Başvuru formu olmadığı için form-belge tutarlılığı kontrol edilemedi."],
        )

    checks = _build_checks(form, identity, payroll, bank)
    positive_checks: list[str] = []
    flags: list[str] = []
    warnings: list[str] = []

    for passed, success_message, fail_message in checks:
        if passed:
            positive_checks.append(success_message)
        else:
            flags.append(fail_message)

    if not checks:
        warnings.append("Form ve belgeler arasında karşılaştırılabilecek yeterli alan bulunamadı.")

    passed_count = len(positive_checks)
    score = passed_count / len(checks) if checks else 0.0

    return FormDocumentConsistency(
        is_consistent=not flags and bool(checks),
        score=round(score, 2),
        flags=flags,
        positive_checks=positive_checks,
        warnings=warnings,
    )


def _build_checks(
    form: dict,
    identity: IdentityInfo | None,
    payroll: PayrollInfo | None,
    bank: BankStatementInfo | None,
) -> list[tuple[bool, str, str]]:
    """Yapılacak form-belge kontrollerini hazırlar."""

    checks: list[tuple[bool, str, str]] = []

    form_name = str(form.get("ad_soyad", "")).strip()
    form_test_id = str(form.get("tckn_test_no", "")).strip()
    form_birth_date = str(form.get("dogum_tarihi", "")).strip()
    form_employer = str(form.get("isveren_adi", "")).strip()
    income_type = str(form.get("gelir_turu", "")).strip()
    form_income = _to_float(form.get("beyan_edilen_aylik_gelir"))

    if identity:
        _add_text_check(
            checks,
            form_value=form_name,
            document_value=identity.full_name,
            success_message="Formdaki ad-soyad kimlik belgesiyle uyumlu.",
            fail_message="Formdaki ad-soyad kimlik belgesiyle uyumsuz.",
        )
        _add_test_id_check(
            checks,
            form_value=form_test_id,
            document_value=identity.test_id,
            success_message="Formdaki test kimlik numarası kimlik belgesiyle uyumlu.",
            fail_message="Formdaki test kimlik numarası kimlik belgesiyle uyumsuz.",
        )
        _add_birth_date_check(
            checks,
            form_value=form_birth_date,
            document_value=identity.birth_date,
            success_message="Formdaki doğum tarihi kimlik belgesiyle uyumlu.",
            fail_message="Formdaki doğum tarihi kimlik belgesiyle uyumsuz.",
        )

    if payroll:
        _add_text_check(
            checks,
            form_value=form_name,
            document_value=payroll.full_name,
            success_message="Formdaki ad-soyad gelir belgesiyle uyumlu.",
            fail_message="Formdaki ad-soyad gelir belgesiyle uyumsuz.",
        )
        _add_employer_check(checks, form_employer, payroll.employer)
        _add_money_check(
            checks,
            form_value=form_income,
            document_value=payroll.net_salary,
            tolerance_ratio=0.20,
            success_message="Formdaki gelir beyanı bordrodaki net maaşla makul aralıkta.",
            fail_message="Formdaki gelir beyanı bordrodaki net maaşla uyumsuz.",
        )

    if bank:
        _add_text_check(
            checks,
            form_value=form_name,
            document_value=bank.full_name,
            success_message="Formdaki ad-soyad banka dökümüyle uyumlu.",
            fail_message="Formdaki ad-soyad banka dökümüyle uyumsuz.",
        )
        _add_test_id_check(
            checks,
            form_value=form_test_id,
            document_value=bank.test_id,
            success_message="Formdaki test kimlik numarası banka dökümüyle uyumlu.",
            fail_message="Formdaki test kimlik numarası banka dökümüyle uyumsuz.",
        )

        if _is_salary_income(income_type):
            average_salary = _average_salary_from_bank(bank)
            _add_money_check(
                checks,
                form_value=form_income,
                document_value=average_salary,
                tolerance_ratio=0.25,
                success_message="Formdaki gelir beyanı banka maaş girişleriyle makul aralıkta.",
                fail_message="Formdaki gelir beyanı banka maaş girişleriyle uyumsuz.",
            )

    return checks


def _add_text_check(
    checks: list[tuple[bool, str, str]],
    form_value: str,
    document_value: str,
    success_message: str,
    fail_message: str,
) -> None:
    """İki metin alanı doluysa sadeleştirerek karşılaştırır."""

    if not form_value or not document_value:
        return

    checks.append((_normalize_text(form_value) == _normalize_text(document_value), success_message, fail_message))


def _add_test_id_check(
    checks: list[tuple[bool, str, str]],
    form_value: str,
    document_value: str,
    success_message: str,
    fail_message: str,
) -> None:
    """Test kimlik numaralarını karşılaştırır."""

    if not form_value or not document_value:
        return

    checks.append((form_value.upper() == document_value.upper(), success_message, fail_message))


def _add_birth_date_check(
    checks: list[tuple[bool, str, str]],
    form_value: str,
    document_value: str,
    success_message: str,
    fail_message: str,
) -> None:
    """Doğum tarihlerini desteklenen formatlarda karşılaştırır."""

    if not form_value or not document_value:
        return

    form_date = _parse_date(form_value)
    document_date = _parse_date(document_value)
    checks.append((form_date is not None and form_date == document_date, success_message, fail_message))


def _add_employer_check(checks: list[tuple[bool, str, str]], form_employer: str, payroll_employer: str) -> None:
    """Formdaki işveren ile bordrodaki işvereni karşılaştırır."""

    if not form_employer or not payroll_employer:
        return

    form_text = _short_company_name(_normalize_text(form_employer))
    payroll_text = _short_company_name(_normalize_text(payroll_employer))
    passed = bool(form_text and payroll_text and (form_text in payroll_text or payroll_text in form_text))
    checks.append(
        (
            passed,
            "Formdaki işveren bilgisi gelir belgesiyle uyumlu.",
            "Formdaki işveren bilgisi gelir belgesiyle uyumsuz.",
        )
    )


def _add_money_check(
    checks: list[tuple[bool, str, str]],
    form_value: float,
    document_value: float,
    tolerance_ratio: float,
    success_message: str,
    fail_message: str,
) -> None:
    """İki parasal değeri belirli toleransla karşılaştırır."""

    if form_value <= 0 or document_value <= 0:
        return

    difference = abs(form_value - document_value)
    allowed_difference = document_value * tolerance_ratio
    checks.append((difference <= allowed_difference, success_message, fail_message))


def _average_salary_from_bank(bank: BankStatementInfo) -> float:
    """Banka hareketlerinden maaş açıklamalı gelirlerin ortalamasını alır."""

    salary_values: list[float] = []
    for transaction in bank.transactions:
        description = _normalize_text(transaction.description)
        if transaction.inflow > 0 and "maas" in description:
            salary_values.append(transaction.inflow)

    return sum(salary_values) / len(salary_values) if salary_values else 0.0


def _is_salary_income(income_type: str) -> bool:
    """Gelir türünün maaşlı çalışma olup olmadığını kontrol eder."""

    normalized = _normalize_text(income_type)
    return normalized in {"maas", "ucret", "ucretli", "salary"}


def _parse_date(value: str):
    """GG.AA.YYYY veya YYYY-AA-GG formatındaki tarihi date nesnesine çevirir."""

    for date_format in ["%d.%m.%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None


def _normalize_text(value: str) -> str:
    """Türkçe karakter ve boşluk farklarını azaltır."""

    translation_table = str.maketrans("ÇĞİÖŞÜçğıöşü", "CGIOSUcgiosu")
    normalized = value.translate(translation_table).lower()
    return " ".join(normalized.split())


def _short_company_name(value: str) -> str:
    """Şirket unvan eklerini sadeleştirir."""

    cleaned = value.replace("a.s.", "").replace("a.ş.", "").replace("ltd.", "")
    cleaned = cleaned.replace("sti.", "").replace("şti.", "")
    cleaned = cleaned.replace("ltd sti", "").replace("ltd şti", "")
    cleaned = cleaned.replace("anonim sirketi", "").replace("limited sirketi", "")
    return " ".join(cleaned.split())


def _to_float(value) -> float:
    """Boş veya hatalı değeri 0.0 kabul ederek sayıya çevirir."""

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
