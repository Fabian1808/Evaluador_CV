"""Renderizador PDF con ReportLab y fuentes TTF embebidas.

Se usa un lienzo directo (no tablas ni marcos) para garantizar:
- texto seleccionable y extraíble por ATS;
- una sola columna;
- control exacto de márgenes, tipografías y saltos de página;
- caracteres acentuados correctamente codificados.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.core.errors import ExportError
from app.config.document_config import normalize_config

_FONT_FILES: dict[str, tuple[str, str, str, str]] = {
    "Arial": ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
    "Calibri": ("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf"),
    "Aptos": ("Aptos.ttf", "Aptos-Bold.ttf", "Aptos-Italic.ttf", "Aptos-Bold-Italic.ttf"),
    "Cambria": ("cambria.ttc", "cambriab.ttf", "cambriai.ttf", "cambriaz.ttf"),
    "Times New Roman": ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"),
}
_FONT_FALLBACKS = {
    "Calibri": "Arial",
    "Aptos": "Calibri",
    "Cambria": "Times New Roman",
    "Arial": None,
    "Times New Roman": None,
}
_BUILTIN = {
    "normal": "Helvetica",
    "bold": "Helvetica-Bold",
    "italic": "Helvetica-Oblique",
    "bolditalic": "Helvetica-BoldOblique",
}
_registered: dict[str, dict[str, str]] = {}


def _font_directory() -> Path:
    return Path(r"C:\Windows\Fonts")


def _find_font_file(filename: str) -> Path | None:
    candidates = [
        _font_directory() / filename,
        Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts" / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def register_family(family: str) -> dict[str, str]:
    """Registra una familia TTF y devuelve los nombres normal/bold/italic/bolditalic."""
    if family in _registered:
        return _registered[family]
    chosen = family
    while chosen and chosen not in _FONT_FILES:
        chosen = _FONT_FALLBACKS.get(chosen, None)  # type: ignore[assignment]
    if not chosen:
        _registered[family] = dict(_BUILTIN)
        return _registered[family]

    files = _FONT_FILES[chosen]
    prefix = "CV" + "".join(character for character in chosen if character.isalnum())
    names: dict[str, str] = {}
    roles = ("normal", "bold", "italic", "bolditalic")
    missing = False
    for role, filename in zip(roles, files):
        path = _find_font_file(filename)
        if path is None:
            missing = True
            break
        font_name = f"{prefix}-{role}"
        try:
            if font_name not in pdfmetrics.getRegisteredFontNames():
                kwargs = {"subfontIndex": 0} if path.suffix.lower() == ".ttc" else {}
                pdfmetrics.registerFont(TTFont(font_name, str(path), **kwargs))
            names[role] = font_name
        except Exception:
            missing = True
            break

    if missing or len(names) != 4:
        fallback = _FONT_FALLBACKS.get(chosen)
        if fallback:
            names = register_family(fallback)
        else:
            names = dict(_BUILTIN)
    else:
        try:
            registerFontFamily(
                prefix,
                normal=names["normal"],
                bold=names["bold"],
                italic=names["italic"],
                boldItalic=names["bolditalic"],
            )
        except Exception:
            pass
    _registered[family] = names
    return names


class PDFRenderer:
    """Genera un PDF Harvard de una columna con ReportLab."""

    def render(
        self, content: dict[str, Any], config: dict[str, Any] | None, path: str | Path
    ) -> Path:
        cfg = normalize_config(config)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.cfg = cfg
        self.fonts = register_family(cfg["font_family"])
        self.text_color = HexColor("#111111")
        self.muted_color = HexColor("#333333")
        self.separator_color = HexColor("#8A8A8A")
        self.page_width, self.page_height = A4
        self.left = cfg["margin_left_cm"] * cm
        self.right = cfg["margin_right_cm"] * cm
        self.top = cfg["margin_top_cm"] * cm
        self.bottom = cfg["margin_bottom_cm"] * cm
        self.width = self.page_width - self.left - self.right
        self.line_spacing = float(cfg["line_spacing"])

        try:
            self.canvas = canvas.Canvas(
                str(target), pagesize=A4, pageCompression=1,
                invariant=0, initialFontName=self.fonts["normal"],
            )
            self.canvas.setTitle("Currículum")
            self.canvas.setAuthor(
                str((content.get("personal") or {}).get("name", "")) or "CV Analyzer Pro"
            )
            self.canvas.setCreator("CV Analyzer Pro")
            self.canvas.setSubject("Currículum profesional")
            self.y = self.page_height - self.top - cfg["body_size"]
            self._draw_document(content)
            self.canvas.save()
        except Exception as exc:
            raise ExportError(f"No se pudo generar el PDF: {exc}") from exc
        if not target.exists() or target.stat().st_size == 0:
            raise ExportError("El PDF se generó vacío.")
        return target

    # ------------------------------------------------------------- primitivas
    def _leading(self, size: float) -> float:
        return size * 1.2 * self.line_spacing

    def _new_page(self, size: float) -> None:
        self.canvas.showPage()
        self.y = self.page_height - self.top - size

    def _ensure(self, needed: float, size: float) -> None:
        if self.y - needed < self.bottom:
            self._new_page(size)

    def _line(
        self,
        text: str,
        font: str,
        size: float,
        x: float | None = None,
        align: str = "left",
        color: Color | None = None,
        leading: float | None = None,
    ) -> None:
        if not text:
            self.y -= self._leading(size)
            return
        leading = leading or self._leading(size)
        self._ensure(leading, size)
        self.canvas.setFont(font, size)
        self.canvas.setFillColor(color or self.text_color)
        draw_x = self.left if x is None else x
        if align == "center":
            draw_x = self.left + (self.width - pdfmetrics.stringWidth(text, font, size)) / 2
        self.canvas.drawString(draw_x, self.y, text)
        self.y -= leading

    def _paragraph(
        self,
        text: str,
        font: str | None = None,
        size: float | None = None,
        x: float | None = None,
        width: float | None = None,
        space_after: float | None = None,
        align: str = "left",
        color: Color | None = None,
    ) -> None:
        text = str(text or "").strip()
        if not text:
            return
        font = font or self.fonts["normal"]
        size = size or self.cfg["body_size"]
        width = width or self.width
        leading = self._leading(size)
        from reportlab.lib.utils import simpleSplit

        for line in simpleSplit(text, font, size, width):
            self._line(line, font, size, x=x, align=align, color=color, leading=leading)
        if space_after:
            self.y -= space_after

    def _heading(self, text: str) -> None:
        size = self.cfg["heading_size"]
        leading = self._leading(size)
        self._ensure(self.cfg["section_space_pt"] + leading * 2, size)
        self.y -= self.cfg["section_space_pt"]
        label = text.upper() if self.cfg["uppercase_headings"] else text
        self._line(label, self.fonts["bold"], size, leading=leading)
        if self.cfg["show_separator"]:
            self.canvas.setStrokeColor(self.separator_color)
            self.canvas.setLineWidth(0.6)
            self.canvas.line(self.left, self.y + 2, self.left + self.width, self.y + 2)
        self.y -= 3

    def _segments(
        self,
        segments: list[tuple[str, str, float, Color]],
        size: float,
        space_after: float = 2,
    ) -> None:
        """Dibuja una línea con varios estilos; si no cabe, usa varias líneas."""
        total = sum(
            pdfmetrics.stringWidth(text, font, font_size)
            for text, font, font_size, _color in segments if text
        )
        leading = self._leading(size)
        self._ensure(leading, size)
        if total <= self.width:
            x = self.left
            for text, font, font_size, color in segments:
                if not text:
                    continue
                self.canvas.setFont(font, font_size)
                self.canvas.setFillColor(color)
                self.canvas.drawString(x, self.y, text)
                x += pdfmetrics.stringWidth(text, font, font_size)
            self.y -= leading + space_after
            return
        # No cabe: dibuja cada segmento en su propia línea.
        for text, font, font_size, color in segments:
            if text:
                self._paragraph(text, font, font_size, color=color, space_after=0)
        self.y -= space_after

    def _bullet(self, text: str) -> None:
        size = self.cfg["body_size"]
        leading = self._leading(size)
        from reportlab.lib.utils import simpleSplit

        lines = simpleSplit(str(text).strip(), self.fonts["normal"], size, self.width - 12)
        if not lines:
            return
        self._ensure(leading, size)
        self.canvas.setFont(self.fonts["normal"], size)
        self.canvas.setFillColor(self.text_color)
        self.canvas.drawString(self.left + 2, self.y, "•")
        for index, line in enumerate(lines):
            self._ensure(leading, size)
            self.canvas.setFont(self.fonts["normal"], size)
            self.canvas.setFillColor(self.text_color)
            self.canvas.drawString(self.left + 12, self.y, line)
            self.y -= leading
        self.y -= 1

    # --------------------------------------------------------------- documento
    def _draw_document(self, content: dict[str, Any]) -> None:
        cfg = self.cfg
        personal = content.get("personal") or {}
        align = "center" if str(cfg.get("alignment", "left")) == "center" else "left"

        if personal.get("name"):
            self._paragraph(
                str(personal["name"]), self.fonts["bold"], cfg["name_size"],
                align=align, space_after=2,
            )
        if personal.get("headline"):
            self._paragraph(
                str(personal["headline"]), self.fonts["normal"], cfg["headline_size"],
                align=align, space_after=2,
            )
        contact = "  |  ".join(
            str(value) for value in (
                personal.get("email"), personal.get("phone"), personal.get("location"),
                personal.get("linkedin"), personal.get("website"),
            ) if value
        )
        if contact:
            self._paragraph(
                contact, self.fonts["normal"], cfg["contact_size"],
                align=align, color=self.muted_color, space_after=6,
            )

        if content.get("summary"):
            self._heading("Perfil profesional")
            self._paragraph(str(content["summary"]))

        experience = content.get("experience") or []
        if experience:
            self._heading("Experiencia profesional")
            for entry in experience:
                role = str(entry.get("role") or "").strip()
                company = str(entry.get("company") or "").strip()
                period = str(entry.get("period") or "").strip()
                location = str(entry.get("location") or "").strip()
                meta = " | ".join(filter(None, [period, location]))
                segments = []
                if role:
                    segments.append((role, self.fonts["bold"], cfg["body_size"], self.text_color))
                if company:
                    segments.append((f" — {company}", self.fonts["normal"], cfg["body_size"], self.text_color))
                if meta:
                    segments.append((f"  ({meta})", self.fonts["italic"], cfg["date_size"], self.muted_color))
                self._segments(segments, cfg["body_size"], space_after=1)
                bullets = entry.get("bullets") or []
                if bullets:
                    for bullet in bullets:
                        self._bullet(str(bullet))
                    self.y -= 2
                elif entry.get("description"):
                    self._paragraph(str(entry["description"]), space_after=3)

        education = content.get("education") or []
        if education:
            self._heading("Educación")
            for entry in education:
                degree = str(entry.get("degree") or "").strip()
                institution = str(entry.get("institution") or "").strip()
                period = str(entry.get("period") or "").strip()
                line = " — ".join(filter(None, [degree, institution]))
                segments = [(line, self.fonts["bold"], cfg["body_size"], self.text_color)]
                if period:
                    segments.append((f"  ({period})", self.fonts["italic"], cfg["date_size"], self.muted_color))
                self._segments(segments, cfg["body_size"], space_after=1)
                if entry.get("details"):
                    self._paragraph(str(entry["details"]), space_after=2)

        skills = content.get("skills") or {}
        if skills.get("technical") or skills.get("soft"):
            self._heading("Competencias")
            if skills.get("technical"):
                self._label_value("Técnicas: ", ", ".join(str(item) for item in skills["technical"]))
            if skills.get("soft"):
                self._label_value("Blandas: ", ", ".join(str(item) for item in skills["soft"]))

        if content.get("certifications"):
            self._heading("Certificaciones")
            for item in content["certifications"]:
                self._bullet(str(item))

        if content.get("languages"):
            self._heading("Idiomas")
            for item in content["languages"]:
                text = str(item.get("language", ""))
                if item.get("level"):
                    text += f" — {item['level']}"
                self._bullet(text)

        if content.get("projects"):
            self._heading("Proyectos")
            for project in content["projects"]:
                name = str(project.get("name", "")).strip()
                description = str(project.get("description", "")).strip()
                segments = [(name, self.fonts["bold"], cfg["body_size"], self.text_color)]
                if description:
                    segments.append((f": {description}", self.fonts["normal"], cfg["body_size"], self.text_color))
                self._segments(segments, cfg["body_size"], space_after=2)

        if content.get("achievements"):
            self._heading("Logros")
            for item in content["achievements"]:
                self._bullet(str(item))

        if content.get("additional"):
            self._heading("Información adicional")
            for item in content["additional"]:
                self._bullet(str(item))

    def _label_value(self, label: str, value: str) -> None:
        size = self.cfg["body_size"]
        leading = self._leading(size)
        from reportlab.lib.utils import simpleSplit

        label_width = pdfmetrics.stringWidth(label, self.fonts["bold"], size)
        if label_width + pdfmetrics.stringWidth(value, self.fonts["normal"], size) <= self.width:
            self._ensure(leading, size)
            self.canvas.setFont(self.fonts["bold"], size)
            self.canvas.setFillColor(self.text_color)
            self.canvas.drawString(self.left, self.y, label)
            self.canvas.setFont(self.fonts["normal"], size)
            self.canvas.drawString(self.left + label_width, self.y, value)
            self.y -= leading + 1
            return
        self._line(label.strip(), self.fonts["bold"], size, leading=leading)
        self._paragraph(value, space_after=1)
