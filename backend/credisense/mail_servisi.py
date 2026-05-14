from __future__ import annotations

"""E-posta gonderim servisi.

Gmail ile token gondermek icin SMTP ayarlari ortam degiskenlerinden okunur.
Yerel gelistirmede SMTP bilgisi yoksa servis e-posta gondermeden tokeni API
cevabinda gelistirme amacli dondurur.
"""

import os
import smtplib
from email.message import EmailMessage


def send_verification_email(email: str, full_name: str, token: str) -> dict:
    """Kullaniciya e-posta dogrulama tokeni gonderir."""

    _load_local_env()
    smtp_user = os.getenv("CREDISENSE_SMTP_USER", "").strip()
    smtp_password = os.getenv("CREDISENSE_SMTP_PASSWORD", "").strip()
    smtp_host = os.getenv("CREDISENSE_SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("CREDISENSE_SMTP_PORT", "587"))
    mail_from = os.getenv("CREDISENSE_MAIL_FROM", smtp_user).strip()

    if not smtp_user or not smtp_password or not mail_from:
        return {
            "sent": False,
            "provider": "local",
            "message": "SMTP ayari bulunamadigi icin e-posta gonderilmedi.",
        }

    message = EmailMessage()
    message["Subject"] = "CrediSense AI e-posta dogrulama kodu"
    message["From"] = mail_from
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                f"Merhaba {full_name},",
                "",
                "CrediSense AI kaydinizi tamamlamak icin asagidaki dogrulama kodunu kullanin:",
                "",
                token,
                "",
                "Bu kod kisa sure sonra gecersiz olur.",
            ]
        )
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

    return {
        "sent": True,
        "provider": "gmail-smtp",
        "message": "Dogrulama e-postasi gonderildi.",
    }


def _load_local_env() -> None:
    """Basit .env okuyucu. Ek kutuphane gerektirmeden SMTP ayarlarini alir."""

    env_path = ".env"
    if not os.path.exists(env_path):
        return

    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            clean_line = line.strip()
            if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
                continue
            key, value = clean_line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
