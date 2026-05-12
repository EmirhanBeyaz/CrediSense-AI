from __future__ import annotations

"""Katman 00 - Başvuru Paketi Ön Kontrolü

Bu katmanın görevi, risk hesabından önce başvuru paketinin analiz edilebilir durumda olup
olmadığını kontrol etmektir.

Bu katmanda yapılan işler:
- Gerekli belge türleri var mı kontrol edilir.
- Aynı belge türü birden fazla kez yüklenmiş mi bakılır.
- PDF okuma veya belge anlama tarafındaki kritik uyarılar toparlanır.
- Başvuru formunun temel kredi alanları var mı kontrol edilir.
- Paket için 0-1 arasında kalite skoru üretilir.

Bu katman kredi riski kararı vermez. Sadece "bu başvuru paketi sağlıklı mı?" sorusunu cevaplar.
"""

from dataclasses import dataclass, field

from .katman_02_belge_anlama import ParsedDocuments


REQUIRED_DOCUMENT_TYPES = ["identity", "payroll", "bank_statement"]
REQUIRED_FORM_FIELDS = ["talep_edilen_kredi_tutari", "vade_ay"]


@dataclass
class ApplicationPackageQuality:
    """Başvuru paketi ön kontrol sonucudur."""

    is_complete: bool
    can_continue: bool
    quality_score: float
    missing_required_documents: list[str] = field(default_factory=list)
    duplicate_document_types: list[str] = field(default_factory=list)
    unknown_documents: list[str] = field(default_factory=list)
    failed_pdf_extractions: list[str] = field(default_factory=list)
    missing_required_form_fields: list[str] = field(default_factory=list)
    critical_warnings: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def evaluate_application_package(
    parsed_documents: ParsedDocuments,
    application_form: dict | None = None,
) -> ApplicationPackageQuality:
    """Belge ve form paketinin ürün akışına uygunluğunu değerlendirir."""

    form = application_form or {}
    document_quality = parsed_documents.document_quality

    document_type_counts = _document_type_counts(document_quality)
    missing_documents = _missing_required_documents(document_type_counts)
    duplicate_documents = _duplicate_document_types(document_type_counts)
    unknown_documents = _unknown_documents(document_quality)
    failed_extractions = _failed_pdf_extractions(document_quality)
    missing_form_fields = _missing_required_form_fields(form)

    critical_warnings = _critical_warnings(
        missing_documents=missing_documents,
        failed_extractions=failed_extractions,
        unknown_documents=unknown_documents,
    )
    warnings = _package_warnings(
        duplicate_documents=duplicate_documents,
        missing_form_fields=missing_form_fields,
        document_quality=document_quality,
    )

    is_complete = not missing_documents and not duplicate_documents and not missing_form_fields
    can_continue = not missing_documents and not failed_extractions
    quality_score = _quality_score(
        missing_documents=missing_documents,
        duplicate_documents=duplicate_documents,
        unknown_documents=unknown_documents,
        failed_extractions=failed_extractions,
        missing_form_fields=missing_form_fields,
        document_quality=document_quality,
    )

    return ApplicationPackageQuality(
        is_complete=is_complete,
        can_continue=can_continue,
        quality_score=quality_score,
        missing_required_documents=missing_documents,
        duplicate_document_types=duplicate_documents,
        unknown_documents=unknown_documents,
        failed_pdf_extractions=failed_extractions,
        missing_required_form_fields=missing_form_fields,
        critical_warnings=critical_warnings,
        warnings=warnings,
    )


def _document_type_counts(document_quality: list[dict]) -> dict[str, int]:
    """Belge türlerinin kaç kez görüldüğünü sayar."""

    counts: dict[str, int] = {}
    for item in document_quality:
        document_type = item.get("document_type", "unknown")
        counts[document_type] = counts.get(document_type, 0) + 1
    return counts


