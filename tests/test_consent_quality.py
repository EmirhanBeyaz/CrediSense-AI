from backend.credisense.katman_00_onay_kontrolu import validate_consents


def test_valid_consents_are_accepted() -> None:
    result = validate_consents({"kvkk_onayi": True, "veri_isleme_onayi": True})

    assert result.is_valid is True
    assert result.missing_consents == []
    assert result.rejected_consents == []


def test_missing_consents_are_reported() -> None:
    result = validate_consents({})

    assert result.is_valid is False
    assert result.missing_consents == ["kvkk_onayi", "veri_isleme_onayi"]


def test_rejected_consents_are_reported() -> None:
    result = validate_consents({"kvkk_onayi": True, "veri_isleme_onayi": False})

    assert result.is_valid is False
    assert result.rejected_consents == ["veri_isleme_onayi"]
