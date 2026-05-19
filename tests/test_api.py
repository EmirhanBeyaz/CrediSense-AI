import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.credisense import api as api_module
from backend.credisense.api import app
from backend.credisense.basvuru_deposu import save_application_record
from backend.credisense.kullanici_deposu import initialize_user_database


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FILES = [
    PROJECT_ROOT / "ornek_belgeler" / "Sentetik Kimlik Belgesi Ornegi.pdf",
    PROJECT_ROOT / "ornek_belgeler" / "Sentetik Maas Bordrosu Ornegi.pdf",
    PROJECT_ROOT / "ornek_belgeler" / "Sentetik Banka Hesap Dokumu Ornegi.pdf",
]
SAMPLE_FORM = PROJECT_ROOT / "ornek_belgeler" / "ornek_basvuru_formu.json"


@pytest.fixture(autouse=True)
def _disable_real_mail_delivery(monkeypatch) -> None:
    """Testlerde gercek Gmail SMTP cagrisi yapmadan tokenleri API cevabinda tutar."""

    monkeypatch.setattr(
        api_module,
        "_send_verification_token",
        lambda _user, _token: {"sent": False, "provider": "test", "message": "Test maili kapali."},
    )
    monkeypatch.setattr(
        api_module,
        "_send_password_reset_token",
        lambda _user, _token: {"sent": False, "provider": "test", "message": "Test maili kapali."},
    )


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_login_and_me_endpoint(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    initialize_user_database(store_path=api_module.USER_STORE_PATH, seed_demo_users=True)
    client = TestClient(app)

    login_response = client.post(
        "/auth/login",
        json={
            "identifier": "deniz.kaya",
            "password": "123456",
            "role": "customer",
        },
    )

    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["access_token"]
    assert payload["user"]["role"] == "customer"

    me_response = client.get("/auth/me", headers=_auth_header(payload["access_token"]))

    assert me_response.status_code == 200
    assert me_response.json()["user"]["full_name"] == "Deniz Kaya"


def test_auth_register_requires_email_verification(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    initialize_user_database(store_path=api_module.USER_STORE_PATH, seed_demo_users=True)
    client = TestClient(app)

    register_response = client.post(
        "/auth/register",
        json={
            "username": "elif.kara",
            "email": "elif@example.test",
            "password": "abcdef",
            "role": "customer",
            "full_name": "Elif Kara",
        },
    )

    assert register_response.status_code == 200
    register_payload = register_response.json()
    assert register_payload["verification_required"] is True
    assert register_payload["development_token"]

    login_before_verify = client.post(
        "/auth/login",
        json={
            "identifier": "elif@example.test",
            "password": "abcdef",
            "role": "customer",
        },
    )
    assert login_before_verify.status_code == 403

    verify_response = client.post(
        "/auth/verify-email",
        json={
            "identifier": "elif@example.test",
            "token": register_payload["development_token"],
        },
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["access_token"]
    assert verify_response.json()["user"]["email_verified"] is True


def test_auth_register_and_login_expert_user(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    initialize_user_database(store_path=api_module.USER_STORE_PATH, seed_demo_users=True)
    client = TestClient(app)

    register_response = client.post(
        "/auth/register",
        json={
            "username": "vahap.uzman",
            "email": "vahap.uzman@example.test",
            "password": "abcdef",
            "role": "expert",
            "full_name": "Vahap Uzman",
            "title": "Banka uzmani",
        },
    )

    assert register_response.status_code == 200
    register_payload = register_response.json()
    assert register_payload["user"]["role"] == "expert"

    verify_response = client.post(
        "/auth/verify-email",
        json={
            "identifier": "vahap.uzman@example.test",
            "token": register_payload["development_token"],
        },
    )
    assert verify_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "identifier": "vahap.uzman@example.test",
            "password": "abcdef",
            "role": "expert",
        },
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["full_name"] == "Vahap Uzman"


def test_forgot_password_resets_customer_password(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    initialize_user_database(store_path=api_module.USER_STORE_PATH, seed_demo_users=True)
    client = TestClient(app)

    forgot_response = client.post(
        "/auth/forgot-password",
        json={
            "email": "deniz.kaya@example.test",
            "role": "customer",
        },
    )

    assert forgot_response.status_code == 200
    forgot_payload = forgot_response.json()
    assert forgot_payload["development_token"]

    reset_response = client.post(
        "/auth/reset-password",
        json={
            "email": "deniz.kaya@example.test",
            "role": "customer",
            "token": forgot_payload["development_token"],
            "new_password": "yenisifre123",
        },
    )

    assert reset_response.status_code == 200
    assert reset_response.json()["user"]["email"] == "deniz.kaya@example.test"

    old_login = client.post(
        "/auth/login",
        json={
            "identifier": "deniz.kaya",
            "password": "123456",
            "role": "customer",
        },
    )
    new_login = client.post(
        "/auth/login",
        json={
            "identifier": "deniz.kaya",
            "password": "yenisifre123",
            "role": "customer",
        },
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_forgot_password_verifies_unverified_registered_account(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    initialize_user_database(store_path=api_module.USER_STORE_PATH, seed_demo_users=True)
    client = TestClient(app)

    register_response = client.post(
        "/auth/register",
        json={
            "username": "emirhan.reset",
            "email": "emirhan.reset@example.test",
            "password": "eskisifre",
            "role": "customer",
            "full_name": "Emirhan Reset",
        },
    )
    assert register_response.status_code == 200

    forgot_response = client.post(
        "/auth/forgot-password",
        json={
            "email": "emirhan.reset@example.test",
            "role": "customer",
        },
    )
    assert forgot_response.status_code == 200

    reset_response = client.post(
        "/auth/reset-password",
        json={
            "email": "emirhan.reset@example.test",
            "role": "customer",
            "token": forgot_response.json()["development_token"],
            "new_password": "yenisifre123",
        },
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["user"]["email_verified"] is True

    login_response = client.post(
        "/auth/login",
        json={
            "identifier": "emirhan.reset@example.test",
            "password": "yenisifre123",
            "role": "customer",
        },
    )
    assert login_response.status_code == 200


def test_forgot_password_checks_email_and_role(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    initialize_user_database(store_path=api_module.USER_STORE_PATH, seed_demo_users=True)
    client = TestClient(app)

    missing_response = client.post(
        "/auth/forgot-password",
        json={
            "email": "deniz.kaya@example.test",
            "role": "expert",
        },
    )

    assert missing_response.status_code == 404


def test_delete_current_account_removes_login(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    initialize_user_database(store_path=api_module.USER_STORE_PATH, seed_demo_users=True)
    client = TestClient(app)

    login_response = client.post(
        "/auth/login",
        json={
            "identifier": "deniz.kaya",
            "password": "123456",
            "role": "customer",
        },
    )
    assert login_response.status_code == 200

    delete_response = client.delete("/auth/me", headers=_auth_header(login_response.json()["access_token"]))
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    login_after_delete = client.post(
        "/auth/login",
        json={
            "identifier": "deniz.kaya",
            "password": "123456",
            "role": "customer",
        },
    )
    assert login_after_delete.status_code == 401


def test_customer_without_active_credit_has_no_payment_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    monkeypatch.setattr("backend.credisense.api.PAYMENT_STORE_PATH", tmp_path / "payment_plans.db")
    initialize_user_database(store_path=api_module.USER_STORE_PATH, seed_demo_users=True)
    client = TestClient(app)

    register_response = client.post(
        "/auth/register",
        json={
            "username": "bos.musteri",
            "email": "bos.musteri@example.test",
            "password": "abcdef",
            "role": "customer",
            "full_name": "Bos Musteri",
        },
    )
    assert register_response.status_code == 200
    verify_response = client.post(
        "/auth/verify-email",
        json={
            "identifier": "bos.musteri@example.test",
            "token": register_response.json()["development_token"],
        },
    )
    assert verify_response.status_code == 200

    response = client.get("/me/payment-plan", headers=_auth_header(verify_response.json()["access_token"]))

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Aktif odeme plani bulunamadi."


def test_document_upload_is_saved_for_customer(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    monkeypatch.setattr("backend.credisense.api.DOCUMENT_STORE_PATH", tmp_path / "documents.db")
    monkeypatch.setattr("backend.credisense.api.DOCUMENT_FOLDER_PATH", tmp_path / "uploaded_documents")
    client = TestClient(app)
    headers = _login_headers(client, role="customer")

    with SAMPLE_FILES[0].open("rb") as sample_file:
        upload_response = client.post(
            "/documents",
            headers=headers,
            files={"document": (SAMPLE_FILES[0].name, sample_file, "application/pdf")},
            data={
                "document_type": "identity",
                "document_name": "Kimlik Belgesi",
            },
        )

    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["document_type"] == "identity"
    assert Path(payload["stored_path"]).exists()

    list_response = client.get("/documents", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1


def test_analyze_endpoint_with_sample_documents(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.APPLICATION_STORE_PATH", tmp_path / "applications.json")
    monkeypatch.setattr("backend.credisense.api.REPORT_STORE_PATH", tmp_path / "reports.db")
    monkeypatch.setattr("backend.credisense.api.REPORT_FOLDER", tmp_path / "reports")
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    client = TestClient(app)
    customer_headers = _login_headers(client, role="customer")

    with _open_sample_files() as files:
        response = client.post(
            "/analyze",
            headers=customer_headers,
            files=files,
            data={
                "application_form": SAMPLE_FORM.read_text(encoding="utf-8"),
                "use_dataset_summary": "true",
                "create_report": "true",
            },
        )

    payload = response.json()
    assert response.status_code == 200
    assert payload["application_id"].startswith("APP-")
    assert payload["analysis_id"] == payload["application_id"]
    assert payload["application_record"]["application_id"] == payload["application_id"]
    assert payload["application_record"]["owner_user_id"] == "USR-CUSTOMER-DENIZ"
    assert payload["documents"]["identity"]["full_name"] == "Deniz Kaya"
    assert payload["documents"]["bank_statement"]["transaction_count"] == 18
    assert payload["consent_quality"]["is_valid"] is True
    assert payload["application_status"]["status_code"] == "MANUAL_REVIEW"
    assert payload["user_view"]["show_risk_score"] is False
    assert payload["risk"]["decision_summary"]["decision_code"] == "MANUAL_REVIEW"
    assert payload["dataset_summary"]["dataset_avg_risk_score"] == 0.49
    assert payload["report_files"]["json_report"].endswith(".json")
    assert payload["report_files"]["markdown_report"].endswith(".md")

    report_response = client.get(f"/reports/{payload['analysis_id']}/md", headers=customer_headers)
    assert report_response.status_code == 200
    report_list_response = client.get("/reports", headers=customer_headers)
    assert report_list_response.status_code == 200
    assert report_list_response.json()["count"] >= 1
    stored_response = client.get(f"/applications/{payload['application_id']}", headers=customer_headers)
    assert stored_response.status_code == 200
    assert stored_response.json()["application_id"] == payload["application_id"]

    list_response = client.get("/applications", headers=customer_headers)
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1

    expert_headers = _login_headers(client, role="expert")
    expert_list_response = client.get("/applications", headers=expert_headers)
    assert expert_list_response.status_code == 200
    assert any(
        item["application_id"] == payload["application_id"]
        for item in expert_list_response.json()["applications"]
    )

    decision_response = client.post(
        f"/applications/{payload['application_id']}/decision",
        headers=expert_headers,
        json={
            "decision_type": "request_extra_document",
            "requested_documents": ["Guncel gelir belgesi"],
        },
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["current_status"]["status_code"] == "EXTRA_DOCUMENT_REQUESTED"
    assert decision_response.json()["bank_decision"]["requested_documents"] == ["Guncel gelir belgesi"]

    expert_report_response = client.post(
        f"/applications/{payload['application_id']}/expert-report",
        headers=expert_headers,
        json={
            "title": "Uzman kanaat raporu",
            "content": "Gelir akisi ve belge tutarliligi incelendi, ek belge beklenmelidir.",
        },
    )
    assert expert_report_response.status_code == 200
    assert expert_report_response.json()["report"]["report_type"] == "Uzman kanaat raporu"

    expert_report_list_response = client.get("/reports", headers=expert_headers)
    assert expert_report_list_response.status_code == 200
    assert any(
        report["report_type"] == "Uzman kanaat raporu"
        for report in expert_report_list_response.json()["reports"]
    )
    assert "CrediSense AI" in report_response.text


def test_analyze_endpoint_rejects_documents_for_different_account(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.APPLICATION_STORE_PATH", tmp_path / "applications.json")
    monkeypatch.setattr("backend.credisense.api.REPORT_STORE_PATH", tmp_path / "reports.db")
    monkeypatch.setattr("backend.credisense.api.REPORT_FOLDER", tmp_path / "reports")
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    initialize_user_database(store_path=api_module.USER_STORE_PATH, seed_demo_users=True)
    client = TestClient(app)

    register_response = client.post(
        "/auth/register",
        json={
            "username": "emirhan.test",
            "email": "emirhan.test@example.test",
            "password": "abcdef",
            "role": "customer",
            "full_name": "Emirhan Beyaz",
        },
    )
    assert register_response.status_code == 200
    verify_response = client.post(
        "/auth/verify-email",
        json={
            "identifier": "emirhan.test@example.test",
            "token": register_response.json()["development_token"],
        },
    )
    assert verify_response.status_code == 200

    form = json.loads(SAMPLE_FORM.read_text(encoding="utf-8"))
    form["ad_soyad"] = "Emirhan Beyaz"
    with _open_sample_files() as files:
        response = client.post(
            "/analyze",
            headers=_auth_header(verify_response.json()["access_token"]),
            files=files,
            data={
                "application_form": json.dumps(form),
                "save_application": "true",
            },
        )

    assert response.status_code == 400
    assert "eslesmiyor" in response.json()["error"]["message"]

    list_response = client.get("/applications", headers=_auth_header(verify_response.json()["access_token"]))
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 0


def test_analyze_endpoint_rejects_invalid_form_json(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    client = TestClient(app)
    headers = _login_headers(client, role="customer")

    with _open_sample_files() as files:
        response = client.post(
            "/analyze",
            headers=headers,
            files=files,
            data={"application_form": json.dumps(["not", "an", "object"])},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_download_report_returns_404_for_unknown_analysis_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    client = TestClient(app)
    headers = _login_headers(client, role="customer")

    response = client.get("/reports/unknown/json", headers=headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_payment_plan_endpoints_for_approved_application(tmp_path, monkeypatch) -> None:
    application_store = tmp_path / "applications.db"
    payment_store = tmp_path / "payment_plans.db"
    monkeypatch.setattr("backend.credisense.api.APPLICATION_STORE_PATH", application_store)
    monkeypatch.setattr("backend.credisense.api.PAYMENT_STORE_PATH", payment_store)
    monkeypatch.setattr("backend.credisense.api.USER_STORE_PATH", tmp_path / "users.db")
    save_application_record(_approved_application_record(), store_path=application_store)
    client = TestClient(app)
    headers = _login_headers(client, role="expert")

    create_response = client.post(
        "/applications/APP-20260512-TEST0001/payment-plan",
        headers=headers,
        json={
            "monthly_interest_rate": 0.02,
            "first_due_date": "2026-06-15",
        },
    )

    assert create_response.status_code == 200
    payment_plan = create_response.json()
    loan_id = payment_plan["loan_id"]
    assert payment_plan["application_id"] == "APP-20260512-TEST0001"
    assert payment_plan["schedule"][0]["due_date"] == "2026-06-15"

    get_response = client.get(f"/payment-plans/{loan_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["loan_id"] == loan_id

    update_response = client.post(
        f"/payment-plans/{loan_id}/installments/1",
        headers=headers,
        json={
            "status": "paid",
            "paid_date": "2026-06-14",
            "note": "Mobil odeme",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["schedule"][0]["status"] == "paid"

    assistant_response = client.post(
        f"/payment-plans/{loan_id}/assistant",
        headers=headers,
        json={"message": "Kalan borcum ne kadar?", "today": "2026-06-20"},
    )
    assert assistant_response.status_code == 200
    assert assistant_response.json()["intent"] == "remaining_debt"

    customer_headers = _login_headers(client, role="customer")
    customer_plan_response = client.get("/me/payment-plan", headers=customer_headers)
    assert customer_plan_response.status_code == 200
    assert customer_plan_response.json()["application_id"] == "APP-20260512-TEST0001"
    assert customer_plan_response.json()["principal"] == payment_plan["principal"]


class _open_sample_files:
    def __enter__(self):
        self._handles = [path.open("rb") for path in SAMPLE_FILES]
        return [
            ("documents", (path.name, handle, "application/pdf"))
            for path, handle in zip(SAMPLE_FILES, self._handles)
        ]

    def __exit__(self, exc_type, exc, traceback):
        for handle in self._handles:
            handle.close()


def _approved_application_record() -> dict:
    return {
        "application_id": "APP-20260512-TEST0001",
        "owner_user_id": "USR-CUSTOMER-DENIZ",
        "created_at": "2026-05-12T10:30:00",
        "current_status": {
            "status_code": "APPROVED",
            "status_text": "Kredi onaylandi",
            "is_final": True,
        },
        "credit_request": {
            "requested_amount": 250000,
            "term_months": 36,
        },
        "status_history": [],
    }


def _login_headers(client: TestClient, role: str) -> dict[str, str]:
    initialize_user_database(store_path=api_module.USER_STORE_PATH, seed_demo_users=True)
    identifier = "uzman@bank.test" if role == "expert" else "deniz.kaya"
    response = client.post(
        "/auth/login",
        json={
            "identifier": identifier,
            "password": "123456",
            "role": role,
        },
    )
    assert response.status_code == 200
    return _auth_header(response.json()["access_token"])


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
