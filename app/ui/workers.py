"""Trabajo en segundo plano con progreso y cancelación.

Ninguna operación pesada (extracción, evaluación, IA, exportación) se ejecuta
en el hilo de la interfaz. ``BackgroundTask`` envuelve una función y emite
señales Qt seguras desde el hilo del pool.
"""

from __future__ import annotations

import inspect
import threading
import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _WorkerSignals(QObject):
    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()


class _Worker(QRunnable):
    def __init__(self, task: "BackgroundTask") -> None:
        super().__init__()
        self.task = task
        self.setAutoDelete(True)

    def run(self) -> None:  # pragma: no cover - ejecutado en otro hilo
        task = self.task
        try:
            result = task._invoke()
        except Exception as exc:  # noqa: BLE001 - se reporta a la interfaz
            if task.cancel_event.is_set():
                task.signals.cancelled.emit()
            else:
                task.signals.failed.emit(_format_error(exc))
            return
        if task.cancel_event.is_set():
            task.signals.cancelled.emit()
        else:
            task.signals.finished.emit(result)


def _format_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    if isinstance(exc, (ValueError, FileNotFoundError, PermissionError, OSError)):
        return message
    detail = traceback.format_exc(limit=3)
    return f"{message}\n\nDetalle técnico:\n{detail}"


class BackgroundTask(QObject):
    """Ejecuta ``fn`` en un hilo del pool y expone señales Qt.

    La función puede declarar ``progress`` (``callable(percent, message)``) y
    ``cancel_event`` (``threading.Event``); el contenedor solo pasa los
    argumentos que la función acepta.
    """

    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, fn: Callable[..., Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.fn = fn
        self.cancel_event = threading.Event()
        self.signals = _WorkerSignals()
        self.signals.progress.connect(self.progress)
        self.signals.finished.connect(self.finished)
        self.signals.failed.connect(self.failed)
        self.signals.cancelled.connect(self.cancelled)
        self._started = False
        self._finished = False

    # ------------------------------------------------------------------ API
    def start(self) -> None:
        if self._started:
            return
        self._started = True
        pool = QThreadPool.globalInstance()
        pool.start(_Worker(self))

    def cancel(self) -> None:
        self.cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def _emit_progress(self, percent: int, message: str) -> None:
        if not self.cancel_event.is_set():
            self.signals.progress.emit(int(percent), str(message))

    def _invoke(self) -> Any:
        try:
            parameters = inspect.signature(self.fn).parameters
        except (TypeError, ValueError):
            parameters = {}
        accepts_kwargs = any(
            item.kind is inspect.Parameter.VAR_KEYWORD for item in parameters.values()
        )
        kwargs: dict[str, Any] = {}
        if accepts_kwargs or "progress" in parameters:
            kwargs["progress"] = self._emit_progress
        if accepts_kwargs or "cancel_event" in parameters:
            kwargs["cancel_event"] = self.cancel_event
        return self.fn(**kwargs)


def run_task(
    parent: QObject,
    fn: Callable[..., Any],
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    on_progress: Callable[[int, str], None] | None = None,
    on_cancelled: Callable[[], None] | None = None,
    keep_alive: list | None = None,
) -> BackgroundTask:
    """Crea, conecta e inicia una tarea en segundo plano.

    ``keep_alive`` permite a la página conservar una referencia hasta que la
    tarea termine (evita que el recolector la destruya).
    """
    task = BackgroundTask(fn, parent)
    if on_success:
        task.finished.connect(on_success)
    if on_error:
        task.failed.connect(on_error)
    if on_progress:
        task.progress.connect(on_progress)
    if on_cancelled:
        task.cancelled.connect(on_cancelled)
    if keep_alive is not None:
        keep_alive.append(task)
        task.finished.connect(lambda _result: _discard(keep_alive, task))
        task.failed.connect(lambda _error: _discard(keep_alive, task))
        task.cancelled.connect(lambda: _discard(keep_alive, task))
    task.start()
    return task


def _discard(container: list, item: Any) -> None:
    try:
        container.remove(item)
    except ValueError:
        pass
