"""Vistas iniciales de gestión para candidatos, ofertas y CV."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLineEdit, QMessageBox, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.core.context import AppContext
from app.database.models import Candidate, JobOffer
from app.database.repositories import (
    CandidateRepository, CVRepository, EvaluationRepository, OfferRepository,
    OptimizationRepository, TechnicalProfileRepository,
)
from app.ui.dialogs import CandidateDialog, OfferDialog
from app.ui.dialogs import CVEditorDialog
from app.ui.evaluation_view import EvaluationDetailDialog, evaluation_to_view
from app.ui.widgets import (
    Card, configure_table, error_message, primary_button, secondary_button,
    run_with_progress, selected_row_data, table_item, warn_message,
)


class CandidatesView(QWidget):
    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        actions = QHBoxLayout()
        actions.addWidget(primary_button("Nuevo candidato", self.create_candidate))
        actions.addWidget(secondary_button("Editar", self.edit_candidate))
        actions.addWidget(secondary_button("Eliminar", self.delete_candidate))
        actions.addStretch(1)
        layout.addLayout(actions)
        self.table = QTableWidget()
        configure_table(self.table, ["Nombre", "Correo", "Teléfono", "CV"])
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        with self.context.database.session() as session:
            candidates = CandidateRepository(session).list_all()
            rows = [(item.id, item.full_name, item.email or "", item.phone or "", len(item.cvs)) for item in candidates]
        self.table.setRowCount(len(rows))
        for row, (item_id, name, email, phone, cv_count) in enumerate(rows):
            self.table.setItem(row, 0, table_item(name, item_id))
            for column, value in enumerate((email, phone, cv_count), start=1):
                self.table.setItem(row, column, table_item(value))
        self.table.resizeColumnsToContents()

    def create_candidate(self) -> None:
        dialog = CandidateDialog(parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        try:
            with self.context.database.session() as session:
                CandidateRepository(session).create(**dialog.values())
            self.refresh()
        except Exception as exc:
            error_message(self, str(exc))

    def edit_candidate(self) -> None:
        candidate_id = selected_row_data(self.table)
        if candidate_id is None:
            warn_message(self, "Selecciona un candidato para editar.")
            return
        with self.context.database.session() as session:
            candidate = CandidateRepository(session).get(candidate_id)
            values = {key: getattr(candidate, key) for key in ("full_name", "email", "phone", "location", "linkedin", "notes")}
        dialog = CandidateDialog(Candidate(id=candidate_id, **values), self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        try:
            with self.context.database.session() as session:
                repo = CandidateRepository(session)
                repo.update(repo.get(candidate_id), **dialog.values())
            self.refresh()
        except Exception as exc:
            error_message(self, str(exc))

    def delete_candidate(self) -> None:
        candidate_id = selected_row_data(self.table)
        if candidate_id is None:
            warn_message(self, "Selecciona un candidato para eliminar.")
            return
        answer = QMessageBox.question(self, "Eliminar candidato", "Se eliminarán también sus CV y evaluaciones. ¿Continuar?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            with self.context.database.session() as session:
                repo = CandidateRepository(session)
                candidate = repo.get(candidate_id)
                if candidate:
                    repo.delete(candidate)
            self.refresh()
        except Exception as exc:
            error_message(self, str(exc))


class OffersView(QWidget):
    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        actions = QHBoxLayout()
        actions.addWidget(primary_button("Nueva oferta", self.create_offer))
        actions.addWidget(secondary_button("Editar", self.edit_offer))
        actions.addWidget(secondary_button("Eliminar", self.delete_offer))
        actions.addStretch(1)
        layout.addLayout(actions)
        self.table = QTableWidget()
        configure_table(self.table, ["Vacante", "Empresa", "Área", "Requisitos"])
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        with self.context.database.session() as session:
            offers = OfferRepository(session).list_all()
            rows = [(item.id, item.title, item.company or "", item.area or "", len(item.requirements)) for item in offers]
        self.table.setRowCount(len(rows))
        for row, (item_id, title, company, area, requirements) in enumerate(rows):
            self.table.setItem(row, 0, table_item(title, item_id))
            for column, value in enumerate((company, area, requirements), start=1):
                self.table.setItem(row, column, table_item(value))
        self.table.resizeColumnsToContents()

    def create_offer(self) -> None:
        dialog = OfferDialog(parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            result = self.context.offer_service.create(
                values["raw_text"], values["title"], values["company"], values["area"], values["use_ai"]
            )
            self.refresh()
            if result.warnings:
                warn_message(self, "\n".join(result.warnings))
        except Exception as exc:
            error_message(self, str(exc))

    def edit_offer(self) -> None:
        offer_id = selected_row_data(self.table)
        if offer_id is None:
            warn_message(self, "Selecciona una oferta para editar.")
            return
        with self.context.database.session() as session:
            offer = OfferRepository(session).get(offer_id)
            snapshot = {"id": offer.id, "title": offer.title, "company": offer.company, "area": offer.area, "raw_text": offer.raw_text}
        dialog = OfferDialog(JobOffer(**snapshot), self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            result = self.context.offer_service.update(
                offer_id, values["raw_text"], values["title"], values["company"], values["area"],
                reanalyze=True, use_ai=values["use_ai"]
            )
            self.refresh()
            if result.warnings:
                warn_message(self, "\n".join(result.warnings))
        except Exception as exc:
            error_message(self, str(exc))

    def delete_offer(self) -> None:
        offer_id = selected_row_data(self.table)
        if offer_id is None:
            warn_message(self, "Selecciona una oferta para eliminar.")
            return
        answer = QMessageBox.question(self, "Eliminar oferta", "¿Eliminar la oferta seleccionada?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            with self.context.database.session() as session:
                repo = OfferRepository(session)
                offer = repo.get(offer_id)
                if offer:
                    repo.delete(offer)
            self.refresh()
        except Exception as exc:
            error_message(self, str(exc))


class CVsView(QWidget):
    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        card = Card("Importar CV", "Admite PDF y DOCX. El original se conserva en el almacenamiento local.")
        controls = QHBoxLayout()
        self.candidate = QComboBox()
        controls.addWidget(self.candidate, 1)
        controls.addWidget(primary_button("Seleccionar archivo e importar", self.import_cv))
        card.body.addLayout(controls)
        layout.addWidget(card)
        actions = QHBoxLayout()
        actions.addWidget(secondary_button("Editar contenido como nueva versión", self.edit_cv))
        actions.addStretch(1)
        layout.addLayout(actions)
        self.table = QTableWidget()
        configure_table(self.table, ["Candidato", "CV", "Formato", "Versiones", "Páginas"])
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        with self.context.database.session() as session:
            candidates = CandidateRepository(session).list_all()
            cvs = CVRepository(session).list_all()
            candidate_rows = [(item.id, item.full_name) for item in candidates]
            rows = [(item.id, item.candidate.full_name, item.title, item.file_type.upper(), len(item.versions), item.page_count) for item in cvs]
        selected = self.candidate.currentData()
        self.candidate.clear()
        for candidate_id, name in candidate_rows:
            self.candidate.addItem(name, candidate_id)
        if selected is not None:
            index = self.candidate.findData(selected)
            if index >= 0:
                self.candidate.setCurrentIndex(index)
        self.table.setRowCount(len(rows))
        for row, (cv_id, name, title, file_type, versions, pages) in enumerate(rows):
            self.table.setItem(row, 0, table_item(name, cv_id))
            for column, value in enumerate((title, file_type, versions, pages), start=1):
                self.table.setItem(row, column, table_item(value))
        self.table.resizeColumnsToContents()

    def import_cv(self) -> None:
        candidate_id = self.candidate.currentData()
        if candidate_id is None:
            warn_message(self, "Primero crea o selecciona un candidato.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Importar CV", "", "CV (PDF o DOCX) (*.pdf *.docx)")
        if not path:
            return
        try:
            result = self.context.cv_service.import_cv(candidate_id, path)
            self.refresh()
            message = f"CV importado. Se extrajeron {result.words} palabras usando {result.method}."
            if result.warnings:
                message += "\n\n" + "\n".join(result.warnings)
            QMessageBox.information(self, "Importación completada", message)
        except Exception as exc:
            error_message(self, str(exc))

    def edit_cv(self) -> None:
        cv_id = selected_row_data(self.table)
        if cv_id is None:
            warn_message(self, "Selecciona un CV para editar.")
            return
        with self.context.database.session() as session:
            cv = CVRepository(session).get(cv_id)
            version = max(cv.versions, key=lambda item: item.created_at) if cv and cv.versions else None
            if version is None:
                warn_message(self, "El CV no tiene una versión editable.")
                return
            version_id, content = version.id, version.content
        dialog = CVEditorDialog(content, self, label="Edición manual")
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        try:
            self.context.cv_service.create_version(
                cv_id, dialog.content(), label="Edición manual", source="user_edit",
                parent_version_id=version_id,
            )
            self.refresh()
            QMessageBox.information(self, "Versión creada", "Se guardó una versión nueva; el documento original permanece intacto.")
        except Exception as exc:
            error_message(self, str(exc))


class DocumentGeneratorView(QWidget):
    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        card = Card("Generar CV profesional", "Exporta una versión estructurada con la plantilla Harvard.")
        controls = QHBoxLayout()
        self.version = QComboBox()
        controls.addWidget(self.version, 1)
        controls.addWidget(primary_button("Exportar PDF", lambda: self.export("pdf")))
        controls.addWidget(secondary_button("Exportar DOCX", lambda: self.export("docx")))
        card.body.addLayout(controls)
        layout.addWidget(card)
        self.refresh()

    def refresh(self) -> None:
        with self.context.database.session() as session:
            versions = CVRepository(session).list_versions()
            items = [
                (item.id, f"{item.cv.candidate.full_name} · {item.cv.title} · {item.label}")
                for item in versions
            ]
        self.version.clear()
        for item_id, label in items:
            self.version.addItem(label, item_id)

    def export(self, file_type: str) -> None:
        version_id = self.version.currentData()
        if version_id is None:
            warn_message(self, "Importa un CV antes de generar un documento.")
            return
        extension = "PDF (*.pdf)" if file_type == "pdf" else "Word (*.docx)"
        path, _ = QFileDialog.getSaveFileName(self, "Guardar CV", f"CV_Profesional.{file_type}", extension)
        if not path:
            return
        try:
            with self.context.database.session() as session:
                version = CVRepository(session).get_version(version_id)
                content = version.content
            if file_type == "pdf":
                self.context.generator.export_pdf(content, self.context.document_config, path)
            else:
                self.context.generator.export_docx(content, self.context.document_config, path)
            QMessageBox.information(self, "Documento generado", f"Se guardó el archivo en:\n{path}")
        except Exception as exc:
            error_message(self, str(exc))


class EvaluationsView(QWidget):
    def __init__(
        self, context: AppContext, history_only: bool = False, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.context = context
        self.history_only = history_only
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if not history_only:
            card = Card("Nueva evaluación", "Selecciona una versión de CV. La oferta es opcional.")
            controls = QHBoxLayout()
            self.version = QComboBox()
            self.offer = QComboBox()
            self.offer.addItem("Sin oferta laboral", None)
            self.profile = QComboBox()
            self.profile.addItem("Perfil técnico general", None)
            self.ai_summary = QCheckBox("Resumen con IA local")
            controls.addWidget(self.version, 2)
            controls.addWidget(self.offer, 2)
            controls.addWidget(self.profile, 2)
            controls.addWidget(self.ai_summary)
            controls.addWidget(primary_button("Evaluar", self.evaluate))
            card.body.addLayout(controls)
            layout.addWidget(card)
            self._load_choices()
        self.table = QTableWidget()
        configure_table(self.table, ["Candidato", "CV", "Oferta", "Puntaje", "Fecha"])
        layout.addWidget(self.table)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.open_detail())
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(secondary_button("Ver detalle", self.open_detail))
        actions.addWidget(secondary_button("Actualizar", self.refresh))
        layout.addLayout(actions)
        self.refresh()

    def _load_choices(self) -> None:
        with self.context.database.session() as session:
            versions = CVRepository(session).list_versions()
            offers = OfferRepository(session).list_all()
            profiles = TechnicalProfileRepository(session).list_all()
            version_rows = [
                (item.id, f"{item.cv.candidate.full_name} · {item.cv.title} · {item.label}")
                for item in versions
            ]
            offer_rows = [(item.id, item.title) for item in offers]
            profile_rows = [(item.id, item.name) for item in profiles]
        for item_id, label in version_rows:
            self.version.addItem(label, item_id)
        for item_id, label in offer_rows:
            self.offer.addItem(label, item_id)
        for item_id, label in profile_rows:
            self.profile.addItem(label, item_id)

    def evaluate(self) -> None:
        version_id = self.version.currentData()
        if version_id is None:
            warn_message(self, "Importa un CV antes de iniciar una evaluación.")
            return
        offer_id = self.offer.currentData()
        profile_id = self.profile.currentData()
        use_ai_summary = self.ai_summary.isChecked()
        result, error, cancelled = run_with_progress(
            self,
            "Evaluando CV",
            lambda cancel_event, progress: self.context.evaluation_service.evaluate(
                version_id,
                offer_id=offer_id,
                technical_profile_id=profile_id,
                use_ai_summary=use_ai_summary,
                weights=self.context.weights,
                cancel_event=cancel_event,
                progress=progress,
            ),
        )
        if error:
            error_message(self, error)
        elif not cancelled and result:
            self.refresh()
            info = QMessageBox(self)
            info.setWindowTitle("Evaluación completada")
            info.setText(f"Puntaje general: {result.bundle.overall_score:.1f}/100")
            info.exec()

    def refresh(self) -> None:
        with self.context.database.session() as session:
            evaluations = EvaluationRepository(session).list_all(limit=100)
            rows = [
                (
                    item.id,
                    item.cv_version.cv.candidate.full_name if item.cv_version and item.cv_version.cv else "—",
                    item.cv_version.label if item.cv_version else "—",
                    item.offer.title if item.offer else "Sin oferta",
                    f"{item.overall_score:.1f}/100",
                    item.created_at.strftime("%d/%m/%Y %H:%M") if item.created_at else "",
                    evaluation_to_view(item),
                )
                for item in evaluations
            ]
        self._views = {item_id: view for item_id, *_rest, view in rows}
        self.table.setRowCount(len(rows))
        for row, (item_id, candidate, cv_label, offer, score, created, _view) in enumerate(rows):
            self.table.setItem(row, 0, table_item(candidate, item_id))
            for column, value in enumerate((cv_label, offer, score, created), start=1):
                self.table.setItem(row, column, table_item(value))
        self.table.resizeColumnsToContents()

    def open_detail(self) -> None:
        item_id = selected_row_data(self.table)
        if item_id is None:
            warn_message(self, "Selecciona una evaluación para consultar el detalle.")
            return
        view = self._views.get(item_id)
        if view:
            EvaluationDetailDialog(view, self).exec()


class ComparisonView(QWidget):
    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        card = Card("Comparar versiones de CV", "Revisa diferencias de texto, competencias y palabras clave.")
        controls = QHBoxLayout()
        self.left, self.right = QComboBox(), QComboBox()
        controls.addWidget(self.left, 1)
        controls.addWidget(self.right, 1)
        controls.addWidget(primary_button("Comparar", self.compare))
        card.body.addLayout(controls)
        layout.addWidget(card)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)
        self.refresh()

    def refresh(self) -> None:
        with self.context.database.session() as session:
            versions = CVRepository(session).list_versions()
            items = [
                (item.id, f"{item.cv.candidate.full_name} · {item.cv.title} · {item.label}")
                for item in versions
            ]
        for combo in (self.left, self.right):
            combo.clear()
            for item_id, label in items:
                combo.addItem(label, item_id)
        if len(items) > 1:
            self.right.setCurrentIndex(1)

    def compare(self) -> None:
        left_id, right_id = self.left.currentData(), self.right.currentData()
        if left_id is None or right_id is None:
            warn_message(self, "Se necesitan al menos dos versiones de CV para comparar.")
            return
        if left_id == right_id:
            warn_message(self, "Selecciona dos versiones distintas.")
            return
        try:
            with self.context.database.session() as session:
                repo = CVRepository(session)
                result = self.context.comparison.compare_versions(
                    repo.get_version(left_id), repo.get_version(right_id)
                )
            lines = [
                f"Similitud: {result['similarity']:.1f}%",
                f"Experiencia: {result['experience_a']} → {result['experience_b']} entradas",
                "",
                "Competencias añadidas: " + (", ".join(result["skills_added"]) or "ninguna"),
                "Competencias retiradas: " + (", ".join(result["skills_removed"]) or "ninguna"),
                "",
                "Palabras clave añadidas: " + (", ".join(result["keywords_added"]) or "ninguna"),
                "Palabras clave retiradas: " + (", ".join(result["keywords_removed"]) or "ninguna"),
                "",
                "Diferencias de texto:",
                *result["diff"],
            ]
            self.output.setPlainText("\n".join(lines))
        except Exception as exc:
            error_message(self, str(exc))


class OptimizerView(QWidget):
    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.proposals: list[dict] = []
        self.version_id: int | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        card = Card("Optimizar CV", "Las sugerencias de reglas funcionan sin IA. Revisa cada cambio antes de aplicarlo.")
        controls = QHBoxLayout()
        self.version, self.offer = QComboBox(), QComboBox()
        self.offer.addItem("Sin oferta laboral", None)
        self.use_ai = QCheckBox("Usar IA local")
        controls.addWidget(self.version, 2)
        controls.addWidget(self.offer, 2)
        controls.addWidget(self.use_ai)
        controls.addWidget(primary_button("Analizar", self.run))
        controls.addWidget(secondary_button("Aplicar seleccionadas", self.apply))
        card.body.addLayout(controls)
        layout.addWidget(card)
        self.table = QTableWidget()
        configure_table(self.table, ["Aplicar", "Sección", "Texto actual", "Sugerencia", "Motivo"])
        layout.addWidget(self.table, 1)
        self.missing = QPlainTextEdit()
        self.missing.setReadOnly(True)
        self.missing.setMaximumHeight(125)
        self.missing.setPlaceholderText("Preguntas para completar información faltante")
        layout.addWidget(self.missing)
        self._load_choices()

    def _load_choices(self) -> None:
        with self.context.database.session() as session:
            versions = CVRepository(session).list_versions()
            offers = OfferRepository(session).list_all()
            version_items = [
                (item.id, f"{item.cv.candidate.full_name} · {item.cv.title} · {item.label}")
                for item in versions
            ]
            offer_items = [(item.id, item.title) for item in offers]
        self.version.clear()
        self.offer.clear()
        self.offer.addItem("Sin oferta laboral", None)
        for item_id, label in version_items:
            self.version.addItem(label, item_id)
        for item_id, label in offer_items:
            self.offer.addItem(label, item_id)

    def run(self) -> None:
        version_id, offer_id, use_ai = (
            self.version.currentData(), self.offer.currentData(), self.use_ai.isChecked()
        )
        if version_id is None:
            warn_message(self, "Importa un CV antes de optimizarlo.")
            return
        result, error, cancelled = run_with_progress(
            self, "Analizando oportunidades de mejora",
            lambda cancel_event, progress: self.context.optimizer.run(
                version_id, offer_id, use_ai, cancel_event=cancel_event, progress=progress
            ),
        )
        if error:
            error_message(self, error)
            return
        if cancelled or not result:
            return
        self.version_id, self.proposals = version_id, result.proposals
        self.table.setRowCount(len(self.proposals))
        for row, item in enumerate(self.proposals):
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, checkbox)
            for column, key in enumerate(
                ("section", "original_text", "proposed_text", "justification"), start=1
            ):
                cell = table_item(item.get(key, ""))
                cell.setToolTip(str(item.get(key, "")))
                self.table.setItem(row, column, cell)
        self.table.resizeColumnsToContents()
        questions = [
            f"• {item.get('question', '')} — {item.get('why_important', '')}"
            for item in result.missing
        ]
        self.missing.setPlainText("\n".join(questions) or "No se detectaron preguntas pendientes.")
        if result.warnings:
            warn_message(self, "\n".join(result.warnings))

    def apply(self) -> None:
        if self.version_id is None or not self.proposals:
            warn_message(self, "Primero ejecuta el análisis de optimización.")
            return
        selected = [
            self.proposals[row]["id"]
            for row in range(self.table.rowCount())
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked
        ]
        if not selected:
            warn_message(self, "Marca al menos una sugerencia para aplicarla.")
            return
        try:
            with self.context.database.session() as session:
                repo = OptimizationRepository(session)
                for proposal_id in selected:
                    proposal = repo.get_proposal(proposal_id)
                    if proposal:
                        repo.update_proposal(proposal, status="accepted")
            new_version_id, count, skipped = self.context.optimizer.apply(self.version_id, selected)
            self._load_choices()
            index = self.version.findData(new_version_id)
            if index >= 0:
                self.version.setCurrentIndex(index)
            self.proposals, self.version_id = [], None
            self.table.setRowCount(0)
            message = f"Se aplicaron {count} sugerencias en una nueva versión."
            if skipped:
                message += "\nNo se pudieron aplicar: " + ", ".join(skipped)
            QMessageBox.information(self, "Nueva versión optimizada", message)
        except Exception as exc:
            error_message(self, str(exc))


class SettingsView(QWidget):
    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        ai_card = Card("IA local (Ollama)", "La aplicación conserva análisis deterministas cuando el servicio local no está disponible.")
        ai_form = QFormLayout()
        ai = context.ai_settings
        self.base_url = QLineEdit(str(ai.get("base_url", "")))
        self.model = QLineEdit(str(ai.get("model", "")))
        self.timeout = QDoubleSpinBox()
        self.timeout.setDecimals(0)
        self.timeout.setRange(10, 900)
        self.timeout.setSuffix(" s")
        self.timeout.setValue(float(ai.get("timeout_seconds", 180)))
        ai_form.addRow("URL del servicio", self.base_url)
        ai_form.addRow("Modelo", self.model)
        ai_form.addRow("Tiempo máximo", self.timeout)
        ai_card.body.addLayout(ai_form)
        ai_card.add(primary_button("Guardar configuración de IA", self.save_ai))
        layout.addWidget(ai_card)

        weight_card = Card("Pesos de evaluación", "Los porcentajes se normalizan automáticamente al calcular el puntaje.")
        weight_form = QFormLayout()
        self.weight_fields = {}
        for key, label in (("ats", "ATS"), ("hr", "Recursos Humanos"), ("technical", "Técnico")):
            field = QDoubleSpinBox()
            field.setRange(0, 100)
            field.setDecimals(1)
            field.setSuffix(" %")
            field.setValue(float(context.weights[key]))
            self.weight_fields[key] = field
            weight_form.addRow(label, field)
        weight_card.body.addLayout(weight_form)
        weight_card.add(primary_button("Guardar pesos", self.save_weights))
        layout.addWidget(weight_card)
        layout.addStretch(1)

    def save_ai(self) -> None:
        settings = self.context.ai_settings
        settings.update({
            "base_url": self.base_url.text().strip(),
            "model": self.model.text().strip(),
            "timeout_seconds": int(self.timeout.value()),
        })
        if not settings["base_url"]:
            warn_message(self, "La URL del servicio no puede quedar vacía.")
            return
        try:
            self.context.save_section("ai", settings)
            QMessageBox.information(self, "Configuración guardada", "La conexión de IA local se actualizó.")
        except Exception as exc:
            error_message(self, str(exc))

    def save_weights(self) -> None:
        values = {key: field.value() for key, field in self.weight_fields.items()}
        if sum(values.values()) <= 0:
            warn_message(self, "La suma de pesos debe ser mayor que cero.")
            return
        try:
            self.context.save_section("weights", values)
            QMessageBox.information(self, "Pesos guardados", "Los nuevos pesos se usarán en las próximas evaluaciones.")
        except Exception as exc:
            error_message(self, str(exc))
