from __future__ import annotations

"""Katman 03 - Tutarlılık ve Anomali Kontrolü

Bu katmanın görevi, Katman 02'de çıkarılan alanları birbiriyle karşılaştırmaktır.

Bu katmanda yapılan işler:
- Kimlik, bordro ve banka dökümündeki ad-soyad bilgisini karşılaştırma
- Kimlik numarasının belgeler arasında aynı olup olmadığını kontrol etme
- Bordrodaki maaş ile banka hesabına gelen maaşı eşleştirme
- Banka hareketlerinde olağandışı büyük çıkışları işaretleme

Bu katmanda yapılmayan işler:
- PDF okuma
- Belge alanı çıkarma
- Nihai risk skoru hesaplama
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from backend.credisense.katman_01_pdf_okuma import extract_pdf_text
    from backend.credisense.katman_02_belge_anlama import (
        BankStatementInfo,
        IdentityInfo,
        PayrollInfo,
        detect_document_type,
        parse_bank_statement,
        parse_identity,
        parse_payroll,
    )
else:
    from .katman_01_pdf_okuma import extract_pdf_text
    from .katman_02_belge_anlama import (
        BankStatementInfo,
        IdentityInfo,
        PayrollInfo,
        detect_document_type,
        parse_bank_statement,
        parse_identity,
        parse_payroll,
    )


@dataclass
class ConsistencyResult:
    """Katman 03'ün dışarı verdiği standart sonuç yapısı."""

    consistency_score: float
    anomaly_score: float
    flags: list[str] = field(default_factory=list)
    positive_checks: list[str] = field(default_factory=list)


def evaluate_consistency(
    identity: IdentityInfo | None,
    payroll: PayrollInfo | None,
    bank: BankStatementInfo | None,
) -> ConsistencyResult:
    """Belgeler arasındaki uyumu ve basit anomalileri hesaplar."""

    checks = _build_consistency_checks(identity, payroll, bank)
    positive_checks: list[str] = []
    flags: list[str] = []

    for passed, success_message, fail_message in checks:
        if passed:
            positive_checks.append(success_message)
        else:
            flags.append(fail_message)

    anomaly_flags = _find_unusual_transactions(bank)
    flags.extend(anomaly_flags)

    passed_count = len(positive_checks)
    total_check_count = len(checks)
    consistency_score = passed_count / total_check_count if total_check_count else 0.0
    anomaly_score = min(1.0, len(anomaly_flags) * 0.25)

    return ConsistencyResult(
        consistency_score=round(consistency_score, 2),
        anomaly_score=round(anomaly_score, 2),
        flags=flags,
        positive_checks=positive_checks,
    )


def _build_consistency_checks(
    identity: IdentityInfo | None,
    payroll: PayrollInfo | None,
    bank: BankStatementInfo | None,
) -> list[tuple[bool, str, str]]:
    """Yapılacak kontrolleri liste halinde hazırlar.

    Her eleman şu yapıya sahiptir:
    (kontrol_sonucu, başarılı_mesajı, başarısız_mesajı)
    """

    checks: list[tuple[bool, str, str]] = []

    if identity and payroll:
        checks.append(
            (
                _same_text(identity.full_name, payroll.full_name),
                "Kimlik ve bordro ad-soyad bilgisi uyumlu.",
                "Kimlik ve bordro ad-soyad bilgisi uyumsuz.",
            )
        )

    if identity and bank:
        checks.append(
            (
                _same_text(identity.full_name, bank.full_name),
                "Kimlik ve banka hesap sahibi bilgisi uyumlu.",
                "Kimlik ve banka hesap sahibi bilgisi uyumsuz.",
            )
        )
        checks.append(
            (
                bool(identity.test_id and identity.test_id == bank.test_id),
                "Kimlik test numarası banka dökümüyle uyumlu.",
                "Kimlik test numarası banka dökümüyle uyumsuz.",
            )
        )

    if payroll and bank:
        salary_inflows = _salary_inflows(bank)
        salary_match = _has_matching_salary(salary_inflows, payroll.net_salary)
        employer_match = _has_employer_in_salary_description(salary_inflows, payroll.employer)

        checks.append(
            (
                salary_match,
                "Bordrodaki net maaş banka maaş girişiyle uyumlu.",
                "Bordrodaki net maaş banka maaş girişiyle eşleşmiyor.",
            )
        )
        checks.append(
            (
                employer_match,
                "Bordrodaki işveren banka maaş açıklamasında geçiyor.",
                "Bordrodaki işveren banka maaş açıklamasında bulunamadı.",
            )
        )

    return checks


