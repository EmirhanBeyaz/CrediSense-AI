from __future__ import annotations

"""CrediSense AI analiz akışı

Bu dosya tek bir yapay zekâ katmanı değildir. Görevi katmanları doğru sırayla çalıştırmaktır.

Akış sırası:
1. PDF metni okunur.
2. Belge türü anlaşılır.
3. Belge alanları çıkarılır.
4. Belgeler arası tutarlılık kontrol edilir.
5. Finansal özellikler hesaplanır.
6. Nihai risk skoru üretilir.
"""

from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .katman_01_pdf_okuma import extract_pdf
from .katman_02_belge_anlama import (
    BankStatementInfo,
    ParsedDocuments,
    parse_bank_statement,
    parse_identity,
    parse_payroll,
    understand_document_text,
)
from .katman_03_tutarlilik_anomali import ConsistencyResult, evaluate_consistency
from .katman_04_finansal_ozellikler import bank_features, payroll_features
from .katman_05_risk_tahmini import RiskResult, enrich_with_dataset_average, score_application


DEFAULT_DEBT_AMOUNT = 125000.0


def analyze_documents(
    pdf_paths: Iterable[str | Path],
    dataset_path: str | Path | None = None,
    application_form: dict | None = None,
) -> dict:
    """Verilen PDF belgelerini baştan sona analiz eder."""

    form = application_form or {}
    parsed_documents = _read_and_parse_documents(pdf_paths)
    consistency = evaluate_consistency(
        parsed_documents.identity,
        parsed_documents.payroll,
        parsed_documents.bank_statement,
    )
    features = _build_features(parsed_documents, consistency, form)
    risk = score_application(
        features=features,
        consistency_score=consistency.consistency_score,
        anomaly_score=consistency.anomaly_score,
        dataset_path=dataset_path,
    )
    dataset_summary = enrich_with_dataset_average(dataset_path) if dataset_path else {}

    return {
        "documents": _documents_to_dict(parsed_documents),
        "document_quality": parsed_documents.document_quality,
        "application_form": form,
        "features": features,
        "consistency": asdict(consistency),
        "risk": asdict(risk),
        "dataset_summary": dataset_summary,
    }


def _read_and_parse_documents(pdf_paths: Iterable[str | Path]) -> ParsedDocuments:
    """PDF dosyalarını okur ve belge türüne göre doğru parser'a gönderir."""

    parsed = ParsedDocuments()

    for raw_path in pdf_paths:
        path = Path(raw_path)
        pdf_result = extract_pdf(path)
        text = pdf_result.text
        understanding = understand_document_text(text)
        document_type = understanding.document_type
        parsed.document_texts[path.name] = text
        parsed.document_quality.append(
            {
                "file_name": path.name,
                "document_type": document_type,
                "confidence": understanding.confidence,
                "missing_fields": understanding.missing_fields,
                "warnings": [*(pdf_result.warnings or []), *understanding.warnings],
                "pdf_extraction": {
                    "ok": pdf_result.extraction_ok,
                    "page_count": pdf_result.page_count,
                    "extractor": pdf_result.extractor,
                    "error": pdf_result.error,
                },
            }
        )

        if document_type == "identity":
            parsed.identity = parse_identity(text)
        elif document_type == "payroll":
            parsed.payroll = parse_payroll(text)
        elif document_type == "bank_statement":
            parsed.bank_statement = parse_bank_statement(text)

    return parsed


def _build_features(
    parsed: ParsedDocuments,
    consistency: ConsistencyResult,
    application_form: dict,
) -> dict[str, float]:
    """Risk katmanına gidecek tüm sayısal özellikleri tek sözlükte toplar."""

    features: dict[str, float] = {}
    features.update(payroll_features(parsed.payroll))
    features.update(bank_features(parsed.bank_statement))
    features["consistency_score"] = consistency.consistency_score
    features["anomaly_score"] = consistency.anomaly_score
    features["document_confidence_score"] = _document_confidence(parsed)
    requested_credit_amount = _requested_credit_amount(application_form)
    total_current_debt = _total_current_debt(application_form)
    features["requested_credit_amount"] = requested_credit_amount
    features["current_total_debt"] = total_current_debt
    features["debt_to_income_ratio"] = _debt_to_income(
        features,
        debt_amount=requested_credit_amount + total_current_debt,
    )
    features.update(_model_feature_aliases(parsed, features, application_form))
    return features


