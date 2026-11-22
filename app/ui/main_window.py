"""Ventana principal y navegación inicial de CV Analyzer Pro."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import constants as C
from app.core.context import AppContext
from app.ui.management_views import (
    CandidatesView, ComparisonView, CVsView, DocumentGeneratorView,
    EvaluationsView, OffersView, OptimizerView, SettingsView,
)
from app.ui.quick_match_view import QuickMatchView
from app.ui.theme import STYLESHEET
from app.ui.widgets import Card, StatCard


class MainWindow(QMainWindow):
    """Contenedor de navegación; cada flujo se conectará conforme se implemente."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self._nav_buttons: dict[str, QPushButton] = {}
        self.setWindowTitle(f"{C.APP_NAME} · {C.APP_VERSION}")
        self.setMinimumSize(1000, 680)
        self.resize(1280, 820)
        self.setStyleSheet(STYLESHEET)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)
        self.header_title = QLabel()
        self.header_title.setObjectName("HeaderTitle")
        self.header_subtitle = QLabel()
        self.header_subtitle.setObjectName("HeaderSubtitle")
        main_layout.addWidget(self.header_title)
        main_layout.addWidget(self.header_subtitle)
        self.pages = QStackedWidget()
        main_layout.addWidget(self.pages, 1)
        layout.addWidget(main, 1)
        self.setCentralWidget(root)

        self._build_pages()
        self.navigate("dashboard")
        self.statusBar().showMessage("Datos almacenados localmente en este equipo")

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(235)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 22, 0, 18)
        layout.setSpacing(4)

        brand = QLabel(C.APP_NAME)
        brand.setObjectName("SidebarBrand")
        brand.setContentsMargins(18, 0, 12, 0)
        layout.addWidget(brand)
        tagline = QLabel("ANÁLISIS CURRICULAR")
        tagline.setObjectName("SidebarBrandAccent")
        tagline.setContentsMargins(18, 2, 12, 20)
        layout.addWidget(tagline)

        for key, title, _description in C.NAV_ITEMS:
            button = QPushButton(title)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, page=key: self.navigate(page))
            self._nav_buttons[key] = button
            layout.addWidget(button)
        layout.addStretch(1)
        footer = QLabel(f"Versión {C.APP_VERSION}")
        footer.setObjectName("SidebarFooter")
        footer.setContentsMargins(18, 0, 12, 0)
        layout.addWidget(footer)
        return sidebar

    def _build_pages(self) -> None:
        self._pages: dict[str, QWidget] = {}
        management_views = {
            "candidates": CandidatesView(self.context),
            "cvs": CVsView(self.context),
            "offers": OffersView(self.context),
            "evaluations": EvaluationsView(self.context),
            "quick_match": QuickMatchView(self.context),
            "history": EvaluationsView(self.context, history_only=True),
            "generator": DocumentGeneratorView(self.context),
            "comparison": ComparisonView(self.context),
            "optimizer": OptimizerView(self.context),
            "settings": SettingsView(self.context),
        }
        for key, title, description in C.NAV_ITEMS:
            if key == "dashboard":
                page = self._dashboard_page()
            else:
                page = management_views.get(key) or self._placeholder_page(title, description)
            self._pages[key] = page
            self.pages.addWidget(page)

    def _dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        intro = QLabel("Resumen de tu espacio de trabajo")
        intro.setObjectName("SectionTitle")
        layout.addWidget(intro)
        stats = self.context.dashboard.stats()
        cards = QHBoxLayout()
        for title, key, hint in (
            ("Candidatos", "candidates", "Perfiles registrados"),
            ("CV", "cvs", f"{stats['versions']} versiones"),
            ("Ofertas", "offers", "Vacantes guardadas"),
            ("Evaluaciones", "evaluations", "Análisis realizados"),
        ):
            card = StatCard(title, str(stats[key]), hint)
            cards.addWidget(card)
        layout.addLayout(cards)

        score = stats["average"]
        score_text = f"{score:.1f}/100" if score is not None else "Sin datos"
        score_card = Card("Calidad promedio", "Promedio de las evaluaciones guardadas")
        score_label = QLabel(score_text)
        score_label.setObjectName("BigScore")
        score_card.add(score_label)
        if score is None:
            score_card.add(QLabel("Cuando completes una evaluación, aparecerá aquí."))
        layout.addWidget(score_card)

        recent = self.context.dashboard.recent_evaluations(limit=5)
        recent_card = Card("Actividad reciente")
        if recent:
            for item in recent:
                row = QLabel(
                    f"{item['candidate_name']} · {item['offer_title']} · "
                    f"{item['overall']:.1f}/100"
                )
                row.setWordWrap(True)
                recent_card.add(row)
        else:
            empty = QLabel("Aún no hay evaluaciones. Esta sección mostrará los análisis recientes.")
            empty.setWordWrap(True)
            recent_card.add(empty)
        layout.addWidget(recent_card)
        layout.addStretch(1)
        return page

    @staticmethod
    def _placeholder_page(title: str, description: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        card = Card(title, description)
        message = QLabel(
            "Esta sección está preparada en la navegación. El flujo de trabajo "
            "correspondiente se conectará en los siguientes pasos."
        )
        message.setWordWrap(True)
        card.add(message)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def navigate(self, page_key: str) -> None:
        page = self._pages.get(page_key)
        if page is None:
            return
        self.pages.setCurrentWidget(page)
        item = next((entry for entry in C.NAV_ITEMS if entry[0] == page_key), None)
        if item:
            _, title, description = item
            self.header_title.setText(title)
            self.header_subtitle.setText(description)
        for key, button in self._nav_buttons.items():
            button.setChecked(key == page_key)

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.context.close()
        super().closeEvent(event)
