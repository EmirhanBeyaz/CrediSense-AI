from __future__ import annotations

"""Katman 05 - Nihai Risk Tahmini

Bu katman önceki katmanlardan gelen sayısal özellikleri kullanarak risk skoru üretir.

Bu dosyada iki ayrı yaklaşım birlikte tutulur:

1. Baseline formül:
   Açıklanabilir, basit ve belge tabanlı skor üretir.

2. Eğitilmiş model:
   `modeller/risk_modeli.pkl` dosyası varsa makine öğrenmesi skoru üretir.

Ürün mantığı açısından önemli karar:
Model skoru her zaman final karar yerine geçmez. Eğer başvurudan çıkarılan özellikler,
modelin eğitimde kullandığı kolonları yeterince karşılamıyorsa final karar baseline formülden
gelir, model skoru ise yardımcı sinyal olarak raporlanır.
"""

import csv
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MODEL_PATH = Path("modeller") / "risk_modeli.pkl"
MIN_MODEL_INPUT_COVERAGE = 0.50


@dataclass
class RiskResult:
    """Katman 05'in dışarı verdiği standart sonuç yapısı."""

    risk_score: float
    risk_level: str
    decision_summary: dict
    reasons: list[str]
    baseline_risk_score: float
    baseline_risk_level: str
    model_risk_score: float | None = None
    model_risk_level: str | None = None
    model_name: str = ""
    model_input_coverage: float = 0.0
    decision_source: str = "baseline_formula"


@dataclass
class ModelRiskResult:
    """Eğitilmiş modelin tek başına ürettiği sonuç."""

    risk_score: float
    risk_level: str
    model_name: str
    input_coverage: float
    missing_columns: list[str]


def score_application(
    features: dict[str, float],
    consistency_score: float,
    anomaly_score: float,
    dataset_path: str | Path | None = None,
) -> RiskResult:
    """Başvuru için nihai risk sonucunu hesaplar."""

    baseline_score = _baseline_score(features, consistency_score, anomaly_score)
    baseline_level = _risk_level(baseline_score)
    model_result = score_with_trained_model(features)

    final_score = baseline_score
    final_level = baseline_level
    decision_source = "baseline_formula"

    if model_result and model_result.input_coverage >= MIN_MODEL_INPUT_COVERAGE:
        final_score = model_result.risk_score
        final_level = model_result.risk_level
        decision_source = "trained_model"

    reasons = _risk_reasons(
        features=features,
        consistency_score=consistency_score,
        anomaly_score=anomaly_score,
        final_score=final_score,
        decision_source=decision_source,
        model_result=model_result,
    )

    return RiskResult(
        risk_score=final_score,
        risk_level=final_level,
        decision_summary=_decision_summary(
            risk_score=final_score,
            risk_level=final_level,
            decision_source=decision_source,
            model_result=model_result,
            reasons=reasons,
        ),
        reasons=reasons,
        baseline_risk_score=baseline_score,
        baseline_risk_level=baseline_level,
        model_risk_score=model_result.risk_score if model_result else None,
        model_risk_level=model_result.risk_level if model_result else None,
        model_name=model_result.model_name if model_result else "",
        model_input_coverage=model_result.input_coverage if model_result else 0.0,
        decision_source=decision_source,
    )


def _decision_summary(
    risk_score: float,
    risk_level: str,
    decision_source: str,
    model_result: ModelRiskResult | None,
    reasons: list[str],
) -> dict:
    """Ürün ekranında doğrudan gösterilebilecek karar özetini üretir."""

    decision_code = _decision_code(risk_score)

    return {
        "decision_code": decision_code,
        "decision_text": _decision_text(decision_code),
        "risk_label": risk_level,
        "final_score": risk_score,
        "decision_source": decision_source,
        "model_used": model_result.model_name if model_result else "",
        "model_input_coverage": model_result.input_coverage if model_result else 0.0,
        "requires_human_review": decision_code != "PRE_APPROVED",
        "main_reasons": reasons[:3],
    }


def score_with_trained_model(
    features: dict[str, float],
    model_path: Path = MODEL_PATH,
) -> ModelRiskResult | None:
    """Kaydedilmiş makine öğrenmesi modeliyle risk olasılığı üretir."""

    if not model_path.exists():
        return None

    try:
        payload = _load_model_payload(model_path)
        feature_columns = payload["feature_columns"]
        model = payload["model"]
        model_name = payload.get("model_name", "Eğitilmiş Model")
    except (OSError, KeyError, pickle.PickleError):
        return None

    feature_values, missing_columns, input_coverage = _model_input_row(features, feature_columns)
    probability = float(model.predict_proba([feature_values])[0][1])
    risk_score = round(_clamp(probability), 2)

    return ModelRiskResult(
        risk_score=risk_score,
        risk_level=_risk_level(risk_score),
        model_name=model_name,
        input_coverage=input_coverage,
        missing_columns=missing_columns,
    )


def enrich_with_dataset_average(dataset_path: str | Path) -> dict[str, float]:
    """Sentetik CSV veri setindeki bazı ortalamaları rapora eklemek için hesaplar."""

    path = Path(dataset_path)
    if not path.exists():
        return {}

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        return {}

    columns = ["risk_score", "expense_income_ratio", "debt_to_income_ratio", "income_stability"]
    summary: dict[str, float] = {}

    for column in columns:
        values = _numeric_column_values(rows, column)
        summary[f"dataset_avg_{column}"] = round(sum(values) / len(values), 2) if values else 0.0

    return summary


