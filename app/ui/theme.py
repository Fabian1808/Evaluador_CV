"""Identidad visual de la aplicación: hoja de estilos y utilidades de color."""

from __future__ import annotations

from app.config import constants as C

# ---------------------------------------------------------------------------
# Hoja de estilos global
# ---------------------------------------------------------------------------
STYLESHEET = f"""
* {{
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    outline: none;
}}
QWidget {{
    color: {C.COLOR_TEXT};
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background: {C.COLOR_BACKGROUND};
}}
QToolTip {{
    background: {C.COLOR_DARK};
    color: #FFFFFF;
    border: none;
    padding: 6px 8px;
    border-radius: 4px;
}}

/* ---------------------------------------------------------------- sidebar */
#Sidebar {{
    background: {C.COLOR_DARK};
    border: none;
}}
#SidebarBrand {{
    color: #FFFFFF;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.3px;
}}
#SidebarBrandAccent {{
    color: {C.COLOR_PRIMARY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
}}
#SidebarSection {{
    color: #9CA3AF;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
    padding: 14px 18px 6px 18px;
}}
QPushButton#NavButton {{
    background: transparent;
    color: #D7D9DE;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton#NavButton:hover {{
    background: rgba(255, 255, 255, 0.06);
    color: #FFFFFF;
}}
QPushButton#NavButton:checked {{
    background: rgba(255, 85, 0, 0.16);
    color: #FFFFFF;
    border-left: 3px solid {C.COLOR_PRIMARY};
    font-weight: 600;
}}
#SidebarFooter {{
    color: #8B8F98;
    font-size: 11px;
}}

/* ------------------------------------------------------------------ header */
#Header {{
    background: {C.COLOR_CARD};
    border-bottom: 1px solid {C.COLOR_BORDER};
}}
#HeaderTitle {{
    font-size: 19px;
    font-weight: 700;
    color: {C.COLOR_DARK};
}}
#HeaderSubtitle {{
    font-size: 12px;
    color: {C.COLOR_MUTED};
}}
#ContentArea {{
    background: {C.COLOR_BACKGROUND};
}}

/* ------------------------------------------------------------------- cards */
QFrame#Card {{
    background: {C.COLOR_CARD};
    border: 1px solid {C.COLOR_BORDER};
    border-radius: 10px;
}}
QFrame#StatCard {{
    background: {C.COLOR_CARD};
    border: 1px solid {C.COLOR_BORDER};
    border-radius: 10px;
}}
#StatValue {{
    font-size: 26px;
    font-weight: 700;
    color: {C.COLOR_DARK};
}}
#StatLabel {{
    font-size: 12px;
    color: {C.COLOR_MUTED};
}}
#StatHint {{
    font-size: 11px;
    color: {C.COLOR_MUTED};
}}
#CardTitle {{
    font-size: 14px;
    font-weight: 700;
    color: {C.COLOR_DARK};
}}
#CardSubtitle {{
    font-size: 12px;
    color: {C.COLOR_MUTED};
}}
#SectionTitle {{
    font-size: 16px;
    font-weight: 700;
    color: {C.COLOR_DARK};
}}
#Muted {{
    color: {C.COLOR_MUTED};
}}
#Mono {{
    font-family: 'Cascadia Mono', 'Consolas', monospace;
    font-size: 12px;
}}
#BigScore {{
    font-size: 30px;
    font-weight: 700;
    color: {C.COLOR_DARK};
}}

/* ------------------------------------------------------------------ botones */
QPushButton {{
    background: {C.COLOR_CARD};
    color: {C.COLOR_DARK};
    border: 1px solid {C.COLOR_BORDER};
    border-radius: 7px;
    padding: 8px 14px;
    font-weight: 600;
    min-height: 18px;
}}
QPushButton:hover {{
    border-color: #C9CDD4;
    background: #FAFAFB;
}}
QPushButton:pressed {{
    background: #F0F1F3;
}}
QPushButton:disabled {{
    color: #A7ABB3;
    background: #F4F5F7;
    border-color: #EDEEF0;
}}
QPushButton[variant="primary"] {{
    background: {C.COLOR_PRIMARY};
    color: #FFFFFF;
    border: 1px solid {C.COLOR_PRIMARY};
}}
QPushButton[variant="primary"]:hover {{
    background: {C.COLOR_PRIMARY_DARK};
    border-color: {C.COLOR_PRIMARY_DARK};
}}
QPushButton[variant="primary"]:pressed {{
    background: #B83D00;
}}
QPushButton[variant="primary"]:disabled {{
    background: #F3B999;
    border-color: #F3B999;
    color: #FFFFFF;
}}
QPushButton[variant="danger"] {{
    color: {C.COLOR_DANGER};
    border-color: #F3C6C2;
    background: #FFFFFF;
}}
QPushButton[variant="danger"]:hover {{
    background: {C.COLOR_DANGER_SOFT};
}}
QPushButton[variant="ghost"] {{
    background: transparent;
    border: none;
    color: {C.COLOR_PRIMARY_DARK};
    padding: 6px 8px;
}}
QPushButton[variant="ghost"]:hover {{
    background: {C.COLOR_PRIMARY_SOFT};
}}
QPushButton#LinkButton {{
    background: transparent;
    border: none;
    color: {C.COLOR_PRIMARY_DARK};
    text-align: left;
    padding: 2px;
    font-weight: 600;
}}
QPushButton#LinkButton:hover {{
    color: {C.COLOR_PRIMARY};
    text-decoration: underline;
}}

/* ------------------------------------------------------------------ inputs */
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background: #FFFFFF;
    border: 1px solid {C.COLOR_BORDER};
    border-radius: 7px;
    padding: 7px 9px;
    selection-background-color: {C.COLOR_PRIMARY_SOFT};
    selection-color: {C.COLOR_DARK};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 1px solid {C.COLOR_PRIMARY};
}}
QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled, QComboBox:disabled {{
    background: #F4F5F7;
    color: #9AA0A8;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background: #FFFFFF;
    border: 1px solid {C.COLOR_BORDER};
    selection-background-color: {C.COLOR_PRIMARY_SOFT};
    selection-color: {C.COLOR_DARK};
    padding: 4px;
}}
QCheckBox, QRadioButton {{
    spacing: 8px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
}}
QCheckBox::indicator:unchecked {{
    border: 1px solid #B9BEC6;
    border-radius: 4px;
    background: #FFFFFF;
}}
QCheckBox::indicator:checked {{
    border: 1px solid {C.COLOR_PRIMARY};
    border-radius: 4px;
    background: {C.COLOR_PRIMARY};
}}
QSlider::groove:horizontal {{
    height: 5px;
    background: #E8EAED;
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {C.COLOR_PRIMARY};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #FFFFFF;
    border: 2px solid {C.COLOR_PRIMARY};
}}

/* ------------------------------------------------------------------ tablas */
QTableWidget, QTableView, QTreeWidget, QListWidget {{
    background: #FFFFFF;
    border: 1px solid {C.COLOR_BORDER};
    border-radius: 8px;
    gridline-color: transparent;
    selection-background-color: {C.COLOR_PRIMARY_SOFT};
    selection-color: {C.COLOR_DARK};
    alternate-background-color: #FBFBFC;
}}
QTableWidget::item, QTableView::item, QListWidget::item {{
    padding: 6px 8px;
    border-bottom: 1px solid #F1F2F4;
}}
QTableWidget::item:selected, QTableView::item:selected, QListWidget::item:selected {{
    background: {C.COLOR_PRIMARY_SOFT};
    color: {C.COLOR_DARK};
}}
QHeaderView::section {{
    background: #F7F8FA;
    color: #4B5563;
    border: none;
    border-bottom: 1px solid {C.COLOR_BORDER};
    padding: 8px;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
}}
QTableCornerButton::section {{
    background: #F7F8FA;
    border: none;
}}

/* ------------------------------------------------------------------ tabs */
QTabWidget::pane {{
    border: 1px solid {C.COLOR_BORDER};
    border-radius: 8px;
    background: #FFFFFF;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {C.COLOR_MUTED};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 16px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {C.COLOR_PRIMARY_DARK};
    border-bottom: 2px solid {C.COLOR_PRIMARY};
}}
QTabBar::tab:hover {{
    color: {C.COLOR_DARK};
}}

/* --------------------------------------------------------------- scroll */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #CBD0D6;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #AEB4BC;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #CBD0D6;
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* --------------------------------------------------------------- progreso */
QProgressBar {{
    background: #EEF0F2;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {C.COLOR_PRIMARY};
    border-radius: 4px;
}}

/* --------------------------------------------------------------- mensajes */
QFrame#Banner {{
    border-radius: 8px;
    border: 1px solid {C.COLOR_BORDER};
    background: {C.COLOR_CARD};
}}
QFrame#Banner[tone="info"] {{
    background: {C.COLOR_INFO_SOFT};
    border-color: #C7D2FE;
}}
QFrame#Banner[tone="success"] {{
    background: {C.COLOR_SUCCESS_SOFT};
    border-color: #BFE3D1;
}}
QFrame#Banner[tone="warning"] {{
    background: {C.COLOR_WARNING_SOFT};
    border-color: #FDE68A;
}}
QFrame#Banner[tone="danger"] {{
    background: {C.COLOR_DANGER_SOFT};
    border-color: #F5C2BE;
}}
#BannerTitle {{
    font-weight: 700;
    color: {C.COLOR_DARK};
}}
#BannerText {{
    color: {C.COLOR_TEXT};
    font-size: 12px;
}}

/* ------------------------------------------------------------------ pills */
QLabel#Pill {{
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#Pill[tone="success"] {{
    background: {C.COLOR_SUCCESS_SOFT};
    color: {C.COLOR_SUCCESS};
}}
QLabel#Pill[tone="warning"] {{
    background: {C.COLOR_WARNING_SOFT};
    color: {C.COLOR_WARNING};
}}
QLabel#Pill[tone="danger"] {{
    background: {C.COLOR_DANGER_SOFT};
    color: {C.COLOR_DANGER};
}}
QLabel#Pill[tone="info"] {{
    background: {C.COLOR_INFO_SOFT};
    color: {C.COLOR_INFO};
}}
QLabel#Pill[tone="muted"] {{
    background: #F1F2F4;
    color: {C.COLOR_MUTED};
}}
QLabel#Pill[tone="primary"] {{
    background: {C.COLOR_PRIMARY_SOFT};
    color: {C.COLOR_PRIMARY_DARK};
}}

/* --------------------------------------------------------------- statusbar */
QStatusBar {{
    background: {C.COLOR_CARD};
    border-top: 1px solid {C.COLOR_BORDER};
    color: {C.COLOR_MUTED};
    font-size: 11px;
}}
QStatusBar::item {{
    border: none;
}}

/* --------------------------------------------------------------- dialogs */
QDialog QLabel#DialogTitle {{
    font-size: 17px;
    font-weight: 700;
    color: {C.COLOR_DARK};
}}
QGroupBox {{
    border: 1px solid {C.COLOR_BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 14px 12px 10px 12px;
    font-weight: 700;
    background: #FFFFFF;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {C.COLOR_MUTED};
    font-size: 11px;
    text-transform: uppercase;
}}
QSplitter::handle {{
    background: {C.COLOR_BORDER};
    width: 1px;
}}
"""


