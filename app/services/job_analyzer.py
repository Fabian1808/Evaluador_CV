"""Analizador heurístico de ofertas laborales.

Extrae puesto, empresa, requisitos y responsabilidades sin depender de IA. La IA
local puede enriquecer el resultado cuando está disponible, pero el análisis
base funciona sin conexión.
"""

from __future__ import annotations

import re
from typing import Any

from app.utils.text import (
    extract_tech_keywords,
    normalize_for_match,
    normalize_whitespace,
    sentences,
    truncate,
    word_count,
)

_REQUIREMENT_HINTS = (
    "experiencia", "conocimiento", "conocimientos", "manejo", "dominio",
    "formación", "formacion", "titulación", "titulacion", "titulo", "título",
    "estudios", "certificación", "certificacion", "inglés", "ingles", "idioma",
    "años", "año", "deseable", "requisito", "imprescindible", "excluyente",
    "capacidad", "habilidad", "competencia", "orientado", "proactivo",
)
_RESPONSIBILITY_HINTS = (
    "realizar", "gestionar", "analizar", "desarrollar", "diseñar", "disenar",
    "coordinar", "elaborar", "administrar", "supervisar", "automatizar",
    "implementar", "mantener", "construir", "crear", "optimizar", "apoyar",
    "colaborar", "participar", "responsable de", "encargado de", "funciones",
)
_SECTION_HEADINGS = {
    "requisitos": "requirements",
    "requisitos obligatorios": "requirements",
    "requisitos deseables": "desirable",
    "deseables": "desirable",
    "funciones": "responsibilities",
    "funciones del puesto": "responsibilities",
    "responsabilidades": "responsibilities",
    "principales responsabilidades": "responsibilities",
    "descripción del puesto": "description",
    "descripcion del puesto": "description",
    "descripción": "description",
    "descripcion": "description",
    "beneficios": "benefits",
    "ofrecemos": "benefits",
    "requerimientos": "requirements",
    "perfil requerido": "requirements",
    "lo que buscamos": "requirements",
    "about the role": "description",
    "requirements": "requirements",
    "responsibilities": "responsibilities",
}
_AREA_KEYWORDS = {
    "Data Analytics": ("data analytics", "analista de datos", "análisis de datos", "analisis de datos", "datos"),
    "Business Intelligence": ("business intelligence", "power bi", "bi ", "inteligencia de negocio"),
    "Automatización": ("automatización", "automatizacion", "rpa", "power automate"),
    "Tecnología": ("tecnología", "tecnologia", "software", "desarrollador", "developer", "ti "),
    "Finanzas": ("finanzas", "financiero", "contabilidad", "contable"),
    "Marketing": ("marketing", "comercial", "ventas", "growth"),
    "Recursos Humanos": ("recursos humanos", "rrhh", "talento humano"),
    "Operaciones": ("operaciones", "logística", "logistica", "producción", "produccion"),
}


