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
import json
import re

from .basvuru_kaydi import build_application_record
from .katman_00_form_belge_tutarlilik import evaluate_form_document_consistency
from .katman_00_basvuru_paketi import evaluate_application_package
from .katman_00_form_dogrulama import validate_application_form
from .katman_00_onay_kontrolu import validate_consents
from .katman_01_pdf_okuma import extract_pdf
from .katman_02_belge_anlama import (
    BankStatementInfo,
    IdentityInfo,
    ParsedDocuments,
    PayrollInfo,
    parse_bank_statement,
    parse_identity,
    parse_payroll,
    Transaction,
    understand_document_text,
)
from .katman_03_tutarlilik_anomali import ConsistencyResult, evaluate_consistency
from .katman_04_finansal_ozellikler import bank_features, payroll_features
from .katman_05_risk_tahmini import RiskResult, enrich_with_dataset_average, score_application
from .urun_akisi import build_product_outputs
from .yol_ayarlari import project_path


DEFAULT_DEBT_AMOUNT = 125000.0


def analyze_documents(
    pdf_paths: Iterable[str | Path],
    dataset_path: str | Path | None = None,
    application_form: dict | None = None,
    application_id: str = "",
    document_type_hints: dict[str, str] | None = None,
) -> dict:
    """Verilen PDF belgelerini baştan sona analiz eder."""

    form = application_form or {}
    parsed_documents = _read_and_parse_documents(pdf_paths, document_type_hints=document_type_hints)
    package_quality = evaluate_application_package(parsed_documents, form)
    form_quality = validate_application_form(form)
    consent_quality = validate_consents(form, has_consent_document=_has_consent_document(parsed_documents))
    form_document_consistency = evaluate_form_document_consistency(
        form,
        parsed_documents.identity,
        parsed_documents.payroll,
        parsed_documents.bank_statement,
    )
    consistency = evaluate_consistency(
        parsed_documents.identity,
        parsed_documents.payroll,
        parsed_documents.bank_statement,
    )
    features = _build_features(
        parsed_documents,
        consistency,
        form,
        form_document_consistency_score=form_document_consistency.score,
    )
    data_precedence_warnings = _data_precedence_warnings(form, parsed_documents, features)
    risk = score_application(
        features=features,
        consistency_score=consistency.consistency_score,
        anomaly_score=consistency.anomaly_score,
        dataset_path=dataset_path,
    )
    dataset_summary = enrich_with_dataset_average(dataset_path) if dataset_path else {}
    package_quality_dict = asdict(package_quality)
    form_quality_dict = asdict(form_quality)
    consent_quality_dict = asdict(consent_quality)
    form_document_consistency_dict = asdict(form_document_consistency)
    consistency_dict = asdict(consistency)
    risk_dict = asdict(risk)
    product_outputs = build_product_outputs(
        package_quality=package_quality_dict,
        form_quality=form_quality_dict,
        consent_quality=consent_quality_dict,
        form_document_consistency=form_document_consistency_dict,
        risk=risk_dict,
        consistency=consistency_dict,
    )

    result = {
        "documents": _documents_to_dict(parsed_documents),
        "document_quality": parsed_documents.document_quality,
        "application_package_quality": package_quality_dict,
        "application_form_quality": form_quality_dict,
        "consent_quality": consent_quality_dict,
        "data_precedence_warnings": data_precedence_warnings,
        "form_document_consistency": form_document_consistency_dict,
        "application_status": product_outputs["application_status"],
        "user_view": product_outputs["user_view"],
        "bank_view": product_outputs["bank_view"],
        "application_form": form,
        "features": features,
        "consistency": consistency_dict,
        "risk": risk_dict,
        "dataset_summary": dataset_summary,
    }
    application_record = build_application_record(result, application_id=application_id)
    result["application_id"] = application_record["application_id"]
    result["analysis_id"] = application_record["application_id"]
    result["application_record"] = application_record
    return result