def _documents_to_dict(parsed: ParsedDocuments) -> dict:
    """Çıkarılan belge alanlarını JSON'a uygun hale getirir."""

    return {
        "identity": asdict(parsed.identity) if parsed.identity else None,
        "payroll": asdict(parsed.payroll) if parsed.payroll else None,
        "bank_statement": _bank_statement_summary(parsed.bank_statement),
    }


def _bank_statement_summary(bank: BankStatementInfo | None) -> dict | None:
    """Banka hareketlerini özetler. Uzun işlem listesi ana çıktıya basılmaz."""

    if not bank:
        return None

    return {
        "full_name": bank.full_name,
        "test_id": bank.test_id,
        "iban": bank.iban,
        "period": bank.period,
        "transaction_count": len(bank.transactions),
    }


def _document_confidence(parsed: ParsedDocuments) -> float:
    """Gerekli üç belgenin temel alanlarının dolu olma oranını hesaplar."""

    required_checks = [
        parsed.identity is not None and bool(parsed.identity.full_name),
        parsed.payroll is not None and bool(parsed.payroll.full_name and parsed.payroll.net_salary),
        parsed.bank_statement is not None and len(parsed.bank_statement.transactions) > 0,
    ]

    passed_count = sum(1 for check in required_checks if check)
    return round(passed_count / len(required_checks), 2)


def _debt_to_income(features: dict[str, float], debt_amount: float) -> float:
    """Talep edilen kredi tutarını aylık gelire oranlar."""

    income = features.get("avg_monthly_income") or features.get("declared_salary") or 0.0
    return round(debt_amount / income, 2) if income else 0.0


def _model_feature_aliases(
    parsed: ParsedDocuments,
    features: dict[str, float],
    application_form: dict,
) -> dict[str, float]:
    """Eğitilmiş modelin beklediği ortak kolonları belge özelliklerinden üretir."""

    monthly_income = features.get("avg_monthly_income") or features.get("declared_salary") or 0.0
    monthly_payment = _monthly_payment(application_form)

    # Sadece gerçekten belge/form akışından bildiğimiz alanları ekliyoruz.
    # Bilmediğimiz alanları 0 diye eklemek model kapsamını olduğundan iyi gösterir.
    # Katman 05 eksik kolonları kendisi 0 ile doldurur ama kapsam skorunu düşük tutar.
    model_features = {
        "yas": _age_from_birth_date(parsed.identity.birth_date if parsed.identity else ""),
        "aylik_gelir": round(monthly_income, 2),
        "aylik_gelir_eksik": 0 if monthly_income else 1,
        "borc_orani": features.get("debt_to_income_ratio", 0.0),
        "teminatsiz_kredi_kullanim_orani": features.get("expense_income_ratio", 0.0),
    }

    if "talep_edilen_kredi_tutari" in application_form:
        model_features["kredi_tutari"] = features.get("requested_credit_amount", 0.0)

    if "vade_ay" in application_form:
        model_features["vade_ay"] = _to_float(application_form.get("vade_ay"))

    if any(key in application_form for key in ["aylik_odeme_tutari", "aylik_taksit_toplami", "vade_ay"]):
        model_features["aylik_odeme_tutari"] = monthly_payment

    _add_optional_form_number(
        model_features,
        application_form,
        source_key="gecikme_30_59_sayisi",
        target_key="gecikme_30_59_sayisi",
    )
    _add_optional_form_number(
        model_features,
        application_form,
        source_key="gecikme_60_89_sayisi",
        target_key="gecikme_60_89_sayisi",
    )
    _add_optional_form_number(
        model_features,
        application_form,
        source_key="gecikme_90_sayisi",
        target_key="gecikme_90_sayisi",
    )
    _add_optional_form_number(
        model_features,
        application_form,
        source_key="gecikme_gun_sayisi",
        target_key="gecikme_gun_sayisi",
    )
    _add_optional_form_number(
        model_features,
        application_form,
        source_key="acik_kredi_sayisi",
        target_key="acik_kredi_sayisi",
    )
    _add_optional_form_number(
        model_features,
        application_form,
        source_key="gayrimenkul_kredi_sayisi",
        target_key="gayrimenkul_kredi_sayisi",
    )

    if "bakmakla_yukumlu_kisi_sayisi" in application_form:
        model_features["bakmakla_yukumlu_kisi_sayisi"] = _to_float(
            application_form.get("bakmakla_yukumlu_kisi_sayisi")
        )
        model_features["bakmakla_yukumlu_kisi_eksik"] = 0
    else:
        model_features["bakmakla_yukumlu_kisi_eksik"] = 1

    delay_30_59 = model_features.get("gecikme_30_59_sayisi", 0.0)
    delay_60_89 = model_features.get("gecikme_60_89_sayisi", 0.0)
    delay_90 = model_features.get("gecikme_90_sayisi", 0.0)
    if any(key in model_features for key in ["gecikme_30_59_sayisi", "gecikme_60_89_sayisi", "gecikme_90_sayisi"]):
        model_features["toplam_gecikme_sayisi"] = delay_30_59 + delay_60_89 + delay_90

    return model_features


