"""Utilidades de archivos y almacenamiento local."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
from pathlib import Path

from app.config import paths


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return cleaned or "documento"


def human_size(size_bytes: int | float | None) -> str:
    if not size_bytes:
        return "—"
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_to_storage(source: Path, category: str = "cvs") -> Path:
    """Copia un documento al almacenamiento interno sin modificar el original."""
    paths.ensure_directories()
    target_dir = paths.CVS_DIR if category == "cvs" else paths.OFFERS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    digest = sha256_file(source)[:12]
    safe_name = sanitize_filename(source.name)
    target = target_dir / f"{digest}_{safe_name}"
    if not target.exists():
        shutil.copy2(source, target)
    return target


def read_text_file(path: Path, max_chars: int = 200_000) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)[:max_chars]
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")[:max_chars]


def open_in_system(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:  # pragma: no cover
        import subprocess
        subprocess.Popen(["xdg-open", str(path)])


def reveal_in_explorer(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    if os.name == "nt":
        os.system(f'explorer /select,"{path}"')  # noqa: S605 - ruta controlada
    else:  # pragma: no cover
        open_in_system(path.parent)


def delete_file_quietly(path: Path | str | None) -> None:
    if not path:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass
