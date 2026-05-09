from __future__ import annotations

"""Katman 04 - Davranışsal Finans Özellikleri

Bu katmanın görevi, banka hesap hareketlerini sayısal özelliklere çevirmektir.

Risk modeli doğrudan ham banka satırlarıyla çalışmak yerine şu tarz özet değerleri kullanır:
- Ortalama aylık gelir
- Ortalama aylık gider
- Ortalama bakiye
- Harcama / gelir oranı
- Gelir düzenliliği
- Büyük işlem oranı
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from backend.credisense.katman_01_pdf_okuma import extract_pdf_text
    from backend.credisense.katman_02_belge_anlama import (
        BankStatementInfo,
        PayrollInfo,
        parse_bank_statement,
        parse_payroll,
    )
else:
    from .katman_01_pdf_okuma import extract_pdf_text
    from .katman_02_belge_anlama import BankStatementInfo, PayrollInfo, parse_bank_statement, parse_payroll


def bank_features(bank: BankStatementInfo | None) -> dict[str, float]:
    """Banka dökümünden finansal özellikler üretir."""

    if not bank or not bank.transactions:
        return _empty_bank_features()

    inflow_by_month: dict[str, float] = defaultdict(float)
    outflow_by_month: dict[str, float] = defaultdict(float)
    balances: list[float] = []
    transaction_amounts: list[float] = []

    for transaction in bank.transactions:
        month = _month_key(transaction.date)
        inflow_by_month[month] += transaction.inflow
        outflow_by_month[month] += transaction.outflow
        balances.append(transaction.balance)

        if transaction.inflow > 0:
            transaction_amounts.append(transaction.inflow)
        if transaction.outflow > 0:
            transaction_amounts.append(transaction.outflow)

    months = sorted(set(inflow_by_month) | set(outflow_by_month))
    average_income = _average([inflow_by_month[month] for month in months])
    average_expense = _average([outflow_by_month[month] for month in months])
    average_balance = _average(balances)

    salary_values = _salary_values(bank)
    income_stability = _stability_score(salary_values)
    large_transaction_ratio = _large_transaction_ratio(transaction_amounts, average_income)

    return {
        "avg_monthly_income": round(average_income, 2),
        "avg_monthly_expense": round(average_expense, 2),
        "avg_balance": round(average_balance, 2),
        "expense_income_ratio": round(average_expense / average_income, 2) if average_income else 0.0,
        "income_stability": round(income_stability, 2),
        "large_transaction_ratio": round(large_transaction_ratio, 2),
    }


def payroll_features(payroll: PayrollInfo | None) -> dict[str, float]:
    """Bordrodan risk modeline gidecek temel sayısal alanları üretir."""

    declared_salary = payroll.net_salary if payroll else 0.0
    return {"declared_salary": round(declared_salary, 2)}


def _empty_bank_features() -> dict[str, float]:
    """Banka dökümü yoksa tüm finansal değerleri 0 döndürür."""

    return {
        "avg_monthly_income": 0.0,
        "avg_monthly_expense": 0.0,
        "avg_balance": 0.0,
        "expense_income_ratio": 0.0,
        "income_stability": 0.0,
        "large_transaction_ratio": 0.0,
    }


def _month_key(date_text: str) -> str:
    """'15.03.2026' tarihinden '03.2026' ay anahtarını üretir."""

    return date_text[3:10]


def _salary_values(bank: BankStatementInfo) -> list[float]:
    """Açıklamasında maaş geçen gelirleri listeler."""

    values: list[float] = []
    for transaction in bank.transactions:
        description = _normalize_text(transaction.description)
        if transaction.inflow > 0 and "maas" in description:
            values.append(transaction.inflow)
    return values


def _large_transaction_ratio(amounts: list[float], average_income: float) -> float:
    """Gelire göre büyük kabul edilen işlem oranını hesaplar."""

    if not amounts:
        return 0.0

    large_transaction_limit = max(average_income * 0.5, 1.0)
    large_count = sum(1 for amount in amounts if amount >= large_transaction_limit)
    return large_count / len(amounts)


def _stability_score(values: list[float]) -> float:
    """Gelirlerin ne kadar düzenli olduğunu 0-1 arasında hesaplar.

    Değer 1'e yaklaştıkça gelir daha düzenli kabul edilir.
    """

    if len(values) == 0:
        return 0.0
    if len(values) == 1:
        return 1.0

    average_value = _average(values)
    if average_value == 0:
        return 0.0

    variance = sum((value - average_value) ** 2 for value in values) / len(values)
    standard_deviation = variance ** 0.5
    coefficient_of_variation = standard_deviation / average_value
    return max(0.0, min(1.0, 1.0 - coefficient_of_variation))


def _average(values: list[float]) -> float:
    """Boş liste geldiğinde hata vermeyen ortalama hesabı."""

    return sum(values) / len(values) if values else 0.0


def _normalize_text(value: str) -> str:
    """Türkçe karakter ve boşluk farklarını azaltır."""

    translation_table = str.maketrans("ÇĞİÖŞÜçğıöşü", "CGIOSUcgiosu")
    normalized = value.translate(translation_table).lower()
    return " ".join(normalized.split())


def main() -> None:
    parser = argparse.ArgumentParser(description="Katman 04 - Finansal özellik çıkarımı")
    parser.add_argument("bank_pdf", help="Banka hesap dökümü PDF dosyası")
    parser.add_argument("--payroll-pdf", help="İsteğe bağlı maaş bordrosu PDF dosyası")
    args = parser.parse_args()

    bank_text = extract_pdf_text(args.bank_pdf)
    bank = parse_bank_statement(bank_text)

    features = bank_features(bank)

    if args.payroll_pdf:
        payroll_text = extract_pdf_text(args.payroll_pdf)
        payroll = parse_payroll(payroll_text)
        features.update(payroll_features(payroll))

    print(json.dumps(features, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
