from backend.credisense.katman_00_form_dogrulama import validate_application_form


def test_valid_application_form_gets_full_quality_score() -> None:
    result = validate_application_form(_valid_form())

    assert result.is_valid is True
    assert result.quality_score == 1.0
    assert result.missing_required_fields == []
    assert result.invalid_fields == []
    assert result.warnings == []


def test_missing_required_application_form_fields_are_reported() -> None:
    result = validate_application_form({})

    assert result.is_valid is False
    assert "ad_soyad" in result.missing_required_fields
    assert "talep_edilen_kredi_tutari" in result.missing_required_fields
    assert result.quality_score < 1.0


def test_invalid_application_form_values_are_reported() -> None:
    form = _valid_form()
    form["dogum_tarihi"] = "12/04/1992"
    form["talep_edilen_kredi_tutari"] = -50000
    form["vade_ay"] = 180

    result = validate_application_form(form)

    assert result.is_valid is False
    assert "dogum_tarihi: GG.AA.YYYY veya YYYY-AA-GG formatında olmalı" in result.invalid_fields
    assert "talep_edilen_kredi_tutari: negatif olamaz" in result.invalid_fields
    assert "vade_ay: 120 aydan büyük olamaz" in result.invalid_fields


def test_application_form_accepts_new_test_id_and_iso_birth_date() -> None:
    form = _valid_form()
    form["tckn_test_no"] = "TEST-TCKN-000006"
    form["dogum_tarihi"] = "1991-04-22"

    result = validate_application_form(form)

    assert result.is_valid is True
    assert result.invalid_fields == []


def _valid_form() -> dict:
    return {
        "ad_soyad": "Deniz Kaya",
        "tckn_test_no": "11111111110",
        "dogum_tarihi": "12.04.1992",
        "meslek": "Veri Analisti",
        "isveren_adi": "Nova Veri Teknolojileri A.S.",
        "beyan_edilen_aylik_gelir": 42350.75,
        "gelir_turu": "Maas",
        "talep_edilen_kredi_tutari": 250000,
        "vade_ay": 36,
        "mevcut_kredi_borcu": 125000,
        "kredi_karti_borcu": 28000,
        "aylik_taksit_toplami": 8500,
        "bakmakla_yukumlu_kisi_sayisi": 0,
        "acik_kredi_sayisi": 2,
        "gayrimenkul_kredi_sayisi": 0,
        "gecikme_30_59_sayisi": 0,
        "gecikme_60_89_sayisi": 0,
        "gecikme_90_sayisi": 0,
        "gecikme_gun_sayisi": 0,
    }
