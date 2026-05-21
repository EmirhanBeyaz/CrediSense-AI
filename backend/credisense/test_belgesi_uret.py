from __future__ import annotations

"""Test icin sentetik PDF belge setleri uretir.

Bu script gercek kisi veya gercek finansal veri kullanmaz. Her kisi icin:
- kimlik test belgesi
- maas bordrosu
- banka hesap dokumu
- basvuru formu JSON
olusturur.
"""

import argparse
import json
from pathlib import Path

try:
    import fitz
except ImportError:
    fitz = None

from .yol_ayarlari import project_path


TEST_PEOPLE = [
    {"code": "A011", "name": "Ayse Demir", "test_id": "22222222220", "birth": "04.02.1990", "salary": 38250.00, "credit": 180000, "debt": 45000},
    {"code": "A012", "name": "Mert Yilmaz", "test_id": "22222222221", "birth": "18.08.1988", "salary": 51600.50, "credit": 320000, "debt": 92000},
    {"code": "A013", "name": "Elif Kara", "test_id": "22222222222", "birth": "25.11.1995", "salary": 29750.75, "credit": 140000, "debt": 18000},
    {"code": "A014", "name": "Bora Tekin", "test_id": "22222222223", "birth": "09.05.1984", "salary": 68420.00, "credit": 450000, "debt": 150000},
    {"code": "A015", "name": "Selin Aydin", "test_id": "22222222224", "birth": "13.09.1992", "salary": 44200.00, "credit": 250000, "debt": 65000},
    {"code": "A016", "name": "Kerem Ozturk", "test_id": "22222222225", "birth": "02.01.1987", "salary": 73500.25, "credit": 600000, "debt": 210000},
    {"code": "A017", "name": "Lara Sahin", "test_id": "22222222226", "birth": "30.06.1997", "salary": 33500.00, "credit": 120000, "debt": 22000},
    {"code": "A018", "name": "Can Eren", "test_id": "22222222227", "birth": "21.03.1991", "salary": 48900.90, "credit": 275000, "debt": 76000},
    {"code": "A019", "name": "Derya Koc", "test_id": "22222222228", "birth": "16.12.1989", "salary": 55800.00, "credit": 350000, "debt": 115000},
    {"code": "A020", "name": "Ece Aral", "test_id": "22222222229", "birth": "07.07.1994", "salary": 40150.40, "credit": 210000, "debt": 38000},
    {
        "code": "A021",
        "name": "Emirhan Beyaz",
        "test_id": "18692237772",
        "birth": "10.01.2005",
        "salary": 28500.00,
        "credit": 850000,
        "debt": 420000,
        "credit_card_debt": 185000,
        "monthly_installments": 26500,
        "dependents": 3,
        "open_credits": 7,
        "real_estate_credits": 1,
        "delay_30_59": 5,
        "delay_60_89": 2,
        "delay_90": 1,
        "delay_days": 118,
        "high_risk": True,
    },
    {
        "code": "A022",
        "name": "Yeki Yilmaz",
        "test_id": "22222222230",
        "birth": "17.04.1999",
        "salary": 24000.00,
        "credit": 900000,
        "debt": 500000,
        "credit_card_debt": 210000,
        "monthly_installments": 29000,
        "dependents": 4,
        "open_credits": 8,
        "real_estate_credits": 2,
        "delay_30_59": 6,
        "delay_60_89": 3,
        "delay_90": 2,
        "delay_days": 146,
        "high_risk": True,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="12 kisilik sentetik CrediSense PDF test seti uretir.")
    parser.add_argument(
        "--output",
        default=str(project_path("ornek_belgeler", "test_kisileri")),
        help="Belgelerin yazilacagi klasor.",
    )
    args = parser.parse_args()

    output_folder = Path(args.output)
    output_folder.mkdir(parents=True, exist_ok=True)

    for person in TEST_PEOPLE:
        person_folder = output_folder / person["code"]
        person_folder.mkdir(parents=True, exist_ok=True)
        _write_identity_pdf(person, person_folder / f"{person['code']}_kimlik_belgesi.pdf")
        _write_payroll_pdf(person, person_folder / f"{person['code']}_maas_bordrosu.pdf")
        _write_bank_pdf(person, person_folder / f"{person['code']}_banka_hesap_dokumu_3_ay.pdf")
        _write_application_form(person, person_folder / f"{person['code']}_kredi_basvuru_formu.json")

    index_path = output_folder / "README.txt"
    index_path.write_text(_build_index_text(output_folder), encoding="utf-8")
    print(f"Test belgeleri olusturuldu: {output_folder}")


def _write_identity_pdf(person: dict, path: Path) -> None:
    lines = [
        "SENTETIK ORNEK BELGEDIR - RESMI KIMLIK BELGESI DEGILDIR",
        "Kimlik Bilgileri Test Dokumani",
        "",
        f"Ad Soyad {person['name']}",
        f"Test Kimlik No {person['test_id']}",
        f"Dogum Tarihi {person['birth']}",
        "Uyruk TR Test",
        f"Belge No SYN-KML-{person['code']}",
        "",
        "Bu belge CrediSense AI alan cikarimi testi icin uretilmistir.",
    ]
    _write_simple_pdf(path, "Kimlik Bilgileri", lines)


def _write_payroll_pdf(person: dict, path: Path) -> None:
    gross_salary = person["salary"] * 1.35
    lines = [
        "SENTETIK MAAS BORDROSU - TEST BELGESI",
        "Maas Bordrosu",
        "",
        f"Ad Soyad {person['name']}",
        "Bordro Donemi 2026 / 03",
        "Isveren Adi Nova Veri Teknolojileri A.S.",
        f"Brut Ucret {_money(gross_salary)} TL",
        f"Net Maas {_money(person['salary'])} TL",
        f"Net Odenecek Tutar {_money(person['salary'])}",
        "",
        "Bu bordro resmi islem icin kullanilamaz.",
    ]
    _write_simple_pdf(path, "Maas Bordrosu", lines)


def _write_bank_pdf(person: dict, path: Path) -> None:
    salary = person["salary"]
    balance = salary * 1.1 if person.get("high_risk") else salary * 0.65
    employer = "Nova Veri Teknolojileri A.S."
    if person.get("high_risk"):
        transactions = [
            ("05.01.2026", f"Maas {employer}", salary, 0.0),
            ("07.01.2026", "Kart borcu toplu odeme", 0.0, 23000.0),
            ("16.01.2026", "Kredi taksiti", 0.0, 19500.0),
            ("28.01.2026", "Nakit cekim", 0.0, 12000.0),
            ("05.02.2026", f"Maas {employer}", salary * 0.63, 0.0),
            ("12.02.2026", "Gecikmis kredi borcu", 0.0, 21000.0),
            ("24.02.2026", "Kart asgari odeme", 0.0, 2000.0),
            ("05.03.2026", f"Maas {employer}", salary * 1.09, 0.0),
            ("14.03.2026", "Icra takip odemesi", 0.0, 24000.0),
            ("26.03.2026", "Limit asimi masrafi", 0.0, 6500.0),
        ]
    else:
        transactions = [
            ("05.01.2026", f"Maas {employer}", salary, 0.0),
            ("08.01.2026", "Kira odemesi", 0.0, salary * 0.28),
            ("15.01.2026", "Kart odemesi", 0.0, salary * 0.19),
            ("05.02.2026", f"Maas {employer}", salary, 0.0),
            ("11.02.2026", "Fatura ve market", 0.0, salary * 0.16),
            ("22.02.2026", "Kredi taksiti", 0.0, salary * 0.12),
            ("05.03.2026", f"Maas {employer}", salary, 0.0),
            ("18.03.2026", "Kart odemesi", 0.0, salary * 0.21),
        ]

    lines = [
        "SENTETIK BANKA HESAP DOKUMU - TEST BELGESI",
        "Banka Hesap Dokumu",
        "",
        f"Hesap Sahibi {person['name']}",
        f"Ad Soyad {person['name']}",
        f"Test Kimlik No {person['test_id']}",
        "Hesap No / IBAN TR00 0000 0000 0000 0000 0000 00",
        "Donem: 01.01.2026 - 31.03.2026",
        "",
        "Tarih Aciklama Giris Cikis Bakiye",
    ]

    for date, description, inflow, outflow in transactions:
        balance += inflow - outflow
        lines.append(
            f"{date} {description} {_money_or_dash(inflow)} TL {_money_or_dash(outflow)} TL {_money(balance)}"
        )

    _write_simple_pdf(path, "Banka Hesap Dokumu", lines)


def _write_application_form(person: dict, path: Path) -> None:
    form = {
        "ad_soyad": person["name"],
        "tckn_test_no": person["test_id"],
        "dogum_tarihi": person["birth"],
        "meslek": "Yazilim ve veri uzmanligi",
        "isveren_adi": "Nova Veri Teknolojileri A.S.",
        "beyan_edilen_aylik_gelir": person["salary"],
        "gelir_turu": "Maas",
        "talep_edilen_kredi_tutari": person["credit"],
        "vade_ay": 36,
        "kredi_amaci": "Ihtiyac",
        "mevcut_kredi_borcu": person["debt"],
        "kredi_karti_borcu": person.get("credit_card_debt", round(person["salary"] * 0.35, 2)),
        "aylik_taksit_toplami": person.get("monthly_installments", round(person["salary"] * 0.18, 2)),
        "bakmakla_yukumlu_kisi_sayisi": person.get("dependents", 0),
        "acik_kredi_sayisi": person.get("open_credits", 2),
        "gayrimenkul_kredi_sayisi": person.get("real_estate_credits", 0),
        "gecikme_30_59_sayisi": person.get("delay_30_59", 0),
        "gecikme_60_89_sayisi": person.get("delay_60_89", 0),
        "gecikme_90_sayisi": person.get("delay_90", 0),
        "gecikme_gun_sayisi": person.get("delay_days", 0),
        "kvkk_onayi": True,
        "veri_isleme_onayi": True,
    }
    path.write_text(json.dumps(form, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_simple_pdf(path: Path, title: str, lines: list[str]) -> None:
    if fitz is None:
        _write_builtin_readable_pdf(path, title, lines)
        return

    document = fitz.open()
    page = document.new_page(width=595, height=842)
    y = 56
    page.insert_text((48, y), title, fontsize=20, fontname="helv")
    y += 36
    for line in lines:
        page.insert_text((48, y), line, fontsize=11, fontname="helv")
        y += 20
    document.save(path)
    document.close()


def _write_builtin_readable_pdf(path: Path, title: str, lines: list[str]) -> None:
    content_lines = [
        _pdf_text_block(title, x=48, y=786, size=20),
    ]
    y = 750
    for line in lines:
        content_lines.append(_pdf_text_block(line, x=48, y=y, size=11))
        y -= 20

    content = "\n".join(content_lines).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(bytes(pdf))


def _pdf_text_block(text: str, x: int, y: int, size: int) -> str:
    return f"BT /F1 {size} Tf 1 0 0 1 {x} {y} Tm ({_escape_pdf_text(text)}) Tj ET"


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _money(value: float) -> str:
    text = f"{value:,.2f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def _money_or_dash(value: float) -> str:
    return "-" if value <= 0 else _money(value)


def _build_index_text(output_folder: Path) -> str:
    rows = ["CrediSense AI 12 kisilik sentetik test belge seti", ""]
    for person in TEST_PEOPLE:
        rows.append(f"{person['code']} - {person['name']} - klasor: {output_folder / person['code']}")
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    main()
