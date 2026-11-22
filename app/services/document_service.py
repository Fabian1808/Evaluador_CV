"""Extracción de texto y diagnóstico documental para PDF y DOCX.

El documento original nunca se modifica: se copia al almacenamiento interno y
se trabaja siempre sobre la copia. El OCR es opcional y solo se intenta cuando
el PDF no contiene texto suficiente y Tesseract está disponible.
"""

from __future__ import annotations

import io
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.errors import DocumentExtractionError, UnsupportedDocumentError
from app.utils.text import normalize_whitespace, word_count


@dataclass
class ExtractionResult:
    text: str
    method: str
    page_count: int
    diagnostics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def characters(self) -> int:
        return len(self.text)

    @property
    def words(self) -> int:
        return word_count(self.text)


def tesseract_path() -> str | None:
    """Localiza el ejecutable de Tesseract en el sistema."""
    found = shutil.which("tesseract")
    if found:
        return found
    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def ocr_available() -> bool:
    if tesseract_path() is None:
        return False
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return True


class DocumentService:
    """Extrae texto y metadatos de estructura de PDF y DOCX."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

    @staticmethod
    def ocr_available() -> bool:
        return ocr_available()

    def extract(self, path: str | Path, use_ocr: bool = True) -> ExtractionResult:
        file_path = Path(path)
        if not file_path.exists():
            raise DocumentExtractionError(f"No se encontró el archivo: {file_path}")
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf(file_path, use_ocr=use_ocr)
        if suffix == ".docx":
            return self._extract_docx(file_path)
        raise UnsupportedDocumentError(
            f"Formato no compatible: {suffix or 'sin extensión'}. Use PDF o DOCX."
        )

    # ------------------------------------------------------------------ PDF
    def _extract_pdf(self, path: Path, use_ocr: bool = True) -> ExtractionResult:
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:  # pragma: no cover
            raise DocumentExtractionError(
                "PyMuPDF no está instalado. Ejecute: pip install PyMuPDF"
            ) from exc

        warnings: list[str] = []
        diagnostics: dict[str, Any] = {
            "file_type": "pdf",
            "has_tables": False,
            "table_count": 0,
            "has_images": False,
            "image_count": 0,
            "estimated_columns": 1,
            "header_footer_text": "",
            "fonts": [],
            "font_sizes": [],
            "ocr_used": False,
            "text_in_images": False,
        }
        page_texts: list[str] = []
        try:
            document = fitz.open(path)
        except Exception as exc:
            raise DocumentExtractionError(f"No se pudo abrir el PDF: {exc}") from exc

        try:
            diagnostics["page_count"] = document.page_count
            if document.is_encrypted:
                warnings.append(
                    "El PDF está protegido. Si no se pudo leer el texto, solicite una copia sin contraseña."
                )
            all_fonts: set[str] = set()
            all_sizes: set[float] = set()
            header_footer_parts: list[str] = []
            max_columns = 1

            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                page_text = page.get_text("text") or ""
                page_texts.append(page_text)
                width = float(page.rect.width or 1)
                height = float(page.rect.height or 1)

                try:
                    tables = page.find_tables()
                    table_count = len(tables.tables)
                    if table_count:
                        diagnostics["has_tables"] = True
                        diagnostics["table_count"] += table_count
                except Exception:
                    pass

                images = page.get_images(full=True)
                if images:
                    diagnostics["has_images"] = True
                    diagnostics["image_count"] += len(images)

                try:
                    blocks = page.get_text("blocks")
                    text_blocks = [
                        block for block in blocks
                        if len(block) >= 5 and block[6] == 0 and str(block[4]).strip()
                    ]
                    left = [b for b in text_blocks if float(b[2]) < width * 0.56]
                    right = [b for b in text_blocks if float(b[0]) > width * 0.44]
                    if len(left) >= 2 and len(right) >= 2:
                        # Verifica solapamiento vertical para confirmar dos columnas.
                        left_y = {round(float(b[1]) / 20) for b in left}
                        right_y = {round(float(b[1]) / 20) for b in right}
                        if left_y & right_y:
                            max_columns = max(max_columns, 2)
                    for block in text_blocks:
                        y0, y1 = float(block[1]), float(block[3])
                        if y1 < height * 0.08 or y0 > height * 0.92:
                            header_footer_parts.append(str(block[4]).strip())
                except Exception:
                    pass

                try:
                    page_dict = page.get_text("dict")
                    for block in page_dict.get("blocks", []):
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                if span.get("font"):
                                    all_fonts.add(str(span["font"]))
                                if span.get("size"):
                                    all_sizes.add(round(float(span["size"]), 1))
                except Exception:
                    pass

            diagnostics["estimated_columns"] = max_columns
            diagnostics["fonts"] = sorted(all_fonts)[:12]
            diagnostics["font_sizes"] = sorted(all_sizes)[:12]
            diagnostics["header_footer_text"] = normalize_whitespace(
                " ".join(dict.fromkeys(header_footer_parts))
            )[:500]

            text = normalize_whitespace("\n\n".join(page_texts))
            method = "pdf_text"
            total_chars = len(text)
            chars_per_page = total_chars / max(1, document.page_count)

            if chars_per_page < 100:
                diagnostics["text_in_images"] = bool(diagnostics["has_images"])
                if use_ocr and ocr_available():
                    ocr_text, ocr_warnings = self._ocr_pdf(document)
                    warnings.extend(ocr_warnings)
                    if len(ocr_text) > total_chars:
                        text = ocr_text
                        method = "pdf_ocr"
                        diagnostics["ocr_used"] = True
                        warnings.append(
                            "El PDF no contenía texto seleccionable. Se aplicó OCR; "
                            "revise la información extraída antes de evaluarla."
                        )
                elif not use_ocr:
                    warnings.append("OCR desactivado por el usuario.")
                else:
                    warnings.append(
                        "El PDF parece escaneado y no hay texto suficiente. "
                        "Instale Tesseract OCR para habilitar la lectura automática."
                    )
            if diagnostics["has_images"] and method == "pdf_text":
                warnings.append(
                    "Se detectaron imágenes. Verifique que no contengan información "
                    "relevante que el ATS no pueda leer."
                )
        finally:
            document.close()

        if not text.strip():
            raise DocumentExtractionError(
                "No se pudo extraer texto del PDF. El archivo puede estar escaneado, "
                "protegido o dañado."
            )

        diagnostics.update(
            {
                "characters": len(text),
                "words": word_count(text),
                "text_per_page": round(len(text) / max(1, diagnostics.get("page_count", 1))),
                "fonts_count": len(diagnostics["fonts"]),
            }
        )
        return ExtractionResult(
            text=text,
            method=method,
            page_count=int(diagnostics.get("page_count", 0)),
            diagnostics=diagnostics,
            warnings=warnings,
        )

    def _ocr_pdf(self, document) -> tuple[str, list[str]]:  # type: ignore[no-untyped-def]
        warnings: list[str] = []
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return "", ["pytesseract o Pillow no están instalados."]
        executable = tesseract_path()
        if executable:
            pytesseract.pytesseract.tesseract_cmd = executable
        texts = []
        for page_index in range(document.page_count):
            try:
                page = document.load_page(page_index)
                pixmap = page.get_pixmap(dpi=200, colorspace=None)
                image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                try:
                    page_text = pytesseract.image_to_string(image, lang="spa+eng")
                except pytesseract.TesseractError:
                    page_text = pytesseract.image_to_string(image)
                texts.append(page_text)
            except Exception as exc:
                warnings.append(f"OCR falló en la página {page_index + 1}: {exc}")
        return normalize_whitespace("\n\n".join(texts)), warnings

    # ----------------------------------------------------------------- DOCX
    def _extract_docx(self, path: Path) -> ExtractionResult:
        try:
            from docx import Document
        except ImportError as exc:  # pragma: no cover
            raise DocumentExtractionError(
                "python-docx no está instalado. Ejecute: pip install python-docx"
            ) from exc

        warnings: list[str] = []
        diagnostics: dict[str, Any] = {
            "file_type": "docx",
            "has_tables": False,
            "table_count": 0,
            "has_images": False,
            "image_count": 0,
            "estimated_columns": 1,
            "header_footer_text": "",
            "fonts": [],
            "font_sizes": [],
            "ocr_used": False,
            "text_in_images": False,
        }
        try:
            document = Document(str(path))
        except Exception as exc:
            raise DocumentExtractionError(f"No se pudo abrir el DOCX: {exc}") from exc

        parts: list[str] = []
        styles: set[str] = set()
        fonts: set[str] = set()
        sizes: set[float] = set()
        paragraph_count = 0
        bullet_count = 0

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            style_name = paragraph.style.name if paragraph.style is not None else ""
            if style_name:
                styles.add(style_name)
            if text:
                paragraph_count += 1
                if style_name.lower().startswith("list") or text[:2] in {"• ", "- "}:
                    bullet_count += 1
                parts.append(text)
            for run in paragraph.runs:
                if run.font.name:
                    fonts.add(run.font.name)
                if run.font.size:
                    sizes.add(round(run.font.size.pt, 1))

        table_count = len(document.tables)
        if table_count:
            diagnostics["has_tables"] = True
            diagnostics["table_count"] = table_count
            for table in document.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        parts.append(" | ".join(dict.fromkeys(cells)))
            warnings.append(
                f"El documento contiene {table_count} tabla(s). Los ATS pueden leerlas "
                "de forma incorrecta; se recomienda una estructura de una sola columna."
            )

        try:
            diagnostics["image_count"] = len(document.inline_shapes)
            diagnostics["has_images"] = diagnostics["image_count"] > 0
        except Exception:
            pass

        header_footer_parts: list[str] = []
        for section in document.sections:
            for container in (section.header, section.footer):
                try:
                    for paragraph in container.paragraphs:
                        if paragraph.text.strip():
                            header_footer_parts.append(paragraph.text.strip())
                except Exception:
                    continue
            try:
                columns = section._sectPr.xpath("./w:cols")  # noqa: SLF001
                if columns:
                    num = columns[0].get(
                        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}num"
                    )
                    if num and int(num) > 1:
                        diagnostics["estimated_columns"] = int(num)
            except Exception:
                pass

        diagnostics["header_footer_text"] = normalize_whitespace(
            " ".join(dict.fromkeys(header_footer_parts))
        )[:500]
        diagnostics["fonts"] = sorted(fonts)
        diagnostics["font_sizes"] = sorted(sizes)
        diagnostics["paragraph_count"] = paragraph_count
        diagnostics["bullet_count"] = bullet_count
        diagnostics["styles"] = sorted(styles)[:25]
        diagnostics["heading_styles"] = [
            style for style in styles if style.lower().startswith("heading")
        ]

        text = normalize_whitespace("\n\n".join(parts))
        if not text:
            raise DocumentExtractionError("El DOCX no contiene texto legible.")

        if diagnostics["has_images"]:
            warnings.append(
                "Se detectaron imágenes en el DOCX. Si contienen texto, ese contenido "
                "no será visible para un ATS."
            )
        if diagnostics["estimated_columns"] > 1:
            warnings.append(
                "El documento usa varias columnas. Muchos ATS leen el contenido en un "
                "orden incorrecto."
            )

        diagnostics.update(
            {
                "characters": len(text),
                "words": word_count(text),
                "text_per_page": round(len(text) / max(1, len(document.sections))),
            }
        )
        return ExtractionResult(
            text=text,
            method="docx_text",
            page_count=max(1, len(document.sections)),
            diagnostics=diagnostics,
            warnings=warnings,
        )

    # ------------------------------------------------------------- Utilidad
    @staticmethod
    def analyze_text_quality(text: str) -> dict[str, Any]:
        lines = [line for line in text.splitlines() if line.strip()]
        words = word_count(text)
        return {
            "characters": len(text),
            "words": words,
            "lines": len(lines),
            "avg_line_length": round(len(text) / max(1, len(lines)), 1),
            "empty": not text.strip(),
        }
