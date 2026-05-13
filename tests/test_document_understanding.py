from backend.credisense.katman_02_belge_anlama import (
    detect_document_type,
    parse_money,
    understand_document_text,
)


def test_parse_money_supports_turkish_format() -> None:
    assert parse_money("42.350,75 TL") == 42350.75
    assert parse_money("0,00") == 0.0


def test_detect_document_type_with_expected_keywords() -> None:
    identity_text = "Kimlik Bilgileri Test Kimlik No Dogum Tarihi"
    payroll_text = "Maas Bordrosu Brut Ucret Net Odenecek Kesinti Bilgileri"
    bank_text = "Hesap Hareketleri Hesap Sahibi Toplam Gelen Toplam Giden"
    consent_text = "Açık Rıza KVKK Onayı Veri İşleme Onay Durumu Kabul edildi"

    assert detect_document_type(identity_text) == "identity"
    assert detect_document_type(payroll_text) == "payroll"
    assert detect_document_type(bank_text) == "bank_statement"
    assert detect_document_type(consent_text) == "consent"
    assert detect_document_type("ilgili anahtar kelime yok") == "unknown"


def test_understand_document_text_reports_missing_fields_for_unknown_text() -> None:
    result = understand_document_text("ilgili anahtar kelime yok")

    assert result.document_type == "unknown"
    assert result.confidence == 0.0
    assert result.missing_fields == ["document_type"]
    assert result.warnings == ["Belge türü belirlenemedi."]


def test_understand_document_text_reports_missing_identity_fields() -> None:
    result = understand_document_text("Kimlik Bilgileri Test Kimlik No")

    assert result.document_type == "identity"
    assert result.missing_fields == ["full_name", "test_id", "birth_date"]
    assert result.warnings == ["Eksik alanlar: full_name, test_id, birth_date"]


def test_understand_document_text_supports_new_identity_format() -> None:
    text = """
    TEST KİMLİK BELGESİ
    Ad Soyad Zeynep Arslan
    TCKN Test No TEST-TCKN-000006
    Doğum Tarihi 1991-04-22
    """

    result = understand_document_text(text)

    assert result.document_type == "identity"
    assert result.fields["full_name"] == "Zeynep Arslan"
    assert result.fields["test_id"] == "TEST-TCKN-000006"
    assert result.fields["birth_date"] == "1991-04-22"
    assert result.missing_fields == []


def test_understand_document_text_supports_new_payroll_format() -> None:
    text = """
    GELİR BELGESİ - ÖRNEK MAAŞ BORDROSU
    Çalışan Ad Soyad Zeynep Arslan
    TCKN Test No TEST-TCKN-000006
    İşveren Adı Mavi Nokta Danışmanlık A.Ş.
    Bordro Dönemi 2026 Nisan
    Brüt Ücret 61.409,00 TL
    Net Maaş 44.500,00 TL
    """

    result = understand_document_text(text)

    assert result.document_type == "payroll"
    assert result.fields["full_name"] == "Zeynep Arslan"
    assert result.fields["employer"] == "Mavi Nokta Danışmanlık A.Ş."
    assert result.fields["period"] == "2026 Nisan"
    assert result.fields["net_salary"] == 44500.0
    assert result.missing_fields == []


def test_understand_document_text_supports_new_bank_statement_format() -> None:
    text = """
    BANKA HESAP DÖKÜMÜ - SON 3 AY
    Müşteri Zeynep Arslan
    TCKN Test No TEST-TCKN-000006
    Hesap No / IBAN TR00 0000 0000 0000 0060 0000 00
    Dönem 01.02.2026 - 30.04.2026
    Tarih Açıklama Giriş Çıkış Bakiye
    05.02.2026 MAAŞ ÖDEMESİ - Mavi Nokta Danışmanlık 44.500,00 TL - 66.789,00 TL
    07.02.2026 KİRA / KONUT GİDERİ - 10.297,00 TL 56.492,00 TL
    """

    result = understand_document_text(text)

    assert result.document_type == "bank_statement"
    assert result.fields["full_name"] == "Zeynep Arslan"
    assert result.fields["test_id"] == "TEST-TCKN-000006"
    assert result.fields["transaction_count"] == 2
    assert result.fields["transactions"][0]["inflow"] == 44500.0
    assert result.fields["transactions"][1]["outflow"] == 10297.0
    assert result.missing_fields == []
