from __future__ import annotations

"""Banka uzmanı kararları

Risk modeli başvuru hakkında öneri üretir. Son karar ise gerçek ürün akışında banka uzmanı
tarafından verilir. Bu dosya, uzman kararını başvuru kaydına işler.
"""

from .basvuru_kaydi import append_status_event


BANK_DECISION_RULES = {
    "approve": {
        "status_code": "APPROVED",
        "status_text": "Kredi onaylandı",
        "next_action": "Kredi kullandırım sürecini başlat.",
        "user_message": "Kredi başvurun onaylandı. Sonraki adımlar için banka bilgilendirmesini takip edebilirsin.",
        "is_final": True,
    },
    "reject": {
        "status_code": "REJECTED",
        "status_text": "Başvuru reddedildi",
        "next_action": "Ret gerekçesini kullanıcıya uygun dille bildir.",
        "user_message": "Başvurun şu aşamada olumlu değerlendirilemedi.",
        "is_final": True,
    },
    "request_extra_document": {
        "status_code": "EXTRA_DOCUMENT_REQUESTED",
        "status_text": "Ek belge istendi",
        "next_action": "Kullanıcıdan istenen ek belgelerin yüklenmesini bekle.",
        "user_message": "Başvurunun tamamlanması için ek belge yüklemen gerekiyor.",
        "is_final": False,
    },
    "send_to_deep_review": {
        "status_code": "DEEP_REVIEW",
        "status_text": "Detaylı inceleme gerekli",
        "next_action": "Başvuruyu detaylı risk inceleme ekibine yönlendir.",
        "user_message": "Başvurun detaylı incelemeye alındı.",
        "is_final": False,
    },
}

FINAL_STATUS_CODES = {"APPROVED", "REJECTED"}


def apply_bank_decision(
    application_record: dict,
    decision_type: str,
    note: str = "",
    actor: str = "bank_user",
    requested_documents: list[str] | None = None,
) -> dict:
    """Banka uzmanı kararını başvuru kaydına işler."""

    if decision_type not in BANK_DECISION_RULES:
        valid_decisions = ", ".join(BANK_DECISION_RULES)
        raise ValueError(f"Geçersiz banka kararı: {decision_type}. Geçerli kararlar: {valid_decisions}")

    current_status_code = application_record.get("current_status", {}).get("status_code", "")
    if current_status_code in FINAL_STATUS_CODES:
        raise ValueError("Final durumdaki başvuru için yeni banka kararı girilemez.")

    decision_rule = BANK_DECISION_RULES[decision_type]
    decision_note = note or decision_rule["next_action"]
    updated_record = append_status_event(
        application_record,
        status_code=decision_rule["status_code"],
        note=decision_note,
        actor=actor,
    )

    updated_record["current_status"] = _current_status(decision_rule)
    updated_record["bank_decision"] = _bank_decision_payload(
        decision_type=decision_type,
        decision_rule=decision_rule,
        note=decision_note,
        actor=actor,
        requested_documents=requested_documents or [],
    )
    updated_record["user_notification"] = {
        "message": decision_rule["user_message"],
        "allowed_actions": _user_actions_after_decision(decision_type),
    }
    return updated_record


def allowed_bank_decisions(current_status_code: str) -> list[str]:
    """Başvurunun güncel durumuna göre uzman ekranında açılacak kararları döndürür."""

    if current_status_code in FINAL_STATUS_CODES:
        return []

    if current_status_code == "CONSENT_REQUIRED":
        return []

    if current_status_code in {"DOCUMENT_REVISION_REQUIRED", "FORM_REVISION_REQUIRED"}:
        return ["request_extra_document", "reject"]

    if current_status_code == "EXTRA_DOCUMENT_REQUESTED":
        return ["reject", "send_to_deep_review"]

    return ["approve", "reject", "request_extra_document", "send_to_deep_review"]


def _current_status(decision_rule: dict) -> dict:
    """Karar kuralından güncel başvuru durumu üretir."""

    status_code = decision_rule["status_code"]
    return {
        "status_code": status_code,
        "status_text": decision_rule["status_text"],
        "is_final": decision_rule["is_final"],
        "requires_human_review": status_code == "DEEP_REVIEW",
        "next_action": decision_rule["next_action"],
    }


def _bank_decision_payload(
    decision_type: str,
    decision_rule: dict,
    note: str,
    actor: str,
    requested_documents: list[str],
) -> dict:
    """Başvuru kaydında saklanacak banka kararı özetini üretir."""

    return {
        "decision_type": decision_type,
        "status_code": decision_rule["status_code"],
        "decision_text": decision_rule["status_text"],
        "note": note,
        "actor": actor,
        "requested_documents": requested_documents,
    }


def _user_actions_after_decision(decision_type: str) -> list[str]:
    """Karardan sonra kullanıcı tarafında açılacak aksiyonları döndürür."""

    if decision_type == "request_extra_document":
        return ["document_upload"]
    if decision_type == "approve":
        return ["loan_terms_view", "payment_plan_view"]
    return ["status_view"]
