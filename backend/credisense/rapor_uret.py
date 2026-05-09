from __future__ import annotations

"""Analiz sonucundan rapor üretme aracı

Bu dosya terminal analizinin ürettiği JSON sonucunu iki dosyaya çevirir:

1. Tam JSON raporu
2. İnsan tarafından okunabilir Markdown özet raporu

Bu raporlar ileride uzman paneli veya web arayüzü için temel çıktı olarak kullanılabilir.
"""

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_REPORT_FOLDER = Path("raporlar")


@dataclass
class ReportFiles:
    """Üretilen rapor dosyalarının yolları."""

    json_report: str
    markdown_report: str


def create_analysis_reports(
    analysis_result: dict,
    output_folder: Path = DEFAULT_REPORT_FOLDER,
) -> ReportFiles:
    """Analiz sonucundan JSON ve Markdown rapor dosyaları üretir."""

    output_folder.mkdir(parents=True, exist_ok=True)

    file_stem = _report_file_stem(analysis_result)
    json_path = output_folder / f"{file_stem}.json"
    markdown_path = output_folder / f"{file_stem}.md"

    json_path.write_text(
        json.dumps(analysis_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(
        build_markdown_report(analysis_result),
        encoding="utf-8",
    )

    return ReportFiles(
        json_report=str(json_path),
        markdown_report=str(markdown_path),
    )


def build_markdown_report(analysis_result: dict) -> str:
    """Analiz sonucunu okunabilir Markdown raporuna çevirir."""

    documents = analysis_result.get("documents", {})
    application_form = analysis_result.get("application_form", {})
    features = analysis_result.get("features", {})
    consistency = analysis_result.get("consistency", {})
    risk = analysis_result.get("risk", {})
    decision = risk.get("decision_summary", {})

    identity = documents.get("identity") or {}
    payroll = documents.get("payroll") or {}
    bank = documents.get("bank_statement") or {}

    lines = [
        "# CrediSense AI Başvuru Analiz Raporu",
        "",
        f"Rapor tarihi: {_current_time_text()}",
        "",
        "## Karar Özeti",
        "",
        f"- Karar kodu: `{decision.get('decision_code', '')}`",
        f"- Karar metni: {decision.get('decision_text', '')}",
        f"- Risk seviyesi: {risk.get('risk_level', '')}",
        f"- Nihai risk skoru: {_format_score(risk.get('risk_score'))}",
        f"- Karar kaynağı: `{risk.get('decision_source', '')}`",
        f"- Kullanılan model: {risk.get('model_name') or 'Yok'}",
        f"- Model giriş kapsamı: {_format_percent(risk.get('model_input_coverage'))}",
        "",
        "## Başvuru Sahibi",
        "",
        f"- Ad soyad: {identity.get('full_name') or application_form.get('ad_soyad', '')}",
        f"- Test kimlik no: {identity.get('test_id') or application_form.get('tckn_test_no', '')}",
        f"- Doğum tarihi: {identity.get('birth_date') or application_form.get('dogum_tarihi', '')}",
        "",
        "## Belge Özeti",
        "",
        f"- Bordro çalışanı: {payroll.get('full_name', '')}",
        f"- İşveren: {payroll.get('employer', '')}",
        f"- Bordro dönemi: {payroll.get('period', '')}",
        f"- Net maaş: {_format_money(payroll.get('net_salary'))}",
        f"- Banka hesap sahibi: {bank.get('full_name', '')}",
        f"- Banka dönem: {bank.get('period', '')}",
        f"- Banka işlem sayısı: {bank.get('transaction_count', '')}",
        "",
        "## Finansal Göstergeler",
        "",
        f"- Ortalama aylık gelir: {_format_money(features.get('avg_monthly_income'))}",
        f"- Ortalama aylık gider: {_format_money(features.get('avg_monthly_expense'))}",
        f"- Ortalama bakiye: {_format_money(features.get('avg_balance'))}",
        f"- Harcama / gelir oranı: {_format_score(features.get('expense_income_ratio'))}",
        f"- Borç / gelir oranı: {_format_score(features.get('debt_to_income_ratio'))}",
        f"- Talep edilen kredi tutarı: {_format_money(features.get('requested_credit_amount'))}",
        f"- Mevcut toplam borç: {_format_money(features.get('current_total_debt'))}",
        "",
        "## Tutarlılık ve Anomali",
        "",
        f"- Tutarlılık skoru: {_format_score(consistency.get('consistency_score'))}",
        f"- Anomali skoru: {_format_score(consistency.get('anomaly_score'))}",
        "",
        "### Başarılı Kontroller",
        "",
    ]

    lines.extend(_markdown_list(consistency.get("positive_checks", [])))
    lines.extend(["", "### Uyarılar", ""])
    lines.extend(_markdown_list(consistency.get("flags", [])))
    lines.extend(["", "## Risk Gerekçeleri", ""])
    lines.extend(_markdown_list(risk.get("reasons", [])))
    lines.extend([""])

    return "\n".join(lines)


def _report_file_stem(analysis_result: dict) -> str:
    """Rapor dosya adını tarih ve kişi adına göre üretir."""

    documents = analysis_result.get("documents", {})
    identity = documents.get("identity") or {}
    application_form = analysis_result.get("application_form", {})
    full_name = identity.get("full_name") or application_form.get("ad_soyad") or "basvuru"
    safe_name = _safe_file_text(full_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{safe_name}_analiz_raporu"


def _safe_file_text(value: str) -> str:
    """Dosya adı için güvenli metin üretir."""

    value = value.lower().strip()
    value = value.translate(str.maketrans("çğıöşü", "cgiosu"))
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "basvuru"


def _markdown_list(items: list[str]) -> list[str]:
    """Listeyi Markdown madde listesine çevirir."""

    if not items:
        return ["- Yok"]
    return [f"- {item}" for item in items]


def _format_money(value) -> str:
    """Sayısal değeri TL metni olarak biçimlendirir."""

    number = _to_float(value)
    return f"{number:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_score(value) -> str:
    """Skorları kısa metne çevirir."""

    return f"{_to_float(value):.2f}"


def _format_percent(value) -> str:
    """0-1 arası değeri yüzde metnine çevirir."""

    return f"%{_to_float(value) * 100:.0f}"


def _current_time_text() -> str:
    """Rapor tarihini okunabilir formatta döndürür."""

    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def _to_float(value) -> float:
    """Boş veya hatalı değeri 0.0 kabul ederek sayıya çevirir."""

    if value is None or str(value).strip() == "":
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def report_files_to_dict(report_files: ReportFiles) -> dict:
    """ReportFiles nesnesini JSON'a uygun sözlüğe çevirir."""

    return asdict(report_files)
