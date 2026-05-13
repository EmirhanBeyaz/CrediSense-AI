from __future__ import annotations

"""Katman 00.25 - Onay Kontrolü

Gerçek ürün akışında belgeler analiz edilmeden önce kullanıcının veri işleme onayları alınmalıdır.
Bu katman form içindeki onay alanlarını kontrol eder.

Bu katman risk hesabı yapmaz. Sadece "bu başvuru işlenebilir mi?" sorusunun hukuki/ürün
tarafındaki minimum kontrolünü temsil eder.
"""

from dataclasses import dataclass, field


REQUIRED_CONSENT_FIELDS = ["kvkk_onayi", "veri_isleme_onayi"]


@dataclass
class ConsentQuality:
    """KVKK ve veri işleme onaylarının kontrol sonucudur."""

    is_valid: bool
    missing_consents: list[str] = field(default_factory=list)
    rejected_consents: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_consents(application_form: dict | None, has_consent_document: bool = False) -> ConsentQuality:
    """Başvuru formundaki zorunlu onay alanlarını kontrol eder."""

    form = application_form or {}
    missing_consents: list[str] = []
    rejected_consents: list[str] = []
    warnings: list[str] = []

    for consent_name in REQUIRED_CONSENT_FIELDS:
        if consent_name not in form and _covered_by_consent_document(consent_name, form, has_consent_document):
            continue

        if consent_name not in form:
            missing_consents.append(consent_name)
            continue

        if not _is_accepted(form.get(consent_name)):
            rejected_consents.append(consent_name)

    if missing_consents:
        warnings.append("Zorunlu onay alanları başvuru formunda bulunmuyor.")

    if rejected_consents:
        warnings.append("Zorunlu onaylar verilmediği için başvuru işlenmemeli.")

    return ConsentQuality(
        is_valid=not missing_consents and not rejected_consents,
        missing_consents=missing_consents,
        rejected_consents=rejected_consents,
        warnings=warnings,
    )


def _is_accepted(value) -> bool:
    """Formdan gelen farklı doğru/yanlış biçimlerini kabul durumuna çevirir."""

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()
    return text in {"true", "1", "evet", "yes", "onaylandi", "onaylandı"}


def _covered_by_consent_document(consent_name: str, form: dict, has_consent_document: bool) -> bool:
    """Açık rıza PDF'i varsa veri işleme onayını form yerine belgeyle kabul eder."""

    if consent_name != "veri_isleme_onayi":
        return False

    if not has_consent_document:
        return False

    return _is_accepted(form.get("kvkk_onayi"))
