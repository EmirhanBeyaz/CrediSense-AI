from __future__ import annotations

"""CrediSense AI HTTP API.

Bu modül terminal analiz akışını FastAPI endpoint'leri arkasına alır. Analiz motoru yine
`analiz_akisi.py` içindedir; API katmanı sadece dosya yükleme, JSON form okuma ve HTTP hata
cevaplarından sorumludur.
"""

import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .analiz_akisi import analyze_documents
from .banka_kararlari import apply_bank_decision
from .basvuru_deposu import DEFAULT_APPLICATION_STORE, get_application_record, list_application_records, save_application_record
from .rapor_uret import create_analysis_reports, report_files_to_dict


APP_VERSION = "0.1.0"
DEFAULT_DATASET_PATH = Path("veri") / "sentetik_kredi_basvuru_veri_seti.csv"
REPORT_FOLDER = Path("raporlar")
APPLICATION_STORE_PATH = DEFAULT_APPLICATION_STORE
MAX_DOCUMENT_COUNT = 10


class BankDecisionRequest(BaseModel):
    """Banka uzmanı karar isteği."""

    decision_type: str = Field(description="approve, reject, request_extra_document veya send_to_deep_review")
    note: str = ""
    actor: str = "bank_user"
    requested_documents: list[str] = Field(default_factory=list)

app = FastAPI(
    title="CrediSense AI API",
    version=APP_VERSION,
    description="Kredi ön değerlendirme prototipi için HTTP API.",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP hatalarını tek tip API hata gövdesine çevirir."""

    return _error_response(
        status_code=exc.status_code,
        code=_error_code_for_status(exc.status_code),
        message=str(exc.detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """FastAPI validasyon hatalarını kendi formatımıza yaklaştırır."""

    return await request_validation_exception_handler(request, exc)


@app.get("/health")
def health() -> dict[str, str]:
    """Servisin ayakta olduğunu gösteren basit sağlık kontrolü."""

    return {
        "status": "ok",
        "service": "credisense-ai",
        "version": APP_VERSION,
    }


@app.post("/analyze")
async def analyze(
    documents: Annotated[list[UploadFile], File(description="Analiz edilecek PDF belgeleri")],
    application_form: Annotated[
        str,
        Form(description="Başvuru formu JSON metni"),
    ] = "{}",
    use_dataset_summary: Annotated[
        bool,
        Form(description="Sentetik veri seti özet ortalamaları rapora eklensin mi?"),
    ] = True,
    create_report: Annotated[
        bool,
        Form(description="Analiz sonucu JSON ve Markdown raporu üretilsin mi?"),
    ] = False,
    save_application: Annotated[
        bool,
        Form(description="Başvuru kaydı ürün deposuna yazılsın mı?"),
    ] = True,
) -> dict:
    """Yüklenen PDF belgelerini ve başvuru formunu analiz eder."""

    _validate_document_count(documents)
    form_payload = _parse_application_form(application_form)
    dataset_path = DEFAULT_DATASET_PATH if use_dataset_summary else None

    with tempfile.TemporaryDirectory(prefix="credisense_api_") as temp_dir:
        temp_path = Path(temp_dir)
        document_paths = []

        for document in documents:
            document_path = _save_upload_file(document, temp_path)
            document_paths.append(document_path)

        result = analyze_documents(
            document_paths,
            dataset_path=dataset_path,
            application_form=form_payload,
        )
        analysis_id = result["application_id"]

        if create_report:
            report_files = create_analysis_reports(
                result,
                output_folder=REPORT_FOLDER,
                analysis_id=analysis_id,
            )
            result["report_files"] = report_files_to_dict(report_files)

        if save_application:
            save_application_record(result["application_record"], store_path=APPLICATION_STORE_PATH)

        return result


@app.get("/applications")
def list_applications(limit: int = 50) -> dict:
    """Kayıt deposundaki son başvuruları listeler."""

    safe_limit = max(1, min(limit, 100))
    records = list_application_records(store_path=APPLICATION_STORE_PATH, limit=safe_limit)
    return {
        "count": len(records),
        "applications": records,
    }


@app.get("/applications/{application_id}")
def get_application(application_id: str) -> dict:
    """Başvuru ID değerine göre ürün kaydını döndürür."""

    record = get_application_record(application_id, store_path=APPLICATION_STORE_PATH)
    if not record:
        raise HTTPException(status_code=404, detail="Başvuru kaydı bulunamadı.")
    return record


@app.post("/applications/{application_id}/decision")
def decide_application(application_id: str, decision_request: BankDecisionRequest) -> dict:
    """Banka uzmanı kararını mevcut başvuru kaydına işler."""

    record = get_application_record(application_id, store_path=APPLICATION_STORE_PATH)
    if not record:
        raise HTTPException(status_code=404, detail="Başvuru kaydı bulunamadı.")

    try:
        updated_record = apply_bank_decision(
            record,
            decision_type=decision_request.decision_type,
            note=decision_request.note,
            actor=decision_request.actor,
            requested_documents=decision_request.requested_documents,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    save_application_record(updated_record, store_path=APPLICATION_STORE_PATH)
    return updated_record


@app.get("/reports/{analysis_id}/{report_type}")
def download_report(analysis_id: str, report_type: str) -> FileResponse:
    """Analiz ID'sine göre JSON veya Markdown raporunu indirir."""

    if report_type not in {"json", "md"}:
        raise HTTPException(status_code=400, detail="Rapor tipi 'json' veya 'md' olmalı.")

    report_path = _find_report_file(analysis_id=analysis_id, report_type=report_type)
    if not report_path:
        raise HTTPException(status_code=404, detail="Rapor bulunamadı.")

    media_type = "application/json" if report_type == "json" else "text/markdown"
    return FileResponse(
        path=report_path,
        media_type=media_type,
        filename=report_path.name,
    )


def _validate_document_count(documents: list[UploadFile]) -> None:
    """Boş veya aşırı büyük belge listelerini HTTP hatasına çevirir."""

    if not documents:
        raise HTTPException(status_code=400, detail="En az bir PDF belgesi yüklenmelidir.")

    if len(documents) > MAX_DOCUMENT_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"En fazla {MAX_DOCUMENT_COUNT} belge yüklenebilir.",
        )


