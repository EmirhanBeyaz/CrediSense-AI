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
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .analiz_akisi import analyze_documents
from .asistan_deposu import DEFAULT_ASSISTANT_STORE, save_assistant_exchange
from .banka_kararlari import apply_bank_decision
from .basvuru_deposu import DEFAULT_APPLICATION_STORE, get_application_record, list_application_records, save_application_record
from .belge_deposu import DEFAULT_DOCUMENT_FOLDER, DEFAULT_DOCUMENT_STORE, list_user_documents, save_uploaded_document
from .kullanici_deposu import (
    DEFAULT_USER_STORE,
    authenticate_user,
    create_email_verification_token,
    create_session,
    get_user_by_identifier,
    get_user_by_token,
    initialize_user_database,
    public_user_from_record,
    register_user,
    update_user_profile,
    verify_email_token,
)
from .mail_servisi import send_verification_email
from .odeme_asistani import answer_payment_message, answer_payment_question
from .odeme_deposu import (
    DEFAULT_PAYMENT_STORE,
    get_payment_plan,
    get_payment_plan_by_application,
    list_payment_plans,
    save_payment_plan,
)
from .odeme_plani import build_payment_plan, update_installment_status
from .rapor_uret import create_analysis_reports, report_files_to_dict
from .rapor_deposu import DEFAULT_REPORT_STORE, list_report_records, save_report_record


APP_VERSION = "0.1.0"
DEFAULT_DATASET_PATH = Path("veri") / "sentetik_kredi_basvuru_veri_seti.csv"
REPORT_FOLDER = Path("raporlar")
APPLICATION_STORE_PATH = DEFAULT_APPLICATION_STORE
PAYMENT_STORE_PATH = DEFAULT_PAYMENT_STORE
USER_STORE_PATH = DEFAULT_USER_STORE
DOCUMENT_STORE_PATH = DEFAULT_DOCUMENT_STORE
DOCUMENT_FOLDER_PATH = DEFAULT_DOCUMENT_FOLDER
ASSISTANT_STORE_PATH = DEFAULT_ASSISTANT_STORE
REPORT_STORE_PATH = DEFAULT_REPORT_STORE
MAX_DOCUMENT_COUNT = 10


class LoginRequest(BaseModel):
    """Kullanici giris istegi."""

    identifier: str = Field(description="Kullanici adi veya e-posta")
    password: str = Field(description="Kullanici sifresi")
    role: str = Field(description="customer veya expert")


class RegisterRequest(BaseModel):
    """Yeni kullanici kayit istegi."""

    username: str
    email: str
    password: str
    role: str = Field(description="customer veya expert")
    full_name: str
    title: str = ""
    profile: dict = Field(default_factory=dict)


class VerifyEmailRequest(BaseModel):
    """E-posta dogrulama istegi."""

    identifier: str = Field(description="Kullanici adi veya e-posta")
    token: str = Field(description="E-posta ile gelen dogrulama tokeni")


class ResendVerificationRequest(BaseModel):
    """Yeni e-posta dogrulama tokeni isteme istegi."""

    identifier: str = Field(description="Kullanici adi veya e-posta")


class ProfileUpdateRequest(BaseModel):
    """Kullanici profilindeki urun alanlarini guncelleme istegi."""

    profile: dict = Field(default_factory=dict)


class BankDecisionRequest(BaseModel):
    """Banka uzmanı karar isteği."""

    decision_type: str = Field(description="approve, reject, request_extra_document veya send_to_deep_review")
    note: str = ""
    actor: str = "bank_user"
    requested_documents: list[str] = Field(default_factory=list)


class PaymentPlanRequest(BaseModel):
    """Odeme plani olusturma istegi."""

    monthly_interest_rate: float = 0.025
    first_due_date: str = ""


class InstallmentStatusRequest(BaseModel):
    """Tek taksit durumu guncelleme istegi."""

    status: str
    paid_date: str = ""
    note: str = ""