class JobAnalyzer:
    """Extrae una estructura verificable de la oferta laboral."""

    def analyze(self, offer_text: str, title_hint: str = "", company_hint: str = "") -> dict[str, Any]:
        text = normalize_whitespace(offer_text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = title_hint.strip() or self._extract_title(lines)
        company = company_hint.strip() or self._extract_company(lines, title)
        area = self._extract_area(text)
        requirements, responsibilities = self._extract_sections(lines)

        if not requirements:
            requirements = self._fallback_requirements(lines)

        # Deduplicar por texto normalizado.
        seen: set[str] = set()
        unique_requirements: list[dict[str, Any]] = []
        for item in requirements:
            key = normalize_for_match(item["text"])
            if key and key not in seen and len(key) >= 5:
                seen.add(key)
                unique_requirements.append(item)

        tech_keywords = extract_tech_keywords(text)
        return {
            "title": title,
            "company": company,
            "area": area,
            "summary": truncate(lines[0] if lines else "", 300),
            "requirements": unique_requirements[:30],
            "responsibilities": list(dict.fromkeys(responsibilities))[:20],
            "keywords": tech_keywords,
            "mandatory_count": sum(
                1 for item in unique_requirements if item["requirement_type"] == "mandatory"
            ),
            "desirable_count": sum(
                1 for item in unique_requirements if item["requirement_type"] == "desirable"
            ),
            "word_count": word_count(text),
            "source": "heuristic",
        }

    # ------------------------------------------------------------ encabezado
    @staticmethod
    def _extract_title(lines: list[str]) -> str:
        for line in lines[:12]:
            match = re.search(
                r"^(?:puesto|cargo|título|titulo|vacante|posición|posicion|role)\s*[:\-]\s*(.+)$",
                line, re.IGNORECASE,
            )
            if match:
                return truncate(match.group(1), 120)
        for line in lines[:5]:
            normalized = normalize_for_match(line)
            if (
                3 <= len(line.split()) <= 12
                and len(line) <= 110
                and not normalized.startswith(("buscamos", "empresa", "descripción", "descripcion", "sobre"))
                and "@" not in line
            ):
                return truncate(line, 120)
        return ""

    @staticmethod
    def _extract_company(lines: list[str], title: str) -> str:
        for line in lines[:15]:
            match = re.search(
                r"^(?:empresa|compañía|compania|organización|organizacion|company)\s*[:\-]\s*(.+)$",
                line, re.IGNORECASE,
            )
            if match:
                return truncate(match.group(1), 120)
        for line in lines[:8]:
            match = re.search(
                r"\b(?:en|para)\s+([A-ZÁÉÍÓÚÑ][\w&.\- ]{2,60}?)(?:\s*[,.]|\s+estamos|\s+buscamos|$)",
                line,
            )
            if match:
                candidate = match.group(1).strip()
                if candidate.lower() != title.lower() and len(candidate.split()) <= 6:
                    return candidate
        return ""

    @staticmethod
    def _extract_area(text: str) -> str:
        normalized = normalize_for_match(text)
        best = ""
        for area, keywords in _AREA_KEYWORDS.items():
            if any(normalize_for_match(keyword) in normalized for keyword in keywords):
                best = area
                break
        return best

    # -------------------------------------------------------- secciones
    def _extract_sections(
        self, lines: list[str]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        requirements: list[dict[str, Any]] = []
        responsibilities: list[str] = []
        current_section = ""
        for raw_line in lines:
            line = re.sub(r"^\s*(?:[•▪◦●○‣·*\-–—]|\d+[.)])\s*", "", raw_line).strip()
            if not line:
                continue
            normalized = normalize_for_match(line).strip(" :")
            if normalized in _SECTION_HEADINGS and len(line) <= 70:
                current_section = _SECTION_HEADINGS[normalized]
                continue

            if current_section == "responsibilities":
                if self._is_responsibility(line):
                    responsibilities.append(truncate(line, 260))
                continue
            if current_section in {"benefits", "description"}:
                # En descripción aún pueden aparecer requisitos explícitos.
                if current_section == "benefits":
                    continue

            if current_section == "desirable":
                requirements.append(self._make_requirement(line, "desirable"))
                continue

            if current_section == "requirements":
                requirements.append(self._make_requirement(line, "mandatory"))
                continue

            # Sin sección activa: detección por contenido.
            if self._is_responsibility(line):
                responsibilities.append(truncate(line, 260))
            elif self._is_requirement(line):
                req_type = "desirable" if self._is_desirable(line) else "mandatory"
                requirements.append(self._make_requirement(line, req_type))
        return requirements, responsibilities

    def _fallback_requirements(self, lines: list[str]) -> list[dict[str, Any]]:
        result = []
        for line in lines:
            cleaned = re.sub(r"^\s*(?:[•▪◦●○‣·*\-–—]|\d+[.)])\s*", "", line).strip()
            if self._is_requirement(cleaned):
                result.append(
                    self._make_requirement(
                        cleaned, "desirable" if self._is_desirable(cleaned) else "mandatory"
                    )
                )
        return result

    @staticmethod
    def _is_requirement(line: str) -> bool:
        normalized = normalize_for_match(line)
        if len(line.split()) < 2 or len(line) > 400:
            return False
        if extract_tech_keywords(line):
            return True
        return any(hint in normalized for hint in _REQUIREMENT_HINTS)

    @staticmethod
    def _is_responsibility(line: str) -> bool:
        normalized = normalize_for_match(line).strip()
        if len(line.split()) < 3:
            return False
        if any(normalized.startswith(hint) for hint in _RESPONSIBILITY_HINTS):
            return True
        return False

    @staticmethod
    def _is_desirable(line: str) -> bool:
        normalized = normalize_for_match(line)
        return any(
            token in normalized
            for token in ("deseable", "plus", "valorable", "no excluyente", "no imprescindible")
        )

    def _make_requirement(self, text: str, req_type: str) -> dict[str, Any]:
        cleaned = text.strip(" .;:-")
        category = self._category(cleaned)
        keywords = self._keywords(cleaned)
        return {
            "text": truncate(cleaned, 400),
            "requirement_type": req_type,
            "category": category,
            "keywords": keywords,
            "weight": 1.0,
        }

    @staticmethod
    def _category(text: str) -> str:
        normalized = normalize_for_match(text)
        if extract_tech_keywords(text):
            return "herramienta"
        if any(lang in normalized for lang in ("inglés", "ingles", "idioma", "español", "frances", "francés")):
            return "idioma"
        if any(word in normalized for word in ("certificación", "certificacion", "certificado")):
            return "certificacion"
        if any(word in normalized for word in ("titulación", "titulacion", "titulo", "título", "licenciatura", "ingeniería", "ingenieria", "formación", "formacion", "estudios")):
            return "formacion"
        if any(word in normalized for word in ("años", "experiencia", "trayectoria")):
            return "experiencia"
        return "competencia"

    @staticmethod
    def _keywords(text: str) -> list[str]:
        keywords = list(extract_tech_keywords(text))
        normalized = normalize_for_match(text)
        for language in ("inglés", "ingles", "español", "espanol", "francés", "frances", "portugués", "portugues"):
            if language in normalized:
                keywords.append(language)
        for degree in ("licenciatura", "ingeniería", "ingenieria", "técnico", "tecnico", "maestría", "maestria", "mba", "bachiller"):
            if degree in normalized:
                keywords.append(degree)
        # Añade una frase corta de contexto si no hay tecnología reconocida.
        if not keywords:
            tokens = [
                token for token in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}", text)
                if normalize_for_match(token) not in _STOPWORDS_REQUIREMENT
            ]
            keywords.extend(tokens[:4])
        seen = set()
        result = []
        for keyword in keywords:
            key = normalize_for_match(keyword)
            if key not in seen:
                seen.add(key)
                result.append(keyword)
        return result[:8]

    @staticmethod
    def _sentences(line: str) -> list[str]:
        return sentences(line)


_STOPWORDS_REQUIREMENT = {
    "experiencia", "conocimiento", "conocimientos", "manejo", "dominio",
    "deseable", "requisito", "requisitos", "años", "año", "formación",
    "formacion", "título", "titulo", "estudios", "capacidad", "habilidad",
    "habilidades", "trabajo", "equipo", "puesto", "cargo", "funciones",
    "responsabilidades", "persona", "profesional", "empresa", "área", "area",
    "nivel", "avanzado", "intermedio", "básico", "basico", "alto", "alta",
    "buscamos", "requerimos", "debe", "deberá", "debera", "tener", "contar",
}
