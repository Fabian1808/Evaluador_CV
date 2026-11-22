"""Vista reutilizable de resultados de evaluación (en pantalla e historial)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import constants as C
from app.config.constants import CONFIDENCE_LABELS, DATA_ORIGINS
from app.services.evaluation_models import EvaluationBundle
from app.ui.theme import score_color, score_tone, status_tone
from app.ui.widgets import (
    Banner,
    Card,
    Pill,
    ScoreBar,
    ScoreRing,
    configure_table,
    format_date,
    primary_button,
    table_item,
)

_DIMENSION_TITLES = {
    "ATS": "Compatibilidad ATS",
    "HR": "Perspectiva de Recursos Humanos",
    "TECHNICAL": "Evaluación técnica",
    "COMPATIBILITY": "Compatibilidad con la oferta",
}


# ---------------------------------------------------------------------------
# Constructores de vista
# ---------------------------------------------------------------------------
def bundle_to_view(bundle: EvaluationBundle, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    dimensions = []
    for key, result in (
        ("ATS", bundle.ats),
        ("HR", bundle.hr),
        ("TECHNICAL", bundle.technical),
    ):
        dimensions.append(
            {
                "key": key,
                "title": _DIMENSION_TITLES[key],
                "score": result.score,
                "confidence": result.confidence,
                "summary": result.summary,
                "criteria": [
                    {
                        "criterion": item.criterion,
                        "score": item.score,
                        "max_score": item.max_score,
                        "status": item.status,
                        "severity": item.severity,
                        "explanation": item.explanation,
                        "evidence": item.evidence,
                        "recommendation": item.recommendation,
                    }
                    for item in result.criteria
                ],
                "strengths": result.strengths,
                "weaknesses": result.weaknesses,
                "missing": result.missing,
                "limitations": result.limitations,
            }
        )
    matches = []
    if bundle.compatibility:
        matches = [
            {
                "requirement_text": item.requirement_text,
                "requirement_type": item.requirement_type,
                "status": item.status,
                "explanation": item.explanation,
                "evidence": item.evidence,
                "score": item.score,
            }
            for item in bundle.compatibility.matches
        ]
    return {
        "overall": bundle.overall_score,
        "ats": bundle.ats.score,
        "hr": bundle.hr.score,
        "technical": bundle.technical.score,
        "compatibility": bundle.compatibility.score if bundle.compatibility else None,
        "confidence": bundle.confidence,
        "weights": bundle.weights,
        "summary": bundle.summary,
        "technical_profile": bundle.technical_profile_name or "",
        "ai_model": bundle.ai_model or "",
        "strengths": bundle.strengths,
        "weaknesses": bundle.weaknesses,
        "missing": bundle.missing,
        "limitations": bundle.limitations,
        "dimensions": dimensions,
        "compatibility_matches": matches,
        "compatibility_limitations": (
            bundle.compatibility.limitations if bundle.compatibility else []
        ),
        "compatibility_strengths": (
            bundle.compatibility.strengths if bundle.compatibility else []
        ),
        "compatibility_weaknesses": (
            bundle.compatibility.weaknesses if bundle.compatibility else []
        ),
        "evidence": [],
        "recommendations": [],
        "created_at": None,
        **context,
    }


def evaluation_to_view(evaluation) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    grouped: dict[str, list[Any]] = {"ATS": [], "HR": [], "TECHNICAL": [], "COMPATIBILITY": []}
    for detail in evaluation.details:
        grouped.setdefault(detail.dimension, []).append(detail)
    dimensions = []
    for key in ("ATS", "HR", "TECHNICAL"):
        items = grouped.get(key, [])
        dimensions.append(
            {
                "key": key,
                "title": _DIMENSION_TITLES[key],
                "score": {
                    "ATS": evaluation.ats_score,
                    "HR": evaluation.hr_score,
                    "TECHNICAL": evaluation.technical_score,
                }[key],
                "confidence": evaluation.confidence,
                "summary": "",
                "criteria": [
                    {
                        "criterion": item.criterion,
                        "score": item.score,
                        "max_score": item.max_score,
                        "status": item.status,
                        "severity": item.severity,
                        "explanation": item.explanation,
                        "evidence": item.evidence,
                        "recommendation": item.recommendation,
                    }
                    for item in items
                ],
                "strengths": [],
                "weaknesses": [],
                "missing": [],
                "limitations": [],
            }
        )
    matches = [
        {
            "requirement_text": item.criterion,
            "requirement_type": (
                "mandatory" if item.severity == "high" else "desirable"
            ),
            "status": item.status,
            "explanation": item.explanation,
            "evidence": item.evidence or "",
            "score": (item.score / 100) if item.max_score else None,
        }
        for item in grouped.get("COMPATIBILITY", [])
    ]
    return {
        "evaluation_id": evaluation.id,
        "overall": evaluation.overall_score,
        "ats": evaluation.ats_score,
        "hr": evaluation.hr_score,
        "technical": evaluation.technical_score,
        "compatibility": evaluation.compatibility_score,
        "confidence": evaluation.confidence,
        "weights": evaluation.weights or {},
        "summary": evaluation.summary or "",
        "technical_profile": evaluation.technical_profile_name or "",
        "ai_model": evaluation.ai_model or "",
        "strengths": evaluation.strengths or [],
        "weaknesses": evaluation.weaknesses or [],
        "missing": evaluation.missing or [],
        "limitations": evaluation.limitations or [],
        "dimensions": dimensions,
        "compatibility_matches": matches,
        "compatibility_limitations": [],
        "compatibility_strengths": [],
        "compatibility_weaknesses": [],
        "evidence": [
            {
                "section": item.section,
                "quote": item.quote,
                "origin": item.origin,
                "confidence": item.confidence,
            }
            for item in evaluation.evidence
        ],
        "recommendations": [
            {
                "area": item.area,
                "priority": item.priority,
                "text": item.text,
                "status": item.status,
            }
            for item in evaluation.recommendations
        ],
        "created_at": evaluation.created_at,
    }


# ---------------------------------------------------------------------------
# Widgets auxiliares
# ---------------------------------------------------------------------------
class BulletList(QWidget):
    def __init__(
        self,
        title: str,
        items: list[str],
        tone: str = "muted",
        empty_text: str = "Sin elementos.",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        heading = QLabel(title)
        heading.setStyleSheet("font-weight:700; font-size:12px;")
        layout.addWidget(heading)
        if not items:
            label = QLabel(empty_text)
            label.setObjectName("Muted")
            label.setWordWrap(True)
            layout.addWidget(label)
            return
        color = {
            "success": C.COLOR_SUCCESS,
            "danger": C.COLOR_DANGER,
            "warning": C.COLOR_WARNING,
            "info": C.COLOR_INFO,
            "muted": C.COLOR_MUTED,
        }.get(tone, C.COLOR_MUTED)
        for item in items:
            label = QLabel(f"•  {item}")
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setStyleSheet(f"color:{color}; font-size:12px;")
            layout.addWidget(label)


def _criteria_table(criteria: list[dict[str, Any]]) -> QTableWidget:
    table = QTableWidget()
    configure_table(table, ["Criterio", "Puntaje", "Estado", "Explicación"])
    table.setWordWrap(True)
    table.setRowCount(len(criteria))
    for row, item in enumerate(criteria):
        table.setItem(row, 0, table_item(item["criterion"]))
        score_text = f"{item['score']:.1f} / {item['max_score']:.0f}"
        score_cell = table_item(score_text)
        score_cell.setForeground(_color(score_color(100 * item["score"] / max(1, item["max_score"]))))
        table.setItem(row, 1, score_cell)
        status_cell = table_item(item["status"])
        status_cell.setForeground(_color(_status_color(item["status"])))
        table.setItem(row, 2, status_cell)
        explanation = item.get("explanation") or ""
        if item.get("evidence"):
            explanation += f"\nEvidencia: {item['evidence']}"
        if item.get("recommendation"):
            explanation += f"\nRecomendación: {item['recommendation']}"
        table.setItem(row, 3, table_item(explanation))
    table.resizeRowsToContents()
    return table


def _color(value: str):
    from PySide6.QtGui import QBrush, QColor

    return QBrush(QColor(value))


def _status_color(status: str) -> str:
    tone = status_tone(status)
    return {
        "success": C.COLOR_SUCCESS,
        "warning": C.COLOR_WARNING,
        "danger": C.COLOR_DANGER,
        "info": C.COLOR_INFO,
        "muted": C.COLOR_MUTED,
    }.get(tone, C.COLOR_MUTED)


def _scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setWidget(widget)
    return area


# ---------------------------------------------------------------------------
# Vista principal
# ---------------------------------------------------------------------------
class EvaluationResultView(QWidget):
    def __init__(self, view: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.view = view
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._build_summary()
        for dimension in view.get("dimensions", []):
            self._build_dimension(dimension)
        self._build_compatibility()
        self._build_evidence()
        self._build_recommendations()

    # ------------------------------------------------------------------ resumen
    def _build_summary(self) -> None:
        view = self.view
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(14, 14, 14, 14)
        page_layout.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(18)
        ring = ScoreRing(view["overall"], "Calidad general")
        top.addWidget(ring, 0, Qt.AlignmentFlag.AlignTop)

        bars = QVBoxLayout()
        bars.setSpacing(2)
        bars.addWidget(ScoreBar("ATS", view["ats"], "Estructura, palabras clave y legibilidad"))
        bars.addWidget(ScoreBar("Recursos Humanos", view["hr"], "Claridad, evidencia y coherencia"))
        bars.addWidget(ScoreBar("Técnico", view["technical"], "Competencias demostradas"))
        if view.get("compatibility") is not None:
            bars.addWidget(
                ScoreBar(
                    "Compatibilidad con la oferta",
                    view["compatibility"],
                    "Requisitos obligatorios y deseables",
                )
            )
        top.addLayout(bars, 1)

        meta = QVBoxLayout()
        meta.setSpacing(4)
        meta.addWidget(
            Pill(
                CONFIDENCE_LABELS.get(view.get("confidence", ""), view.get("confidence", "")),
                {"alta": "success", "media": "info", "baja": "warning"}.get(
                    view.get("confidence", ""), "muted"
                ),
            )
        )
        if view.get("technical_profile"):
            meta.addWidget(QLabel(f"Perfil técnico: {view['technical_profile']}"))
        if view.get("ai_model"):
            meta.addWidget(QLabel(f"Resumen con IA local: {view['ai_model']}"))
        if view.get("created_at"):
            meta.addWidget(QLabel(f"Fecha: {format_date(view['created_at'])}"))
        weights = view.get("weights") or {}
        if weights:
            meta.addWidget(
                QLabel(
                    "Pesos: "
                    + " · ".join(
                        f"{name.upper()} {value:.0f}%"
                        for name, value in weights.items()
                    )
                )
            )
        meta.addStretch(1)
        top.addLayout(meta, 0)
        page_layout.addLayout(top)

        if view.get("summary"):
            card = Card("Resumen ejecutivo")
            summary = QLabel(view["summary"])
            summary.setWordWrap(True)
            summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            card.add(summary)
            page_layout.addWidget(card)

        columns = QGridLayout()
        columns.setHorizontalSpacing(10)
        strengths = Card("Fortalezas")
        strengths.add(BulletList("", view.get("strengths", []), "success", "Sin fortalezas destacadas."))
        weaknesses = Card("Áreas de mejora")
        weaknesses.add(BulletList("", view.get("weaknesses", []), "warning", "Sin debilidades relevantes."))
        missing = Card("Información faltante")
        missing.add(BulletList("", view.get("missing", []), "danger", "No se detectó información crítica faltante."))
        columns.addWidget(strengths, 0, 0)
        columns.addWidget(weaknesses, 0, 1)
        columns.addWidget(missing, 1, 0, 1, 2)
        page_layout.addLayout(columns)

        limitations = view.get("limitations") or []
        if limitations:
            banner = Banner("", "info", "Alcance y limitaciones del análisis")
            banner.text_label.setText("\n".join(f"• {item}" for item in limitations))
            page_layout.addWidget(banner)
        page_layout.addStretch(1)
        self.tabs.addTab(_scroll(page), "Resumen")

    # ---------------------------------------------------------------- dimensión
    def _build_dimension(self, dimension: dict[str, Any]) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel(dimension["title"])
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(Pill(f"{dimension['score']:.1f}/100", score_tone(dimension["score"])))
        layout.addLayout(header)
        if dimension.get("summary"):
            summary = QLabel(dimension["summary"])
            summary.setWordWrap(True)
            summary.setObjectName("Muted")
            layout.addWidget(summary)
        if dimension.get("criteria"):
            layout.addWidget(_criteria_table(dimension["criteria"]), 1)
        lists = QGridLayout()
        lists.setHorizontalSpacing(12)
        lists.addWidget(
            BulletList("Fortalezas", dimension.get("strengths", []), "success", "—"), 0, 0
        )
        lists.addWidget(
            BulletList("Debilidades", dimension.get("weaknesses", []), "warning", "—"), 0, 1
        )
        lists.addWidget(
            BulletList("Faltantes", dimension.get("missing", []), "danger", "—"), 1, 0, 1, 2
        )
        layout.addLayout(lists)
        if dimension.get("limitations"):
            limits = QLabel("\n".join(f"• {item}" for item in dimension["limitations"]))
            limits.setWordWrap(True)
            limits.setObjectName("Muted")
            layout.addWidget(limits)
        self.tabs.addTab(_scroll(page), dimension["title"].replace("Compatibilidad ATS", "ATS"))

    # ------------------------------------------------------------- compatibilidad
    def _build_compatibility(self) -> None:
        matches = self.view.get("compatibility_matches") or []
        if not matches:
            return
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Matriz de requisitos")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        score = self.view.get("compatibility")
        if score is not None:
            header.addWidget(Pill(f"{score:.1f}/100", score_tone(score)))
        layout.addLayout(header)

        table = QTableWidget()
        configure_table(table, ["Requisito", "Tipo", "Estado", "Explicación y evidencia"])
        table.setWordWrap(True)
        table.setRowCount(len(matches))
        for row, item in enumerate(matches):
            table.setItem(row, 0, table_item(item["requirement_text"]))
            table.setItem(
                row,
                1,
                table_item("Obligatorio" if item["requirement_type"] == "mandatory" else "Deseable"),
            )
            status_cell = table_item(item["status"].replace("_", " ").capitalize())
            status_cell.setForeground(_color(_status_color(item["status"])))
            table.setItem(row, 2, status_cell)
            text = item.get("explanation") or ""
            if item.get("evidence"):
                text += f"\nEvidencia: {item['evidence']}"
            table.setItem(row, 3, table_item(text))
        table.resizeRowsToContents()
        layout.addWidget(table, 1)

        lists = QGridLayout()
        lists.addWidget(
            BulletList(
                "Requisitos cubiertos",
                self.view.get("compatibility_strengths", []),
                "success",
                "—",
            ),
            0,
            0,
        )
        lists.addWidget(
            BulletList(
                "Brechas detectadas",
                self.view.get("compatibility_weaknesses", []),
                "warning",
                "—",
            ),
            0,
            1,
        )
        layout.addLayout(lists)
        if self.view.get("compatibility_limitations"):
            limits = QLabel(
                "\n".join(f"• {item}" for item in self.view["compatibility_limitations"])
            )
            limits.setWordWrap(True)
            limits.setObjectName("Muted")
            layout.addWidget(limits)
        self.tabs.addTab(_scroll(page), "Compatibilidad")

    # ----------------------------------------------------------------- evidencia
    def _build_evidence(self) -> None:
        evidence = self.view.get("evidence") or []
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        intro = QLabel(
            "Toda la evidencia proviene del documento original. Las citas permiten "
            "verificar cada hallazgo; no se generan citas artificiales."
        )
        intro.setWordWrap(True)
        intro.setObjectName("Muted")
        layout.addWidget(intro)
        if not evidence:
            empty = QLabel(
                "La evidencia detallada se guarda al ejecutar la evaluación desde la "
                "pestaña Evaluaciones y queda disponible en el Historial."
            )
            empty.setWordWrap(True)
            empty.setObjectName("Muted")
            layout.addWidget(empty)
        else:
            table = QTableWidget()
            configure_table(table, ["Sección", "Cita del documento", "Origen", "Confianza"])
            table.setWordWrap(True)
            table.setRowCount(len(evidence))
            for row, item in enumerate(evidence):
                table.setItem(row, 0, table_item(item.get("section", "")))
                table.setItem(row, 1, table_item(item.get("quote", "")))
                table.setItem(
                    row,
                    2,
                    table_item(DATA_ORIGINS.get(item.get("origin", ""), item.get("origin", ""))),
                )
                table.setItem(row, 3, table_item(item.get("confidence", "")))
            table.resizeRowsToContents()
            layout.addWidget(table, 1)
        self.tabs.addTab(_scroll(page), "Evidencias")

    # ----------------------------------------------------------- recomendaciones
    def _build_recommendations(self) -> None:
        recommendations = self.view.get("recommendations") or []
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        if not recommendations:
            empty = QLabel(
                "Las recomendaciones detalladas se generan al ejecutar la evaluación y "
                "quedan guardadas en el Historial."
            )
            empty.setWordWrap(True)
            empty.setObjectName("Muted")
            layout.addWidget(empty)
        else:
            table = QTableWidget()
            configure_table(table, ["Área", "Prioridad", "Recomendación"])
            table.setWordWrap(True)
            table.setRowCount(len(recommendations))
            for row, item in enumerate(recommendations):
                table.setItem(row, 0, table_item(item.get("area", "")))
                priority = item.get("priority", "")
                cell = table_item(priority)
                cell.setForeground(
                    _color(
                        {
                            "alta": C.COLOR_DANGER,
                            "media": C.COLOR_WARNING,
                            "baja": C.COLOR_MUTED,
                        }.get(priority, C.COLOR_MUTED)
                    )
                )
                table.setItem(row, 1, cell)
                table.setItem(row, 2, table_item(item.get("text", "")))
            table.resizeRowsToContents()
            layout.addWidget(table, 1)
        self.tabs.addTab(_scroll(page), "Recomendaciones")


class EvaluationDetailDialog(QDialog):
    def __init__(self, view: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Detalle de la evaluación")
        self.resize(1000, 720)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)
        heading = QLabel("Detalle de la evaluación")
        heading.setObjectName("DialogTitle")
        layout.addWidget(heading)
        context = QLabel(
            " · ".join(
                filter(
                    None,
                    [
                        view.get("candidate_name", ""),
                        view.get("cv_label", ""),
                        view.get("offer_title", ""),
                        format_date(view.get("created_at")) if view.get("created_at") else "",
                    ],
                )
            )
        )
        context.setObjectName("Muted")
        context.setWordWrap(True)
        layout.addWidget(context)
        layout.addWidget(EvaluationResultView(view), 1)
        close = primary_button("Cerrar", self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        layout.addLayout(row)