class PaymentAssistantRequest(BaseModel):
    """Odeme asistani soru istegi."""

    question_type: str = ""
    message: str = ""
    today: str = ""

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """API acilirken SQLite kullanici veritabanini hazirlar."""

    initialize_user_database(store_path=USER_STORE_PATH, seed_demo_users=True)
    yield


app = FastAPI(
    title="CrediSense AI API",
    version=APP_VERSION,
    lifespan=lifespan,
    description="Kredi ön değerlendirme prototipi için HTTP API.",
)


def _require_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict:
    """Authorization header icindeki bearer token ile kullaniciyi dogrular."""

    token = _extract_bearer_token(authorization or "")
    user = get_user_by_token(token, store_path=USER_STORE_PATH)
    if not user:
        raise HTTPException(status_code=401, detail="Gecerli oturum bulunamadi.")
    return user


def _require_customer(current_user: dict) -> None:
    """Endpointin musteri kullanicisi gerektirdigini kontrol eder."""

    if current_user.get("role") != "customer":
        raise HTTPException(status_code=403, detail="Bu islem sadece musteri kullanicisi icindir.")


def _require_expert(current_user: dict) -> None:
    """Endpointin banka uzmani gerektirdigini kontrol eder."""

    if current_user.get("role") != "expert":
        raise HTTPException(status_code=403, detail="Bu islem sadece banka uzmani icindir.")


def _extract_bearer_token(authorization: str) -> str:
    """Authorization header degerinden token metnini ayiklar."""

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return ""
    return authorization[len(prefix):].strip()


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


@app.post("/auth/login")
def login(login_request: LoginRequest) -> dict:
    """Kullanici adi/e-posta ve sifre ile oturum acar."""

    role = login_request.role.strip()
    if role not in {"customer", "expert"}:
        raise HTTPException(status_code=400, detail="Rol customer veya expert olmali.")

    user = authenticate_user(
        identifier=login_request.identifier,
        password=login_request.password,
        role=role,
        store_path=USER_STORE_PATH,
    )
    if not user:
        raise HTTPException(status_code=401, detail="Kullanici adi/e-posta, sifre veya rol hatali.")

    session = create_session(user["id"], store_path=USER_STORE_PATH)
    return {
        "user": user,
        **session,
    }