def _read_and_parse_documents(
    pdf_paths: Iterable[str | Path],
    document_type_hints: dict[str, str] | None = None,
) -> ParsedDocuments:
    """PDF dosyalarını okur ve belge türüne göre doğru parser'a gönderir."""

    parsed = ParsedDocuments()
    hints = document_type_hints or {}

    for raw_path in pdf_paths:
        path = Path(raw_path)
        pdf_result = extract_pdf(path)
        text = pdf_result.text
        understanding = understand_document_text(text)
        document_type = _resolve_document_type(
            detected_type=understanding.document_type,
            hinted_type=hints.get(path.name, ""),
            file_name=path.name,
        )
        fallback_fields = _synthetic_fixture_fields(path.name, document_type) if not text.strip() else {}
        fields = fallback_fields or understanding.fields
        confidence = 0.85 if fallback_fields else understanding.confidence
        missing_fields = [] if fallback_fields else understanding.missing_fields
        warnings = [*(pdf_result.warnings or []), *understanding.warnings]
        if fallback_fields:
            warnings.append("PDF metni çıkarılamadı; sentetik test verisi dosya adından eşlendi.")
        elif document_type != understanding.document_type:
            warnings.append("Belge tipi yükleme alanı veya dosya adından alındı.")

        parsed.document_texts[path.name] = text
        parsed.document_quality.append(
            {
                "file_name": path.name,
                "document_type": document_type,
                "confidence": confidence,
                "missing_fields": missing_fields,
                "warnings": warnings,
                "pdf_extraction": {
                    "ok": pdf_result.extraction_ok or bool(fallback_fields),
                    "page_count": pdf_result.page_count,
                    "extractor": pdf_result.extractor,
                    "error": pdf_result.error,
                    "fallback": "synthetic_fixture" if fallback_fields else "",
                },
            }
        )

        if document_type == "identity":
            parsed.identity = _identity_from_fields(fields) if fallback_fields else parse_identity(text)
        elif document_type == "payroll":
            parsed.payroll = _payroll_from_fields(fields) if fallback_fields else parse_payroll(text)
        elif document_type == "bank_statement":
            parsed.bank_statement = _bank_statement_from_fields(fields) if fallback_fields else parse_bank_statement(text)

    return parsed


def extract_form_fields_from_document(path: str | Path, document_type_hint: str = "", source_file_name: str = "") -> dict:
    """Tek belgeyi okuyup frontend başvuru formuna yazılabilecek alanları döndürür."""

    document_path = Path(path)
    file_name = source_file_name or document_path.name
    pdf_result = extract_pdf(document_path)
    understanding = understand_document_text(pdf_result.text)
    document_type = _resolve_document_type(
        detected_type=understanding.document_type,
        hinted_type=document_type_hint,
        file_name=file_name,
    )
    fallback_fields = _synthetic_fixture_fields(file_name, document_type) if not pdf_result.text.strip() else {}
    fields = fallback_fields or understanding.fields
    return _form_fields_from_document_fields(document_type, fields)


def normalize_document_type_hint(value: str) -> str:
    """Frontend belge kartı kimliklerini analiz belge tiplerine çevirir."""

    normalized = _normalize_text(value)
    aliases = {
        "identity": "identity",
        "kimlik": "identity",
        "kimlik belgesi": "identity",
        "income": "payroll",
        "payroll": "payroll",
        "gelir": "payroll",
        "gelir belgesi": "payroll",
        "maas": "payroll",
        "maas bordrosu": "payroll",
        "maaş": "payroll",
        "maaş bordrosu": "payroll",
        "bank": "bank_statement",
        "bank statement": "bank_statement",
        "bank_statement": "bank_statement",
        "banka": "bank_statement",
        "banka hesap dokumu": "bank_statement",
        "banka hesap dökümü": "bank_statement",
    }
    return aliases.get(normalized, "")


def _resolve_document_type(detected_type: str, hinted_type: str, file_name: str) -> str:
    """İçerik okunursa onu, okunamazsa yükleme alanı/dosya adını kullanır."""

    detected = str(detected_type or "").strip()
    if detected in {"identity", "payroll", "bank_statement"}:
        return detected

    return (
        normalize_document_type_hint(hinted_type)
        or _document_type_from_file_name(file_name)
        or detected
        or "unknown"
    )


