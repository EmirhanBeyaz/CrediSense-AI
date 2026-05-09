from __future__ import annotations

"""Ham veri setlerini proje formatına dönüştürme aracı

Bu dosya farklı kaynaklardan gelen CSV veri setlerini ortak ve anlaşılır bir formata çevirir.

Önemli not:
Her veri seti aynı kolonlara sahip değildir. Bu yüzden bazı alanlar boş/0 kalabilir.
Örneğin Kaggle German Credit CSV dosyasında hedef risk etiketi yoktur. Bu dosya model eğitimi
için değil, özellik yapısını görmek için kullanılmalıdır.
"""

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


KAGGLE_FOLDER = Path("veri") / "kaynak_veri_setleri" / "kaggle"
OUTPUT_FOLDER = Path("veri") / "islenmis"

RAW_GIVE_ME_SOME_CREDIT = KAGGLE_FOLDER / "GiveMeSomeCredit" / "cs-training.csv"
RAW_GERMAN_CREDIT_KAGGLE = KAGGLE_FOLDER / "german_credit_data.csv"
RAW_TURKIYE_BANKACILIK = (
    KAGGLE_FOLDER
    / "Türkiye Bankacılık Ürünleri ve Kullanımı Veri Seti"
    / "turkiye_2026_bankacilik_verisi.csv"
)
RAW_HOME_CREDIT = KAGGLE_FOLDER / "Home Credit Default Risk" / "application_train.csv"

OUTPUT_GIVE_ME_SOME_CREDIT = OUTPUT_FOLDER / "give_me_some_credit_ortak_format.csv"
OUTPUT_GERMAN_CREDIT_KAGGLE = OUTPUT_FOLDER / "german_credit_kaggle_ortak_format.csv"
OUTPUT_TURKIYE_BANKACILIK = OUTPUT_FOLDER / "turkiye_bankacilik_ortak_format.csv"
OUTPUT_HOME_CREDIT = OUTPUT_FOLDER / "home_credit_application_train_ortak_format.csv"


