import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.credisense.api import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FILES = [
    PROJECT_ROOT / "ornek_belgeler" / "Sentetik Kimlik Belgesi Ornegi.pdf",
    PROJECT_ROOT / "ornek_belgeler" / "Sentetik Maas Bordrosu Ornegi.pdf",
    PROJECT_ROOT / "ornek_belgeler" / "Sentetik Banka Hesap Dokumu Ornegi.pdf",
]
SAMPLE_FORM = PROJECT_ROOT / "ornek_belgeler" / "ornek_basvuru_formu.json"


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_endpoint_with_sample_documents(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("backend.credisense.api.APPLICATION_STORE_PATH", tmp_path / "applications.json")
    client = TestClient(app)

    with _open_sample_files() as files:
        response = client.post(
            "/analyze",
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
    assert payload["documents"]["identity"]["full_name"] == "Deniz Kaya"
    assert payload["documents"]["bank_statement"]["transaction_count"] == 18
    assert payload["consent_quality"]["is_valid"] is True
    assert payload["application_status"]["status_code"] == "MANUAL_REVIEW"
    assert payload["user_view"]["show_risk_score"] is False
    assert payload["risk"]["decision_summary"]["decision_code"] == "MANUAL_REVIEW"
    assert payload["dataset_summary"]["dataset_avg_risk_score"] == 0.49
    assert payload["report_files"]["json_report"].endswith(".json")
    assert payload["report_files"]["markdown_report"].endswith(".md")

    report_response = client.get(f"/reports/{payload['analysis_id']}/md")
    assert report_response.status_code == 200
    stored_response = client.get(f"/applications/{payload['application_id']}")
    assert stored_response.status_code == 200
    assert stored_response.json()["application_id"] == payload["application_id"]

    list_response = client.get("/applications")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1

    decision_response = client.post(
        f"/applications/{payload['application_id']}/decision",
        json={
            "decision_type": "request_extra_document",
            "requested_documents": ["Güncel gelir belgesi"],
        },
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["current_status"]["status_code"] == "EXTRA_DOCUMENT_REQUESTED"
    assert "CrediSense AI Başvuru Analiz Raporu" in report_response.text


def test_analyze_endpoint_rejects_invalid_form_json() -> None:
    client = TestClient(app)

    with _open_sample_files() as files:
        response = client.post(
            "/analyze",
            files=files,
            data={"application_form": json.dumps(["not", "an", "object"])},
        )

    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "bad_request",
        "message": "Başvuru formu JSON nesnesi olmalı.",
    }


def test_download_report_returns_404_for_unknown_analysis_id() -> None:
    client = TestClient(app)

    response = client.get("/reports/unknown/json")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


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
