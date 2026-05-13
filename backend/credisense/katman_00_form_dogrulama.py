from __future__ import annotations

"""Katman 00.5 - Başvuru Formu Doğrulama

Bu katman, kullanıcının doldurduğu başvuru formundaki alanları kontrol eder.

Amaç:
- Zorunlu alanlar boş mu bakmak.
- Sayısal alanlara gerçekten sayı girilmiş mi kontrol etmek.
- Yaş, vade ve borç/gelir gibi basit mantık kontrolleri yapmak.
- Form için 0-1 arasında kalite skoru üretmek.

Bu katman kredi riski kararı vermez. Sadece "form sağlıklı mı?" sorusunu cevaplar.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime


REQUIRED_FIELDS = [
    "ad_soyad",
    "tckn_test_no",
    "dogum_tarihi",
    "meslek",
    "isveren_adi",
    "beyan_edilen_aylik_gelir",
    "gelir_turu",
    "talep_edilen_kredi_tutari",
    "vade_ay",
]

NUMBER_FIELDS = [
    "beyan_edilen_aylik_gelir",
    "ek_gelir",
    "talep_edilen_kredi_tutari",
    "vade_ay",
    "mevcut_kredi_borcu",
    "kredi_karti_borcu",
    "aylik_taksit_toplami",
    "aylik_odeme_tutari",
    "acik_kredi_sayisi",
    "gayrimenkul_kredi_sayisi",
    "bakmakla_yukumlu_kisi_sayisi",
    "gecikme_30_59_sayisi",
    "gecikme_60_89_sayisi",
    "gecikme_90_sayisi",
    "gecikme_gun_sayisi",
    "calisma_suresi_ay",
    "aylik_kira_tutari",
]

POSITIVE_NUMBER_FIELDS = [
    "beyan_edilen_aylik_gelir",
    "talep_edilen_kredi_tutari",
    "vade_ay",
]

MINIMUM_AGE = 18
MAXIMUM_AGE_WARNING_LIMIT = 80
MAXIMUM_TERM_MONTHS = 120


@dataclass
class ApplicationFormQuality:
    """Başvuru formu doğrulama sonucudur."""

    is_valid: bool
    quality_score: float
    missing_required_fields: list[str] = field(default_factory=list)
    invalid_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_application_form(application_form: dict | None) -> ApplicationFormQuality:
    """Başvuru formundaki temel eksik ve hatalı alanları kontrol eder."""

    form = application_form or {}
    missing_fields = _missing_required_fields(form)
    invalid_fields = _invalid_number_fields(form)
    warnings: list[str] = []

    if not form:
        warnings.append("Başvuru formu gönderilmedi. Risk hesabı belge verileriyle sınırlı kalır.")

    invalid_fields.extend(_identity_field_errors(form))
    invalid_fields.extend(_birth_date_errors(form))
    invalid_fields.extend(_term_errors(form))
    warnings.extend(_financial_warnings(form))

    quality_score = _quality_score(
        missing_fields=missing_fields,
        invalid_fields=invalid_fields,
        warnings=warnings,
    )

    return ApplicationFormQuality(
        is_valid=not missing_fields and not invalid_fields,
        quality_score=quality_score,
        missing_required_fields=missing_fields,
        invalid_fields=invalid_fields,
        warnings=warnings,
    )


def _missing_required_fields(form: dict) -> list[str]:
    """Formda boş bırakılan zorunlu alanları bulur."""

    missing: list[str] = []
    for field_name in REQUIRED_FIELDS:
        value = form.get(field_name)
        if value is None or str(value).strip() == "":
            missing.append(field_name)
    return missing


def _invalid_number_fields(form: dict) -> list[str]:
    """Sayısal olması gereken alanları kontrol eder."""

    invalid_fields: list[str] = []

    for field_name in NUMBER_FIELDS:
        if field_name not in form or str(form.get(field_name)).strip() == "":
            continue

        number = _to_float_or_none(form.get(field_name))
        if number is None:
            invalid_fields.append(f"{field_name}: sayısal değer olmalı")
            continue

        if number < 0:
            invalid_fields.append(f"{field_name}: negatif olamaz")
            continue

        if field_name in POSITIVE_NUMBER_FIELDS and number == 0:
            invalid_fields.append(f"{field_name}: 0'dan büyük olmalı")

    return invalid_fields


def _identity_field_errors(form: dict) -> list[str]:
    """Kimlik benzeri form alanlarının basit biçim kontrollerini yapar."""

    invalid_fields: list[str] = []

    test_id = str(form.get("tckn_test_no", "")).strip()
    if test_id and not _is_valid_test_id(test_id):
        invalid_fields.append("tckn_test_no: 11 haneli sayı veya TEST-TCKN-000000 formatında olmalı")

    full_name = str(form.get("ad_soyad", "")).strip()
    if full_name and len(full_name.split()) < 2:
        invalid_fields.append("ad_soyad: ad ve soyad birlikte girilmeli")

    return invalid_fields


def _birth_date_errors(form: dict) -> list[str]:
    """Doğum tarihi alanını ve yaş sınırını kontrol eder."""

    birth_date_text = str(form.get("dogum_tarihi", "")).strip()
    if not birth_date_text:
        return []

    birth_date = _parse_date(birth_date_text)
    if birth_date is None:
        return ["dogum_tarihi: GG.AA.YYYY veya YYYY-AA-GG formatında olmalı"]

    age = _calculate_age(birth_date)
    if age < MINIMUM_AGE:
        return [f"dogum_tarihi: başvuru sahibi en az {MINIMUM_AGE} yaşında olmalı"]

    return []


def _term_errors(form: dict) -> list[str]:
    """Kredi vadesinin temel sınırlar içinde olup olmadığını kontrol eder."""

    term_months = _to_float_or_none(form.get("vade_ay"))
    if term_months is None:
        return []

    if term_months > MAXIMUM_TERM_MONTHS:
        return [f"vade_ay: {MAXIMUM_TERM_MONTHS} aydan büyük olamaz"]

    return []


def _financial_warnings(form: dict) -> list[str]:
    """Hatalı olmayan ama uzman panelinde görünmesi faydalı finansal uyarıları üretir."""

    warnings: list[str] = []
    monthly_income = _to_float_or_none(form.get("beyan_edilen_aylik_gelir")) or 0.0
    requested_credit = _to_float_or_none(form.get("talep_edilen_kredi_tutari")) or 0.0
    monthly_debt = _to_float_or_none(form.get("aylik_taksit_toplami")) or 0.0
    monthly_rent = _to_float_or_none(form.get("aylik_kira_tutari")) or 0.0

    if monthly_income and requested_credit > monthly_income * 60:
        warnings.append("Talep edilen kredi tutarı aylık gelire göre çok yüksek görünüyor.")

    if monthly_income and (monthly_debt + monthly_rent) > monthly_income:
        warnings.append("Aylık borç ve kira toplamı beyan edilen aylık geliri aşıyor.")

    if _is_yes(form.get("kira_oduyor_mu")) and monthly_rent <= 0:
        warnings.append("Kira ödendiği belirtilmiş ama aylık kira tutarı girilmemiş.")

    birth_date = _parse_date(str(form.get("dogum_tarihi", "")).strip())
    if birth_date and _calculate_age(birth_date) > MAXIMUM_AGE_WARNING_LIMIT:
        warnings.append("Başvuru sahibinin yaşı yüksek olduğu için vade ayrıca incelenmeli.")

    return warnings


def _quality_score(
    missing_fields: list[str],
    invalid_fields: list[str],
    warnings: list[str],
) -> float:
    """Form kalite skorunu basit ve anlaşılır bir puanlama ile hesaplar."""

    score = 1.0
    score -= len(missing_fields) * 0.08
    score -= len(invalid_fields) * 0.12
    score -= len(warnings) * 0.04
    return round(_clamp(score), 2)


def _parse_date(value: str) -> date | None:
    """Desteklenen doğum tarihi formatlarını date nesnesine çevirir."""

    for date_format in ["%d.%m.%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None


def _is_valid_test_id(value: str) -> bool:
    """Formdaki test kimlik numarasının kabul edilen formatta olup olmadığını kontrol eder."""

    if value.isdigit() and len(value) == 11:
        return True

    return bool(re.fullmatch(r"TEST-TCKN-\d{6}", value, re.I))


def _calculate_age(birth_date: date) -> int:
    """Doğum tarihinden bugünkü yaşı hesaplar."""

    today = date.today()
    age = today.year - birth_date.year
    birthday_passed = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return age if birthday_passed else age - 1


def _to_float_or_none(value) -> float | None:
    """Değer sayıya çevrilemiyorsa None döndürür."""

    if value is None or str(value).strip() == "":
        return None

    try:
        return float(str(value).replace(",", ".").strip())
    except ValueError:
        return None


def _is_yes(value) -> bool:
    """Evet/hayır gibi form değerlerini boolean mantığına yaklaştırır."""

    text = str(value).strip().lower()
    return text in {"evet", "true", "1", "yes", "var"}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Değeri belirlenen aralıkta tutar."""

    return max(low, min(high, value))
