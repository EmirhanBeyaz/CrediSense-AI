from __future__ import annotations

"""İndirilen veri setlerini hızlı kontrol etme aracı

Büyük CSV dosyalarını tamamen belleğe almadan kontrol eder.
Her dosya için:
- dosya yolu
- dosya boyutu
- satır sayısı
- sütun sayısı
- ilk birkaç sütun adı
bilgilerini üretir.
"""

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_FOLDER = Path("veri") / "kaynak_veri_setleri" / "kaggle"


@dataclass
class DatasetFileSummary:
    file_path: str
    file_size_mb: float
    row_count: int
    column_count: int
    first_columns: list[str]
    error: str = ""


def inspect_csv_files(folder: Path = DEFAULT_FOLDER) -> list[DatasetFileSummary]:
    """Klasör altındaki CSV dosyalarını tarar."""

    summaries: list[DatasetFileSummary] = []

    for csv_path in sorted(folder.rglob("*.csv")):
        summaries.append(inspect_csv_file(csv_path))

    return summaries


def inspect_csv_file(csv_path: Path) -> DatasetFileSummary:
    """Tek bir CSV dosyasını satır satır okuyarak özetler."""

    try:
        file_size_mb = csv_path.stat().st_size / (1024 * 1024)

        with csv_path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file)
            header = next(reader, [])
            row_count = sum(1 for _ in reader)

        return DatasetFileSummary(
            file_path=str(csv_path),
            file_size_mb=round(file_size_mb, 2),
            row_count=row_count,
            column_count=len(header),
            first_columns=header[:15],
        )
    except Exception as error:
        return DatasetFileSummary(
            file_path=str(csv_path),
            file_size_mb=0.0,
            row_count=0,
            column_count=0,
            first_columns=[],
            error=f"{type(error).__name__}: {error}",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="İndirilen Kaggle CSV veri setlerini kontrol eder")
    parser.add_argument(
        "--folder",
        default=str(DEFAULT_FOLDER),
        help="Kontrol edilecek veri seti klasörü",
    )
    args = parser.parse_args()

    summaries = inspect_csv_files(Path(args.folder))
    print(json.dumps([asdict(summary) for summary in summaries], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
