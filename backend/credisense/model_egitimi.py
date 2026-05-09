from __future__ import annotations

"""Risk modeli eğitimi

Bu dosya işlenmiş CSV verisini kullanarak iki temel makine öğrenmesi modeli eğitir:

1. Lojistik Regresyon
2. Random Forest

Amaç, Katman 05'te kullandığımız açıklanabilir formülün yanına gerçek veriyle eğitilmiş
bir model alternatifi eklemektir.
"""

import argparse
import csv
import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


DEFAULT_DATASET_PATH = Path("veri") / "islenmis" / "give_me_some_credit_ortak_format.csv"
MODEL_FOLDER = Path("modeller")
MODEL_PATH = MODEL_FOLDER / "risk_modeli.pkl"
METRICS_PATH = MODEL_FOLDER / "risk_modeli_sonuclari.json"


FEATURE_COLUMNS = [
    "yas",
    "aylik_gelir",
    "aylik_gelir_eksik",
    "kredi_tutari",
    "vade_ay",
    "aylik_odeme_tutari",
    "borc_orani",
    "teminatsiz_kredi_kullanim_orani",
    "gecikme_30_59_sayisi",
    "gecikme_60_89_sayisi",
    "gecikme_90_sayisi",
    "toplam_gecikme_sayisi",
    "gecikme_gun_sayisi",
    "acik_kredi_sayisi",
    "gayrimenkul_kredi_sayisi",
    "bakmakla_yukumlu_kisi_sayisi",
    "bakmakla_yukumlu_kisi_eksik",
]


@dataclass
class DatasetInfo:
    path: str
    row_count: int
    low_risk_count: int
    high_risk_count: int
    feature_columns: list[str]


@dataclass
class ModelMetrics:
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    true_negative: int
    false_positive: int
    false_negative: int
    true_positive: int


@dataclass
class TrainingResult:
    dataset: DatasetInfo
    metrics: list[ModelMetrics]
    best_model_name: str
    saved_model_path: str
    saved_metrics_path: str


def train_risk_models(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    model_path: Path = MODEL_PATH,
    metrics_path: Path = METRICS_PATH,
) -> TrainingResult:
    """CSV veri setinden modelleri eğitir ve en iyi modeli kaydeder."""

    features, targets, dataset_info = load_training_data(dataset_path)

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        targets,
        test_size=0.20,
        random_state=42,
        stratify=targets,
    )

    models = build_models()
    metrics: list[ModelMetrics] = []
    trained_models = {}

    for model_name, model in models.items():
        model.fit(x_train, y_train)
        trained_models[model_name] = model
        metrics.append(evaluate_model(model_name, model, x_test, y_test))

    best_metric = max(metrics, key=lambda item: item.f1)
    best_model = trained_models[best_metric.model_name]

    save_model(best_model, best_metric.model_name, model_path)
    result = TrainingResult(
        dataset=dataset_info,
        metrics=metrics,
        best_model_name=best_metric.model_name,
        saved_model_path=str(model_path),
        saved_metrics_path=str(metrics_path),
    )
    save_metrics(result, metrics_path)

    return result


def load_training_data(dataset_path: Path) -> tuple[list[list[float]], list[int], DatasetInfo]:
    """Ortak formattaki CSV dosyasını model eğitim verisine çevirir."""

    features: list[list[float]] = []
    targets: list[int] = []
    low_risk_count = 0
    high_risk_count = 0

    with dataset_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            target = row.get("hedef_risk", "")
            if target not in {"0", "1"}:
                continue

            target_value = int(target)
            feature_values = [_to_float(row.get(column)) for column in FEATURE_COLUMNS]

            features.append(feature_values)
            targets.append(target_value)

            if target_value == 1:
                high_risk_count += 1
            else:
                low_risk_count += 1

    dataset_info = DatasetInfo(
        path=str(dataset_path),
        row_count=len(targets),
        low_risk_count=low_risk_count,
        high_risk_count=high_risk_count,
        feature_columns=FEATURE_COLUMNS,
    )
    return features, targets, dataset_info


def build_models() -> dict[str, object]:
    """Karşılaştırılacak modelleri hazırlar."""

    logistic_regression = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )

    random_forest = RandomForestClassifier(
        n_estimators=80,
        max_depth=10,
        min_samples_leaf=20,
        class_weight="balanced",
        random_state=42,
        # Windows sandbox ortamında paralel iş parçacığı izin hatası verebildiği için
        # tek çekirdek kullanıyoruz. Veri boyutu bu proje için yine yönetilebilir.
        n_jobs=1,
    )

    return {
        "Lojistik Regresyon": logistic_regression,
        "Random Forest": random_forest,
    }


def evaluate_model(model_name: str, model, x_test: list[list[float]], y_test: list[int]) -> ModelMetrics:
    """Eğitilmiş modelin test verisi üzerindeki başarısını hesaplar."""

    predictions = model.predict(x_test)
    probabilities = model.predict_proba(x_test)[:, 1]
    tn, fp, fn, tp = confusion_matrix(y_test, predictions).ravel()

    return ModelMetrics(
        model_name=model_name,
        accuracy=round(accuracy_score(y_test, predictions), 4),
        precision=round(precision_score(y_test, predictions, zero_division=0), 4),
        recall=round(recall_score(y_test, predictions, zero_division=0), 4),
        f1=round(f1_score(y_test, predictions, zero_division=0), 4),
        roc_auc=round(roc_auc_score(y_test, probabilities), 4),
        true_negative=int(tn),
        false_positive=int(fp),
        false_negative=int(fn),
        true_positive=int(tp),
    )


def save_model(model, model_name: str, model_path: Path) -> None:
    """En iyi modeli ve kolon listesini pickle dosyası olarak kaydeder."""

    model_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_name": model_name,
        "feature_columns": FEATURE_COLUMNS,
        "model": model,
    }

    with model_path.open("wb") as file:
        pickle.dump(payload, file)


def save_metrics(result: TrainingResult, metrics_path: Path) -> None:
    """Eğitim sonuçlarını JSON dosyasına kaydeder."""

    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _to_float(value: str | None) -> float:
    """Boş veya hatalı değeri 0.0 kabul ederek float'a çevirir."""

    if value is None or str(value).strip() == "":
        return 0.0

    try:
        return float(str(value).strip())
    except ValueError:
        return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="CrediSense AI risk modeli eğitimi")
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
        help="Ortak formattaki eğitim CSV dosyası",
    )
    parser.add_argument(
        "--model-output",
        default=str(MODEL_PATH),
        help="Kaydedilecek model dosyası",
    )
    parser.add_argument(
        "--metrics-output",
        default=str(METRICS_PATH),
        help="Kaydedilecek metrik JSON dosyası",
    )
    args = parser.parse_args()

    result = train_risk_models(
        dataset_path=Path(args.dataset),
        model_path=Path(args.model_output),
        metrics_path=Path(args.metrics_output),
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
