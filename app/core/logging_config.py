"""Configuración de registro de eventos.

Los logs nunca incluyen el texto de los CV ni datos personales: solo eventos
técnicos, rutas de almacenamiento y errores.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import paths


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    paths.ensure_directories()
    logger = logging.getLogger("cv_analyzer")
    if logger.handlers:
        return logger
    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        paths.LOGS_DIR / "cv_analyzer.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(formatter)
    logger.addHandler(console)
    return logger
