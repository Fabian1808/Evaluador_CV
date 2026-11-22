"""Widgets reutilizables de la interfaz."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import constants as C
from app.ui.theme import score_color
from app.ui.workers import BackgroundTask


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def restyle(widget: QWidget) -> None:
    """Reaplica la hoja de estilos tras cambiar una propiedad dinámica."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def set_variant(button: QPushButton, variant: str) -> QPushButton:
    button.setProperty("variant", variant)
    restyle(button)
    return button


def primary_button(text: str, on_click: Callable | None = None) -> QPushButton:
    button = QPushButton(text)
    set_variant(button, "primary")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click:
        button.clicked.connect(on_click)
    return button


def secondary_button(text: str, on_click: Callable | None = None) -> QPushButton:
    button = QPushButton(text)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click:
        button.clicked.connect(on_click)
    return button


def danger_button(text: str, on_click: Callable | None = None) -> QPushButton:
    button = QPushButton(text)
    set_variant(button, "danger")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click:
        button.clicked.connect(on_click)
    return button


def ghost_button(text: str, on_click: Callable | None = None) -> QPushButton:
    button = QPushButton(text)
    set_variant(button, "ghost")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click:
        button.clicked.connect(on_click)
    return button


def format_date(value: datetime | None) -> str:
    if value is None:
        return "—"
    try:
        return value.strftime("%d/%m/%Y %H:%M")
    except (AttributeError, ValueError):
        return str(value)


def format_short_date(value: datetime | None) -> str:
    if value is None:
        return "—"
    try:
        return value.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        return str(value)


# ---------------------------------------------------------------------------
# Mensajes
# ---------------------------------------------------------------------------
def _message_box(
    parent: QWidget | None,
    title: str,
    text: str,
    icon: QMessageBox.Icon,
    confirm: bool = False,
    confirm_text: str = "Confirmar",
) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(icon)
    box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    if confirm:
        accept = box.addButton(confirm_text, QMessageBox.ButtonRole.AcceptRole)
        cancel = box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel)
        box.exec()
        return box.clickedButton() is accept
    close = box.addButton("Entendido", QMessageBox.ButtonRole.AcceptRole)
    box.setDefaultButton(close)
    box.exec()
    return True


def info_message(parent: QWidget | None, text: str, title: str = "Información") -> None:
    _message_box(parent, title, text, QMessageBox.Icon.Information)


def warn_message(parent: QWidget | None, text: str, title: str = "Aviso") -> None:
    _message_box(parent, title, text, QMessageBox.Icon.Warning)


def error_message(parent: QWidget | None, text: str, title: str = "No se pudo completar la acción") -> None:
    _message_box(parent, title, text, QMessageBox.Icon.Critical)


def confirm_message(
    parent: QWidget | None,
    text: str,
    title: str = "Confirmar acción",
    confirm_text: str = "Confirmar",
) -> bool:
    return _message_box(
        parent, title, text, QMessageBox.Icon.Question, confirm=True, confirm_text=confirm_text
    )


# ---------------------------------------------------------------------------
# Contenedores
# ---------------------------------------------------------------------------
class Card(QFrame):
    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        parent: QWidget | None = None,
        padding: int = 16,
        spacing: int = 10,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(spacing)
        if title:
            header = QVBoxLayout()
            header.setSpacing(2)
            title_label = QLabel(title)
            title_label.setObjectName("CardTitle")
            header.addWidget(title_label)
            if subtitle:
                subtitle_label = QLabel(subtitle)
                subtitle_label.setObjectName("CardSubtitle")
                subtitle_label.setWordWrap(True)
                header.addWidget(subtitle_label)
            self._layout.addLayout(header)
        self.body = self._layout

    def add(self, widget: QWidget, stretch: int = 0) -> None:
        self._layout.addWidget(widget, stretch)


