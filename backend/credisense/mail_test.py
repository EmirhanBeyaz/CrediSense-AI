from __future__ import annotations

"""Gmail SMTP dogrulama testi."""

import argparse

from .mail_servisi import get_mail_settings_status, send_verification_email


def main() -> None:
    parser = argparse.ArgumentParser(description="CrediSense Gmail SMTP test araci")
    parser.add_argument("email", help="Test kodunun gonderilecegi e-posta adresi")
    args = parser.parse_args()

    status = get_mail_settings_status()
    print("SMTP durum:", status)
    if not status["ready"]:
        print(".env dosyasindaki Gmail SMTP ayarlari eksik.")
        return

    result = send_verification_email(
        email=args.email,
        full_name="CrediSense Test",
        token="123456",
    )
    print("Gonderim sonucu:", result)


if __name__ == "__main__":
    main()
