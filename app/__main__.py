"""Permite iniciar la aplicación con python -m app."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config.constants import APP_NAME
from app.core.context import AppContext
from app.core.logging_config import setup_logging
from app.ui.main_window import MainWindow


def main() -> int:
    setup_logging()
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    context = AppContext()
    window = MainWindow(context)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
