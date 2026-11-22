"""Rutas del proyecto y del almacenamiento local.

Todas las rutas se calculan a partir de la ubicación del paquete para que la
aplicación funcione tanto en desarrollo como dentro de un ejecutable PyInstaller.
La variable de entorno ``CV_ANALYZER_DATA_DIR`` permite redirigir el
almacenamiento (útil para pruebas y para instalaciones portables).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _project_root() -> Path:
    # PyInstaller extrae recursos en _MEIPASS; __file__ ya no representa el
    # directorio de trabajo del usuario en un ejecutable one-file.
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    # app/config/paths.py -> app/config -> app -> raíz del proyecto
    return Path(__file__).resolve().parents[2]


def _data_root() -> Path:
    override = os.environ.get("CV_ANALYZER_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / "CV Analyzer Pro"
    return _project_root() / "storage"


PROJECT_ROOT: Path = _project_root()
RESOURCES_DIR: Path = PROJECT_ROOT / "resources"
TEMPLATES_DIR: Path = RESOURCES_DIR / "templates"
STYLES_DIR: Path = RESOURCES_DIR / "styles"
ICONS_DIR: Path = RESOURCES_DIR / "icons"

STORAGE_DIR: Path = _data_root()
CVS_DIR: Path = STORAGE_DIR / "cvs"
OFFERS_DIR: Path = STORAGE_DIR / "offers"
EXPORTS_DIR: Path = STORAGE_DIR / "exports"
DATABASE_DIR: Path = STORAGE_DIR / "database"
BACKUPS_DIR: Path = STORAGE_DIR / "backups"
LOGS_DIR: Path = STORAGE_DIR / "logs"
DOCUMENTS_DIR: Path = STORAGE_DIR / "documents"

DATABASE_PATH: Path = DATABASE_DIR / "cv_analyzer.db"


def ensure_directories() -> None:
    """Crea los directorios de trabajo si no existen."""
    for directory in (
        STORAGE_DIR,
        CVS_DIR,
        OFFERS_DIR,
        EXPORTS_DIR,
        DATABASE_DIR,
        BACKUPS_DIR,
        LOGS_DIR,
        DOCUMENTS_DIR,
        TEMPLATES_DIR,
        STYLES_DIR,
        ICONS_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
