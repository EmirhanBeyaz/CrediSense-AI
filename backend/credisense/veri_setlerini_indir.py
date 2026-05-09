from __future__ import annotations

"""Açık veri setlerini indirme yardımcısı

Bu dosya model eğitiminde kullanabileceğimiz açık veri setlerini indirir.

Şimdilik Kaggle veri setlerini otomatik indirmiyoruz. Çünkü Kaggle çoğu zaman kullanıcı
girişi veya API anahtarı ister. Bu yüzden ilk aşamada doğrudan indirilebilen UCI veri
setleriyle başlıyoruz.
"""

import argparse
import json
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path


DATASET_FOLDER = Path("veri") / "kaynak_veri_setleri"


@dataclass
class DatasetSource:
    """İndirilecek veri setinin temel bilgileri."""

    name: str
    url: str
    file_name: str
    description: str
    source_page: str


@dataclass
class DownloadResult:
    """İndirme sonucunu terminalde anlaşılır göstermek için kullanılır."""

    name: str
    ok: bool
    saved_path: str
    extracted_folder: str
    message: str


DATASETS = [
    DatasetSource(
        name="statlog_german_credit",
        url="https://archive.ics.uci.edu/static/public/144/statlog+german+credit+data.zip",
        file_name="statlog_german_credit.zip",
        description="1.000 kayıtlı klasik iyi/kötü kredi riski veri seti.",
        source_page="https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data",
    ),
    DatasetSource(
        name="south_german_credit",
        url="https://archive.ics.uci.edu/static/public/522/south+german+credit.zip",
        file_name="south_german_credit.zip",
        description="German Credit veri setinin düzeltilmiş ve açıklamalı sürümü.",
        source_page="https://archive.ics.uci.edu/dataset/522/south+german+credit",
    ),
    DatasetSource(
        name="default_of_credit_card_clients",
        url="https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip",
        file_name="default_of_credit_card_clients.zip",
        description="30.000 kredi kartı müşterisi ve temerrüt hedef değişkeni.",
        source_page="https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients",
    ),
    DatasetSource(
        name="statlog_australian_credit_approval",
        url="https://archive.ics.uci.edu/static/public/143/statlog+australian+credit+approval.zip",
        file_name="statlog_australian_credit_approval.zip",
        description="690 kredi kartı başvurusu, onay/red sınıflandırma veri seti.",
        source_page="https://archive.ics.uci.edu/dataset/143/statlog+australian+credit+approval",
    ),
]


def download_all_datasets(output_folder: Path = DATASET_FOLDER) -> list[DownloadResult]:
    """Tanımlı tüm veri setlerini indirir."""

    output_folder.mkdir(parents=True, exist_ok=True)
    results: list[DownloadResult] = []

    for dataset in DATASETS:
        result = download_dataset(dataset, output_folder)
        results.append(result)

    _write_manifest(output_folder, results)
    return results


def download_dataset(dataset: DatasetSource, output_folder: Path) -> DownloadResult:
    """Tek bir veri setini indirir ve zip ise klasöre açar."""

    zip_path = output_folder / dataset.file_name
    extract_folder = output_folder / dataset.name

    try:
        _download_file(dataset.url, zip_path)
        _extract_zip(zip_path, extract_folder)
        return DownloadResult(
            name=dataset.name,
            ok=True,
            saved_path=str(zip_path),
            extracted_folder=str(extract_folder),
            message="İndirildi ve klasöre açıldı.",
        )
    except (OSError, urllib.error.URLError, zipfile.BadZipFile) as error:
        return DownloadResult(
            name=dataset.name,
            ok=False,
            saved_path=str(zip_path),
            extracted_folder=str(extract_folder),
            message=f"{type(error).__name__}: {error}",
        )


def _download_file(url: str, target_path: Path) -> None:
    """URL'deki dosyayı hedef yola indirir."""

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CrediSenseAIStudentProject/1.0"},
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        target_path.write_bytes(response.read())


def _extract_zip(zip_path: Path, extract_folder: Path) -> None:
    """Zip dosyasını aynı isimli klasöre açar."""

    extract_folder.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zip_file:
        zip_file.extractall(extract_folder)


def _write_manifest(output_folder: Path, results: list[DownloadResult]) -> None:
    """İndirilen veri setleri için küçük bir özet JSON dosyası yazar."""

    payload = {
        "datasets": [asdict(dataset) for dataset in DATASETS],
        "download_results": [asdict(result) for result in results],
    }
    manifest_path = output_folder / "manifest.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="CrediSense AI açık veri setlerini indirir")
    parser.add_argument(
        "--output",
        default=str(DATASET_FOLDER),
        help="Veri setlerinin indirileceği klasör",
    )
    args = parser.parse_args()

    results = download_all_datasets(Path(args.output))
    print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
