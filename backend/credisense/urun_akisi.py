from __future__ import annotations

"""Ürün akışı çıktıları

Analiz motoru teknik skorlar üretir. Ürün tarafında ise bu skorların kullanıcıya ve banka
uzmanına farklı şekilde gösterilmesi gerekir.

Bu dosya:
- Başvurunun durum kodunu üretir.
- Kullanıcıya gösterilecek sade çıktıyı hazırlar.
- Banka/uzman panelinde gösterilecek daha detaylı çıktıyı hazırlar.
"""

from .banka_kararlari import allowed_bank_decisions


def build_product_outputs(
    package_quality: dict,
    form_quality: dict,
    consent_quality: dict,
    risk: dict,
    consistency: dict,
    form_document_consistency: dict | None = None,
) -> dict:
    """Analiz sonucundan ürün ekranlarının kullanacağı özet çıktıları üretir."""

    form_document_consistency = form_document_consistency or {}
    status_code = _application_status_code(
        package_quality=package_quality,
        form_quality=form_quality,
        consent_quality=consent_quality,
        form_document_consistency=form_document_consistency,
        risk=risk,
    )

    return {
        "application_status": _application_status(status_code),
        "user_view": _user_view(status_code),
        "bank_view": _bank_view(
            status_code=status_code,
            package_quality=package_quality,
            form_quality=form_quality,
            consent_quality=consent_quality,
            form_document_consistency=form_document_consistency,
            risk=risk,
            consistency=consistency,
        ),
    }


def _application_status_code(
    package_quality: dict,
    form_quality: dict,
    consent_quality: dict,
    form_document_consistency: dict,
    risk: dict,
) -> str:
    """Başvurunun ürün durum kodunu belirler."""

    if not consent_quality.get("is_valid", False):
        return "CONSENT_REQUIRED"

    if not package_quality.get("can_continue", False):
        return "DOCUMENT_REVISION_REQUIRED"

    if not form_quality.get("is_valid", False):
        return "FORM_REVISION_REQUIRED"

    if form_document_consistency and not form_document_consistency.get("is_consistent", False):
        return "MANUAL_REVIEW"

    decision_code = risk.get("decision_summary", {}).get("decision_code", "")
    if decision_code == "PRE_APPROVED":
        return "PRE_APPROVED"
    if decision_code == "DEEP_REVIEW":
        return "DEEP_REVIEW"

    return "MANUAL_REVIEW"


def _application_status(status_code: str) -> dict:
    """Durum kodunu genel başvuru durumu nesnesine çevirir."""

    status_texts = {
        "CONSENT_REQUIRED": "Onay bekleniyor",
        "DOCUMENT_REVISION_REQUIRED": "Belge düzeltmesi gerekli",
        "FORM_REVISION_REQUIRED": "Form düzeltmesi gerekli",
        "PRE_APPROVED": "Ön onaya uygun",
        "MANUAL_REVIEW": "Uzman incelemesinde",
        "DEEP_REVIEW": "Detaylı inceleme gerekli",
    }

    return {
        "status_code": status_code,
        "status_text": status_texts.get(status_code, "Bilinmeyen durum"),
        "is_final": status_code in {"PRE_APPROVED", "DEEP_REVIEW"},
        "requires_human_review": status_code in {"MANUAL_REVIEW", "DEEP_REVIEW"},
        "next_action": _next_action(status_code),
    }


def _user_view(status_code: str) -> dict:
    """Kullanıcı ekranında gösterilecek sade sonucu üretir."""

    messages = {
        "CONSENT_REQUIRED": "Başvurunu işleyebilmemiz için gerekli onayları tamamlamalısın.",
        "DOCUMENT_REVISION_REQUIRED": "Belgelerinde eksik veya okunamayan alanlar var.",
        "FORM_REVISION_REQUIRED": "Başvuru formundaki bazı alanları düzeltmen gerekiyor.",
        "PRE_APPROVED": "Başvurun ön değerlendirmede uygun görünüyor.",
        "MANUAL_REVIEW": "Başvurun uzman incelemesine alındı.",
        "DEEP_REVIEW": "Başvurun detaylı risk incelemesine alındı.",
    }

    return {
        "visible_status": status_code,
        "message": messages.get(status_code, "Başvuru durumu hesaplandı."),
        "show_risk_score": False,
        "allowed_actions": _user_actions(status_code),
    }


