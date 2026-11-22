"""Evaluador técnico basado en evidencia textual.

Una mención en la lista de habilidades no equivale a dominio. Para cada
competencia se busca evidencia en experiencia y proyectos; solo se considera
demostrada cuando aparece en un contexto de acción o resultado.
"""

from __future__ import annotations

from typing import Any

from app.services.evaluation_models import CriterionResult, DimensionResult
from app.services.evaluation_utils import (
    contains_keyword,
    experience_sentences,
    section_contexts,
)
from app.utils.text import (
    has_metric,
    normalize_for_match,
    starts_with_action_verb,
    truncate,
)

STATUS_DEMONSTRATED = "DEMOSTRADO"
STATUS_PARTIAL = "PARCIALMENTE_DEMOSTRADO"
STATUS_MENTIONED = "MENCIONADO_SIN_EVIDENCIA"
STATUS_MISSING = "NO_IDENTIFICADO"

_SCORE_MAP = {
    STATUS_DEMONSTRATED: 100.0,
    STATUS_PARTIAL: 65.0,
    STATUS_MENTIONED: 30.0,
    STATUS_MISSING: 0.0,
}
_SEVERITY_MAP = {
    STATUS_DEMONSTRATED: "info",
    STATUS_PARTIAL: "medium",
    STATUS_MENTIONED: "high",
    STATUS_MISSING: "critical",
}