COMMON_COLUMNS = [
    "kaynak_veri_seti",
    "musteri_id",
    "hedef_risk",
    "risk_seviyesi",
    "hedef_kaynagi",
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
class ConvertResult:
    dataset_name: str
    input_path: str
    output_path: str
    row_count: int
    high_risk_count: int
    low_risk_count: int
    unknown_risk_count: int
    missing_income_count: int
    missing_dependents_count: int


def convert_all() -> list[ConvertResult]:
    """Şimdilik desteklenen tüm veri setlerini ortak formata dönüştürür."""

    return [
        convert_give_me_some_credit(),
        convert_german_credit_kaggle(),
        convert_turkiye_bankacilik(),
        convert_home_credit_application_train(),
    ]


def convert_give_me_some_credit(
    input_path: Path = RAW_GIVE_ME_SOME_CREDIT,
    output_path: Path = OUTPUT_GIVE_ME_SOME_CREDIT,
) -> ConvertResult:
    """Give Me Some Credit eğitim dosyasını ortak proje formatına çevirir."""

    return _convert_csv(
        dataset_name="GiveMeSomeCredit",
        input_path=input_path,
        output_path=output_path,
        row_converter=_convert_give_me_some_credit_row,
    )


def convert_german_credit_kaggle(
    input_path: Path = RAW_GERMAN_CREDIT_KAGGLE,
    output_path: Path = OUTPUT_GERMAN_CREDIT_KAGGLE,
) -> ConvertResult:
    """Kaggle German Credit CSV dosyasını ortak formata çevirir.

    Bu dosyada hedef risk etiketi yoktur. Bu yüzden `hedef_risk` boş bırakılır.
    """

    return _convert_csv(
        dataset_name="GermanCreditKaggle",
        input_path=input_path,
        output_path=output_path,
        row_converter=_convert_german_credit_kaggle_row,
    )


def convert_turkiye_bankacilik(
    input_path: Path = RAW_TURKIYE_BANKACILIK,
    output_path: Path = OUTPUT_TURKIYE_BANKACILIK,
) -> ConvertResult:
    """Türkiye bankacılık veri setini ortak formata çevirir.

    Bu veri setinde doğrudan temerrüt etiketi yoktur. Risk hedefi, müşteri skoru,
    gecikme günü ve limit kullanım oranından türetilir.
    """

    return _convert_csv(
        dataset_name="TurkiyeBankacilik2026",
        input_path=input_path,
        output_path=output_path,
        row_converter=_convert_turkiye_bankacilik_row,
    )


def convert_home_credit_application_train(
    input_path: Path = RAW_HOME_CREDIT,
    output_path: Path = OUTPUT_HOME_CREDIT,
) -> ConvertResult:
    """Home Credit application_train dosyasını ortak formata çevirir."""

    return _convert_csv(
        dataset_name="HomeCreditDefaultRisk",
        input_path=input_path,
        output_path=output_path,
        row_converter=_convert_home_credit_row,
    )


def _convert_csv(dataset_name: str, input_path: Path, output_path: Path, row_converter) -> ConvertResult:
    """Ortak CSV dönüştürme akışı."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    row_count = 0
    high_risk_count = 0
    low_risk_count = 0
    unknown_risk_count = 0
    missing_income_count = 0
    missing_dependents_count = 0

    with input_path.open(encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)

        with output_path.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=COMMON_COLUMNS)
            writer.writeheader()

            for line_number, raw_row in enumerate(reader, start=1):
                converted_row = row_converter(raw_row, line_number)
                writer.writerow(converted_row)

                row_count += 1
                if converted_row["hedef_risk"] == 1:
                    high_risk_count += 1
                elif converted_row["hedef_risk"] == 0:
                    low_risk_count += 1
                else:
                    unknown_risk_count += 1

                missing_income_count += converted_row["aylik_gelir_eksik"]
                missing_dependents_count += converted_row["bakmakla_yukumlu_kisi_eksik"]

    return ConvertResult(
        dataset_name=dataset_name,
        input_path=str(input_path),
        output_path=str(output_path),
        row_count=row_count,
        high_risk_count=high_risk_count,
        low_risk_count=low_risk_count,
        unknown_risk_count=unknown_risk_count,
        missing_income_count=missing_income_count,
        missing_dependents_count=missing_dependents_count,
    )


def _convert_give_me_some_credit_row(raw_row: dict[str, str], line_number: int) -> dict:
    """Give Me Some Credit satırını ortak formata çevirir."""

    target = _to_int(raw_row.get("SeriousDlqin2yrs"))
    monthly_income_text = raw_row.get("MonthlyIncome", "")
    dependents_text = raw_row.get("NumberOfDependents", "")

    delay_30_59 = _to_int(raw_row.get("NumberOfTime30-59DaysPastDueNotWorse"))
    delay_60_89 = _to_int(raw_row.get("NumberOfTime60-89DaysPastDueNotWorse"))
    delay_90 = _to_int(raw_row.get("NumberOfTimes90DaysLate"))

    return _common_row(
        dataset_name="GiveMeSomeCredit",
        customer_id=raw_row.get("", "") or line_number,
        target=target,
        target_source="orijinal",
        age=_to_int(raw_row.get("age")),
        monthly_income=_to_float(monthly_income_text),
        monthly_income_missing=_is_empty(monthly_income_text),
        debt_ratio=_to_float(raw_row.get("DebtRatio")),
        revolving_ratio=_to_float(raw_row.get("RevolvingUtilizationOfUnsecuredLines")),
        delay_30_59=delay_30_59,
        delay_60_89=delay_60_89,
        delay_90=delay_90,
        open_credit_count=_to_int(raw_row.get("NumberOfOpenCreditLinesAndLoans")),
        real_estate_loan_count=_to_int(raw_row.get("NumberRealEstateLoansOrLines")),
        dependent_count=_to_int(dependents_text),
        dependent_missing=_is_empty(dependents_text),
    )


def _convert_german_credit_kaggle_row(raw_row: dict[str, str], line_number: int) -> dict:
    """German Credit Kaggle satırını ortak formata çevirir."""

    return _common_row(
        dataset_name="GermanCreditKaggle",
        customer_id=raw_row.get("", "") or line_number,
        target="",
        target_source="yok",
        age=_to_int(raw_row.get("Age")),
        monthly_income=0.0,
        monthly_income_missing=True,
        credit_amount=_to_float(raw_row.get("Credit amount")),
        term_months=_to_int(raw_row.get("Duration")),
        open_credit_count=_to_int(raw_row.get("Job")),
    )


def _convert_turkiye_bankacilik_row(raw_row: dict[str, str], line_number: int) -> dict:
    """Türkiye bankacılık satırını ortak formata çevirir."""

    limit_amount = _to_float(raw_row.get("Kredi_Karti_Limiti_TL"))
    debt_amount = _to_float(raw_row.get("Toplam_Borc_TL"))
    utilization_ratio_percent = _to_float(raw_row.get("Limit_Kullanim_Orani"))
    delay_days = _to_int(raw_row.get("Gecikme_Gun_Sayisi"))
    customer_score = _to_int(raw_row.get("Musteri_Skoru"))

    target = _derived_turkiye_risk_target(
        customer_score=customer_score,
        delay_days=delay_days,
        utilization_ratio_percent=utilization_ratio_percent,
    )

    return _common_row(
        dataset_name="TurkiyeBankacilik2026",
        customer_id=raw_row.get("Musteri_ID", "") or line_number,
        target=target,
        target_source="türetilmiş",
        age=_to_int(raw_row.get("Yas")),
        monthly_income=0.0,
        monthly_income_missing=True,
        credit_amount=limit_amount,
        monthly_payment=_to_float(raw_row.get("Son_Ay_Odenen_TL")),
        debt_ratio=_safe_divide(debt_amount, limit_amount),
        revolving_ratio=utilization_ratio_percent / 100,
        total_delay_count=1 if delay_days > 0 else 0,
        delay_days=delay_days,
    )


def _convert_home_credit_row(raw_row: dict[str, str], line_number: int) -> dict:
    """Home Credit application_train satırını ortak formata çevirir."""

    annual_income = _to_float(raw_row.get("AMT_INCOME_TOTAL"))
    credit_amount = _to_float(raw_row.get("AMT_CREDIT"))
    target = _to_int(raw_row.get("TARGET"))
    days_birth = _to_int(raw_row.get("DAYS_BIRTH"))

    return _common_row(
        dataset_name="HomeCreditDefaultRisk",
        customer_id=raw_row.get("SK_ID_CURR", "") or line_number,
        target=target,
        target_source="orijinal",
        age=abs(days_birth) // 365 if days_birth else 0,
        monthly_income=annual_income / 12 if annual_income else 0.0,
        monthly_income_missing=_is_empty(raw_row.get("AMT_INCOME_TOTAL")),
        credit_amount=credit_amount,
        monthly_payment=_to_float(raw_row.get("AMT_ANNUITY")),
        debt_ratio=_safe_divide(credit_amount, annual_income),
        dependent_count=_to_int(raw_row.get("CNT_CHILDREN")),
        dependent_missing=_is_empty(raw_row.get("CNT_CHILDREN")),
    )


def _common_row(
    dataset_name: str,
    customer_id: str | int,
    target: int | str,
    target_source: str,
    age: int = 0,
    monthly_income: float = 0.0,
    monthly_income_missing: bool = False,
    credit_amount: float = 0.0,
    term_months: int = 0,
    monthly_payment: float = 0.0,
    debt_ratio: float = 0.0,
    revolving_ratio: float = 0.0,
    delay_30_59: int = 0,
    delay_60_89: int = 0,
    delay_90: int = 0,
    total_delay_count: int | None = None,
    delay_days: int = 0,
    open_credit_count: int = 0,
    real_estate_loan_count: int = 0,
    dependent_count: int = 0,
    dependent_missing: bool = False,
) -> dict:
    """Ortak CSV satırı oluşturur."""

    if total_delay_count is None:
        total_delay_count = delay_30_59 + delay_60_89 + delay_90

    return {
        "kaynak_veri_seti": dataset_name,
        "musteri_id": customer_id,
        "hedef_risk": target,
        "risk_seviyesi": _risk_level_text(target),
        "hedef_kaynagi": target_source,
        "yas": age,
        "aylik_gelir": round(monthly_income, 2),
        "aylik_gelir_eksik": 1 if monthly_income_missing else 0,
        "kredi_tutari": round(credit_amount, 2),
        "vade_ay": term_months,
        "aylik_odeme_tutari": round(monthly_payment, 2),
        "borc_orani": round(debt_ratio, 4),
        "teminatsiz_kredi_kullanim_orani": round(revolving_ratio, 4),
        "gecikme_30_59_sayisi": delay_30_59,
        "gecikme_60_89_sayisi": delay_60_89,
        "gecikme_90_sayisi": delay_90,
        "toplam_gecikme_sayisi": total_delay_count,
        "gecikme_gun_sayisi": delay_days,
        "acik_kredi_sayisi": open_credit_count,
        "gayrimenkul_kredi_sayisi": real_estate_loan_count,
        "bakmakla_yukumlu_kisi_sayisi": dependent_count,
        "bakmakla_yukumlu_kisi_eksik": 1 if dependent_missing else 0,
    }


def _derived_turkiye_risk_target(
    customer_score: int,
    delay_days: int,
    utilization_ratio_percent: float,
) -> int:
    """Türkiye sentetik veri seti için basit türetilmiş risk etiketi üretir."""

    if delay_days >= 30:
        return 1
    if customer_score < 40:
        return 1
    if utilization_ratio_percent >= 90:
        return 1
    return 0


def _risk_level_text(target: int | str) -> str:
    """0/1 hedef değerini okunabilir risk seviyesine çevirir."""

    if target == 1:
        return "Yüksek"
    if target == 0:
        return "Düşük"
    return "Bilinmiyor"


def _safe_divide(left: float, right: float) -> float:
    """Sıfıra bölme hatası vermeyen oran hesabı."""

    return left / right if right else 0.0


def _to_float(value: str | None) -> float:
    """Boş veya hatalı değeri 0.0 kabul ederek float'a çevirir."""

    if _is_empty(value):
        return 0.0

    try:
        return float(str(value).strip())
    except ValueError:
        return 0.0


def _to_int(value: str | None) -> int:
    """Boş veya hatalı değeri 0 kabul ederek int'e çevirir."""

    if _is_empty(value):
        return 0

    try:
        return int(float(str(value).strip()))
    except ValueError:
        return 0


def _is_empty(value: str | None) -> bool:
    """CSV hücresinin boş olup olmadığını kontrol eder."""

    return value is None or str(value).strip() == ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Ham veri setlerini ortak proje formatına dönüştürür")
    parser.add_argument(
        "--dataset",
        choices=["all", "give_me_some_credit", "german_credit", "turkiye_bankacilik", "home_credit"],
        default="all",
        help="Dönüştürülecek veri seti",
    )
    args = parser.parse_args()

    if args.dataset == "all":
        results = convert_all()
    elif args.dataset == "give_me_some_credit":
        results = [convert_give_me_some_credit()]
    elif args.dataset == "german_credit":
        results = [convert_german_credit_kaggle()]
    elif args.dataset == "turkiye_bankacilik":
        results = [convert_turkiye_bankacilik()]
    else:
        results = [convert_home_credit_application_train()]

    print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