def _bank_view(
    status_code: str,
    package_quality: dict,
    form_quality: dict,
    consent_quality: dict,
    form_document_consistency: dict,
    risk: dict,
    consistency: dict,
) -> dict:
    """Banka/uzman panelinde gösterilecek teknik özeti üretir."""

    decision_summary = risk.get("decision_summary", {})

    return {
        "status_code": status_code,
        "recommended_action": _bank_recommended_action(status_code),
        "risk_score": risk.get("risk_score"),
        "risk_level": risk.get("risk_level"),
        "decision_code": decision_summary.get("decision_code", ""),
        "decision_source": risk.get("decision_source", ""),
        "model_name": risk.get("model_name", ""),
        "package_quality_score": package_quality.get("quality_score"),
        "form_quality_score": form_quality.get("quality_score"),
        "form_document_consistency_score": form_document_consistency.get("score"),
        "form_document_flags": form_document_consistency.get("flags", []),
        "consent_valid": consent_quality.get("is_valid", False),
        "consistency_score": consistency.get("consistency_score"),
        "anomaly_score": consistency.get("anomaly_score"),
        "main_reasons": risk.get("reasons", [])[:5],
        "blockers": _bank_blockers(package_quality, form_quality, consent_quality, form_document_consistency),
        "allowed_decisions": allowed_bank_decisions(status_code),
    }


def _next_action(status_code: str) -> str:
    """Duruma göre sistemin beklediği sonraki aksiyonu döndürür."""

    actions = {
        "CONSENT_REQUIRED": "Kullanıcıdan KVKK ve veri işleme onaylarını al.",
        "DOCUMENT_REVISION_REQUIRED": "Kullanıcıdan eksik veya okunamayan belgeleri yeniden iste.",
        "FORM_REVISION_REQUIRED": "Kullanıcıdan başvuru formunu düzeltmesini iste.",
        "PRE_APPROVED": "Banka uzmanına ön onay kontrolü için gönder.",
        "MANUAL_REVIEW": "Banka uzmanının başvuruyu incelemesini bekle.",
        "DEEP_REVIEW": "Başvuruyu detaylı risk incelemesine yönlendir.",
    }
    return actions.get(status_code, "Başvuru durumunu kontrol et.")


def _user_actions(status_code: str) -> list[str]:
    """Kullanıcı ekranında aktif edilebilecek aksiyonları listeler."""

    if status_code == "CONSENT_REQUIRED":
        return ["consent_update"]
    if status_code == "DOCUMENT_REVISION_REQUIRED":
        return ["document_upload"]
    if status_code == "FORM_REVISION_REQUIRED":
        return ["form_update"]
    return ["status_view"]


def _bank_recommended_action(status_code: str) -> str:
    """Uzman panelindeki önerilen aksiyonu üretir."""

    actions = {
        "CONSENT_REQUIRED": "Onaylar tamamlanmadan finansal inceleme başlatma.",
        "DOCUMENT_REVISION_REQUIRED": "Eksik belgeleri kullanıcıdan yeniden talep et.",
        "FORM_REVISION_REQUIRED": "Form düzeltmesi iste.",
        "PRE_APPROVED": "Belge ve skor özetini kontrol edip ön onayı kesinleştir.",
        "MANUAL_REVIEW": "Risk gerekçelerini ve anomalileri manuel incele.",
        "DEEP_REVIEW": "Detaylı risk değerlendirmesi ve ek belge süreci başlat.",
    }
    return actions.get(status_code, "Başvuruyu manuel kontrol et.")


def _bank_blockers(
    package_quality: dict,
    form_quality: dict,
    consent_quality: dict,
    form_document_consistency: dict,
) -> list[str]:
    """Banka tarafında iş akışını durduran veya yavaşlatan maddeleri toparlar."""

    blockers: list[str] = []

    blockers.extend(consent_quality.get("missing_consents", []))
    blockers.extend(consent_quality.get("rejected_consents", []))
    blockers.extend(package_quality.get("missing_required_documents", []))
    blockers.extend(package_quality.get("failed_pdf_extractions", []))
    blockers.extend(form_quality.get("missing_required_fields", []))
    blockers.extend(form_quality.get("invalid_fields", []))
    blockers.extend(form_document_consistency.get("flags", []))

    return blockers
