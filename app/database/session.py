"""Gestión de la base de datos SQLite y de las sesiones SQLAlchemy."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import paths
from app.database.models import Base


class Database:
    """Contenedor del motor y de la fábrica de sesiones.

    Se usa una base SQLite con ``check_same_thread=False`` porque la interfaz
    crea sesiones independientes en hilos de trabajo. Nunca se comparte una
    misma ``Session`` entre hilos.
    """

    def __init__(self, url: str | None = None, echo: bool = False) -> None:
        paths.ensure_directories()
        if url is None:
            url = f"sqlite:///{paths.DATABASE_PATH.as_posix()}"
        self.url = url
        self.engine: Engine = create_engine(
            url,
            echo=echo,
            future=True,
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        self._install_sqlite_pragmas()
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )

    def _install_sqlite_pragmas(self) -> None:
        if not self.url.startswith("sqlite"):
            return

        @event.listens_for(self.engine, "connect")
        def _set_pragmas(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        self.engine.dispose()

    @property
    def database_path(self) -> Path | None:
        if self.url.startswith("sqlite:///"):
            return Path(self.url.replace("sqlite:///", "", 1))
        return None