class TechnicalEvaluator:
    dimension = "TECHNICAL"

    def evaluate(
        self,
        raw_text: str,
        content: dict[str, Any],
        profile: dict[str, Any] | None = None,
    ) -> DimensionResult:
        profile = profile or {}
        competencies = self._normalize_competencies(profile.get("competencies") or [])
        contexts = section_contexts(content)
        experience_items = experience_sentences(content)
        criteria: list[CriterionResult] = []
        strengths: list[str] = []
        weaknesses: list[str] = []
        missing: list[str] = []
        limitations = [
            "La mención de una tecnología no demuestra dominio: se exige evidencia en "
            "experiencia o proyectos.",
            "La evaluación es textual y no verifica la profundidad real de los conocimientos.",
        ]

        if not competencies:
            return DimensionResult(
                dimension=self.dimension,
                score=0.0,
                criteria=[],
                weaknesses=["No hay competencias configuradas en el perfil técnico."],
                missing=["Perfil técnico con competencias"],
                limitations=limitations,
                confidence="baja",
                summary="No se pudo evaluar: el perfil técnico no tiene competencias configuradas.",
            )

        for competency in competencies:
            name = competency["name"]
            aliases = competency.get("aliases") or [name]
            status, evidence, where = self._classify(
                aliases, experience_items, contexts
            )
            score = _SCORE_MAP[status]
            if status == STATUS_DEMONSTRATED:
                strengths.append(f"{name}: evidencia en {where}.")
            elif status == STATUS_MENTIONED:
                missing.append(
                    f"{name}: aparece mencionada pero sin evidencia de uso o resultado."
                )
            elif status == STATUS_MISSING:
                weaknesses.append(f"{name}: no se encontró evidencia en el CV.")
            criteria.append(
                CriterionResult(
                    criterion=name,
                    score=score,
                    max_score=100,
                    status=status,
                    severity=_SEVERITY_MAP[status],
                    explanation=self._explanation(name, status, where),
                    evidence=truncate(evidence, 240) if evidence else None,
                    recommendation=self._recommendation(name, status),
                )
            )

        score = round(sum(item.score for item in criteria) / len(criteria), 1)
        confidence = self._confidence(len(experience_items), bool(contexts["experience"]))
        summary = (
            f"Evaluación técnica ({profile.get('name', 'perfil no especificado')}): "
            f"{score:.1f}/100. "
            f"{sum(1 for item in criteria if item.status == STATUS_DEMONSTRATED)} competencias "
            "con evidencia demostrada."
        )
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            criteria=criteria,
            strengths=strengths,
            weaknesses=weaknesses,
            missing=missing,
            limitations=limitations,
            confidence=confidence,
            summary=summary,
        )

    # ------------------------------------------------------------ interno
    @staticmethod
    def _normalize_competencies(raw: list[Any]) -> list[dict[str, Any]]:
        result = []
        for item in raw:
            if isinstance(item, str):
                result.append({"name": item, "aliases": [item]})
            elif isinstance(item, dict) and item.get("name"):
                aliases = item.get("aliases") or [item["name"]]
                result.append(
                    {
                        "name": str(item["name"]),
                        "aliases": [str(alias) for alias in aliases if str(alias).strip()],
                    }
                )
        return result

    @staticmethod
    def _classify(
        aliases: list[str],
        experience_items: list[tuple[str, str]],
        contexts: dict[str, str],
    ) -> tuple[str, str, str]:
        strong_evidence: str | None = None
        strong_where = ""
        partial_evidence: str | None = None
        partial_where = ""
        for sentence, label in experience_items:
            if any(contains_keyword(sentence, alias) for alias in aliases):
                if starts_with_action_verb(sentence) or has_metric(sentence):
                    strong_evidence = sentence
                    strong_where = label
                    break
                if partial_evidence is None:
                    partial_evidence = sentence
                    partial_where = label
        if strong_evidence:
            return STATUS_DEMONSTRATED, strong_evidence, strong_where or "experiencia"
        if partial_evidence:
            return STATUS_PARTIAL, partial_evidence, partial_where or "experiencia"

        for key, label in (
            ("summary", "perfil profesional"),
            ("skills", "lista de competencias"),
            ("education", "formación"),
            ("certifications", "certificaciones"),
            ("projects", "proyectos"),
        ):
            text = contexts.get(key, "")
            for alias in aliases:
                if contains_keyword(text, alias):
                    snippet = TechnicalEvaluator._snippet(text, alias)
                    return STATUS_MENTIONED, snippet or text[:200], label
        return STATUS_MISSING, "", ""

    @staticmethod
    def _snippet(text: str, keyword: str) -> str:
        normalized = normalize_for_match(text)
        needle = normalize_for_match(keyword)
        index = normalized.find(needle)
        if index < 0:
            return ""
        start = max(0, index - 100)
        end = min(len(text), index + len(keyword) + 100)
        return text[start:end].strip()

    @staticmethod
    def _explanation(name: str, status: str, where: str) -> str:
        if status == STATUS_DEMONSTRATED:
            return f"Se encontró evidencia de uso de {name} en {where}, con acción o resultado."
        if status == STATUS_PARTIAL:
            return f"{name} aparece en {where}, pero sin un resultado o alcance verificable."
        if status == STATUS_MENTIONED:
            return f"{name} solo aparece en {where}; no hay evidencia de aplicación práctica."
        return f"No se encontró ninguna mención de {name} en el CV."

    @staticmethod
    def _recommendation(name: str, status: str) -> str | None:
        if status == STATUS_DEMONSTRATED:
            return None
        if status == STATUS_PARTIAL:
            return (
                f"Añada en la experiencia una frase concreta sobre {name}: qué hizo, "
                "para qué área y qué resultado obtuvo (sin inventar cifras)."
            )
        if status == STATUS_MENTIONED:
            return (
                f"Incluya {name} dentro de una responsabilidad o proyecto real. Si no lo "
                "ha usado profesionalmente, muévalo a formación o retírelo."
            )
        return (
            f"Si domina {name}, documente un ejemplo de uso. Si no, no lo agregue solo "
            "para coincidir con la oferta."
        )

    @staticmethod
    def _confidence(experience_items: int, has_experience: bool) -> str:
        if experience_items >= 8 and has_experience:
            return "alta"
        if experience_items >= 3:
            return "media"
        return "baja"