def _age_from_birth_date(birth_date: str) -> int:
    """`12.04.1992` formatındaki doğum tarihinden yaş hesaplar."""

    if not birth_date:
        return 0

    try:
        parsed_birth_date = datetime.strptime(birth_date, "%d.%m.%Y").date()
    except ValueError:
        return 0

    today = date.today()
    age = today.year - parsed_birth_date.year
    birthday_passed = (today.month, today.day) >= (parsed_birth_date.month, parsed_birth_date.day)
    return age if birthday_passed else age - 1


def _requested_credit_amount(application_form: dict) -> float:
    """Formdan talep edilen kredi tutarını okur."""

    value = _to_float(application_form.get("talep_edilen_kredi_tutari"))
    return value if value else DEFAULT_DEBT_AMOUNT


def _total_current_debt(application_form: dict) -> float:
    """Formdaki mevcut borçları toplar."""

    current_loan_debt = _to_float(application_form.get("mevcut_kredi_borcu"))
    credit_card_debt = _to_float(application_form.get("kredi_karti_borcu"))
    return current_loan_debt + credit_card_debt


def _monthly_payment(application_form: dict) -> float:
    """Formdaki aylık ödeme bilgisini okur veya basitçe tahmin eder."""

    direct_payment = _to_float(application_form.get("aylik_odeme_tutari"))
    if direct_payment:
        return direct_payment

    installment_total = _to_float(application_form.get("aylik_taksit_toplami"))
    if installment_total:
        return installment_total

    requested_credit = _requested_credit_amount(application_form)
    term_months = _to_float(application_form.get("vade_ay"))
    return round(requested_credit / term_months, 2) if requested_credit and term_months else 0.0


def _add_optional_form_number(
    target: dict[str, float],
    application_form: dict,
    source_key: str,
    target_key: str,
) -> None:
    """Formda varsa sayısal alanı model özelliklerine ekler."""

    if source_key in application_form:
        target[target_key] = _to_float(application_form.get(source_key))


def _to_float(value) -> float:
    """Boş veya hatalı değeri 0.0 kabul ederek sayıya çevirir."""

    if value is None or str(value).strip() == "":
        return 0.0

    try:
        return float(str(value).replace(",", ".").strip())
    except ValueError:
        return 0.0
