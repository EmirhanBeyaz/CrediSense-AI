from __future__ import annotations

"""Kullanici sifresi sifirlama araci.

Sifreler veritabaninda duz metin tutulmaz. Bu nedenle eski sifre goruntulenemez;
gerekirse bu komutla yeni sifre atanir.
"""

import argparse
import getpass
import json

from .kullanici_deposu import change_user_password


def main() -> None:
    parser = argparse.ArgumentParser(description="CrediSense kullanici sifresi sifirlama")
    parser.add_argument("identifier", help="Kullanici adi veya e-posta")
    parser.add_argument("--password", default="", help="Yeni sifre. Bos birakilirsa gizli istenir.")
    args = parser.parse_args()

    new_password = args.password or getpass.getpass("Yeni sifre: ")
    updated_user = change_user_password(args.identifier, new_password)

    print(
        json.dumps(
            {
                "ok": True,
                "message": "Kullanici sifresi guncellendi.",
                "user": updated_user,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
