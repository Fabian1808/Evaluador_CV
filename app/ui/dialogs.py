"""Diálogos de la aplicación: candidatos, ofertas, edición de CV y respuestas."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import constants as C
from app.ui.widgets import (
    Pill,
    configure_table,
    primary_button,
    restyle,
    secondary_button,
    selected_row_data,
    table_item,
)


# ---------------------------------------------------------------------------
# Formulario genérico
# ---------------------------------------------------------------------------
@dataclass
class FormField:
    key: str
    label: str
    kind: str = "line"  # line | text | multiline | combo | check | int
    default: Any = ""
    placeholder: str = ""
    options: list[str] = field(default_factory=list)
    minimum: int = 0
    maximum: int = 100


class FormDialog(QDialog):
    def __init__(
        self,
        title: str,
        fields: list[FormField],
        parent: QWidget | None = None,
        subtitle: str = "",
        confirm_text: str = "Guardar",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(520)
        self._fields = fields
        self._widgets: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        heading = QLabel(title)
        heading.setObjectName("DialogTitle")
        layout.addWidget(heading)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("Muted")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for item in fields:
            widget = self._build_widget(item)
            self._widgets[item.key] = widget
            form.addRow(item.label, widget)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        self._accept = buttons.addButton(confirm_text, QDialogButtonBox.ButtonRole.AcceptRole)
        self._accept.setProperty("variant", "primary")
        restyle(self._accept)
        cancel = buttons.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_widget(self, item: FormField) -> QWidget:
        if item.kind == "multiline":
            widget = QPlainTextEdit()
            widget.setPlainText(str(item.default or ""))
            widget.setPlaceholderText(item.placeholder)
            widget.setMinimumHeight(90)
            return widget
        if item.kind == "text":
            widget = QPlainTextEdit()
            widget.setPlainText(str(item.default or ""))
            widget.setPlaceholderText(item.placeholder)
            widget.setMinimumHeight(140)
            return widget
        if item.kind == "combo":
            widget = QComboBox()
            widget.addItems(item.options)
            value = str(item.default or "")
            if value:
                index = widget.findText(value)
                if index >= 0:
                    widget.setCurrentIndex(index)
                else:
                    widget.addItem(value)
                    widget.setCurrentText(value)
            return widget
        if item.kind == "check":
            widget = QCheckBox(str(item.label))
            widget.setText("")
            widget.setChecked(bool(item.default))
            return widget
        if item.kind == "int":
            widget = QSpinBox()
            widget.setRange(item.minimum, item.maximum)
            widget.setValue(int(item.default or 0))
            return widget
        widget = QLineEdit(str(item.default or ""))
        widget.setPlaceholderText(item.placeholder)
        return widget

    def _validate(self) -> None:
        required = [item for item in self._fields if item.key in {"full_name", "raw_text", "role"}]
        for item in required:
            widget = self._widgets[item.key]
            if isinstance(widget, QPlainTextEdit):
                value = widget.toPlainText().strip()
            elif isinstance(widget, QLineEdit):
                value = widget.text().strip()
            else:
                value = ""
            if not value:
                widget.setFocus()
                if isinstance(widget, (QLineEdit, QPlainTextEdit)):
                    widget.setStyleSheet(f"border:1px solid {C.COLOR_DANGER};")
                return
        self.accept()

    def values(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for item in self._fields:
            widget = self._widgets[item.key]
            if isinstance(widget, QPlainTextEdit):
                result[item.key] = widget.toPlainText().strip()
            elif isinstance(widget, QLineEdit):
                result[item.key] = widget.text().strip()
            elif isinstance(widget, QComboBox):
                result[item.key] = widget.currentText().strip()
            elif isinstance(widget, QCheckBox):
                result[item.key] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                result[item.key] = widget.value()
        return result


# ---------------------------------------------------------------------------
# Candidato
# ---------------------------------------------------------------------------
class CandidateDialog(FormDialog):
    def __init__(self, candidate=None, parent: QWidget | None = None) -> None:
        fields = [
            FormField("full_name", "Nombre completo *", default=getattr(candidate, "full_name", "")),
            FormField("email", "Correo electrónico", default=getattr(candidate, "email", "") or ""),
            FormField("phone", "Teléfono", default=getattr(candidate, "phone", "") or ""),
            FormField("location", "Ubicación", default=getattr(candidate, "location", "") or ""),
            FormField("linkedin", "LinkedIn", default=getattr(candidate, "linkedin", "") or ""),
            FormField(
                "notes",
                "Notas internas",
                kind="multiline",
                default=getattr(candidate, "notes", "") or "",
                placeholder="Información de contexto para el análisis (no se incluye en el CV).",
            ),
        ]
        super().__init__(
            "Editar candidato" if candidate else "Nuevo candidato",
            fields,
            parent,
            subtitle="Los datos de contacto se usan para identificar al candidato y generar el CV.",
        )


# ---------------------------------------------------------------------------
# Oferta
# ---------------------------------------------------------------------------
class OfferDialog(FormDialog):
    def __init__(self, offer=None, parent: QWidget | None = None) -> None:
        fields = [
            FormField("title", "Título de la vacante", default=getattr(offer, "title", "") or ""),
            FormField("company", "Empresa", default=getattr(offer, "company", "") or ""),
            FormField("area", "Área", default=getattr(offer, "area", "") or ""),
            FormField(
                "raw_text",
                "Texto de la oferta *",
                kind="text",
                default=getattr(offer, "raw_text", "") or "",
                placeholder="Pegue aquí la descripción completa de la oferta laboral.",
            ),
            FormField(
                "use_ai",
                "Analizar con IA local",
                kind="check",
                default=False,
            ),
        ]
        super().__init__(
            "Editar oferta" if offer else "Nueva oferta laboral",
            fields,
            parent,
            subtitle=(
                "El análisis separa requisitos obligatorios y deseables. Si la IA local no "
                "está disponible se usa el analizador heurístico y se le indicará."
            ),
        )
        self.setMinimumWidth(640)

    def _validate(self) -> None:
        text = self._widgets["raw_text"].toPlainText().strip()
        if len(text) < 30:
            self._widgets["raw_text"].setFocus()
            self._widgets["raw_text"].setStyleSheet(f"border:1px solid {C.COLOR_DANGER};")
            return
        super()._validate()


# ---------------------------------------------------------------------------
# Respuesta a información faltante
# ---------------------------------------------------------------------------
class AnswerDialog(QDialog):
    def __init__(
        self,
        question: str,
        why: str = "",
        example: str = "",
        current: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Responder información faltante")
        self.setModal(True)
        self.setMinimumWidth(620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(10)

        heading = QLabel(question)
        heading.setObjectName("DialogTitle")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        if why:
            why_label = QLabel(why)
            why_label.setObjectName("Muted")
            why_label.setWordWrap(True)
            layout.addWidget(why_label)

        if example:
            example_box = QLabel(example)
            example_box.setWordWrap(True)
            example_box.setStyleSheet(
                f"background:{C.COLOR_WARNING_SOFT}; border:1px solid #FDE68A; "
                "border-radius:7px; padding:8px; font-size:12px;"
            )
            layout.addWidget(example_box)

        self.answer = QPlainTextEdit()
        self.answer.setPlainText(current)
        self.answer.setPlaceholderText("Escriba la respuesta real del candidato. No se inventará nada.")
        self.answer.setMinimumHeight(130)
        layout.addWidget(self.answer)

        hint = QLabel(
            "La respuesta se guarda como información proporcionada por el usuario. "
            "El ejemplo ilustrativo nunca se copia automáticamente."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox()
        save = buttons.addButton("Guardar respuesta", QDialogButtonBox.ButtonRole.AcceptRole)
        save.setProperty("variant", "primary")
        restyle(save)
        buttons.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def text(self) -> str:
        return self.answer.toPlainText().strip()


# ---------------------------------------------------------------------------
# Editor de contenido del CV
# ---------------------------------------------------------------------------
class CVEditorDialog(QDialog):
    """Edición estructurada del contenido de una versión del CV.

    Cada sección mantiene la estructura del parser para que evaluadores y
    generador trabajen con datos consistentes. Al guardar se crea una versión
    nueva: el documento original nunca se modifica.
    """

    def __init__(
        self,
        content: dict[str, Any],
        parent: QWidget | None = None,
        title: str = "Editar contenido del CV",
        label: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(900, 680)
        self._content = copy.deepcopy(content or {})
        self._label = label

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        heading = QLabel(title)
        heading.setObjectName("DialogTitle")
        layout.addWidget(heading)
        subtitle = QLabel(
            "Los cambios se guardarán como una versión nueva. El documento original "
            "importado no se modifica."
        )
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._build_personal_tab()
        self._build_experience_tab()
        self._build_education_tab()
        self._build_skills_tab()
        self._build_languages_tab()
        self._build_other_tab()

        footer = QHBoxLayout()
        if self._label:
            footer.addWidget(QLabel(f"Etiqueta de la nueva versión: {self._label}"))
        footer.addStretch(1)
        cancel = secondary_button("Cancelar", self.reject)
        save = primary_button("Guardar como versión nueva", self._save)
        footer.addWidget(cancel)
        footer.addWidget(save)
        layout.addLayout(footer)

    # ------------------------------------------------------------------ tabs
    def _build_personal_tab(self) -> None:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setContentsMargins(16, 14, 16, 14)
        form.setSpacing(9)
        personal = self._content.get("personal") or {}
        self.personal_fields: dict[str, QLineEdit] = {}
        for key, label in (
            ("name", "Nombre"),
            ("headline", "Titular profesional"),
            ("email", "Correo"),
            ("phone", "Teléfono"),
            ("location", "Ubicación"),
            ("linkedin", "LinkedIn"),
            ("website", "Sitio web"),
        ):
            widget = QLineEdit(str(personal.get(key) or ""))
            self.personal_fields[key] = widget
            form.addRow(label, widget)
        self.summary = QPlainTextEdit(str(self._content.get("summary") or ""))
        self.summary.setMinimumHeight(150)
        self.summary.setPlaceholderText("Perfil profesional: especialidad, años de experiencia y evidencia.")
        form.addRow("Perfil profesional", self.summary)
        scroll.setWidget(inner)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self.tabs.addTab(page, "Datos y perfil")

    def _build_experience_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.experience_table = QTableWidget()
        configure_table(self.experience_table, ["Puesto", "Empresa", "Periodo", "Viñetas"])
        self.experience_table.doubleClicked.connect(lambda _index: self._edit_experience())
        layout.addWidget(self.experience_table, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(primary_button("Añadir puesto", self._add_experience))
        buttons.addWidget(secondary_button("Editar", self._edit_experience))
        buttons.addWidget(secondary_button("Eliminar", self._remove_experience))
        buttons.addStretch(1)
        hint = QLabel("Las viñetas deben describir acciones y resultados reales; no invente datos.")
        hint.setObjectName("Muted")
        buttons.addWidget(hint)
        layout.addLayout(buttons)
        self.tabs.addTab(page, "Experiencia")
        self._refresh_experience()

    def _build_education_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.education_table = QTableWidget()
        configure_table(self.education_table, ["Título", "Institución", "Periodo"])
        self.education_table.doubleClicked.connect(lambda _index: self._edit_education())
        layout.addWidget(self.education_table, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(primary_button("Añadir formación", self._add_education))
        buttons.addWidget(secondary_button("Editar", self._edit_education))
        buttons.addWidget(secondary_button("Eliminar", self._remove_education))
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.tabs.addTab(page, "Educación")
        self._refresh_education()

    def _build_skills_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        skills = self._content.get("skills") or {}
        layout.addWidget(QLabel("Competencias técnicas (separadas por comas)"))
        self.technical_skills = QPlainTextEdit(", ".join(skills.get("technical") or []))
        self.technical_skills.setMinimumHeight(90)
        self.technical_skills.setPlaceholderText("SQL, Python, Power BI…")
        layout.addWidget(self.technical_skills)
        layout.addWidget(QLabel("Competencias blandas (separadas por comas)"))
        self.soft_skills = QPlainTextEdit(", ".join(skills.get("soft") or []))
        self.soft_skills.setMinimumHeight(70)
        self.soft_skills.setPlaceholderText("Comunicación, colaboración…")
        layout.addWidget(self.soft_skills)
        layout.addWidget(
            QLabel(
                "Incluya solo competencias demostrables. El optimizador puede señalar "
                "competencias mencionadas sin evidencia en la experiencia."
            )
        )
        layout.addStretch(1)
        self.tabs.addTab(page, "Competencias")

    def _build_languages_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.languages_table = QTableWidget()
        configure_table(self.languages_table, ["Idioma", "Nivel"])
        self.languages_table.doubleClicked.connect(lambda _index: self._edit_language())
        layout.addWidget(self.languages_table, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(primary_button("Añadir idioma", self._add_language))
        buttons.addWidget(secondary_button("Editar", self._edit_language))
        buttons.addWidget(secondary_button("Eliminar", self._remove_language))
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.tabs.addTab(page, "Idiomas")
        self._refresh_languages()

    def _build_other_tab(self) -> None:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Certificaciones (una por línea)"))
        self.certifications = QPlainTextEdit("\n".join(self._content.get("certifications") or []))
        self.certifications.setMinimumHeight(70)
        layout.addWidget(self.certifications)

        layout.addWidget(QLabel("Logros (uno por línea)"))
        self.achievements = QPlainTextEdit("\n".join(self._content.get("achievements") or []))
        self.achievements.setMinimumHeight(70)
        layout.addWidget(self.achievements)

        layout.addWidget(QLabel("Información adicional (una por línea)"))
        self.additional = QPlainTextEdit("\n".join(self._content.get("additional") or []))
        self.additional.setMinimumHeight(60)
        layout.addWidget(self.additional)

        layout.addWidget(QLabel("Proyectos"))
        self.projects_table = QTableWidget()
        configure_table(self.projects_table, ["Nombre", "Descripción"])
        self.projects_table.doubleClicked.connect(lambda _index: self._edit_project())
        layout.addWidget(self.projects_table, 1)
        project_buttons = QHBoxLayout()
        project_buttons.addWidget(primary_button("Añadir proyecto", self._add_project))
        project_buttons.addWidget(secondary_button("Editar", self._edit_project))
        project_buttons.addWidget(secondary_button("Eliminar", self._remove_project))
        project_buttons.addStretch(1)
        layout.addLayout(project_buttons)

        scroll.setWidget(inner)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self.tabs.addTab(page, "Otros")
        self._refresh_projects()

    # ------------------------------------------------------------- experiencia
    def _experience(self) -> list[dict[str, Any]]:
        return self._content.setdefault("experience", [])

    def _refresh_experience(self) -> None:
        rows = self._experience()
        self.experience_table.setRowCount(len(rows))
        for index, entry in enumerate(rows):
            self.experience_table.setItem(index, 0, table_item(entry.get("role", ""), index))
            self.experience_table.setItem(index, 1, table_item(entry.get("company", "")))
            self.experience_table.setItem(
                index, 2, table_item(entry.get("period") or _period(entry))
            )
            self.experience_table.setItem(
                index, 3, table_item(str(len(entry.get("bullets") or [])))
            )

    def _add_experience(self) -> None:
        dialog = ExperienceDialog(None, self)
        if dialog.exec():
            self._experience().append(dialog.entry())
            self._refresh_experience()

    def _edit_experience(self) -> None:
        index = selected_row_data(self.experience_table)
        if index is None or not (0 <= int(index) < len(self._experience())):
            return
        dialog = ExperienceDialog(self._experience()[int(index)], self)
        if dialog.exec():
            self._experience()[int(index)] = dialog.entry()
            self._refresh_experience()

    def _remove_experience(self) -> None:
        index = selected_row_data(self.experience_table)
        if index is None:
            return
        del self._experience()[int(index)]
        self._refresh_experience()

    # --------------------------------------------------------------- educación
    def _education(self) -> list[dict[str, Any]]:
        return self._content.setdefault("education", [])

    def _refresh_education(self) -> None:
        rows = self._education()
        self.education_table.setRowCount(len(rows))
        for index, entry in enumerate(rows):
            self.education_table.setItem(index, 0, table_item(entry.get("degree", ""), index))
            self.education_table.setItem(index, 1, table_item(entry.get("institution", "")))
            self.education_table.setItem(
                index, 2, table_item(entry.get("period") or _period(entry))
            )

    def _add_education(self) -> None:
        dialog = EducationDialog(None, self)
        if dialog.exec():
            self._education().append(dialog.entry())
            self._refresh_education()

    def _edit_education(self) -> None:
        index = selected_row_data(self.education_table)
        if index is None or not (0 <= int(index) < len(self._education())):
            return
        dialog = EducationDialog(self._education()[int(index)], self)
        if dialog.exec():
            self._education()[int(index)] = dialog.entry()
            self._refresh_education()

    def _remove_education(self) -> None:
        index = selected_row_data(self.education_table)
        if index is None:
            return
        del self._education()[int(index)]
        self._refresh_education()

    # ----------------------------------------------------------------- idiomas
    def _languages(self) -> list[dict[str, Any]]:
        return self._content.setdefault("languages", [])

    def _refresh_languages(self) -> None:
        rows = self._languages()
        self.languages_table.setRowCount(len(rows))
        for index, entry in enumerate(rows):
            self.languages_table.setItem(
                index, 0, table_item(entry.get("language", ""), index)
            )
            self.languages_table.setItem(index, 1, table_item(entry.get("level", "")))

    def _add_language(self) -> None:
        dialog = FormDialog(
            "Añadir idioma",
            [
                FormField("language", "Idioma", placeholder="Inglés"),
                FormField("level", "Nivel", kind="combo", options=list(C.LANGUAGE_LEVELS)),
            ],
            self,
        )
        if dialog.exec():
            values = dialog.values()
            if values["language"]:
                self._languages().append(values)
                self._refresh_languages()

    def _edit_language(self) -> None:
        index = selected_row_data(self.languages_table)
        if index is None or not (0 <= int(index) < len(self._languages())):
            return
        current = self._languages()[int(index)]
        dialog = FormDialog(
            "Editar idioma",
            [
                FormField("language", "Idioma", default=current.get("language", "")),
                FormField(
                    "level", "Nivel", kind="combo",
                    options=list(C.LANGUAGE_LEVELS), default=current.get("level", ""),
                ),
            ],
            self,
        )
        if dialog.exec():
            self._languages()[int(index)] = dialog.values()
            self._refresh_languages()

    def _remove_language(self) -> None:
        index = selected_row_data(self.languages_table)
        if index is None:
            return
        del self._languages()[int(index)]
        self._refresh_languages()

    # --------------------------------------------------------------- proyectos
    def _projects(self) -> list[dict[str, Any]]:
        return self._content.setdefault("projects", [])

    def _refresh_projects(self) -> None:
        rows = self._projects()
        self.projects_table.setRowCount(len(rows))
        for index, entry in enumerate(rows):
            self.projects_table.setItem(index, 0, table_item(entry.get("name", ""), index))
            self.projects_table.setItem(index, 1, table_item(entry.get("description", "")))

    def _add_project(self) -> None:
        dialog = FormDialog(
            "Añadir proyecto",
            [
                FormField("name", "Nombre", placeholder="Proyecto real"),
                FormField("description", "Descripción", kind="multiline"),
                FormField("technologies", "Tecnologías (separadas por comas)"),
            ],
            self,
        )
        if dialog.exec():
            values = dialog.values()
            if values["name"]:
                values["technologies"] = _split_list(values.get("technologies", ""))
                self._projects().append(values)
                self._refresh_projects()

    def _edit_project(self) -> None:
        index = selected_row_data(self.projects_table)
        if index is None or not (0 <= int(index) < len(self._projects())):
            return
        current = self._projects()[int(index)]
        dialog = FormDialog(
            "Editar proyecto",
            [
                FormField("name", "Nombre", default=current.get("name", "")),
                FormField(
                    "description", "Descripción", kind="multiline",
                    default=current.get("description", ""),
                ),
                FormField(
                    "technologies", "Tecnologías (separadas por comas)",
                    default=", ".join(current.get("technologies") or []),
                ),
            ],
            self,
        )
        if dialog.exec():
            values = dialog.values()
            values["technologies"] = _split_list(values.get("technologies", ""))
            self._projects()[int(index)] = values
            self._refresh_projects()

    def _remove_project(self) -> None:
        index = selected_row_data(self.projects_table)
        if index is None:
            return
        del self._projects()[int(index)]
        self._refresh_projects()

    # ------------------------------------------------------------------ guardar
    def _save(self) -> None:
        personal = self._content.setdefault("personal", {})
        for key, widget in self.personal_fields.items():
            personal[key] = widget.text().strip()
        self._content["summary"] = self.summary.toPlainText().strip()
        self._content["skills"] = {
            "technical": _split_list(self.technical_skills.toPlainText()),
            "soft": _split_list(self.soft_skills.toPlainText()),
        }
        self._content["certifications"] = _lines(self.certifications.toPlainText())
        self._content["achievements"] = _lines(self.achievements.toPlainText())
        self._content["additional"] = _lines(self.additional.toPlainText())
        self.accept()

    def content(self) -> dict[str, Any]:
        return self._content


def _period(entry: dict[str, Any]) -> str:
    start = str(entry.get("start_date") or "")
    end = str(entry.get("end_date") or "")
    if start and end:
        return f"{start} – {end}"
    return start or end


def _split_list(text: str) -> list[str]:
    raw = text.replace("\n", ",").replace(";", ",")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _lines(text: str) -> list[str]:
    return [line.strip(" •-–—\t") for line in text.splitlines() if line.strip(" •-–—\t")]


class ExperienceDialog(FormDialog):
    def __init__(self, entry: dict[str, Any] | None, parent: QWidget | None = None) -> None:
        entry = entry or {}
        fields = [
            FormField("role", "Puesto *", default=entry.get("role", "")),
            FormField("company", "Empresa", default=entry.get("company", "")),
            FormField("location", "Ubicación", default=entry.get("location", "")),
            FormField(
                "period", "Periodo",
                default=entry.get("period", ""),
                placeholder="enero 2022 – actualidad",
            ),
            FormField(
                "bullets", "Logros y responsabilidades (uno por línea)",
                kind="multiline",
                default="\n".join(entry.get("bullets") or []),
                placeholder="Desarrollé…\nAutomaticé…",
            ),
            FormField(
                "description", "Descripción adicional",
                kind="multiline",
                default=entry.get("description", ""),
            ),
        ]
        super().__init__(
            "Editar puesto" if entry.get("role") else "Añadir puesto",
            fields,
            parent,
            subtitle="Use verbos de acción y datos verificables del CV original.",
        )
        self._original = entry
        self.setMinimumWidth(600)

    def entry(self) -> dict[str, Any]:
        values = self.values()
        bullets = _lines(values.pop("bullets", ""))
        entry = {**self._original, **values, "bullets": bullets}
        if not entry.get("period") and (entry.get("start_date") or entry.get("end_date")):
            entry["period"] = _period(entry)
        entry.setdefault("start_date", self._original.get("start_date", ""))
        entry.setdefault("end_date", self._original.get("end_date", ""))
        return entry


class EducationDialog(FormDialog):
    def __init__(self, entry: dict[str, Any] | None, parent: QWidget | None = None) -> None:
        entry = entry or {}
        fields = [
            FormField("degree", "Título", default=entry.get("degree", "")),
            FormField("institution", "Institución", default=entry.get("institution", "")),
            FormField("location", "Ubicación", default=entry.get("location", "")),
            FormField(
                "period", "Periodo",
                default=entry.get("period", ""),
                placeholder="2014 – 2018",
            ),
            FormField(
                "details", "Detalles", kind="multiline",
                default=entry.get("details", ""),
            ),
        ]
        super().__init__(
            "Editar formación" if entry.get("degree") else "Añadir formación",
            fields,
            parent,
        )
        self._original = entry
        self.setMinimumWidth(560)

    def entry(self) -> dict[str, Any]:
        values = self.values()
        entry = {**self._original, **values}
        entry.setdefault("start_date", self._original.get("start_date", ""))
        entry.setdefault("end_date", self._original.get("end_date", ""))
        return entry