class StatCard(QFrame):
    def __init__(
        self,
        label: str,
        value: str = "0",
        hint: str = "",
        accent: str = C.COLOR_PRIMARY,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(3)

        top = QHBoxLayout()
        top.setSpacing(8)
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{accent}; font-size:12px;")
        self.label = QLabel(label)
        self.label.setObjectName("StatLabel")
        top.addWidget(dot)
        top.addWidget(self.label)
        top.addStretch(1)
        layout.addLayout(top)

        self.value = QLabel(value)
        self.value.setObjectName("StatValue")
        layout.addWidget(self.value)

        self.hint = QLabel(hint)
        self.hint.setObjectName("StatHint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

    def set_value(self, value: str, hint: str | None = None) -> None:
        self.value.setText(value)
        if hint is not None:
            self.hint.setText(hint)


class Pill(QLabel):
    def __init__(self, text: str = "", tone: str = "muted", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("Pill")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        restyle(self)


class Banner(QFrame):
    def __init__(
        self,
        text: str = "",
        tone: str = "info",
        title: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Banner")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(10)
        self.icon = QLabel("●")
        self.icon.setStyleSheet("font-size:13px;")
        self._layout.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("BannerTitle")
        self.title_label.setVisible(bool(title))
        self.text_label = QLabel(text)
        self.text_label.setObjectName("BannerText")
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.text_label)
        self._layout.addLayout(text_layout, 1)
        self.set_tone(tone)
        self.setVisible(bool(text or title))

    def set_tone(self, tone: str) -> None:
        colors = {
            "info": C.COLOR_INFO,
            "success": C.COLOR_SUCCESS,
            "warning": C.COLOR_WARNING,
            "danger": C.COLOR_DANGER,
        }
        self.icon.setStyleSheet(f"color:{colors.get(tone, C.COLOR_MUTED)}; font-size:13px;")
        self.setProperty("tone", tone)
        restyle(self)

    def set_message(self, text: str, tone: str | None = None, title: str | None = None) -> None:
        self.text_label.setText(text)
        if title is not None:
            self.title_label.setText(title)
            self.title_label.setVisible(bool(title))
        if tone:
            self.set_tone(tone)
        self.setVisible(bool(text or self.title_label.text()))


class SectionTitle(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("SectionTitle")


class PageHeader(QWidget):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self.title = QLabel(title)
        self.title.setObjectName("HeaderTitle")
        text_layout.addWidget(self.title)
        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("HeaderSubtitle")
        self.subtitle.setWordWrap(True)
        text_layout.addWidget(self.subtitle)
        layout.addLayout(text_layout, 1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)
        layout.addLayout(self.actions)

    def add_action(self, widget: QWidget) -> None:
        self.actions.addWidget(widget)


class EmptyState(QWidget):
    def __init__(
        self,
        title: str,
        text: str,
        action_text: str = "",
        on_action: Callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 36, 24, 36)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel("◔")
        icon.setStyleSheet(f"color:{C.COLOR_PRIMARY}; font-size:34px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size:15px; font-weight:700;")
        layout.addWidget(title_label)
        text_label = QLabel(text)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setWordWrap(True)
        text_label.setObjectName("Muted")
        text_label.setMaximumWidth(520)
        layout.addWidget(text_label, 0, Qt.AlignmentFlag.AlignHCenter)
        if action_text and on_action:
            button = primary_button(action_text, on_action)
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)


class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(f"color:{C.COLOR_BORDER};")


# ---------------------------------------------------------------------------
# Puntuaciones
# ---------------------------------------------------------------------------
class ScoreRing(QWidget):
    """Anillo de progreso con la puntuación en el centro."""

    def __init__(
        self,
        value: float = 0.0,
        caption: str = "",
        diameter: int = 104,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._value = max(0.0, min(100.0, float(value)))
        self.caption = caption
        self._diameter = diameter
        self.setFixedSize(diameter, diameter + (18 if caption else 0))

    def set_value(self, value: float, caption: str | None = None) -> None:
        self._value = max(0.0, min(100.0, float(value)))
        if caption is not None:
            self.caption = caption
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - API Qt
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        margin = 7
        rect = QRectF(
            margin,
            margin,
            self._diameter - margin * 2,
            self._diameter - margin * 2,
        )
        pen = QPen(QColor("#EDEFF2"), 9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)
        pen.setColor(QColor(score_color(self._value)))
        painter.setPen(pen)
        painter.drawArc(rect, 90 * 16, -int(360 * 16 * self._value / 100))
        painter.setPen(QColor(C.COLOR_DARK))
        font = QFont(self.font())
        font.setPointSizeF(max(11.0, self._diameter / 8.2))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self._value:.0f}")
        if self.caption:
            painter.setPen(QColor(C.COLOR_MUTED))
            small = QFont(self.font())
            small.setPointSizeF(8.5)
            painter.setFont(small)
            painter.drawText(
                QRectF(0, self._diameter - 2, self._diameter, 18),
                Qt.AlignmentFlag.AlignCenter,
                self.caption,
            )


class ScoreBar(QWidget):
    def __init__(
        self,
        label: str = "",
        value: float = 0.0,
        detail: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._value = max(0.0, min(100.0, float(value)))
        self._label_text = label
        self._detail_text = detail
        self.setMinimumHeight(34)

    def set_value(self, value: float, detail: str | None = None) -> None:
        self._value = max(0.0, min(100.0, float(value)))
        if detail is not None:
            self._detail_text = detail
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width()
        painter.setPen(QColor(C.COLOR_DARK))
        font = QFont(self.font())
        font.setPointSizeF(9.0)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, width * 0.6, 16), Qt.AlignmentFlag.AlignLeft, self._label_text)
        painter.setPen(QColor(score_color(self._value)))
        painter.drawText(
            QRectF(width * 0.6, 0, width * 0.4, 16),
            Qt.AlignmentFlag.AlignRight,
            f"{self._value:.0f}/100",
        )
        track = QRectF(0, 21, width, 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#EDEFF2")))
        painter.drawRoundedRect(track, 3, 3)
        painter.setBrush(QBrush(QColor(score_color(self._value))))
        painter.drawRoundedRect(QRectF(0, 21, width * self._value / 100, 6), 3, 3)
        if self._detail_text:
            painter.setPen(QColor(C.COLOR_MUTED))
            small = QFont(self.font())
            small.setPointSizeF(8.0)
            painter.setFont(small)
            painter.drawText(
                QRectF(0, 29, width, 14),
                Qt.AlignmentFlag.AlignLeft,
                self._detail_text,
            )


# ---------------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------------
def configure_table(
    table: QTableWidget,
    headers: list[str],
    stretch_last: bool = True,
    row_height: int = 34,
) -> None:
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setWordWrap(False)
    table.verticalHeader().setDefaultSectionSize(row_height)
    table.horizontalHeader().setHighlightSections(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if stretch_last:
        table.horizontalHeader().setStretchLastSection(True)


def table_item(text: Any, user_data: Any = None, tooltip: str = "") -> QTableWidgetItem:
    item = QTableWidgetItem("" if text is None else str(text))
    if user_data is not None:
        item.setData(Qt.ItemDataRole.UserRole, user_data)
    if tooltip:
        item.setToolTip(tooltip)
    return item


def selected_row_data(table: QTableWidget) -> Any:
    row = table.currentRow()
    if row < 0:
        return None
    item = table.item(row, 0)
    if item is None:
        return None
    return item.data(Qt.ItemDataRole.UserRole)


# ---------------------------------------------------------------------------
# Diálogo de progreso
# ---------------------------------------------------------------------------
class BusyDialog(QDialog):
    """Ejecuta una tarea mostrando progreso real y permitiendo cancelar."""

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        fn: Callable[..., Any],
        cancelable: bool = True,
        success_text: str = "Operación completada.",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._cancelable = cancelable
        self._success_text = success_text
        self.result_value: Any = None
        self.error_text = ""
        self.was_cancelled = False
        self._closing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(10)

        heading = QLabel(title)
        heading.setObjectName("DialogTitle")
        layout.addWidget(heading)

        self.status = QLabel("Iniciando…")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.cancel_button = secondary_button("Cancelar")
        self.cancel_button.setEnabled(cancelable)
        self.cancel_button.clicked.connect(self._cancel)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

        self.task = BackgroundTask(fn, self)
        self.task.progress.connect(self._on_progress)
        self.task.finished.connect(self._on_finished)
        self.task.failed.connect(self._on_failed)
        self.task.cancelled.connect(self._on_cancelled)

    # ------------------------------------------------------------------ run
    def run(self) -> Any:
        self.task.start()
        self.exec()
        return self.result_value

    # --------------------------------------------------------------- eventos
    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(max(0, min(100, percent)))
        if message:
            self.status.setText(message)

    def _on_finished(self, result: Any) -> None:
        self.result_value = result
        self._closing = True
        self.accept()

    def _on_failed(self, message: str) -> None:
        self.error_text = message
        self._closing = True
        self.reject()

    def _on_cancelled(self) -> None:
        self.was_cancelled = True
        self._closing = True
        self.reject()

    def _cancel(self) -> None:
        if not self._cancelable:
            return
        self.task.cancel()
        self.cancel_button.setEnabled(False)
        self.status.setText("Cancelando… espere a que finalice la operación en curso.")
        self.progress.setRange(0, 0)

    def reject(self) -> None:
        if not self._closing:
            self._cancel()
            return
        super().reject()

    def closeEvent(self, event) -> None:  # noqa: N802
        if not self._closing:
            self._cancel()
            event.ignore()
            return
        super().closeEvent(event)


def run_with_progress(
    parent: QWidget | None,
    title: str,
    fn: Callable[..., Any],
    cancelable: bool = True,
) -> tuple[Any, str, bool]:
    """Ejecuta ``fn`` con un diálogo modal.

    Devuelve ``(resultado, error, cancelado)``.
    """
    dialog = BusyDialog(parent, title, fn, cancelable=cancelable)
    result = dialog.run()
    return result, dialog.error_text, dialog.was_cancelled


# ---------------------------------------------------------------------------
# Etiquetas de metadatos
# ---------------------------------------------------------------------------
class TagList(QWidget):
    """Lista de etiquetas que se ajusta al ancho disponible."""

    def __init__(self, tags: Iterable[str] = (), tone: str = "muted", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._layout.addStretch(1)
        self._tone = tone
        self.set_tags(tags)

    def set_tags(self, tags: Iterable[str], tone: str | None = None) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._tone = tone or self._tone
        for tag in tags:
            pill = Pill(str(tag), self._tone)
            self._layout.addWidget(pill)
        self._layout.addStretch(1)


class KeyValueRow(QWidget):
    def __init__(self, key: str, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        key_label = QLabel(key)
        key_label.setObjectName("Muted")
        key_label.setMinimumWidth(140)
        key_label.setMaximumWidth(190)
        value_label = QLabel(value)
        value_label.setWordWrap(True)
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(key_label, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(value_label, 1)
        self.value_label = value_label

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)
