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


def test_product_flow_sends_form_document_mismatch_to_manual_review() -> None:
    result = build_product_outputs(
        package_quality={"can_continue": True, "quality_score": 1.0},
        form_quality={"is_valid": True, "quality_score": 1.0},
        consent_quality={"is_valid": True},
        form_document_consistency={
            "is_consistent": False,
            "score": 0.75,
            "flags": ["Formdaki ad-soyad kimlik belgesiyle uyumsuz."],
        },
        risk={
            "risk_score": 0.25,
            "risk_level": "DÃ¼ÅŸÃ¼k",
            "decision_summary": {"decision_code": "PRE_APPROVED"},
            "reasons": [],
        },
        consistency={"consistency_score": 1.0, "anomaly_score": 0.0},
    )

    assert result["application_status"]["status_code"] == "MANUAL_REVIEW"
    assert result["bank_view"]["form_document_consistency_score"] == 0.75
    assert "Formdaki ad-soyad kimlik belgesiyle uyumsuz." in result["bank_view"]["blockers"]


def test_product_flow_sends_high_risk_to_deep_manual_review() -> None:
    result = build_product_outputs(
        package_quality={"can_continue": True, "quality_score": 1.0},
        form_quality={"is_valid": True, "quality_score": 1.0},
        consent_quality={"is_valid": True},
        form_document_consistency={"is_consistent": True, "score": 1.0, "flags": []},
        risk={
            "risk_score": 0.88,
            "risk_level": "Yüksek",
            "decision_summary": {"decision_code": "DEEP_REVIEW"},
            "reasons": ["Risk skoru yüksek."],
        },
        consistency={"consistency_score": 0.72, "anomaly_score": 0.45},
    )

    assert result["application_status"]["status_code"] == "DEEP_REVIEW"
    assert result["application_status"]["is_final"] is False
    assert result["application_status"]["requires_human_review"] is True
    assert "approve" in result["bank_view"]["allowed_decisions"]
    assert "reject" in result["bank_view"]["allowed_decisions"]