def score_color(score: float) -> str:
    """Color semántico para una puntuación de 0 a 100."""
    if score >= 80:
        return C.COLOR_SUCCESS
    if score >= 60:
        return C.COLOR_PRIMARY
    if score >= 40:
        return C.COLOR_WARNING
    return C.COLOR_DANGER


def score_tone(score: float) -> str:
    if score >= 80:
        return "success"
    if score >= 60:
        return "primary"
    if score >= 40:
        return "warning"
    return "danger"


def severity_tone(severity: str) -> str:
    return {
        "critical": "danger",
        "high": "danger",
        "medium": "warning",
        "low": "info",
        "info": "muted",
    }.get(severity, "muted")


def status_tone(status: str) -> str:
    mapping = {
        "DEMOSTRADO": "success",
        "Cumple": "success",
        "accepted": "success",
        "answered": "success",
        "PARCIALMENTE_DEMOSTRADO": "warning",
        "Parcial": "warning",
        "edited": "info",
        "MENCIONADO_SIN_EVIDENCIA": "warning",
        "PENDIENTE_CONFIRMACION": "info",
        "pending": "muted",
        "open": "muted",
        "NO_IDENTIFICADO": "danger",
        "No cumple": "danger",
        "rejected": "danger",
    }
    return mapping.get(status, "muted")


def score_label(score: float) -> str:
    if score >= 85:
        return "Excelente"
    if score >= 70:
        return "Sólido"
    if score >= 55:
        return "Mejorable"
    if score >= 40:
        return "Débil"
    return "Crítico"