def _parse_application_form(application_form: str) -> dict:
    """Form alanından gelen JSON metnini sözlüğe çevirir."""

    if not application_form.strip():
        return {}

    try:
        payload = json.loads(application_form)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=400, detail="Başvuru formu geçerli JSON değil.") from error

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Başvuru formu JSON nesnesi olmalı.")

    return payload


def _save_upload_file(upload_file: UploadFile, target_folder: Path) -> Path:
    """UploadFile içeriğini geçici klasöre güvenli isimle kaydeder."""

    original_name = Path(upload_file.filename or "document.pdf").name
    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"PDF olmayan dosya reddedildi: {original_name}")

    target_path = _unique_target_path(target_folder, original_name)

    with target_path.open("wb") as output_file:
        shutil.copyfileobj(upload_file.file, output_file)

    return target_path


def _unique_target_path(target_folder: Path, file_name: str) -> Path:
    """Aynı isimli dosya yüklenirse çakışmayacak bir geçici dosya yolu üretir."""

    candidate = target_folder / file_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    index = 1

    while True:
        next_candidate = target_folder / f"{stem}_{index}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        index += 1


def _find_report_file(analysis_id: str, report_type: str) -> Path | None:
    """Analiz ID'siyle üretilmiş rapor dosyasını bulur."""

    safe_analysis_id = _safe_file_text(analysis_id)
    if not safe_analysis_id:
        return None

    matches = sorted(REPORT_FOLDER.glob(f"*_{safe_analysis_id}_analiz_raporu.{report_type}"))
    return matches[-1] if matches else None


def _safe_file_text(value: str) -> str:
    """Rapor ararken dosya adındaki güvenli başvuru ID biçimini üretir."""

    value = value.lower().strip()
    value = value.translate(str.maketrans("çğıöşü", "cgiosu"))
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """API hata cevapları için ortak gövde üretir."""

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


def _error_code_for_status(status_code: int) -> str:
    """HTTP status değerinden kısa hata kodu üretir."""

    if status_code == 400:
        return "bad_request"
    if status_code == 404:
        return "not_found"
    return "http_error"
