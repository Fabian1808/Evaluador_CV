"""Matriz de compatibilidad CV ↔ oferta laboral.

Cada requisito se clasifica con evidencia textual. No se inventa información
para elevar el porcentaje de coincidencia.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.evaluation_models import CompatibilityResult, RequirementMatch
from app.services.evaluation_utils import (
    contains_keyword,
    experience_sentences,
    section_contexts,
)
from app.utils.dates import parse_date_token, years_of_experience
from app.utils.text import (
    extract_tech_keywords,
    has_metric,
    normalize_for_match,
    starts_with_action_verb,
    tokenize,
    truncate,
)

_STATUS_SCORE = {
    "DEMOSTRADO": 1.0,
    "PARCIALMENTE_DEMOSTRADO": 0.6,
    "MENCIONADO_SIN_EVIDENCIA": 0.25,
    "NO_IDENTIFICADO": 0.0,
    "PENDIENTE_CONFIRMACION": None,
}
_GENERIC_REQUIREMENT_WORDS = {
    "experiencia", "conocimiento", "conocimientos", "manejo", "dominio",
    "deseable", "requisito", "requisitos", "años", "año", "formación",
    "formacion", "título", "titulo", "estudios", "capacidad", "habilidad",
    "habilidades", "trabajo", "equipo", "puesto", "cargo", "funciones",
    "responsabilidades", "persona", "profesional", "empresa", "área", "area",
    "nivel", "avanzado", "intermedio", "básico", "basico", "alto", "alta",
}
_LANGUAGE_HINTS = (
    "inglés", "ingles", "español", "espanol", "francés", "frances", "alemán",
    "aleman", "portugués", "portugues", "italiano", "mandarín", "mandarin",
    "japonés", "japones",
)
_DEGREE_HINTS = (
    "licenciatura", "ingeniería", "ingenieria", "técnico", "tecnico",
    "maestría", "maestria", "máster", "master", "mba", "bachiller", "doctorado",
    "administración", "administracion", "contabilidad", "economía", "economia",
)


class CompatibilityEvaluator:
    def evaluate(
        self,
        content: dict[str, Any],
        requirements: list[dict[str, Any]],
        offer_text: str = "",
    ) -> CompatibilityResult:
        contexts = section_contexts(content)
        experience_items = experience_sentences(content)
        periods = [
            (str(entry.get("start_date", "")), str(entry.get("end_date", "")))
            for entry in content.get("experience") or []
            if entry.get("start_date") or entry.get("end_date")
        ]
        total_years = years_of_experience(periods)
        matches: list[RequirementMatch] = []
        missing_keywords: list[str] = []

        for requirement in requirements:
            text = str(requirement.get("text", "")).strip()
            if not text:
                continue
            req_type = str(requirement.get("requirement_type", "mandatory"))
            keywords = self.keywords_for_requirement(
                text, requirement.get("keywords") or []
            )
            match = self._match_requirement(
                text, req_type, keywords, experience_items, contexts, total_years
            )
            matches.append(match)
            missing_keywords.extend(match.missing_keywords)

        if not matches:
            return CompatibilityResult(
                score=0.0,
                mandatory_score=None,
                desirable_score=None,
                matches=[],
                limitations=[
                    "No hay requisitos estructurados en la oferta. Analice la oferta "
                    "nuevamente o agregue requisitos manualmente."
                ],
                confidence="baja",
            )

        mandatory = [m for m in matches if m.requirement_type == "mandatory"]
        desirable = [m for m in matches if m.requirement_type != "mandatory"]
        mandatory_score = self._average(mandatory)
        desirable_score = self._average(desirable)

        if mandatory_score is not None and desirable_score is not None:
            score = mandatory_score * 0.7 + desirable_score * 0.3
        elif mandatory_score is not None:
            score = mandatory_score
        elif desirable_score is not None:
            score = desirable_score
        else:
            score = 0.0

        strengths = [
            f"Requisito demostrado: {truncate(m.requirement_text, 120)}"
            for m in matches if m.status == "DEMOSTRADO"
        ][:10]
        weaknesses = [
            f"Requisito no identificado: {truncate(m.requirement_text, 120)}"
            for m in matches if m.status == "NO_IDENTIFICADO"
        ][:10]
        limitations = [
            "La compatibilidad es una estimación documental, no una probabilidad de "
            "contratación ni una garantía de superar filtros ATS.",
            "Los requisitos se extraen del texto de la oferta y pueden requerir revisión "
            "manual si la vacante está mal redactada.",
        ]
        if not offer_text.strip():
            limitations.append("No se analizó el texto completo de la oferta.")
        confidence = self._confidence(matches, len(experience_items))

        return CompatibilityResult(
            score=round(max(0.0, min(100.0, score * 100)), 1),
            mandatory_score=(
                round(mandatory_score * 100, 1) if mandatory_score is not None else None
            ),
            desirable_score=(
                round(desirable_score * 100, 1) if desirable_score is not None else None
            ),
            matches=matches,
            missing_keywords=list(dict.fromkeys(missing_keywords)),
            strengths=strengths,
            weaknesses=weaknesses,
            limitations=limitations,
            confidence=confidence,
        )

    # ------------------------------------------------------------ requisitos
    def keywords_for_requirement(
        self, text: str, provided: list[str] | None = None
    ) -> list[str]:
        keywords: list[str] = []
        for keyword in provided or []:
            if keyword and len(str(keyword).strip()) >= 2:
                keywords.append(str(keyword).strip())
        keywords.extend(extract_tech_keywords(text))
        normalized = normalize_for_match(text)
        for language in _LANGUAGE_HINTS:
            if language in normalized:
                keywords.append(language)
        for degree in _DEGREE_HINTS:
            if degree in normalized:
                keywords.append(degree)

        # Frase técnica después de "en" / "de" (ej. "en análisis de datos").
        phrase_match = re.search(
            r"\b(?:en|de|sobre)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9+#./ -]{4,70})",
            text, re.IGNORECASE,
        )
        if phrase_match:
            phrase = phrase_match.group(1).strip(" .,;")
            if len(phrase.split()) <= 6 and not phrase.lower().startswith(
                ("la ", "el ", "los ", "las ")
            ):
                keywords.append(phrase)

        if not keywords:
            tokens = [
                token for token in tokenize(text)
                if len(token) >= 4
                and normalize_for_match(token) not in _GENERIC_REQUIREMENT_WORDS
            ]
            keywords.extend(tokens[:4])

        seen: set[str] = set()
        result = []
        for keyword in keywords:
            key = normalize_for_match(keyword)
            if key and key not in seen and key not in _GENERIC_REQUIREMENT_WORDS:
                seen.add(key)
                result.append(keyword)
        return result[:8]

    def _match_requirement(
        self,
        text: str,
        req_type: str,
        keywords: list[str],
        experience_items: list[tuple[str, str]],
        contexts: dict[str, str],
        total_years: float,
    ) -> RequirementMatch:
        if not keywords:
            return RequirementMatch(
                requirement_text=text,
                requirement_type=req_type,
                status="PENDIENTE_CONFIRMACION",
                explanation=(
                    "El requisito es demasiado general o no contiene términos verificables. "
                    "Debe confirmarse manualmente."
                ),
                score=None,
            )

        # Requisito de años de experiencia.
        years_match = re.search(r"(\d+)\s*(?:\+)?\s*años?", normalize_for_match(text))
        if years_match and any(
            word in normalize_for_match(text) for word in ("experiencia", "años", "anos")
        ):
            required = int(years_match.group(1))
            if total_years >= required:
                return RequirementMatch(
                    requirement_text=text,
                    requirement_type=req_type,
                    status="DEMOSTRADO",
                    explanation=(
                        f"La trayectoria documentada suma aproximadamente {total_years:g} años, "
                        f"frente a {required} solicitados."
                    ),
                    evidence=f"Trayectoria calculada a partir de las fechas: {total_years:g} años.",
                    matched_keywords=[f"{required} años"],
                    score=1.0,
                )
            if total_years > 0:
                return RequirementMatch(
                    requirement_text=text,
                    requirement_type=req_type,
                    status="PARCIALMENTE_DEMOSTRADO",
                    explanation=(
                        f"Se documentan {total_years:g} años y el requisito pide {required}."
                    ),
                    evidence="Duración estimada con las fechas del CV.",
                    matched_keywords=[f"{required} años"],
                    missing_keywords=[f"{required - total_years:g} años adicionales"],
                    score=0.6,
                )
            return RequirementMatch(
                requirement_text=text,
                requirement_type=req_type,
                status="NO_IDENTIFICADO",
                explanation="No se pudieron calcular años de experiencia a partir de fechas legibles.",
                missing_keywords=keywords,
                score=0.0,
            )

        # Requisito de formación.
        if any(degree in normalize_for_match(text) for degree in _DEGREE_HINTS):
            education_text = contexts.get("education", "")
            if education_text.strip():
                return RequirementMatch(
                    requirement_text=text,
                    requirement_type=req_type,
                    status="DEMOSTRADO",
                    explanation="El CV incluye formación académica relacionada.",
                    evidence=truncate(education_text, 240),
                    matched_keywords=keywords,
                    score=1.0,
                )
            return RequirementMatch(
                requirement_text=text,
                requirement_type=req_type,
                status="NO_IDENTIFICADO",
                explanation="No se identificó formación académica en el CV.",
                missing_keywords=keywords,
                score=0.0,
            )

        strong: list[str] = []
        weak: list[str] = []
        mentioned: list[str] = []
        absent: list[str] = []
        evidence_quote = ""

        for keyword in keywords:
            strong_sentence = None
            weak_sentence = None
            for sentence, _label in experience_items:
                if contains_keyword(sentence, keyword):
                    if starts_with_action_verb(sentence) or has_metric(sentence):
                        strong_sentence = sentence
                        break
                    weak_sentence = weak_sentence or sentence
            if strong_sentence:
                strong.append(keyword)
                evidence_quote = evidence_quote or strong_sentence
                continue
            if weak_sentence:
                weak.append(keyword)
                evidence_quote = evidence_quote or weak_sentence
                continue
            mentioned_context = ""
            for key in ("skills", "summary", "education", "certifications", "projects"):
                if contains_keyword(contexts.get(key, ""), keyword):
                    mentioned_context = contexts.get(key, "")
                    break
            if mentioned_context:
                mentioned.append(keyword)
                evidence_quote = evidence_quote or truncate(mentioned_context, 240)
            else:
                absent.append(keyword)

        if len(absent) == len(keywords):
            status = "NO_IDENTIFICADO"
            explanation = "No se encontró ninguna mención de los términos del requisito."
        elif strong and not absent:
            status = "DEMOSTRADO"
            explanation = (
                "El requisito aparece en la experiencia con acción o resultado verificable."
            )
        elif strong or weak:
            status = "PARCIALMENTE_DEMOSTRADO"
            explanation = (
                "Hay evidencia parcial: el requisito aparece en la experiencia, pero no "
                "todos sus términos están respaldados o falta contexto de resultado."
            )
        elif mentioned:
            status = "MENCIONADO_SIN_EVIDENCIA"
            explanation = (
                "El requisito solo aparece en habilidades, perfil o formación; no se "
                "encontró evidencia de aplicación profesional."
            )
        else:
            status = "PARCIALMENTE_DEMOSTRADO"
            explanation = "La evidencia es incompleta."

        return RequirementMatch(
            requirement_text=text,
            requirement_type=req_type,
            status=status,
            explanation=explanation,
            evidence=truncate(evidence_quote, 300) if evidence_quote else "",
            matched_keywords=list(dict.fromkeys(strong + weak + mentioned)),
            missing_keywords=list(dict.fromkeys(absent)),
            score=_STATUS_SCORE[status],
        )

    @staticmethod
    def _average(matches: list[RequirementMatch]) -> float | None:
        scores = [m.score for m in matches if m.score is not None]
        if not scores:
            return None
        return sum(scores) / len(scores)

    @staticmethod
    def _confidence(matches: list[RequirementMatch], experience_items: int) -> str:
        verifiable = sum(1 for m in matches if m.status != "PENDIENTE_CONFIRMACION")
        if verifiable >= 5 and experience_items >= 6:
            return "alta"
        if verifiable >= 2:
            return "media"
        return "baja"
