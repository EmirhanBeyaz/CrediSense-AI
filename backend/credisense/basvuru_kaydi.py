from __future__ import annotations

"""Başvuru kaydı üretimi

Analiz sonucu tek başına teknik bir çıktıdır. Ürün tarafında ise her başvurunun bir kimliği,
durumu ve durum geçmişi olmalıdır. Bu dosya analiz sonucunu takip edilebilir bir başvuru kaydına
çevirir.
"""

from datetime import datetime
from uuid import uuid4


APPLICATION_ID_PREFIX = "APP"


def create_application_id(now: datetime | None = None) -> str:
    """Okunabilir ve kısa bir başvuru numarası üretir."""

    current_time = now or datetime.now()
    date_part = current_time.strftime("%Y%m%d")
    random_part = uuid4().hex[:8].upper()
    return f"{APPLICATION_ID_PREFIX}-{date_part}-{random_part}"


def build_application_record(analysis_result: dict, application_id: str = "") -> dict:
    """Analiz sonucunu ürün tarafında saklanabilecek başvuru kaydına çevirir."""

    final_application_id = application_id or create_application_id()
    created_at = _current_time_text()
    current_status = analysis_result.get("application_status", {})

    return {
        "application_id": final_application_id,
        "created_at": created_at,
        "current_status": current_status,
        "applicant": _applicant_summary(analysis_result),
        "credit_request": _credit_request_summary(analysis_result),
        "risk_summary": _risk_summary(analysis_result),
        "status_history": [
            _status_event(
                status_code=current_status.get("status_code", "UNKNOWN"),
                note=current_status.get("next_action", ""),
                actor="system",
                created_at=created_at,
            )
        ],
    }


def append_status_event(
    application_record: dict,
    status_code: str,
    note: str = "",
    actor: str = "system",
) -> dict:
    """Başvuru kaydına yeni durum olayı ekler ve güncel durumu değiştirir."""

    updated_record = dict(application_record)
    status_history = list(updated_record.get("status_history", []))
    status_history.append(
        _status_event(
            status_code=status_code,
            note=note,
            actor=actor,
            created_at=_current_time_text(),
        )
    )

    updated_record["current_status"] = {
        "status_code": status_code,
        "status_text": status_code,
        "next_action": note,
    }
    updated_record["status_history"] = status_history
    return updated_record


def _applicant_summary(analysis_result: dict) -> dict:
    """Başvuru sahibine ait temel kimlik özetini üretir."""

    documents = analysis_result.get("documents", {})
    identity = documents.get("identity") or {}
    application_form = analysis_result.get("application_form", {})

    return {
        "full_name": identity.get("full_name") or application_form.get("ad_soyad", ""),
        "test_id": identity.get("test_id") or application_form.get("tckn_test_no", ""),
        "birth_date": identity.get("birth_date") or application_form.get("dogum_tarihi", ""),
    }


def _credit_request_summary(analysis_result: dict) -> dict:
    """Kredi talebine ait kısa ürün özetini üretir."""

    application_form = analysis_result.get("application_form", {})
    features = analysis_result.get("features", {})

    return {
        "requested_amount": features.get(
            "requested_credit_amount",
            application_form.get("talep_edilen_kredi_tutari", 0),
        ),
        "term_months": application_form.get("vade_ay", 0),
        "declared_monthly_income": application_form.get("beyan_edilen_aylik_gelir", 0),
        "current_total_debt": features.get("current_total_debt", 0),
    }


def _risk_summary(analysis_result: dict) -> dict:
    """Risk sonucunu başvuru kaydında saklanacak kısa yapıya çevirir."""

    risk = analysis_result.get("risk", {})
    bank_view = analysis_result.get("bank_view", {})
    features = analysis_result.get("features", {})
    consistency = analysis_result.get("consistency", {})
    form_document_consistency = analysis_result.get("form_document_consistency", {})

    return {
        "risk_score": risk.get("risk_score"),
        "risk_level": risk.get("risk_level", ""),
        "document_confidence_score": features.get("document_confidence_score", 0),
        "consistency_score": features.get("consistency_score", consistency.get("consistency_score", 0)),
        "anomaly_score": features.get("anomaly_score", consistency.get("anomaly_score", 0)),
        "decision_source": risk.get("decision_source", ""),
        "recommended_action": bank_view.get("recommended_action", ""),
        "main_reasons": risk.get("reasons", [])[:5],
        "consistency_flags": consistency.get("flags", []),
        "form_document_flags": form_document_consistency.get("flags", []),
        "data_precedence_warnings": analysis_result.get("data_precedence_warnings", []),
        "blockers": bank_view.get("blockers", []),
    }


def _status_event(status_code: str, note: str, actor: str, created_at: str) -> dict:
    """Durum geçmişine eklenecek tek olayı üretir."""

    return {
        "status_code": status_code,
        "note": note,
        "actor": actor,
        "created_at": created_at,
    }


def _current_time_text() -> str:
    """Başvuru kayıt zamanı için ISO benzeri okunabilir metin üretir."""

    return datetime.now().replace(microsecond=0).isoformat()