def _missing_required_documents(document_type_counts: dict[str, int]) -> list[str]:
    """Zorunlu belge türlerinden eksik olanları bulur."""

    missing: list[str] = []
    for document_type in REQUIRED_DOCUMENT_TYPES:
        if document_type_counts.get(document_type, 0) == 0:
            missing.append(document_type)
    return missing


def _duplicate_document_types(document_type_counts: dict[str, int]) -> list[str]:
    """Birden fazla kez yüklenen zorunlu belge türlerini bulur."""

    duplicates: list[str] = []
    for document_type in REQUIRED_DOCUMENT_TYPES:
        if document_type_counts.get(document_type, 0) > 1:
            duplicates.append(document_type)
    return duplicates


def _unknown_documents(document_quality: list[dict]) -> list[str]:
    """Türü belirlenemeyen belgelerin dosya adlarını döndürür."""

    unknown: list[str] = []
    for item in document_quality:
        if item.get("document_type") == "unknown":
            unknown.append(item.get("file_name", ""))
    return unknown


def _failed_pdf_extractions(document_quality: list[dict]) -> list[str]:
    """PDF metni çıkarılamayan dosyaları bulur."""

    failed: list[str] = []
    for item in document_quality:
        extraction = item.get("pdf_extraction", {})
        if extraction.get("ok") is False:
            failed.append(item.get("file_name", ""))
    return failed


def _missing_required_form_fields(application_form: dict) -> list[str]:
    """Başvuru formunda eksik olan temel kredi alanlarını bulur."""

    if not application_form:
        return REQUIRED_FORM_FIELDS.copy()

    missing: list[str] = []
    for field_name in REQUIRED_FORM_FIELDS:
        value = application_form.get(field_name)
        if value is None or str(value).strip() == "":
            missing.append(field_name)
    return missing


def _critical_warnings(
    missing_documents: list[str],
    failed_extractions: list[str],
    unknown_documents: list[str],
) -> list[str]:
    """Analizi güvenilmez hale getiren kritik uyarıları üretir."""

    warnings: list[str] = []

    if missing_documents:
        warnings.append(f"Eksik zorunlu belge türleri: {', '.join(missing_documents)}")

    if failed_extractions:
        warnings.append(f"PDF metni çıkarılamayan belgeler: {', '.join(failed_extractions)}")

    if unknown_documents:
        warnings.append(f"Türü belirlenemeyen belgeler: {', '.join(unknown_documents)}")

    return warnings


def _package_warnings(
    duplicate_documents: list[str],
    missing_form_fields: list[str],
    document_quality: list[dict],
) -> list[str]:
    """Kritik olmayan ama uzman ekranında gösterilmesi gereken uyarıları üretir."""

    warnings: list[str] = []

    if duplicate_documents:
        warnings.append(f"Tekrarlı belge türleri: {', '.join(duplicate_documents)}")

    if missing_form_fields:
        warnings.append(f"Başvuru formunda eksik alanlar: {', '.join(missing_form_fields)}")

    for item in document_quality:
        for warning in item.get("warnings", []):
            file_name = item.get("file_name", "")
            warnings.append(f"{file_name}: {warning}")

    return warnings


def _quality_score(
    missing_documents: list[str],
    duplicate_documents: list[str],
    unknown_documents: list[str],
    failed_extractions: list[str],
    missing_form_fields: list[str],
    document_quality: list[dict],
) -> float:
    """Başvuru paketi için 0-1 arasında basit kalite skoru hesaplar."""

    score = 1.0
    score -= len(missing_documents) * 0.25
    score -= len(failed_extractions) * 0.25
    score -= len(unknown_documents) * 0.15
    score -= len(duplicate_documents) * 0.10
    score -= len(missing_form_fields) * 0.05

    for item in document_quality:
        missing_fields = item.get("missing_fields", [])
        score -= len(missing_fields) * 0.03

    return round(_clamp(score), 2)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Değeri belirlenen aralıkta tutar."""

    return max(low, min(high, value))
