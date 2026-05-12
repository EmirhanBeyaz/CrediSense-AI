from backend.credisense.urun_akisi import build_product_outputs


def test_product_flow_stops_when_consent_is_missing() -> None:
    result = build_product_outputs(
        package_quality={"can_continue": True},
        form_quality={"is_valid": True},
        consent_quality={"is_valid": False, "missing_consents": ["kvkk_onayi"]},
        risk={"decision_summary": {"decision_code": "PRE_APPROVED"}},
        consistency={},
    )

    assert result["application_status"]["status_code"] == "CONSENT_REQUIRED"
    assert result["user_view"]["show_risk_score"] is False
    assert result["bank_view"]["blockers"] == ["kvkk_onayi"]
    assert result["bank_view"]["allowed_decisions"] == []


def test_product_flow_routes_pre_approved_application() -> None:
    result = build_product_outputs(
        package_quality={"can_continue": True, "quality_score": 1.0},
        form_quality={"is_valid": True, "quality_score": 1.0},
        consent_quality={"is_valid": True},
        risk={
            "risk_score": 0.25,
            "risk_level": "Düşük",
            "decision_summary": {"decision_code": "PRE_APPROVED"},
            "reasons": ["Belgeler tutarlı."],
        },
        consistency={"consistency_score": 1.0, "anomaly_score": 0.0},
    )

    assert result["application_status"]["status_code"] == "PRE_APPROVED"
    assert result["application_status"]["is_final"] is True
    assert result["bank_view"]["recommended_action"] == "Belge ve skor özetini kontrol edip ön onayı kesinleştir."
    assert "approve" in result["bank_view"]["allowed_decisions"]