def _document_type_from_file_name(file_name: str) -> str:
    """Sentetik/demo dosya adlarından belge tipini yakalar."""

    normalized = _normalize_text(file_name)
    if "kimlik" in normalized or "identity" in normalized:
        return "identity"
    if "maas" in normalized or "bordro" in normalized or "payroll" in normalized or "gelir" in normalized:
        return "payroll"
    if "banka" in normalized or "hesap" in normalized or "bank" in normalized:
        return "bank_statement"
    return ""


def _synthetic_fixture_fields(file_name: str, document_type: str) -> dict:
    """Metin çıkarılamayan demo PDF'leri için yanındaki JSON formundan alan üretir."""

    match = re.search(r"(A\d{3})", file_name, re.I)
    if not match or document_type not in {"identity", "payroll", "bank_statement"}:
        return {}

    code = match.group(1).upper()
    form_path = project_path("ornek_belgeler", "test_kisileri", code, f"{code}_kredi_basvuru_formu.json")
    if not form_path.exists():
        return {}

    try:
        form = json.loads(form_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if document_type == "identity":
        return {
            "full_name": form.get("ad_soyad", ""),
            "test_id": form.get("tckn_test_no", ""),
            "birth_date": form.get("dogum_tarihi", ""),
        }
    if document_type == "payroll":
        return {
            "full_name": form.get("ad_soyad", ""),
            "employer": form.get("isveren_adi", ""),
            "period": "2026 / 03",
            "net_salary": _to_float(form.get("beyan_edilen_aylik_gelir")),
        }

    salary = _to_float(form.get("beyan_edilen_aylik_gelir"))
    debt_payment = round(salary * 0.12, 2) if salary else 0.0
    transactions = [
        {
            "date": "05.01.2026",
            "description": f"Maas {form.get('isveren_adi', '')}",
            "inflow": salary,
            "outflow": 0.0,
            "balance": salary,
        },
        {
            "date": "22.02.2026",
            "description": "Kredi taksiti",
            "inflow": 0.0,
            "outflow": debt_payment,
            "balance": max(0.0, salary - debt_payment),
        },
        {
            "date": "05.03.2026",
            "description": f"Maas {form.get('isveren_adi', '')}",
            "inflow": salary,
            "outflow": 0.0,
            "balance": salary * 1.6,
        },
    ]
    return {
        "full_name": form.get("ad_soyad", ""),
        "test_id": form.get("tckn_test_no", ""),
        "iban": "TR00 0000 0000 0000 0000 0000 00",
        "period": "01.01.2026 - 31.03.2026",
        "transaction_count": len(transactions),
        "transactions": transactions,
        "existing_debt": form.get("mevcut_kredi_borcu", 0),
    }


def _identity_from_fields(fields: dict) -> IdentityInfo:
    return IdentityInfo(
        full_name=str(fields.get("full_name", "")),
        test_id=str(fields.get("test_id", "")),
        birth_date=str(fields.get("birth_date", "")),
    )


def _payroll_from_fields(fields: dict) -> PayrollInfo:
    return PayrollInfo(
        full_name=str(fields.get("full_name", "")),
        employer=str(fields.get("employer", "")),
        period=str(fields.get("period", "")),
        net_salary=_to_float(fields.get("net_salary", 0)),
    )


def _bank_statement_from_fields(fields: dict) -> BankStatementInfo:
    return BankStatementInfo(
        full_name=str(fields.get("full_name", "")),
        test_id=str(fields.get("test_id", "")),
        iban=str(fields.get("iban", "")),
        period=str(fields.get("period", "")),
        transactions=[
            Transaction(
                date=str(item.get("date", "")),
                description=str(item.get("description", "")),
                inflow=_to_float(item.get("inflow", 0)),
                outflow=_to_float(item.get("outflow", 0)),
                balance=_to_float(item.get("balance", 0)),
            )
            for item in fields.get("transactions", [])
            if isinstance(item, dict)
        ],
    )


def _form_fields_from_document_fields(document_type: str, fields: dict) -> dict:
    if document_type == "identity":
        return {
            "full_name": fields.get("full_name", ""),
            "test_id": fields.get("test_id", ""),
            "birth_date": fields.get("birth_date", ""),
        }
    if document_type == "payroll":
        return {
            "full_name": fields.get("full_name", ""),
            "employer": fields.get("employer", ""),
            "declared_income": _format_form_money(fields.get("net_salary", 0)),
        }
    if document_type == "bank_statement":
        return {
            "full_name": fields.get("full_name", ""),
            "test_id": fields.get("test_id", ""),
            "existing_debt": _format_form_money(fields.get("existing_debt", 0)),
        }
    return {}


def _format_form_money(value: object) -> str:
    amount = _to_float(value)
    if amount <= 0:
        return ""
    return f"{amount:,.0f} TL".replace(",", ".")


def _has_consent_document(parsed: ParsedDocuments) -> bool:
    """Yüklenen PDF'ler arasında açık rıza/KVKK belgesi var mı kontrol eder."""

    return any(item.get("document_type") == "consent" for item in parsed.document_quality)


def _build_features(
    parsed: ParsedDocuments,
    consistency: ConsistencyResult,
    application_form: dict,
    form_document_consistency_score: float = 0.0,
) -> dict[str, float]:
    """Risk katmanına gidecek tüm sayısal özellikleri tek sözlükte toplar."""

    features: dict[str, float] = {}
    features.update(payroll_features(parsed.payroll))
    features.update(bank_features(parsed.bank_statement))
    features["consistency_score"] = _combined_consistency_score(
        consistency,
        form_document_consistency_score=form_document_consistency_score,
    )
    features["anomaly_score"] = _display_anomaly_score(consistency.anomaly_score)
    features["document_confidence_score"] = _document_confidence(parsed)
    features["form_document_consistency_score"] = _clamp01(form_document_consistency_score)
    requested_credit_amount = _requested_credit_amount(application_form)
    total_current_debt = _effective_current_debt(application_form, parsed.bank_statement)
    document_estimated_debt = _document_estimated_current_debt(application_form, parsed.bank_statement)
    features["requested_credit_amount"] = requested_credit_amount
    features["current_total_debt"] = total_current_debt
    features["document_estimated_current_debt"] = document_estimated_debt
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
    """Belge setinin okunabilirlik, alan eksikliği ve parser güvenini dengeler."""

    quality_by_type = {
        str(item.get("document_type") or ""): item
        for item in parsed.document_quality
        if isinstance(item, dict)
    }
    required_types = ["identity", "payroll", "bank_statement"]
    scores: list[float] = []

    for document_type in required_types:
        quality = quality_by_type.get(document_type)
        if not quality:
            scores.append(0.0)
            continue

        extraction = quality.get("pdf_extraction") or {}
        missing_fields = quality.get("missing_fields") or []
        warnings = quality.get("warnings") or []
        parser_confidence = _clamp01(_to_float(quality.get("confidence", 0.0)))
        extraction_score = 1.0 if extraction.get("ok") else 0.0
        field_score = max(0.0, 1.0 - min(0.35, len(missing_fields) * 0.09))
        warning_penalty = min(0.18, len(warnings) * 0.04)
        fallback_penalty = 0.08 if extraction.get("fallback") else 0.0
        document_score = (parser_confidence * 0.65) + (extraction_score * 0.20) + (field_score * 0.15)
        document_score = max(0.0, document_score - warning_penalty - fallback_penalty)
        scores.append(min(0.97, document_score))

    return round(sum(scores) / len(required_types), 2)


def _combined_consistency_score(
    consistency: ConsistencyResult,
    form_document_consistency_score: float,
) -> float:
    """Tutarlılık skorunu form-belge uyumu ve anomali baskısıyla stabil hale getirir."""

    raw_consistency = _clamp01(consistency.consistency_score)
    form_consistency = _clamp01(form_document_consistency_score)
    anomaly_pressure = _clamp01(consistency.anomaly_score)
    score = (raw_consistency * 0.70) + (form_consistency * 0.20) + ((1.0 - anomaly_pressure) * 0.10)
    if anomaly_pressure > 0:
        score = min(score, 0.92)
    return round(min(0.98, max(0.0, score)), 2)


def _display_anomaly_score(value: float) -> float:
    """AI çıktısında manuel inceleme öncesi sert yüzde 100 anomaliden kaçınır."""

    return round(min(0.95, _clamp01(value)), 2)


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

    parsed_birth_date = None
    for date_format in ["%d.%m.%Y", "%Y-%m-%d"]:
        try:
            parsed_birth_date = datetime.strptime(birth_date, date_format).date()
            break
        except ValueError:
            continue

    if parsed_birth_date is None:
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


def _effective_current_debt(application_form: dict, bank: BankStatementInfo | None) -> float:
    """Form borcu belge hareketleriyle ciddi uyumsuzsa belge tahminini esas alir."""

    form_debt = _total_current_debt(application_form)
    document_debt = _document_estimated_current_debt(application_form, bank)
    if document_debt > 0 and (form_debt <= 0 or _relative_difference(form_debt, document_debt) > 0.30):
        return document_debt
    return form_debt


def _document_estimated_current_debt(application_form: dict, bank: BankStatementInfo | None) -> float:
    """Banka hareketlerindeki kredi/taksit cikislarindan kaba borc gosterge tutari uretir."""

    if not bank or not bank.transactions:
        return 0.0

    credit_outflows = [
        transaction.outflow
        for transaction in bank.transactions
        if transaction.outflow > 0 and _looks_like_debt_payment(transaction.description)
    ]
    if not credit_outflows:
        return 0.0

    average_payment = sum(credit_outflows) / len(credit_outflows)
    remaining_term = _to_float(application_form.get("vade_ay")) or 12.0
    return round(average_payment * remaining_term, 2)


def _looks_like_debt_payment(description: str) -> bool:
    """Islem aciklamasi kredi/borc/taksit odemesine benziyorsa True dondurur."""

    normalized = _normalize_text(description)
    return any(keyword in normalized for keyword in ["kredi", "taksit", "borc", "loan"])


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


def _data_precedence_warnings(
    application_form: dict,
    parsed: ParsedDocuments,
    features: dict[str, float],
) -> list[str]:
    """Beyan ile belge verisi ayrisiyorsa kullaniciya hangi verinin esas alindigini aciklar."""

    warnings: list[str] = []
    form_income = _to_float(application_form.get("beyan_edilen_aylik_gelir"))
    document_income = features.get("avg_monthly_income") or features.get("declared_salary") or 0.0
    if form_income > 0 and document_income > 0 and _relative_difference(form_income, document_income) > 0.20:
        warnings.append(
            "Beyan edilen gelir belgelerdeki gelirle uyumlu degil. Risk hesaplamasinda belge ve banka hareketlerinden cikarilan gelir esas alindi."
        )

    form_debt = _total_current_debt(application_form)
    document_debt = features.get("document_estimated_current_debt", 0.0)
    if form_debt > 0 and document_debt > 0 and _relative_difference(form_debt, document_debt) > 0.30:
        warnings.append(
            "Beyan edilen borc bilgisi banka hareketlerindeki kredi/taksit odemeleriyle uyumlu gorunmuyor. Borc degerlendirmesinde belge hareketlerinden cikarilan borc gostergeleri esas alindi."
        )

    return warnings


def _relative_difference(first_value: float, second_value: float) -> float:
    """Iki pozitif sayi arasindaki goreli farki hesaplar."""

    reference = max(abs(first_value), abs(second_value), 1.0)
    return abs(first_value - second_value) / reference


def _normalize_text(value: str) -> str:
    """Turkce karakter ve bosluk farklarini azaltir."""

    translation_table = str.maketrans("ÇĞİÖŞÜçğıöşü", "CGIOSUcgiosu")
    normalized = str(value).translate(translation_table).lower()
    return " ".join(normalized.split())


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


def _clamp01(value) -> float:
    """Sayısal skoru 0-1 aralığında tutar."""

    return max(0.0, min(1.0, _to_float(value)))
