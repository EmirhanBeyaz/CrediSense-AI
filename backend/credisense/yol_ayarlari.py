from __future__ import annotations

"""Proje genelinde kullanilan dosya yolu yardimcilari."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def project_path(*parts: str) -> Path:
    """Proje kokune gore mutlak dosya yolu uretir."""

    return PROJECT_ROOT.joinpath(*parts)


def data_path(file_name: str) -> Path:
    """`veri` klasoru altindaki dosyalar icin mutlak yol uretir."""

    return project_path("veri", file_name)


def data_folder(folder_name: str) -> Path:
    """`veri` klasoru altindaki klasorler icin mutlak yol uretir."""

    return project_path("veri", folder_name)