@app.post("/auth/register")
def register(register_request: RegisterRequest) -> dict:
    """Yeni kullaniciyi SQLite veritabanina kaydeder ve dogrulama tokeni gonderir."""

    role = register_request.role.strip()
    if role not in {"customer", "expert"}:
        raise HTTPException(status_code=400, detail="Rol customer veya expert olmali.")

    try:
        user = register_user(
            username=register_request.username,
            email=register_request.email,
            password=register_request.password,
            role=role,
            full_name=register_request.full_name,
            title=register_request.title,
            profile=register_request.profile,
            store_path=USER_STORE_PATH,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    token_info = create_email_verification_token(user["id"], store_path=USER_STORE_PATH)
    mail_result = _send_verification_token(user, token_info["token"])

    return _verification_response(user, token_info, mail_result)


@app.post("/auth/verify-email")
def verify_email(verify_request: VerifyEmailRequest) -> dict:
    """E-posta tokeni dogruysa kullaniciyi aktif eder ve oturum acar."""

    user = verify_email_token(
        identifier=verify_request.identifier,
        token=verify_request.token,
        store_path=USER_STORE_PATH,
    )
    if not user:
        raise HTTPException(status_code=400, detail="Dogrulama tokeni hatali veya suresi dolmus.")

    session = create_session(user["id"], store_path=USER_STORE_PATH)
    return {
        "user": user,
        **session,
    }


@app.post("/auth/resend-verification")
def resend_verification(resend_request: ResendVerificationRequest) -> dict:
    """Kayitli ama dogrulanmamis kullanici icin yeni token gonderir."""

    user_record = get_user_by_identifier(resend_request.identifier, store_path=USER_STORE_PATH)
    if not user_record:
        raise HTTPException(status_code=404, detail="Kullanici bulunamadi.")
    if user_record.get("email_verified", False):
        raise HTTPException(status_code=400, detail="Bu e-posta zaten dogrulanmis.")

    user = public_user_from_record(user_record)
    token_info = create_email_verification_token(user["id"], store_path=USER_STORE_PATH)
    mail_result = _send_verification_token(user, token_info["token"])

    return _verification_response(user, token_info, mail_result)


@app.get("/auth/me")
def get_me(current_user: Annotated[dict, Depends(_require_current_user)]) -> dict:
    """Token sahibi kullanicinin genel profil bilgisini dondurur."""

    return {
        "user": public_user_from_record(current_user),
    }


@app.put("/auth/me/profile")
def update_me_profile(
    profile_request: ProfileUpdateRequest,
    current_user: Annotated[dict, Depends(_require_current_user)],
) -> dict:
    """Token sahibi kullanicinin profil verisini SQLite uzerinde gunceller."""

    try:
        updated_user = update_user_profile(
            current_user["user_id"],
            profile_request.profile,
            store_path=USER_STORE_PATH,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return {
        "user": updated_user,
    }


@app.get("/me/payment-plan")
def get_my_payment_plan(current_user: Annotated[dict, Depends(_require_current_user)]) -> dict:
    """Musterinin aktif odeme planini veritabanindan dondurur."""

    _require_customer(current_user)
    profile = current_user.get("profile", {})
    active_loan_id = str(profile.get("active_loan_id", "")).strip()
    active_application_id = str(profile.get("active_application_id", "")).strip()

    payment_plan = get_payment_plan(active_loan_id, store_path=PAYMENT_STORE_PATH) if active_loan_id else None
    if not payment_plan and active_application_id:
        payment_plan = get_payment_plan_by_application(active_application_id, store_path=PAYMENT_STORE_PATH)

    if not payment_plan:
        payment_plan = _create_profile_payment_plan(current_user)
        save_payment_plan(payment_plan, store_path=PAYMENT_STORE_PATH)

    return payment_plan


@app.post("/documents")
async def upload_document(
    document: Annotated[UploadFile, File(description="Kaydedilecek PDF belgesi")],
    document_type: Annotated[str, Form(description="Belge tipi")] = "other",
    document_name: Annotated[str, Form(description="Belge adi")] = "Belge",
    current_user: Annotated[dict, Depends(_require_current_user)] = None,
) -> dict:
    """Yuklenen belgeyi kalici dosyaya ve SQLite metadata deposuna kaydeder."""

    _require_customer(current_user)
    try:
        record = save_uploaded_document(
            file_name=document.filename or "document.pdf",
            file_stream=document.file,
            owner_user_id=current_user["user_id"],
            document_type=document_type,
            document_name=document_name,
            store_path=DOCUMENT_STORE_PATH,
            file_folder=DOCUMENT_FOLDER_PATH,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return record


@app.get("/documents")
def list_documents(current_user: Annotated[dict, Depends(_require_current_user)]) -> dict:
    """Oturumdaki musteriye ait belge metadata kayitlarini listeler."""

    _require_customer(current_user)
    documents = list_user_documents(current_user["user_id"], store_path=DOCUMENT_STORE_PATH)
    return {
        "count": len(documents),
        "documents": documents,
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
    current_user: Annotated[dict, Depends(_require_current_user)] = None,
) -> dict:
    """Yüklenen PDF belgelerini ve başvuru formunu analiz eder."""

    _require_customer(current_user)
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
            report_files_dict = report_files_to_dict(report_files)
            result["report_files"] = report_files_dict
            save_report_record(
                application_id=analysis_id,
                owner_user_id=current_user["user_id"],
                report_files=report_files_dict,
                store_path=REPORT_STORE_PATH,
            )

        if save_application:
            application_record = result["application_record"]
            application_record["owner_user_id"] = current_user["user_id"]
            application_record["owner_role"] = current_user["role"]
            result["application_record"] = application_record
            save_application_record(application_record, store_path=APPLICATION_STORE_PATH)

        return result


@app.get("/applications")
def list_applications(
    current_user: Annotated[dict, Depends(_require_current_user)],
    limit: int = 50,
) -> dict:
    """Kayıt deposundaki son başvuruları listeler."""

    safe_limit = max(1, min(limit, 100))
    records = list_application_records(store_path=APPLICATION_STORE_PATH, limit=safe_limit)
    if current_user["role"] == "customer":
        records = [
            record for record in records
            if record.get("owner_user_id") == current_user["user_id"]
        ]
    return {
        "count": len(records),
        "applications": records,
    }


@app.get("/applications/{application_id}")
def get_application(
    application_id: str,
    current_user: Annotated[dict, Depends(_require_current_user)],
) -> dict:
    """Başvuru ID değerine göre ürün kaydını döndürür."""

    record = get_application_record(application_id, store_path=APPLICATION_STORE_PATH)
    if not record:
        raise HTTPException(status_code=404, detail="Başvuru kaydı bulunamadı.")
    _ensure_application_access(record, current_user)
    return record


@app.post("/applications/{application_id}/decision")
def decide_application(
    application_id: str,
    decision_request: BankDecisionRequest,
    current_user: Annotated[dict, Depends(_require_current_user)],
) -> dict:
    """Banka uzmanı kararını mevcut başvuru kaydına işler."""

    _require_expert(current_user)
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


@app.post("/applications/{application_id}/payment-plan")
def create_payment_plan(
    application_id: str,
    payment_request: PaymentPlanRequest,
    current_user: Annotated[dict, Depends(_require_current_user)],
) -> dict:
    """Onayli basvuru kaydindan odeme plani olusturur."""

    _require_expert(current_user)
    record = get_application_record(application_id, store_path=APPLICATION_STORE_PATH)
    if not record:
        raise HTTPException(status_code=404, detail="Başvuru kaydı bulunamadı.")

    first_due_date = _parse_optional_date(payment_request.first_due_date, field_name="first_due_date")
    try:
        payment_plan = build_payment_plan(
            record,
            monthly_interest_rate=payment_request.monthly_interest_rate,
            first_due_date=first_due_date,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    save_payment_plan(payment_plan, store_path=PAYMENT_STORE_PATH)
    return payment_plan


@app.get("/payment-plans")
def list_payment_plan_records(
    current_user: Annotated[dict, Depends(_require_current_user)],
    limit: int = 50,
) -> dict:
    """Kayitli odeme planlarini listeler."""

    safe_limit = max(1, min(limit, 100))
    plans = list_payment_plans(store_path=PAYMENT_STORE_PATH, limit=safe_limit)
    if current_user["role"] == "customer":
        plans = [plan for plan in plans if _can_access_payment_plan(plan, current_user)]
    return {
        "count": len(plans),
        "payment_plans": plans,
    }


@app.get("/payment-plans/{loan_id}")
def get_payment_plan_record(
    loan_id: str,
    current_user: Annotated[dict, Depends(_require_current_user)],
) -> dict:
    """Kredi ID degerine gore odeme planini dondurur."""

    payment_plan = get_payment_plan(loan_id, store_path=PAYMENT_STORE_PATH)
    if not payment_plan:
        raise HTTPException(status_code=404, detail="Ödeme planı bulunamadı.")
    _ensure_payment_plan_access(payment_plan, current_user)
    return payment_plan


@app.post("/payment-plans/{loan_id}/installments/{installment_no}")
def update_payment_installment(
    loan_id: str,
    installment_no: int,
    status_request: InstallmentStatusRequest,
    current_user: Annotated[dict, Depends(_require_current_user)],
) -> dict:
    """Odeme planindaki tek taksitin durumunu gunceller."""

    _require_expert(current_user)
    payment_plan = get_payment_plan(loan_id, store_path=PAYMENT_STORE_PATH)
    if not payment_plan:
        raise HTTPException(status_code=404, detail="Ödeme planı bulunamadı.")

    try:
        updated_plan = update_installment_status(
            payment_plan,
            installment_no=installment_no,
            status=status_request.status,
            paid_date=status_request.paid_date,
            note=status_request.note,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    save_payment_plan(updated_plan, store_path=PAYMENT_STORE_PATH)
    return updated_plan


@app.post("/payment-plans/{loan_id}/assistant")
def ask_payment_assistant(
    loan_id: str,
    assistant_request: PaymentAssistantRequest,
    current_user: Annotated[dict, Depends(_require_current_user)],
) -> dict:
    """Odeme plani uzerinden kontrollu asistan cevabi uretir."""

    payment_plan = get_payment_plan(loan_id, store_path=PAYMENT_STORE_PATH)
    if not payment_plan:
        raise HTTPException(status_code=404, detail="Ödeme planı bulunamadı.")
    _ensure_payment_plan_access(payment_plan, current_user)

    today = _parse_optional_date(assistant_request.today, field_name="today")
    if assistant_request.message.strip():
        response = answer_payment_message(payment_plan, assistant_request.message, today=today)
        saved_message = save_assistant_exchange(
            user_id=current_user["user_id"],
            loan_id=loan_id,
            user_message=assistant_request.message,
            assistant_response=response,
            store_path=ASSISTANT_STORE_PATH,
        )
        response["saved_message_id"] = saved_message["message_id"]
        return response

    question_type = assistant_request.question_type.strip() or "summary"
    response = answer_payment_question(payment_plan, question_type, today=today)
    saved_message = save_assistant_exchange(
        user_id=current_user["user_id"],
        loan_id=loan_id,
        user_message=question_type,
        assistant_response=response,
        store_path=ASSISTANT_STORE_PATH,
    )
    response["saved_message_id"] = saved_message["message_id"]
    return response


@app.get("/reports")
def list_reports(
    current_user: Annotated[dict, Depends(_require_current_user)],
    limit: int = 50,
) -> dict:
    """SQLite rapor metadata kayitlarini listeler."""

    owner_user_id = "" if current_user["role"] == "expert" else current_user["user_id"]
    reports = list_report_records(
        owner_user_id=owner_user_id,
        store_path=REPORT_STORE_PATH,
        limit=limit,
    )
    return {
        "count": len(reports),
        "reports": reports,
    }


@app.get("/reports/{analysis_id}/{report_type}")
def download_report(
    analysis_id: str,
    report_type: str,
    current_user: Annotated[dict, Depends(_require_current_user)],
) -> FileResponse:
    """Analiz ID'sine göre JSON veya Markdown raporunu indirir."""

    if current_user["role"] == "customer":
        record = get_application_record(analysis_id, store_path=APPLICATION_STORE_PATH)
        if record:
            _ensure_application_access(record, current_user)

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


def _ensure_application_access(application_record: dict, current_user: dict) -> None:
    """Musterinin sadece kendi basvurusuna, uzmanın tum basvurulara erismesini saglar."""

    if current_user["role"] == "expert":
        return

    owner_user_id = application_record.get("owner_user_id", "")
    if owner_user_id and owner_user_id == current_user["user_id"]:
        return

    raise HTTPException(status_code=403, detail="Bu basvuruya erisim yetkiniz yok.")


def _send_verification_token(user: dict, token: str) -> dict:
    """E-posta dogrulama tokenini mail servisine iletir."""

    try:
        return send_verification_email(
            email=str(user.get("email", "")),
            full_name=str(user.get("full_name", "")),
            token=token,
        )
    except Exception as error:
        return {
            "sent": False,
            "provider": "gmail-smtp",
            "message": f"E-posta gonderilemedi: {error}",
        }


def _verification_response(user: dict, token_info: dict, mail_result: dict) -> dict:
    """Kayit/dogrulama tokeni cevabini ortak formatta uretir."""

    response = {
        "user": user,
        "verification_required": True,
        "email_sent": bool(mail_result.get("sent", False)),
        "email_provider": mail_result.get("provider", ""),
        "expires_at": token_info.get("expires_at", ""),
        "message": mail_result.get("message", ""),
    }
    if not mail_result.get("sent", False):
        response["development_token"] = token_info.get("token", "")
    return response


def _ensure_payment_plan_access(payment_plan: dict, current_user: dict) -> None:
    """Odeme planinda rol ve sahiplik kontrolu yapar."""

    if _can_access_payment_plan(payment_plan, current_user):
        return
    raise HTTPException(status_code=403, detail="Bu odeme planina erisim yetkiniz yok.")


def _can_access_payment_plan(payment_plan: dict, current_user: dict) -> bool:
    """Odeme plani goruntuleme yetkisini kontrol eder."""

    if current_user["role"] == "expert":
        return True

    profile = current_user.get("profile", {})
    if payment_plan.get("loan_id") == profile.get("active_loan_id"):
        return True

    application_id = payment_plan.get("application_id", "")
    if not application_id:
        return False

    application_record = get_application_record(application_id, store_path=APPLICATION_STORE_PATH)
    return bool(application_record and application_record.get("owner_user_id") == current_user["user_id"])


def _create_profile_payment_plan(current_user: dict) -> dict:
    """Kullanici profilindeki finansal bilgilerden ilk odeme planini olusturur."""

    profile = current_user.get("profile", {})
    principal = _safe_float(profile.get("current_debt", 0))
    requested_amount = _safe_float(profile.get("requested_credit", principal))
    monthly_payment = 7950.0
    term_months = int(_safe_float(profile.get("maturity_months", 36)) or 36)
    first_due_date = date.today().replace(day=15)

    schedule = []
    remaining_principal = principal
    for index in range(1, min(term_months, 12) + 1):
        due_date = first_due_date + timedelta(days=30 * (index - 1))
        principal_payment = round(min(remaining_principal, monthly_payment * 0.72), 2)
        remaining_principal = round(max(0.0, remaining_principal - principal_payment), 2)
        schedule.append(
            {
                "installment_no": index,
                "due_date": due_date.isoformat(),
                "payment_amount": monthly_payment,
                "principal_amount": principal_payment,
                "interest_amount": round(monthly_payment - principal_payment, 2),
                "remaining_principal": remaining_principal,
                "status": "pending",
                "paid_date": "",
                "note": "",
            }
        )

    return {
        "loan_id": profile.get("active_loan_id") or f"LOAN-{current_user['user_id']}",
        "application_id": profile.get("active_application_id", ""),
        "customer_user_id": current_user["user_id"],
        "principal": requested_amount,
        "current_debt": principal,
        "term_months": term_months,
        "monthly_interest_rate": 0.025,
        "monthly_payment": monthly_payment,
        "total_payment": round(monthly_payment * term_months, 2),
        "total_interest": round((monthly_payment * term_months) - requested_amount, 2),
        "first_due_date": first_due_date.isoformat(),
        "schedule": schedule,
        "payment_summary": {
            "paid_installment_count": 0,
            "pending_installment_count": len(schedule),
            "overdue_installment_count": 0,
            "payment_progress_ratio": 0.0,
            "remaining_principal_after_last_payment": principal,
        },
    }


def _safe_float(value: object) -> float:
    """Sayisal profil degerini guvenli float degerine cevirir."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_optional_date(value: str, field_name: str) -> date | None:
    """Bos olmayan ISO tarih metnini date nesnesine cevirir."""

    if not value.strip():
        return None

    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=f"{field_name} YYYY-AA-GG formatında olmalı.") from error


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
