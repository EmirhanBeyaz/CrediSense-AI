from backend.credisense.katman_00_form_belge_tutarlilik import evaluate_form_document_consistency
from backend.credisense.katman_02_belge_anlama import BankStatementInfo, IdentityInfo, PayrollInfo, Transaction


def test_form_document_consistency_passes_when_core_fields_match() -> None:
    result = evaluate_form_document_consistency(
        application_form={
            "ad_soyad": "Deniz Kaya",
            "tckn_test_no": "11111111110",
            "dogum_tarihi": "1992-04-12",
            "isveren_adi": "Nova Veri Teknolojileri A.S.",
            "beyan_edilen_aylik_gelir": 42350.75,
        },
        identity=IdentityInfo(full_name="Deniz Kaya", test_id="11111111110", birth_date="12.04.1992"),
        payroll=PayrollInfo(
            full_name="Deniz Kaya",
            employer="Nova Veri Teknolojileri A.S.",
            net_salary=42350.75,
        ),
        bank=BankStatementInfo(
            full_name="Deniz Kaya",
            test_id="11111111110",
            transactions=[
                Transaction("01.01.2026", "Nova Veri Teknolojileri Maas", 42350.75, 0.0, 50000.0),
                Transaction("01.02.2026", "Nova Veri Teknolojileri Maas", 42350.75, 0.0, 51000.0),
            ],
        ),
    )

    assert result.is_consistent is True
    assert result.score == 1.0
    assert result.flags == []


def test_form_document_consistency_reports_mismatched_identity_fields() -> None:
    result = evaluate_form_document_consistency(
        application_form={
            "ad_soyad": "Deniz Kaya",
            "tckn_test_no": "11111111110",
            "dogum_tarihi": "1992-04-12",
        },
        identity=IdentityInfo(full_name="Derya Kaya", test_id="11111111110", birth_date="12.04.1992"),
        payroll=None,
        bank=None,
    )

    assert result.is_consistent is False
    assert result.score < 1.0
    assert "Formdaki ad-soyad kimlik belgesiyle uyumsuz." in result.flags


def test_form_document_consistency_skips_bank_salary_check_for_self_employed_income() -> None:
    result = evaluate_form_document_consistency(
        application_form={
            "ad_soyad": "Seda Acar",
            "tckn_test_no": "TEST-TCKN-000010",
            "gelir_turu": "serbest_meslek",
            "beyan_edilen_aylik_gelir": 34000,
        },
        identity=None,
        payroll=None,
        bank=BankStatementInfo(
            full_name="Seda Acar",
            test_id="TEST-TCKN-000010",
            transactions=[
                Transaction("01.02.2026", "Proje odemesi", 60000.0, 0.0, 60000.0),
            ],
        ),
    )

    assert result.is_consistent is True
    assert result.flags == []
