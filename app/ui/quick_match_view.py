"""Flujo guiado para comparar un CV con una vacante."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from app.core.context import AppContext
from app.config import paths
from app.database.repositories import CandidateRepository, CVRepository
from app.services.evaluation_models import EvaluationBundle
from app.ui.evaluation_view import EvaluationResultView, bundle_to_view
from app.utils.files import sanitize_filename, sha256_file
from app.ui.widgets import Card, error_message, primary_button, run_with_progress, warn_message


@dataclass
class QuickMatchReport:
    candidate_name: str
    offer_title: str
    bundle: EvaluationBundle
    proposals: list[dict]
    questions: list[dict]
    warnings: list[str]


class QuickMatchView(QWidget):
    """Importa el CV y analiza la oferta en una sola accion."""

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.cv_path = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        card = Card(
            "Compara tu CV con una vacante",
            "Carga tu CV y pega la descripcion del puesto. El aplicativo guardara el analisis y mostrara el match, brechas y sugerencias.",
        )
        form = QFormLayout()
        file_row = QHBoxLayout()
        self.file_label = QLabel("Ningun archivo seleccionado")
        self.file_label.setObjectName("Muted")
        file_row.addWidget(self.file_label, 1)
        file_row.addWidget(primary_button("Subir CV", self.choose_file))
        form.addRow("CV (PDF o DOCX)", file_row)
        self.title = QLineEdit()
        self.title.setPlaceholderText("Ej.: Analista de datos")
        form.addRow("Puesto", self.title)
        self.company = QLineEdit()
        self.company.setPlaceholderText("Empresa (opcional)")
        form.addRow("Empresa", self.company)
        self.offer_text = QPlainTextEdit()
        self.offer_text.setPlaceholderText("Pega aqui la descripcion completa del puesto y sus requisitos.")
        self.offer_text.setMinimumHeight(220)
        form.addRow("Descripcion de la vacante", self.offer_text)
        card.body.addLayout(form)
        card.add(primary_button("Analizar match y sugerir cambios", self.analyze))
        layout.addWidget(card)
        layout.addStretch(1)

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar CV", "", "CV (PDF o DOCX) (*.pdf *.docx)"
        )
        if path:
            self.cv_path = path
            self.file_label.setText(Path(path).name)

    def analyze(self) -> None:
        if not self.cv_path:
            warn_message(self, "Selecciona tu CV en PDF o DOCX.")
            return
        offer_text = self.offer_text.toPlainText().strip()
        if len(offer_text) < 30:
            warn_message(self, "Pega la descripcion del puesto (al menos 30 caracteres).")
            return
        cv_path = self.cv_path
        title = self.title.text().strip()
        company = self.company.text().strip()
        result, error, cancelled = run_with_progress(
            self,
            "Analizando CV y vacante",
            lambda cancel_event, progress: self._run_analysis(
                cv_path, offer_text, title, company, cancel_event, progress
            ),
        )
        if error:
            error_message(self, error)
        elif not cancelled and result:
            MatchResultDialog(result, self).exec()

    def _run_analysis(self, cv_path, offer_text, title, company, cancel_event, progress):
        if cancel_event.is_set():
            return None
        progress(5, "Leyendo el CV y preparando el perfil...")
        extraction = self.context.document_service.extract(cv_path)
        parsed = self.context.parser.parse(extraction.text, fallback_name=Path(cv_path).stem)
        personal = parsed.content.get("personal") or {}
        candidate_name = str(personal.get("name") or Path(cv_path).stem).strip()
        email = personal.get("email") or None

        with self.context.database.session() as session:
            candidates = CandidateRepository(session).list_all()
            candidate = next(
                (
                    item for item in candidates
                    if (email and (item.email or "").casefold() == email.casefold())
                    or item.full_name.casefold() == candidate_name.casefold()
                ),
                None,
            )
            if candidate is None:
                candidate = CandidateRepository(session).create(
                    full_name=candidate_name,
                    email=email,
                    phone=personal.get("phone") or None,
                    location=personal.get("location") or None,
                    linkedin=personal.get("linkedin") or None,
                )
            candidate_id = candidate.id

        if cancel_event.is_set():
            return None
        progress(15, "Guardando el CV y creando el perfil estructurado...")
        stored_path = paths.CVS_DIR / f"{sha256_file(Path(cv_path))[:12]}_{sanitize_filename(Path(cv_path).name)}"
        with self.context.database.session() as session:
            existing_cvs = [
                item for item in CVRepository(session).list_all()
                if item.candidate_id == candidate_id and item.stored_path == str(stored_path)
            ]
            existing_versions = (
                CVRepository(session).list_versions(existing_cvs[0].id)
                if existing_cvs else []
            )
            current_version = next(
                (item for item in existing_versions if item.is_current), None
            )
            existing_version_id = current_version.id if current_version else None
        if existing_version_id is None:
            imported = self.context.cv_service.import_cv(candidate_id, cv_path)
            version_id = imported.version_id
            import_warnings = imported.warnings
        else:
            version_id = existing_version_id
            import_warnings = []
        if cancel_event.is_set():
            return None

        progress(28, "Analizando los requisitos del puesto...")
        offer = self.context.offer_service.create(
            offer_text, title=title, company=company, use_ai=False
        )
        if cancel_event.is_set():
            return None

        evaluation = self.context.evaluation_service.evaluate(
            version_id,
            offer_id=offer.offer_id,
            weights=self.context.weights,
            cancel_event=cancel_event,
            progress=lambda percent, message: progress(
                30 + int(percent * 0.42), message
            ),
        )
        if cancel_event.is_set():
            return None

        ready, _reason = self.context.ai_ready()
        progress(75, "Generando sugerencias para mejorar el CV...")
        optimization = self.context.optimizer.run(
            version_id,
            offer_id=offer.offer_id,
            use_ai=ready,
            cancel_event=cancel_event,
            progress=lambda percent, message: progress(
                74 + int(percent * 0.25), message
            ),
        )
        return QuickMatchReport(
            candidate_name=candidate_name,
            offer_title=offer.analysis.get("title") or title or "Vacante",
            bundle=evaluation.bundle,
            proposals=optimization.proposals,
            questions=optimization.missing,
            warnings=list(dict.fromkeys(import_warnings + offer.warnings + optimization.warnings)),
        )


class MatchResultDialog(QDialog):
    def __init__(self, report: QuickMatchReport, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Resultado de match")
        self.resize(1080, 760)
        layout = QVBoxLayout(self)
        match_score = report.bundle.compatibility.score if report.bundle.compatibility else None
        score_label = f" · Match {match_score:.1f}/100" if match_score is not None else ""
        heading = QLabel(f"{report.candidate_name} · {report.offer_title}{score_label}")
        heading.setObjectName("SectionTitle")
        layout.addWidget(heading)
        tabs = QTabWidget()
        tabs.addTab(
            EvaluationResultView(
                bundle_to_view(
                    report.bundle,
                    {"candidate_name": report.candidate_name, "offer_title": report.offer_title},
                )
            ),
            "Match y evaluacion",
        )
        suggestions = QPlainTextEdit()
        suggestions.setReadOnly(True)
        lines = []
        for number, item in enumerate(report.proposals, 1):
            lines.extend([
                f"{number}. {item.get('section', 'CV')} — {item.get('problem', '')}",
                f"   Actual: {item.get('original_text', '')}",
                f"   Sugerencia: {item.get('proposed_text', '')}",
                f"   Motivo: {item.get('justification', '')}",
                "",
            ])
        if not report.proposals:
            lines.append("No se encontraron cambios de redaccion especificos para proponer.")
        if report.questions:
            lines.extend(["Informacion que conviene completar:", ""])
            for item in report.questions:
                lines.append(f"• {item.get('question', '')} — {item.get('why_important', '')}")
        if report.warnings:
            lines.extend(["", "Avisos:", *[f"• {warning}" for warning in report.warnings]])
        suggestions.setPlainText("\n".join(lines))
        tabs.addTab(suggestions, "Que cambiar")
        layout.addWidget(tabs, 1)
        close = QPushButton("Cerrar")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
