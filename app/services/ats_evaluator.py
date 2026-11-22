"""Evaluador de compatibilidad con sistemas ATS.

Analiza estructura, legibilidad, fechas, contacto y palabras clave. La
puntuación es orientativa: ningún análisis puede garantizar el resultado en un
ATS real, porque cada empresa configura el suyo de forma distinta.
"""

from __future__ import annotations

import re
from typing import Any

from app.config.constants import SCORE_DISCLAIMER
from app.services.evaluation_models import CriterionResult, DimensionResult
from app.services.evaluation_utils import offer_keyword_list
from app.utils.dates import date_format_consistency
from app.utils.text import extract_tech_keywords, keyword_coverage, word_count

_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF]"
)


def _severity(ratio: float) -> str:
    if ratio >= 0.85:
        return "info"
    if ratio >= 0.6:
        return "medium"
    if ratio >= 0.35:
        return "high"
    return "critical"


class ATSEvaluator:
    dimension = "ATS"

    def evaluate(
        self,
        raw_text: str,
        content: dict[str, Any],
        diagnostics: dict[str, Any] | None = None,
        offer_requirements: list[dict[str, Any]] | None = None,
        offer_text: str = "",
        offer_keywords: list[str] | None = None,
    ) -> DimensionResult:
        diagnostics = diagnostics or {}
        criteria: list[CriterionResult] = []
        missing: list[str] = []
        limitations: list[str] = [SCORE_DISCLAIMER]
        personal = content.get("personal") or {}
        experience = content.get("experience") or []
        section_order = set(content.get("section_order") or [])
        words = word_count(raw_text)
        keywords = offer_keyword_list(offer_requirements, offer_text, offer_keywords)

        # 1. Estructura documental (20)
        structure = 20.0
        issues: list[str] = []
        if diagnostics.get("has_tables"):
            structure -= 4
            issues.append("tablas")
        if int(diagnostics.get("estimated_columns", 1) or 1) > 1:
            structure -= 6
            issues.append("varias columnas")
        if diagnostics.get("header_footer_text"):
            structure -= 3
            issues.append("texto en encabezado/pie")
        if diagnostics.get("has_images") and diagnostics.get("text_in_images"):
            structure -= 4
            issues.append("texto dentro de imágenes")
        if not section_order and not (experience and content.get("education")):
            structure -= 6
            issues.append("encabezados no convencionales")
        if int(diagnostics.get("fonts_count", 0) or 0) > 3:
            structure -= 2
            issues.append("exceso de tipografías")
        if _EMOJI_RE.search(raw_text):
            structure -= 1
            issues.append("iconos o símbolos")
        if words < 150:
            structure -= 4
            issues.append("contenido muy breve")
        structure = max(0.0, min(20.0, structure))
        criteria.append(
            CriterionResult(
                criterion="Estructura documental",
                score=structure,
                max_score=20,
                severity=_severity(structure / 20),
                explanation=(
                    "La estructura es de una sola columna y sin elementos que dificulten "
                    "la extracción." if not issues else
                    "Se detectaron elementos que pueden afectar la lectura automática: "
                    + ", ".join(issues) + "."
                ),
                evidence=(
                    f"Tablas: {diagnostics.get('table_count', 0)}; "
                    f"columnas estimadas: {diagnostics.get('estimated_columns', 1)}; "
                    f"imágenes: {diagnostics.get('image_count', 0)}."
                ),
                recommendation=(
                    "Use una sola columna, sin tablas ni cuadros de texto, con encabezados "
                    "convencionales y todo el contenido en el cuerpo del documento."
                    if issues else None
                ),
            )
        )

        # 2. Encabezados convencionales (15)
        core_sections = {
            "perfil": bool(str(content.get("summary") or "").strip()),
            "experiencia": bool(experience),
            "educacion": bool(content.get("education")),
            "competencias_tecnicas": bool(
                (content.get("skills") or {}).get("technical")
            ),
        }
        found_sections = sum(1 for present in core_sections.values() if present)
        heading_score = 15.0 * found_sections / len(core_sections)
        missing_sections = [name for name, present in core_sections.items() if not present]
        if missing_sections:
            missing.extend(
                {
                    "perfil": "Perfil profesional",
                    "experiencia": "Experiencia profesional",
                    "educacion": "Educación",
                    "competencias_tecnicas": "Competencias técnicas",
                }[name]
                for name in missing_sections
            )
        criteria.append(
            CriterionResult(
                criterion="Encabezados y secciones estándar",
                score=heading_score,
                max_score=15,
                severity=_severity(heading_score / 15),
                explanation=(
                    f"Se identificaron {found_sections} de 4 secciones esenciales."
                    + (" Faltan: " + ", ".join(missing_sections) + "." if missing_sections else "")
                ),
                evidence=", ".join(
                    f"{name}: {'sí' if present else 'no'}"
                    for name, present in core_sections.items()
                ),
                recommendation=(
                    "Incluya las secciones faltantes con títulos estándar: Perfil, "
                    "Experiencia profesional, Educación y Competencias."
                    if missing_sections else None
                ),
            )
        )

        # 3. Legibilidad y extracción (15)
        if words >= 350:
            readability = 15.0
        elif words >= 250:
            readability = 12.0
        elif words >= 150:
            readability = 8.0
        elif words >= 80:
            readability = 4.0
        else:
            readability = 1.0
        readability_notes: list[str] = []
        method = str(diagnostics.get("extraction_method") or diagnostics.get("method") or "")
        if diagnostics.get("ocr_used"):
            readability -= 3
            readability_notes.append("texto obtenido por OCR")
        if diagnostics.get("avg_line_length") and float(diagnostics["avg_line_length"]) > 160:
            readability -= 2
            readability_notes.append("líneas muy densas")
        bullets = sum(len(entry.get("bullets") or []) for entry in experience)
        if bullets < 4:
            readability -= 2
            readability_notes.append("pocas viñetas")
        readability = max(0.0, min(15.0, readability))
        criteria.append(
            CriterionResult(
                criterion="Legibilidad y extracción de texto",
                score=readability,
                max_score=15,
                severity=_severity(readability / 15),
                explanation=(
                    f"El texto extraído contiene {words} palabras."
                    + (" Observaciones: " + ", ".join(readability_notes) + "." if readability_notes else "")
                ),
                recommendation=(
                    "Aumente la claridad con viñetas breves y verifique que el PDF tenga "
                    "texto seleccionable (no una imagen escaneada)."
                    if readability < 12 else None
                ),
            )
        )

        # 4. Consistencia de fechas (15)
        dated_entries = [
            entry for entry in experience
            if entry.get("start_date") and entry.get("end_date")
        ]
        all_date_tokens: list[str] = []
        for entry in experience:
            if entry.get("start_date"):
                all_date_tokens.append(str(entry["start_date"]))
            if entry.get("end_date"):
                all_date_tokens.append(str(entry["end_date"]))
        if not experience:
            date_score = 0.0
            date_explanation = "No se pudo identificar experiencia con periodos legibles."
            missing.append("Fechas de experiencia profesional")
            date_recommendation = (
                "Incluya cada puesto con el formato 'Mes AAAA – Mes AAAA' o 'AAAA – AAAA'."
            )
        else:
            ratio = len(dated_entries) / len(experience)
            date_score = 15.0 * ratio
            consistent, formats = date_format_consistency(all_date_tokens)
            if not consistent:
                date_score = max(0.0, date_score - 3)
            date_explanation = (
                f"{len(dated_entries)} de {len(experience)} puestos tienen fecha de inicio y fin. "
                + (
                    "Formatos detectados: " + ", ".join(formats) + "."
                    if formats else "No se detectaron formatos de fecha."
                )
            )
            if not consistent:
                date_explanation += " Se mezclan formatos de fecha."
            date_recommendation = (
                "Unifique el formato de fechas en todo el CV y evite dejar periodos sin explicar."
                if date_score < 13 else None
            )
        criteria.append(
            CriterionResult(
                criterion="Consistencia de fechas",
                score=date_score,
                max_score=15,
                severity=_severity(date_score / 15),
                explanation=date_explanation,
                recommendation=date_recommendation,
            )
        )

        # 5. Datos de contacto (10)
        contact_score = 0.0
        contact_found = []
        if personal.get("email"):
            contact_score += 4
            contact_found.append("correo")
        if personal.get("phone"):
            contact_score += 3
            contact_found.append("teléfono")
        if personal.get("linkedin"):
            contact_score += 2
            contact_found.append("LinkedIn")
        if personal.get("location"):
            contact_score += 1
            contact_found.append("ubicación")
        if not personal.get("email"):
            missing.append("Correo electrónico de contacto")
        if not personal.get("phone"):
            missing.append("Teléfono de contacto")
        criteria.append(
            CriterionResult(
                criterion="Datos de contacto",
                score=min(10.0, contact_score),
                max_score=10,
                severity=_severity(contact_score / 10),
                explanation=(
                    "Datos detectados: " + ", ".join(contact_found) + "."
                    if contact_found else "No se detectaron datos de contacto legibles."
                ),
                recommendation=(
                    "Incluya correo, teléfono y LinkedIn en el cuerpo del documento, "
                    "no dentro de imágenes o encabezados."
                    if contact_score < 8 else None
                ),
            )
        )

        # 6. Palabras clave (15)
        keyword_missing: list[str] = []
        if keywords:
            present, keyword_missing = keyword_coverage(raw_text, keywords)
            coverage = len(present) / max(1, len(keywords))
            keyword_score = 15.0 * coverage
            keyword_explanation = (
                f"Se encontraron {len(present)} de {len(keywords)} palabras clave "
                "relevantes de la oferta."
            )
            if keyword_missing:
                keyword_explanation += " Faltan: " + ", ".join(keyword_missing[:8]) + "."
                missing.extend(f"Palabra clave: {item}" for item in keyword_missing[:8])
            keyword_recommendation = (
                "Incorpore las palabras clave que realmente correspondan a su experiencia; "
                "no agregue tecnologías que no pueda demostrar."
                if keyword_missing else None
            )
        else:
            tech = extract_tech_keywords(raw_text)
            if len(tech) >= 8:
                keyword_score = 15.0
            elif len(tech) >= 5:
                keyword_score = 12.0
            elif len(tech) >= 3:
                keyword_score = 8.0
            elif tech:
                keyword_score = 4.0
            else:
                keyword_score = 0.0
            keyword_explanation = (
                f"No se proporcionó una oferta. Se detectaron {len(tech)} tecnologías "
                "o herramientas explícitas en el CV."
            )
            keyword_recommendation = (
                "Adjunte una oferta laboral para calcular la coincidencia real de palabras clave."
                if not tech else None
            )
        criteria.append(
            CriterionResult(
                criterion="Palabras clave y coincidencia con la oferta",
                score=keyword_score,
                max_score=15,
                severity=_severity(keyword_score / 15),
                explanation=keyword_explanation,
                recommendation=keyword_recommendation,
            )
        )

        # 7. Formato compatible (10)
        format_score = 10.0
        format_issues = []
        file_type = str(diagnostics.get("file_type", "")).lower()
        if file_type not in {"pdf", "docx"}:
            format_score -= 3
            format_issues.append("formato no estándar")
        if diagnostics.get("has_tables"):
            format_score -= 2
            format_issues.append("tablas")
        if int(diagnostics.get("estimated_columns", 1) or 1) > 1:
            format_score -= 2
            format_issues.append("columnas")
        if int(diagnostics.get("fonts_count", 0) or 0) > 3:
            format_score -= 1
            format_issues.append("tipografías múltiples")
        if diagnostics.get("has_images") and not diagnostics.get("ocr_used"):
            format_score -= 1
            format_issues.append("imágenes")
        format_score = max(0.0, min(10.0, format_score))
        criteria.append(
            CriterionResult(
                criterion="Formato compatible con ATS",
                score=format_score,
                max_score=10,
                severity=_severity(format_score / 10),
                explanation=(
                    "El formato es compatible con la extracción automática."
                    if not format_issues else
                    "Aspectos a corregir: " + ", ".join(format_issues) + "."
                ),
                recommendation=(
                    "Exporte el CV en PDF con texto seleccionable o DOCX, sin tablas, "
                    "columnas ni gráficos." if format_issues else None
                ),
            )
        )

        score = round(sum(item.score for item in criteria), 1)
        strengths = [
            f"{item.criterion}: {item.status.lower()}"
            for item in criteria if item.ratio >= 0.85
        ]
        weaknesses = [
            f"{item.criterion}: {item.explanation}"
            for item in criteria if item.ratio < 0.6
        ]
        if diagnostics.get("ocr_used"):
            limitations.append(
                "El texto se obtuvo mediante OCR; pueden existir errores de reconocimiento "
                "que afecten la puntuación."
            )
        if not keywords:
            limitations.append(
                "Sin oferta laboral asociada, la coincidencia de palabras clave se evalúa "
                "solo por presencia de tecnologías en el CV."
            )
        if not diagnostics:
            limitations.append(
                "No se dispone de metadatos del documento; parte del análisis estructural "
                "es limitado."
            )
        if _EMOJI_RE.search(raw_text):
            weaknesses.append(
                "Se detectaron iconos o símbolos que pueden sustituir información textual."
            )

        confidence = self._confidence(words, diagnostics, bool(keywords))
        summary = (
            f"Compatibilidad ATS estimada: {score:.1f}/100. "
            + (
                "Los principales puntos de mejora son: "
                + "; ".join(item.criterion.lower() for item in criteria if item.ratio < 0.6)
                + "."
                if any(item.ratio < 0.6 for item in criteria)
                else "No se detectaron problemas estructurales graves."
            )
        )
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            criteria=criteria,
            strengths=strengths,
            weaknesses=weaknesses,
            missing=list(dict.fromkeys(missing)),
            limitations=limitations,
            confidence=confidence,
            summary=summary,
        )

    @staticmethod
    def _confidence(words: int, diagnostics: dict[str, Any], has_offer: bool) -> str:
        points = 0
        if words >= 300:
            points += 1
        if words >= 500:
            points += 1
        if not diagnostics.get("ocr_used"):
            points += 1
        if diagnostics:
            points += 1
        if has_offer:
            points += 1
        if points >= 4:
            return "alta"
        if points >= 2:
            return "media"
        return "baja"
