from __future__ import annotations

"""Katman 02 - Belge Anlama

Bu katmanın görevi Katman 01'den gelen metni anlamlandırmaktır.

Bu katmanda yapılan işler:
- Belge türünü tahmin etme
- Kimlik belgesinden temel alanları çıkarma
- Maaş bordrosundan gelir alanlarını çıkarma
- Banka hesap dökümünden hesap hareketlerini çıkarma

Bu katmanda yapılmayan işler:
- Belgeler arası tutarlılık kontrolü
- Finansal özellik skoru üretme
- Nihai kredi riski tahmini
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from backend.credisense.katman_01_pdf_okuma import extract_pdf
else:
    from .katman_01_pdf_okuma import extract_pdf


# ---------------------------------------------------------------------------
# Katman 02 veri yapıları
# ---------------------------------------------------------------------------


@dataclass
class IdentityInfo:
    full_name: str = ""
    test_id: str = ""
    birth_date: str = ""


@dataclass
class PayrollInfo:
    full_name: str = ""
    employer: str = ""
    period: str = ""
    net_salary: float = 0.0


@dataclass
class Transaction:
    date: str
    description: str
    inflow: float
    outflow: float
    balance: float


@dataclass
class BankStatementInfo:
    full_name: str = ""
    test_id: str = ""
    iban: str = ""
    period: str = ""
    transactions: list[Transaction] = field(default_factory=list)


@dataclass
class ParsedDocuments:
    identity: IdentityInfo | None = None
    payroll: PayrollInfo | None = None
    bank_statement: BankStatementInfo | None = None
    document_texts: dict[str, str] = field(default_factory=dict)
    document_quality: list[dict] = field(default_factory=list)


@dataclass
class DocumentUnderstandingResult:
    document_type: str
    confidence: float
    fields: dict
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Dışarıdan kullanılan ana fonksiyonlar
# ---------------------------------------------------------------------------


def understand_document_text(text: str) -> DocumentUnderstandingResult:
    """Metni alır, belge türünü bulur ve ilgili alanları çıkarır."""

    document_type = detect_document_type(text)

    if document_type == "identity":
        fields = asdict(parse_identity(text))
    elif document_type == "payroll":
        fields = asdict(parse_payroll(text))
    elif document_type == "bank_statement":
        bank_statement = parse_bank_statement(text)
        fields = {
            "full_name": bank_statement.full_name,
            "test_id": bank_statement.test_id,
            "iban": bank_statement.iban,
            "period": bank_statement.period,
            "transaction_count": len(bank_statement.transactions),
            "transactions": [asdict(transaction) for transaction in bank_statement.transactions],
        }
    elif document_type == "consent":
        fields = parse_consent_document(text)
    else:
        fields = {}

    missing_fields = _missing_fields(document_type, fields)
    confidence = _field_confidence(fields)
    return DocumentUnderstandingResult(
        document_type=document_type,
        confidence=confidence,
        fields=fields,
        missing_fields=missing_fields,
        warnings=_understanding_warnings(document_type, missing_fields),
    )


def detect_document_type(text: str) -> str:
    """Belgenin kimlik, bordro veya banka dökümü olduğunu anahtar kelimelerle tahmin eder."""

    normalized_text = _normalize_for_search(text)
    scores = {
        "identity": _keyword_score(
            normalized_text,
            [
                "kimlik bilgileri",
                "test kimlik belgesi",
                "kisi bilgileri",
                "test kimlik no",
                "tckn test no",
                "dogum tarihi",
            ],
        ),
        "payroll": _keyword_score(
            normalized_text,
            [
                "maas bordrosu",
                "gelir belgesi",
                "net odenecek",
                "net maas",
                "brut ucret",
                "kesinti bilgileri",
                "isveren adi",
                "bordro donemi",
            ],
        ),
        "bank_statement": _keyword_score(
            normalized_text,
            [
                "banka hesap dokumu",
                "hesap hareketleri",
                "hesap sahibi",
                "musteri",
                "toplam gelen",
                "toplam giden",
                "giris",
                "cikis",
                "bakiye",
            ],
        ),
        "consent": _keyword_score(
            normalized_text,
            ["acik riza", "kvkk onayi", "veri isleme", "onay durumu", "kabul edildi"],
        ),
    }

    best_type = "unknown"
    best_score = 0
    for document_type, score in scores.items():
        if score > best_score:
            best_type = document_type
            best_score = score

    return best_type


def parse_identity(text: str) -> IdentityInfo:
    """Kimlik test belgesinden kişi bilgilerini çıkarır."""

    return IdentityInfo(
        full_name=_find_identity_name(text),
        test_id=_find_test_id(text),
        birth_date=_find_birth_date(text),
    )


def parse_payroll(text: str) -> PayrollInfo:
    """Maaş bordrosundan çalışan ve maaş bilgilerini çıkarır."""

    return PayrollInfo(
        full_name=_first_non_empty(
            _value_after_label(text, "Çalışan Ad Soyad"),
            _value_after_label(text, "Calisan Ad Soyad"),
            _value_after_label(text, "Ad Soyad"),
        ),
        employer=_find_company_name(text),
        period=_find_payroll_period(text),
        net_salary=_find_net_salary(text),
    )


def parse_bank_statement(text: str) -> BankStatementInfo:
    """Banka hesap dökümünden hesap sahibi ve işlem listesini çıkarır."""

    return BankStatementInfo(
        full_name=_first_non_empty(
            _value_after_label(text, "Ad Soyad"),
            _find_bank_customer_name(text),
            _value_after_label(text, "Hesap Sahibi"),
        ),
        test_id=_find_test_id(text),
        iban=_first_non_empty(
            _value_after_label(text, "Hesap No / IBAN"),
            _value_after_label(text, "IBAN"),
        ),
        period=_find_bank_statement_period(text),
        transactions=_parse_transactions(text),
    )


def parse_consent_document(text: str) -> dict:
    """KVKK/açık rıza metninden temel onay bilgisini çıkarır."""

    return {
        "full_name": _first_non_empty(
            _value_after_label(text, "Ad Soyad"),
            _find_name_before_test_id(text),
        ),
        "test_id": _find_test_id(text),
        "consent_status": _find_consent_status(text),
    }


def parse_money(value: str) -> float:
    """Türkçe para formatını float değere çevirir.

    Örnek:
    - "42.350,75" -> 42350.75
    - "0,00" -> 0.0
    """

    cleaned_value = value.strip().replace("TL", "").replace(" ", "")
    if cleaned_value in {"", "-"}:
        return 0.0
    if "," in cleaned_value:
        cleaned_value = cleaned_value.replace(".", "").replace(",", ".")

    try:
        return float(cleaned_value)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Belge alanı çıkarma yardımcıları
# ---------------------------------------------------------------------------


def _parse_transactions(text: str) -> list[Transaction]:
    """Banka hesap dökümündeki hareket satırlarını Transaction listesine çevirir."""

    transactions: list[Transaction] = []

    transaction_pattern = re.compile(
        r"(?P<date>\d{2}\.\d{2}\.\d{4})\s+"
        r"(?P<description>.+?)\s+"
        r"(?P<inflow>\d{1,3}(?:\.\d{3})*,\d{2}|0,00|-)\s+(?:TL\s+)?"
        r"(?P<outflow>\d{1,3}(?:\.\d{3})*,\d{2}|0,00|-)\s+(?:TL\s+)?"
        r"(?P<balance>\d{1,3}(?:\.\d{3})*,\d{2}|0,00)"
    )

    for match in transaction_pattern.finditer(text):
        transactions.append(
            Transaction(
                date=match.group("date"),
                description=match.group("description").strip(),
                inflow=parse_money(match.group("inflow")),
                outflow=parse_money(match.group("outflow")),
                balance=parse_money(match.group("balance")),
            )
        )

    return transactions


def _find_identity_name(text: str) -> str:
    """Kimlik metninde ad ve soyadı bulur."""

    direct_match = re.search(r"\bAd\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+Soyad\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)", text)
    if direct_match:
        return f"{direct_match.group(1)} {direct_match.group(2)}"

    table_match = re.search(r"Ad Soyad\s+([A-Za-zÇĞİÖŞÜçğıöşü]+\s+[A-Za-zÇĞİÖŞÜçğıöşü]+)", text)
    return table_match.group(1) if table_match else ""


def _find_bank_customer_name(text: str) -> str:
    """Banka dökümündeki müşteri adını bulur."""

    customer_name = _first_non_empty(
        _value_after_label(text, "Müşteri"),
        _value_after_label(text, "Musteri"),
    )
    if customer_name.lower() in {"bilgileri", "bilgi"}:
        return ""
    return customer_name


def _find_test_id(text: str) -> str:
    """Metin içindeki 11 haneli sentetik kimlik numarasını bulur."""

    match = re.search(
        r"(?:TCKN(?:\s+Benzeri)?(?:\s+Test\s+No)?|Test\s+Kimlik\s+No)\s+([A-Z0-9-]{6,20}|\d{11})",
        text,
        re.I,
    )
    if match:
        return match.group(1)

    fallback_match = re.search(r"\b(TEST-TCKN-\d{6})\b", text, re.I)
    return fallback_match.group(1) if fallback_match else ""


def _find_birth_date(text: str) -> str:
    """Kimlik metninden doğum tarihini kabul edilen formatlardan biriyle bulur."""

    return _first_non_empty(
        _find_date_after_label(text, "Doğum Tarihi"),
        _find_date_after_label(text, "Dogum Tarihi"),
    )


def _find_date_after_label(text: str, label: str) -> str:
    """Belirli bir etiketten sonra gelen tarihi bulur."""

    match = re.search(re.escape(label) + r"\s+(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})", text, re.I)
    return match.group(1) if match else ""


def _find_net_salary(text: str) -> float:
    """Bordrodaki net ödenecek tutarı bulur."""

    normal_value = _first_non_zero(
        _find_money_after_label(text, "Net Ödenecek Tutar"),
        _find_money_after_label(text, "Net Odenecek Tutar"),
        _find_money_after_label(text, "Net Maaş"),
        _find_money_after_label(text, "Net Maas"),
    )
    if normal_value:
        return normal_value

    # Chrome PDF çıktısında bazen tutar etiketten önce gelebiliyor.
    reverse_match = re.search(
        r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+TL\s+Brut\s+Net Odenecek Tutar",
        text,
        re.I,
    )
    if reverse_match:
        return parse_money(reverse_match.group(1))

    return 0.0


def _find_money_after_label(text: str, label: str) -> float:
    """Bir etiketten sonra gelen para değerini bulur."""

    pattern = re.compile(re.escape(label) + r"\s+(\d{1,3}(?:\.\d{3})*,\d{2})", re.I)
    match = pattern.search(text)
    return parse_money(match.group(1)) if match else 0.0


def _find_payroll_period(text: str) -> str:
    """Bordro dönemini bulur. Örnek: 2026 / 03"""

    label_value = _first_non_empty(
        _value_after_label(text, "Bordro Dönemi"),
        _value_after_label(text, "Bordro Donemi"),
    )
    if label_value:
        return label_value

    match = re.search(r"(\d{4}\s*/\s*\d{2})", text)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _find_bank_statement_period(text: str) -> str:
    """Banka dökümü dönemini bulur."""

    period_match = re.search(
        r"(?:Dönem|Donem):?\s*(\d{2}\.\d{2}\.\d{4}\s*-\s*\d{2}\.\d{2}\.\d{4})",
        text,
        re.I,
    )
    if period_match:
        return period_match.group(1)

    dates = re.findall(r"\d{2}\.\d{2}\.\d{4}", text)
    return f"{min(dates)} - {max(dates)}" if dates else ""


def _find_company_name(text: str) -> str:
    """Bordro içindeki işveren adını bulur."""

    known_company_match = re.search(r"(Nova Veri Teknolojileri A\.S\.)", text)
    if known_company_match:
        return known_company_match.group(1)
    return _first_non_empty(
        _value_after_label(text, "İşveren Adı"),
        _value_after_label(text, "Isveren Adi"),
        _value_after_label(text, "İşveren"),
        _value_after_label(text, "Isveren"),
    )


def _value_after_label(text: str, label: str) -> str:
    """Tablo metninde bir etiketten sonra gelen değeri yakalar.

    PDF metni tabloyu düz metne çevirdiği için hücre sınırları kaybolabilir. Bu yüzden
    bir sonraki bilinen etikete kadar olan bölümü değer olarak alıyoruz.
    """

    stop_words = [
        "TCKN",
        "Soyad",
        "Ad ",
        "Adı",
        "Adi",
        "Dogum",
        "Doğum",
        "Belge",
        "Uyruk",
        "Departman",
        "Gorev",
        "Görev",
        "Ise",
        "İşe",
        "Calisma",
        "Çalışma",
        "Banka",
        "IBAN",
        "Adres",
        "Telefon",
        "E-posta",
        "Donem",
        "Dönem",
        "Duzenleme",
        "Düzenleme",
        "Bordro",
        "Tarih",
        "Aciklama",
        "Açıklama",
        "Para",
        "Hesap",
        "Meslek",
        "Brüt",
        "Brut",
        "Toplam",
        "Net",
        "Ödeme",
        "Odeme",
        "Çıkarılacak",
        "Cikarilacak",
    ]

    search_text = text.replace("|", " ")

    stop_pattern = "|".join(
        re.escape(stop_word) for stop_word in stop_words if stop_word.strip() != label.strip()
    )
    value_pattern = re.compile(
        rf"{re.escape(label)}\s+(.+?)(?=\s+(?:{stop_pattern})\b|$)",
        re.I,
    )

    match = value_pattern.search(search_text)
    if not match:
        return ""

    value = match.group(1).strip(" :-|")
    return re.sub(r"\s+", " ", value).strip()


# ---------------------------------------------------------------------------
# Genel yardımcılar
# ---------------------------------------------------------------------------


def _keyword_score(text: str, keywords: list[str]) -> int:
    """Metinde kaç anahtar kelime geçtiğini sayar."""

    return sum(1 for keyword in keywords if keyword in text)


def _normalize_for_search(text: str) -> str:
    """Türkçe karakterleri sadeleştirip küçük harfe çevirir."""

    translation_table = str.maketrans("ÇĞİÖŞÜçğıöşü", "CGIOSUcgiosu")
    return text.translate(translation_table).lower()


def _field_confidence(fields: dict) -> float:
    """Çıkarılan alanların doluluk oranından basit güven skoru üretir."""

    if not fields:
        return 0.0

    important_values = []
    for key, value in fields.items():
        if key == "transactions":
            important_values.append(bool(value))
        elif key == "transaction_count":
            important_values.append(value > 0)
        else:
            important_values.append(bool(value))

    filled_count = sum(1 for value in important_values if value)
    return round(filled_count / len(important_values), 2)


def _missing_fields(document_type: str, fields: dict) -> list[str]:
    """Belge türüne göre beklenen ama çıkarılamayan alanları listeler."""

    required_fields = {
        "identity": ["full_name", "test_id", "birth_date"],
        "payroll": ["full_name", "employer", "period", "net_salary"],
        "bank_statement": ["full_name", "test_id", "iban", "period", "transaction_count"],
        "consent": ["full_name", "test_id", "consent_status"],
    }

    if document_type == "unknown":
        return ["document_type"]

    missing = []
    for field_name in required_fields.get(document_type, []):
        value = fields.get(field_name)
        if not value:
            missing.append(field_name)

    return missing


def _understanding_warnings(document_type: str, missing_fields: list[str]) -> list[str]:
    """Belge anlama sonucunu uzman ekranında okunabilir uyarılara çevirir."""

    if document_type == "unknown":
        return ["Belge türü belirlenemedi."]

    if not missing_fields:
        return []

    return [f"Eksik alanlar: {', '.join(missing_fields)}"]


def _first_non_empty(*values: str) -> str:
    """Verilen metinlerden ilk dolu olanı döndürür."""

    for value in values:
        if value:
            return value
    return ""


def _first_non_zero(*values: float) -> float:
    """Verilen sayılardan ilk 0 olmayanı döndürür."""

    for value in values:
        if value:
            return value
    return 0.0


def _find_name_before_test_id(text: str) -> str:
    """KVKK metnindeki 'Ben Ad Soyad (TEST-...)' kalıbından adı bulur."""

    match = re.search(r"Ben\s+([A-Za-zÇĞİÖŞÜçğıöşü]+\s+[A-Za-zÇĞİÖŞÜçğıöşü]+)\s+\(", text)
    return match.group(1) if match else ""


def _find_consent_status(text: str) -> str:
    """Açık rıza metninde onay durumunu bulur."""

    normalized_text = _normalize_for_search(text)
    if "kabul edildi" in normalized_text or "kabul ederim" in normalized_text:
        return "accepted"
    return ""


# ---------------------------------------------------------------------------
# Terminalden tek belge anlama testi
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Katman 02 - Belge anlama")
    parser.add_argument("pdf", help="Anlaşılacak PDF dosyası")
    parser.add_argument(
        "--hide-transactions",
        action="store_true",
        help="Banka dökümü işlemlerini çıktıda gizler",
    )
    args = parser.parse_args()

    pdf_result = extract_pdf(args.pdf)
    if not pdf_result.extraction_ok:
        print(json.dumps(asdict(pdf_result), ensure_ascii=False, indent=2))
        return

    result = understand_document_text(pdf_result.text)
    payload = asdict(result)

    if args.hide_transactions and "transactions" in payload["fields"]:
        payload["fields"]["transactions"] = []

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
