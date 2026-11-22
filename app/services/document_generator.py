"""Generador de CV con plantilla Harvard.

Características: una columna, fondo blanco, texto negro, sin fotografía, sin
tablas, sin gráficos y con encabezados convencionales. La exportación a PDF usa
ReportLab con fuentes TTF embebidas para garantizar texto seleccionable y
extraíble por sistemas ATS.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from app.config.document_config import normalize_config
from app.core.errors import ExportError

_DEFAULT = normalize_config({})


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=False)


class HarvardGenerator:
    def build_html(
        self, content: dict[str, Any], config: dict[str, Any] | None = None,
        for_preview: bool = False,
    ) -> str:
        cfg = normalize_config(config)
        font = cfg["font_family"]
        name_size = cfg["name_size"]
        body_size = cfg["body_size"]
        heading_size = cfg["heading_size"]
        date_size = cfg["date_size"]
        contact_size = cfg["contact_size"]
        personal = content.get("personal") or {}
        margin = "0" if not for_preview else "28px 34px"
        separator = (
            f"border-bottom:0.8pt solid #8A8A8A; padding-bottom:1.5pt;"
            if cfg["show_separator"] else ""
        )
        heading_transform = "text-transform:uppercase;" if cfg["uppercase_headings"] else ""

        parts: list[str] = [
            f"<div style=\"font-family:'{_esc(font)}'; color:#111111; "
            f"font-size:{body_size}pt; line-height:{cfg['line_spacing']}; "
            f"margin:{margin}; background:#FFFFFF;\">"
        ]

        # Encabezado
        if personal.get("name"):
            parts.append(
                f"<p style=\"font-family:'{_esc(font)}'; font-size:{name_size}pt; "
                f"font-weight:bold; margin:0 0 2pt 0; line-height:1.05;\">"
                f"{_esc(personal['name'])}</p>"
            )
        if personal.get("headline"):
            parts.append(
                f"<p style=\"font-size:{cfg['headline_size']}pt; margin:0 0 3pt 0;\">"
                f"{_esc(personal['headline'])}</p>"
            )
        contact_bits = [
            personal.get("email"), personal.get("phone"), personal.get("location"),
            personal.get("linkedin"), personal.get("website"),
        ]
        contact = "  |  ".join(_esc(item) for item in contact_bits if item)
        if contact:
            parts.append(
                f"<p style=\"font-size:{contact_size}pt; margin:0 0 8pt 0; color:#222222;\">"
                f"{contact}</p>"
            )

        def heading(text: str) -> str:
            return (
                f"<p style=\"font-size:{heading_size}pt; font-weight:bold; "
                f"margin:{cfg['section_space_pt']}pt 0 3pt 0; {heading_transform} "
                f"{separator}\">{_esc(text)}</p>"
            )

        def paragraph(text: str, size: float | None = None) -> str:
            return (
                f"<p style=\"font-size:{size or body_size}pt; margin:0 0 "
                f"{cfg['space_after_pt']}pt 0; text-align:justify;\">"
                f"{_esc(text)}</p>"
            )

        if content.get("summary"):
            parts.append(heading("Perfil profesional"))
            parts.append(paragraph(str(content["summary"])))

        experience = content.get("experience") or []
        if experience:
            parts.append(heading("Experiencia profesional"))
            for entry in experience:
                title = " — ".join(
                    filter(None, [str(entry.get("role") or ""), str(entry.get("company") or "")])
                )
                period = str(entry.get("period") or "")
                location = str(entry.get("location") or "")
                meta = " | ".join(filter(None, [period, location]))
                line = f"<span style=\"font-weight:bold;\">{_esc(title)}</span>"
                if meta:
                    line += (
                        f"  <span style=\"font-size:{date_size}pt; color:#333333;\">"
                        f"({_esc(meta)})</span>"
                    )
                parts.append(
                    f"<p style=\"font-size:{body_size}pt; margin:3pt 0 1pt 0;\">{line}</p>"
                )
                bullets = entry.get("bullets") or []
                if bullets:
                    parts.append(
                        f"<ul style=\"margin:0 0 3pt 14pt; padding:0; "
                        f"font-size:{body_size}pt;\">"
                    )
                    for bullet in bullets:
                        parts.append(
                            f"<li style=\"margin:0 0 1pt 0;\">{_esc(bullet)}</li>"
                        )
                    parts.append("</ul>")
                elif entry.get("description"):
                    parts.append(paragraph(str(entry["description"])))

        education = content.get("education") or []
        if education:
            parts.append(heading("Educación"))
            for entry in education:
                line = " — ".join(
                    filter(None, [
                        str(entry.get("degree") or ""),
                        str(entry.get("institution") or ""),
                    ])
                )
                period = str(entry.get("period") or "")
                text = line
                if period:
                    text += f" ({period})"
                parts.append(
                    f"<p style=\"font-size:{body_size}pt; margin:2pt 0 0 0; "
                    f"font-weight:bold;\">{_esc(text)}</p>"
                )
                if entry.get("details"):
                    parts.append(paragraph(str(entry["details"])))

        skills = content.get("skills") or {}
        if skills.get("technical") or skills.get("soft"):
            parts.append(heading("Competencias"))
            if skills.get("technical"):
                parts.append(
                    f"<p style=\"font-size:{body_size}pt; margin:0 0 2pt 0;\">"
                    f"<span style=\"font-weight:bold;\">Técnicas: </span>"
                    f"{_esc(', '.join(skills['technical']))}</p>"
                )
            if skills.get("soft"):
                parts.append(
                    f"<p style=\"font-size:{body_size}pt; margin:0 0 2pt 0;\">"
                    f"<span style=\"font-weight:bold;\">Blandas: </span>"
                    f"{_esc(', '.join(skills['soft']))}</p>"
                )

        if content.get("certifications"):
            parts.append(heading("Certificaciones"))
            parts.append(
                f"<ul style=\"margin:0 0 3pt 14pt; padding:0; font-size:{body_size}pt;\">"
                + "".join(f"<li>{_esc(item)}</li>" for item in content["certifications"])
                + "</ul>"
            )

        if content.get("languages"):
            parts.append(heading("Idiomas"))
            parts.append(
                f"<ul style=\"margin:0 0 3pt 14pt; padding:0; font-size:{body_size}pt;\">"
                + "".join(
                    f"<li>{_esc(item.get('language', ''))}"
                    + (f" — {_esc(item.get('level'))}" if item.get("level") else "")
                    + "</li>"
                    for item in content["languages"]
                )
                + "</ul>"
            )

        if content.get("projects"):
            parts.append(heading("Proyectos"))
            for project in content["projects"]:
                name = _esc(project.get("name", ""))
                description = _esc(project.get("description", ""))
                parts.append(
                    f"<p style=\"font-size:{body_size}pt; margin:0 0 2pt 0;\">"
                    f"<span style=\"font-weight:bold;\">{name}</span>"
                    + (f": {description}" if description else "") + "</p>"
                )

        if content.get("achievements"):
            parts.append(heading("Logros"))
            parts.append(
                f"<ul style=\"margin:0 0 3pt 14pt; padding:0; font-size:{body_size}pt;\">"
                + "".join(f"<li>{_esc(item)}</li>" for item in content["achievements"])
                + "</ul>"
            )

        if content.get("additional"):
            parts.append(heading("Información adicional"))
            parts.append(
                f"<ul style=\"margin:0 0 3pt 14pt; padding:0; font-size:{body_size}pt;\">"
                + "".join(f"<li>{_esc(item)}</li>" for item in content["additional"])
                + "</ul>"
            )

        parts.append("</div>")
        return "\n".join(parts)

    # ----------------------------------------------------------------- DOCX
    def export_docx(
        self, content: dict[str, Any], config: dict[str, Any] | None, path: str | Path
    ) -> Path:
        try:
            from docx import Document
            from docx.enum.section import WD_SECTION
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.oxml import OxmlElement
            from docx.oxml.ns import qn
            from docx.shared import Cm, Pt, RGBColor
        except ImportError as exc:  # pragma: no cover
            raise ExportError("python-docx no está instalado.") from exc

        cfg = normalize_config(config)
        font = cfg["font_family"]
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        document = Document()

        # Página A4 y márgenes.
        section = document.sections[0]
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(cfg["margin_top_cm"])
        section.bottom_margin = Cm(cfg["margin_bottom_cm"])
        section.left_margin = Cm(cfg["margin_left_cm"])
        section.right_margin = Cm(cfg["margin_right_cm"])

        normal = document.styles["Normal"]
        normal.font.name = font
        normal.font.size = Pt(cfg["body_size"])
        normal.font.color.rgb = RGBColor(0x11, 0x11, 0x11)
        normal.paragraph_format.space_after = Pt(cfg["space_after_pt"])
        normal.paragraph_format.line_spacing = cfg["line_spacing"]
        # Fuente para caracteres latinos.
        rpr = normal.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        rfonts.set(qn("w:ascii"), font)
        rfonts.set(qn("w:hAnsi"), font)

        personal = content.get("personal") or {}
        alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
            if str(cfg.get("alignment", "left")) == "center"
            else WD_ALIGN_PARAGRAPH.LEFT
        )

        def add_paragraph(text: str = "", size: float | None = None, bold: bool = False,
                          space_after: float | None = None, italic: bool = False):
            paragraph = document.add_paragraph()
            paragraph.alignment = alignment
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(
                cfg["space_after_pt"] if space_after is None else space_after
            )
            paragraph.paragraph_format.line_spacing = cfg["line_spacing"]
            run = paragraph.add_run(text)
            run.bold = bold
            run.italic = italic
            run.font.name = font
            run.font.size = Pt(size or cfg["body_size"])
            return paragraph

        def add_heading(text: str) -> None:
            paragraph = document.add_paragraph()
            paragraph.alignment = alignment
            paragraph.paragraph_format.space_before = Pt(cfg["section_space_pt"])
            paragraph.paragraph_format.space_after = Pt(3)
            paragraph.paragraph_format.keep_with_next = True
            run = paragraph.add_run(text.upper() if cfg["uppercase_headings"] else text)
            run.bold = True
            run.font.name = font
            run.font.size = Pt(cfg["heading_size"])
            if cfg["show_separator"]:
                p_pr = paragraph._p.get_or_add_pPr()
                p_bdr = OxmlElement("w:pBdr")
                bottom = OxmlElement("w:bottom")
                bottom.set(qn("w:val"), "single")
                bottom.set(qn("w:sz"), "4")
                bottom.set(qn("w:space"), "1")
                bottom.set(qn("w:color"), "8A8A8A")
                p_bdr.append(bottom)
                p_pr.append(p_bdr)

        def add_bullet(text: str) -> None:
            try:
                paragraph = document.add_paragraph(style="List Bullet")
            except KeyError:
                paragraph = document.add_paragraph()
                text = "• " + text
            paragraph.paragraph_format.space_after = Pt(1)
            paragraph.paragraph_format.line_spacing = cfg["line_spacing"]
            run = paragraph.add_run(text)
            run.font.name = font
            run.font.size = Pt(cfg["body_size"])

        # Encabezado.
        if personal.get("name"):
            add_paragraph(str(personal["name"]), cfg["name_size"], bold=True, space_after=2)
        if personal.get("headline"):
            add_paragraph(str(personal["headline"]), cfg["headline_size"], space_after=2)
        contact = "  |  ".join(
            str(value) for value in (
                personal.get("email"), personal.get("phone"), personal.get("location"),
                personal.get("linkedin"), personal.get("website"),
            ) if value
        )
        if contact:
            add_paragraph(contact, cfg["contact_size"], space_after=6)

        if content.get("summary"):
            add_heading("Perfil profesional")
            add_paragraph(str(content["summary"]))

        if content.get("experience"):
            add_heading("Experiencia profesional")
            for entry in content["experience"]:
                paragraph = document.add_paragraph()
                paragraph.alignment = alignment
                paragraph.paragraph_format.space_before = Pt(3)
                paragraph.paragraph_format.space_after = Pt(1)
                paragraph.paragraph_format.keep_with_next = True
                run = paragraph.add_run(
                    " — ".join(
                        filter(None, [
                            str(entry.get("role") or ""),
                            str(entry.get("company") or ""),
                        ])
                    )
                )
                run.bold = True
                run.font.name = font
                run.font.size = Pt(cfg["body_size"])
                meta = " | ".join(
                    filter(None, [str(entry.get("period") or ""), str(entry.get("location") or "")])
                )
                if meta:
                    date_run = paragraph.add_run(f"  ({meta})")
                    date_run.italic = True
                    date_run.font.name = font
                    date_run.font.size = Pt(cfg["date_size"])
                    date_run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
                if entry.get("bullets"):
                    for bullet in entry["bullets"]:
                        add_bullet(str(bullet))
                elif entry.get("description"):
                    add_paragraph(str(entry["description"]))

        if content.get("education"):
            add_heading("Educación")
            for entry in content["education"]:
                line = " — ".join(
                    filter(None, [
                        str(entry.get("degree") or ""),
                        str(entry.get("institution") or ""),
                    ])
                )
                if entry.get("period"):
                    line += f" ({entry['period']})"
                add_paragraph(line, bold=True, space_after=1)
                if entry.get("details"):
                    add_paragraph(str(entry["details"]))

        skills = content.get("skills") or {}
        if skills.get("technical") or skills.get("soft"):
            add_heading("Competencias")
            if skills.get("technical"):
                paragraph = document.add_paragraph()
                paragraph.paragraph_format.space_after = Pt(1)
                label = paragraph.add_run("Técnicas: ")
                label.bold = True
                label.font.name = font
                label.font.size = Pt(cfg["body_size"])
                value = paragraph.add_run(", ".join(str(item) for item in skills["technical"]))
                value.font.name = font
                value.font.size = Pt(cfg["body_size"])
            if skills.get("soft"):
                paragraph = document.add_paragraph()
                paragraph.paragraph_format.space_after = Pt(1)
                label = paragraph.add_run("Blandas: ")
                label.bold = True
                label.font.name = font
                label.font.size = Pt(cfg["body_size"])
                value = paragraph.add_run(", ".join(str(item) for item in skills["soft"]))
                value.font.name = font
                value.font.size = Pt(cfg["body_size"])

        if content.get("certifications"):
            add_heading("Certificaciones")
            for item in content["certifications"]:
                add_bullet(str(item))

        if content.get("languages"):
            add_heading("Idiomas")
            for item in content["languages"]:
                text = str(item.get("language", ""))
                if item.get("level"):
                    text += f" — {item['level']}"
                add_bullet(text)

        if content.get("projects"):
            add_heading("Proyectos")
            for project in content["projects"]:
                add_paragraph(str(project.get("name", "")), bold=True, space_after=1)
                if project.get("description"):
                    add_paragraph(str(project["description"]))

        if content.get("achievements"):
            add_heading("Logros")
            for item in content["achievements"]:
                add_bullet(str(item))

        if content.get("additional"):
            add_heading("Información adicional")
            for item in content["additional"]:
                add_bullet(str(item))

        try:
            document.save(str(target))
        except Exception as exc:
            raise ExportError(f"No se pudo guardar el DOCX: {exc}") from exc
        return target

    # ------------------------------------------------------------------ PDF
    def export_pdf(
        self, content: dict[str, Any], config: dict[str, Any] | None, path: str | Path
    ) -> Path:
        from app.services.pdf_renderer import PDFRenderer

        return PDFRenderer().render(content, config, path)

    def export_html(
        self, content: dict[str, Any], config: dict[str, Any] | None, path: str | Path
    ) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<title>Currículum</title></head><body style='background:#fff;'>"
            + self.build_html(content, config, for_preview=True)
            + "</body></html>",
            encoding="utf-8",
        )
        return target
