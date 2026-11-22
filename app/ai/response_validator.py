"""Validación de respuestas de IA y protección contra datos inventados."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.config.constants import ORIGIN_AI, ORIGIN_ILLUSTRATIVE
from app.core.errors import AIValidationError
from app.utils.text import extract_numbers, extract_tech_keywords, normalize_for_match


class ProposalPayload(BaseModel):
    section: str = Field(default="General", max_length=100)
    original_text: str = Field(min_length=1)
    problem: str = Field(min_length=1)
    proposed_text: str = Field(min_length=1)
    justification: str = Field(min_length=1)
    evidence: str = ""
    origin: str = ORIGIN_AI
    issues: list[str] = Field(default_factory=list)

    @field_validator("section", "problem", "justification", mode="before")
    @classmethod
    def _clean_text(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("proposed_text", mode="before")
    @classmethod
    def _clean_proposed(cls, value: Any) -> str:
        return str(value or "").strip()


class MissingInfoPayload(BaseModel):
    topic: str = Field(min_length=1, max_length=150)
    question: str = Field(min_length=1)
    why_important: str = Field(min_length=1)
    example_text: str = ""
    origin: str = ORIGIN_ILLUSTRATIVE

    @field_validator("topic", "question", "why_important", "example_text", mode="before")
    @classmethod
    def _clean(cls, value: Any) -> str:
        return str(value or "").strip()


class JobRequirementPayload(BaseModel):
    text: str = Field(min_length=1)
    requirement_type: str = "mandatory"
    category: str = "otro"
    keywords: list[str] = Field(default_factory=list)

    @field_validator("requirement_type", mode="before")
    @classmethod
    def _normalize_type(cls, value: Any) -> str:
        normalized = normalize_for_match(str(value or ""))
        if "dese" in normalized or "plus" in normalized or "valorable" in normalized:
            return "desirable"
        return "mandatory"

    @field_validator("category", mode="before")
    @classmethod
    def _normalize_category(cls, value: Any) -> str:
        normalized = normalize_for_match(str(value or "otro"))
        mapping = {
            "herramienta": "herramienta", "tool": "herramienta",
            "experiencia": "experiencia", "experience": "experiencia",
            "formacion": "formacion", "formación": "formacion", "education": "formacion",
            "certificacion": "certificacion", "certificación": "certificacion",
            "idioma": "idioma", "language": "idioma",
            "competencia": "competencia", "skill": "competencia",
        }
        return mapping.get(normalized, "otro")


class JobAnalysisPayload(BaseModel):
    title: str = ""
    company: str = ""
    area: str = ""
    requirements: list[JobRequirementPayload] = Field(default_factory=list)


class ResponseValidator:
    """Extrae y valida JSON, y marca propuestas que introducen datos no respaldados."""

    @staticmethod
    def extract_json(text: str) -> Any:
        if not text or not text.strip():
            raise AIValidationError("La IA no devolvió contenido.")
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        # Busca el primer objeto o array equilibrado.
        for start_char, end_char in (("{", "}"), ("[", "]")):
            start = cleaned.find(start_char)
            if start == -1:
                continue
            depth = 0
            in_string = False
            escape = False
            for index in range(start, len(cleaned)):
                char = cleaned[index]
                if escape:
                    escape = False
                    continue
                if char == "\\":
                    escape = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == start_char:
                    depth += 1
                elif char == end_char:
                    depth -= 1
                    if depth == 0:
                        candidate = cleaned[start : index + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break
        raise AIValidationError(
            "La respuesta de la IA no contiene JSON válido. Intente de nuevo o use un modelo más capaz."
        )

    @staticmethod
    def validate_proposals(data: Any, source_text: str) -> list[dict[str, Any]]:
        if isinstance(data, dict):
            raw = data.get("proposals", [])
        elif isinstance(data, list):
            raw = data
        else:
            raw = []
        if not isinstance(raw, list):
            raise AIValidationError("El campo 'proposals' no es una lista.")

        source_normalized = normalize_for_match(source_text)
        source_numbers = set(extract_numbers(source_text))
        source_tech = {normalize_for_match(item) for item in extract_tech_keywords(source_text)}
        proposals: list[dict[str, Any]] = []
        for item in raw[:15]:
            if not isinstance(item, dict):
                continue
            try:
                payload = ProposalPayload(**item)
            except Exception:
                continue
            issues: list[str] = []
            proposed = payload.proposed_text
            original = payload.original_text

            # El texto original debe existir realmente en el CV.
            if normalize_for_match(original)[:80] not in source_normalized:
                issues.append(
                    "El fragmento original no se encontró literalmente en el CV; "
                    "la propuesta requiere revisión manual."
                )
            # No se permiten métricas nuevas que no estén en el CV.
            new_numbers = [
                number for number in extract_numbers(proposed)
                if number not in source_numbers and len(number) > 1
            ]
            if new_numbers:
                issues.append(
                    "La propuesta introduce cifras que no aparecen en el CV: "
                    + ", ".join(new_numbers[:5])
                )
            # No se permiten tecnologías nuevas sin respaldo.
            new_tech = [
                tech for tech in extract_tech_keywords(proposed)
                if normalize_for_match(tech) not in source_tech
                and normalize_for_match(tech) not in normalize_for_match(original)
            ]
            if new_tech:
                issues.append(
                    "La propuesta añade tecnologías no respaldadas por el CV: "
                    + ", ".join(new_tech[:5])
                )
            if normalize_for_match(proposed) == normalize_for_match(original):
                issues.append("La propuesta no modifica el texto original.")

            proposals.append(
                {
                    "section": payload.section or "General",
                    "original_text": original,
                    "problem": payload.problem,
                    "proposed_text": proposed,
                    "justification": payload.justification,
                    "evidence": payload.evidence or original,
                    "origin": ORIGIN_AI,
                    "issues": issues,
                }
            )
        if not proposals:
            raise AIValidationError(
                "La IA no generó propuestas utilizables. Pruebe con otro modelo o revise el CV."
            )
        return proposals

    @staticmethod
    def validate_missing_information(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, dict):
            raw = data.get("questions", [])
        elif isinstance(data, list):
            raw = data
        else:
            raw = []
        result = []
        for item in raw[:10]:
            if not isinstance(item, dict):
                continue
            try:
                payload = MissingInfoPayload(**item)
            except Exception:
                continue
            result.append(
                {
                    "topic": payload.topic,
                    "question": payload.question,
                    "why_important": payload.why_important,
                    "example_text": payload.example_text,
                    "origin": ORIGIN_ILLUSTRATIVE,
                }
            )
        if not result:
            raise AIValidationError("La IA no devolvió preguntas válidas.")
        return result

    @staticmethod
    def validate_job_analysis(data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise AIValidationError("La respuesta de análisis de oferta no es un objeto JSON.")
        try:
            payload = JobAnalysisPayload(**data)
        except Exception as exc:
            raise AIValidationError(f"Estructura de oferta inválida: {exc}") from exc
        return {
            "title": payload.title.strip(),
            "company": payload.company.strip(),
            "area": payload.area.strip(),
            "requirements": [
                {
                    "text": req.text.strip(),
                    "requirement_type": req.requirement_type,
                    "category": req.category,
                    "keywords": [keyword.strip() for keyword in req.keywords if keyword.strip()][:12],
                    "weight": 1.0,
                }
                for req in payload.requirements
                if req.text.strip()
            ],
        }