def _salary_inflows(bank: BankStatementInfo) -> list:
    """Banka hareketleri içinden maaş girişlerini seçer."""

    salary_rows = []
    for transaction in bank.transactions:
        description = _normalize_text(transaction.description)
        if transaction.inflow > 0 and "maas" in description:
            salary_rows.append(transaction)
    return salary_rows


def _has_matching_salary(salary_inflows: list, payroll_salary: float) -> bool:
    """Bordrodaki net maaş ile banka giriş tutarlarından biri eşleşiyor mu bakar."""

    for transaction in salary_inflows:
        if abs(transaction.inflow - payroll_salary) < 1:
            return True
    return False


def _has_employer_in_salary_description(salary_inflows: list, employer: str) -> bool:
    """Maaş açıklamasında işveren adının geçip geçmediğini kontrol eder."""

    normalized_employer = _normalize_text(employer)
    if not normalized_employer:
        return False

    for transaction in salary_inflows:
        description = _normalize_text(transaction.description)
        short_employer = _short_company_name(normalized_employer)
        if normalized_employer in description or (short_employer and short_employer in description):
            return True
    return False


def _find_unusual_transactions(bank: BankStatementInfo | None) -> list[str]:
    """Maaşa göre olağandışı büyük para çıkışlarını bulur."""

    if not bank or not bank.transactions:
        return ["Banka hesap dökümünden işlem çıkarılamadı."]

    salary_values = [
        transaction.inflow
        for transaction in bank.transactions
        if transaction.inflow > 0 and "maas" in _normalize_text(transaction.description)
    ]

    average_salary = sum(salary_values) / len(salary_values) if salary_values else 0.0
    if average_salary == 0:
        return ["Düzenli maaş girişi bulunamadı."]

    flags: list[str] = []
    high_outflow_limit = average_salary * 0.60

    for transaction in bank.transactions:
        if transaction.outflow > high_outflow_limit:
            flags.append(
                f"Olağandışı yüksek çıkış tespit edildi: "
                f"{transaction.date} - {transaction.outflow:.2f} TL"
            )

    return flags


def _same_text(left: str, right: str) -> bool:
    """İki metni sadeleştirerek karşılaştırır."""

    return bool(left and right and _normalize_text(left) == _normalize_text(right))


def _normalize_text(value: str) -> str:
    """Türkçe karakter ve boşluk farklarını azaltır."""

    translation_table = str.maketrans("ÇĞİÖŞÜçğıöşü", "CGIOSUcgiosu")
    normalized = value.translate(translation_table).lower()
    return " ".join(normalized.split())


def _short_company_name(value: str) -> str:
    """Şirket unvan eklerini sadeleştirerek maaş açıklamasıyla eşleşmeyi kolaylaştırır."""

    cleaned = value.replace("a.s.", "").replace("a.ş.", "").replace("ltd.", "")
    cleaned = cleaned.replace("sti.", "").replace("şti.", "")
    cleaned = cleaned.replace("ltd sti", "").replace("ltd şti", "")
    cleaned = cleaned.replace("anonim sirketi", "").replace("limited sirketi", "")
    return " ".join(cleaned.split())


def _parse_documents_for_test(pdf_paths: list[str]) -> tuple[IdentityInfo | None, PayrollInfo | None, BankStatementInfo | None]:
    """Katmanı terminalden tek başına test etmek için PDF'leri okur."""

    identity: IdentityInfo | None = None
    payroll: PayrollInfo | None = None
    bank: BankStatementInfo | None = None

    for pdf_path in pdf_paths:
        text = extract_pdf_text(pdf_path)
        document_type = detect_document_type(text)

        if document_type == "identity":
            identity = parse_identity(text)
        elif document_type == "payroll":
            payroll = parse_payroll(text)
        elif document_type == "bank_statement":
            bank = parse_bank_statement(text)

    return identity, payroll, bank


def main() -> None:
    parser = argparse.ArgumentParser(description="Katman 03 - Tutarlılık ve anomali kontrolü")
    parser.add_argument("pdfs", nargs="+", help="Kontrol edilecek PDF dosyaları")
    args = parser.parse_args()

    identity, payroll, bank = _parse_documents_for_test(args.pdfs)
    result = evaluate_consistency(identity, payroll, bank)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