def _baseline_score(
    features: dict[str, float],
    consistency_score: float,
    anomaly_score: float,
) -> float:
    """Açıklanabilir baseline formül ile risk skoru hesaplar."""

    expense_ratio = features.get("expense_income_ratio", 0.0)
    income_stability = features.get("income_stability", 0.0)
    average_balance = features.get("avg_balance", 0.0)
    average_income = features.get("avg_monthly_income", 0.0)
    debt_to_income = features.get("debt_to_income_ratio", 0.0)
    document_confidence = features.get("document_confidence_score", 0.9)

    score = 0.18
    score += _risk_after_limit(expense_ratio, limit=0.55, spread=0.70) * 0.28
    score += _risk_after_limit(debt_to_income, limit=1.5, spread=5.5) * 0.20
    score += (1.0 - _clamp(income_stability)) * 0.16
    score += (1.0 - _clamp(consistency_score)) * 0.18
    score += _clamp(anomaly_score) * 0.14
    score += (1.0 - _clamp(document_confidence)) * 0.08

    if average_income and average_balance > average_income:
        score -= 0.05

    return round(_clamp(score), 2)


def _load_model_payload(model_path: Path) -> dict[str, Any]:
    """Pickle dosyasındaki model paketini okur."""

    with model_path.open("rb") as file:
        return pickle.load(file)


def _model_input_row(
    features: dict[str, float],
    feature_columns: list[str],
) -> tuple[list[float], list[str], float]:
    """Modelin beklediği kolon sırasına göre tek satırlık giriş üretir."""

    values: list[float] = []
    missing_columns: list[str] = []

    for column in feature_columns:
        value = features.get(column)
        if value is None:
            missing_columns.append(column)
            values.append(0.0)
        else:
            values.append(float(value))

    present_count = len(feature_columns) - len(missing_columns)
    input_coverage = present_count / len(feature_columns) if feature_columns else 0.0
    return values, missing_columns, round(input_coverage, 2)


def _numeric_column_values(rows: list[dict[str, str]], column: str) -> list[float]:
    """CSV içinden sayısal okunabilen değerleri toplar."""

    values: list[float] = []
    for row in rows:
        raw_value = row.get(column, "")
        if not raw_value:
            continue
        try:
            values.append(float(raw_value))
        except ValueError:
            continue
    return values


def _risk_after_limit(value: float, limit: float, spread: float) -> float:
    """Bir değer güvenli sınırı aşınca 0-1 arası risk etkisine çevirir."""

    return _clamp((value - limit) / spread)


def _risk_level(score: float) -> str:
    """Skoru okunabilir risk seviyesine çevirir."""

    if score < 0.34:
        return "Düşük"
    if score < 0.67:
        return "Orta"
    return "Yüksek"


def _decision_code(risk_score: float) -> str:
    """Risk skorunu ürün karar koduna çevirir."""

    if risk_score < 0.34:
        return "PRE_APPROVED"
    if risk_score < 0.67:
        return "MANUAL_REVIEW"
    return "DEEP_REVIEW"


def _decision_text(decision_code: str) -> str:
    """Karar kodunu kullanıcıya/uzmana okunabilir metne çevirir."""

    if decision_code == "PRE_APPROVED":
        return "Ön onaya uygun görünüyor."
    if decision_code == "MANUAL_REVIEW":
        return "Uzman incelemesi önerilir."
    return "Detaylı risk incelemesi gerekir."


def _risk_reasons(
    features: dict[str, float],
    consistency_score: float,
    anomaly_score: float,
    final_score: float,
    decision_source: str,
    model_result: ModelRiskResult | None,
) -> list[str]:
    """Risk skorunun nedenlerini kısa cümlelerle açıklar."""

    reasons: list[str] = []

    if features.get("expense_income_ratio", 0.0) > 0.85:
        reasons.append("Harcama/gelir oranı yüksek.")
    else:
        reasons.append("Harcama/gelir oranı kabul edilebilir seviyede.")

    if features.get("income_stability", 0.0) >= 0.85:
        reasons.append("Maaş girişleri düzenli görünüyor.")
    else:
        reasons.append("Gelir düzenliliği zayıf görünüyor.")

    if consistency_score >= 0.85:
        reasons.append("Belgeler arası tutarlılık yüksek.")
    else:
        reasons.append("Belgeler arası tutarlılık kontrolünde uyarılar var.")

    if anomaly_score > 0:
        reasons.append("Banka hareketlerinde incelenmesi gereken olağandışı işlem var.")

    if model_result is None:
        reasons.append("Eğitilmiş model dosyası bulunamadığı için final karar baseline formülle üretildi.")
    elif decision_source == "trained_model":
        reasons.append(f"Final karar {model_result.model_name} modeliyle üretildi.")
    else:
        reasons.append(
            "Eğitilmiş model skoru hesaplandı ancak model giriş kapsamı düşük olduğu için "
            "final karar baseline formülden alındı."
        )

    if final_score < 0.34:
        reasons.append("Genel risk seviyesi düşük olarak hesaplandı.")
    elif final_score < 0.67:
        reasons.append("Genel risk seviyesi orta olarak hesaplandı.")
    else:
        reasons.append("Genel risk seviyesi yüksek olarak hesaplandı.")

    return reasons


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Değeri belirlenen alt ve üst sınırlar arasında tutar."""

    return max(low, min(high, value))
