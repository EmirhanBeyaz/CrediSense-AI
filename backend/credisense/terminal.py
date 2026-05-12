from __future__ import annotations

"""Terminal giriş noktası

Şu an projede web arayüzü yok. Bu dosya, tüm analiz akışını terminalden çalıştırmak için
kullanılır.
"""

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from backend.credisense.analiz_akisi import analyze_documents
    from backend.credisense.rapor_uret import create_analysis_reports, report_files_to_dict
else:
    from .analiz_akisi import analyze_documents
    from .rapor_uret import create_analysis_reports, report_files_to_dict


def main() -> None:
    parser = argparse.ArgumentParser(description="CrediSense AI terminal analiz motoru")
    parser.add_argument("pdfs", nargs="+", help="Analiz edilecek PDF belgeleri")
    parser.add_argument(
        "--dataset",
        default="veri/sentetik_kredi_basvuru_veri_seti.csv",
        help="Sentetik CSV veri seti yolu",
    )
    parser.add_argument(
        "--form",
        default="",
        help="Başvuru formu JSON dosyası",
    )
    parser.add_argument(
        "--report-dir",
        default="raporlar",
        help="Analiz raporlarının yazılacağı klasör",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Rapor dosyası üretmeden sadece terminal çıktısı verir",
    )
    args = parser.parse_args()

    pdf_paths = [Path(path) for path in args.pdfs]
    missing_pdfs = [str(path) for path in pdf_paths if not path.exists()]
    if missing_pdfs:
        parser.error(f"PDF dosyası bulunamadı: {', '.join(missing_pdfs)}")

    dataset_path = Path(args.dataset) if args.dataset else None

    try:
        application_form = _read_application_form(args.form)
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))

    result = analyze_documents(
        pdf_paths,
        dataset_path=dataset_path,
        application_form=application_form,
    )

    if not args.no_report:
        report_files = create_analysis_reports(
            result,
            output_folder=Path(args.report_dir),
            analysis_id=result.get("application_id", ""),
        )
        result["report_files"] = report_files_to_dict(report_files)

    print(json.dumps(result, ensure_ascii=False, indent=2))


def _read_application_form(form_path: str) -> dict:
    """Varsa başvuru formu JSON dosyasını okur."""

    if not form_path:
        return {}

    path = Path(form_path)
    if not path.exists():
        raise FileNotFoundError(f"Başvuru formu bulunamadı: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Başvuru formu geçerli JSON değil: {path}") from error

    if not isinstance(payload, dict):
        raise ValueError(f"Başvuru formu JSON nesnesi olmalı: {path}")

    return payload


if __name__ == "__main__":
    main()
