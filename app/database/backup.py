"""Copias de seguridad de la base de datos SQLite."""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import paths


def create_backup(database_path: Path | None = None, destination_dir: Path | None = None) -> Path:
    """Crea una copia consistente usando la API de backup de SQLite."""
    source = database_path or paths.DATABASE_PATH
    target_dir = destination_dir or paths.BACKUPS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = target_dir / f"cv_analyzer_backup_{stamp}.db"

    if not source.exists():
        raise FileNotFoundError(f"No existe la base de datos: {source}")

    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    return target


def list_backups(directory: Path | None = None) -> list[Path]:
    target_dir = directory or paths.BACKUPS_DIR
    if not target_dir.exists():
        return []
    return sorted(target_dir.glob("cv_analyzer_backup_*.db"), reverse=True)


def restore_backup(backup_path: Path, database_path: Path | None = None) -> Path:
    """Restaura una copia. La base actual se conserva como respaldo previo."""
    target = database_path or paths.DATABASE_PATH
    if target.exists():
        safety = target.with_name(target.stem + "_pre_restore.db")
        shutil.copy2(target, safety)
    shutil.copy2(backup_path, target)
    return target
