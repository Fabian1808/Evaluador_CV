"""Servicio de creación y análisis de ofertas laborales."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ai.ai_service import AIService
from app.database.models import JobOffer
from app.database.repositories import OfferRepository
from app.database.session import Database
from app.services.job_analyzer import JobAnalyzer
from app.utils.text import normalize_whitespace


@dataclass
class OfferResult:
    offer_id: int
    analysis: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    used_ai: bool = False


class OfferService:
    def __init__(
        self, database: Database, ai_service: AIService, analyzer: JobAnalyzer | None = None
    ) -> None:
        self.database = database
        self.ai = ai_service
        self.analyzer = analyzer or JobAnalyzer()

    def create(
        self,
        text: str,
        title: str = "",
        company: str = "",
        area: str = "",
        use_ai: bool = False,
    ) -> OfferResult:
        text = normalize_whitespace(text)
        if len(text) < 30:
            raise ValueError("La oferta debe contener al menos 30 caracteres de texto.")
        analysis = self.analyzer.analyze(text, title, company)
        warnings: list[str] = []
        used_ai = False
        if use_ai:
            enriched, ai_warning, used_ai = self._enrich_with_ai(text, analysis)
            analysis = enriched
            if ai_warning:
                warnings.append(ai_warning)
        if area and not analysis.get("area"):
            analysis["area"] = area
        if title and not analysis.get("title"):
            analysis["title"] = title
        if company and not analysis.get("company"):
            analysis["company"] = company

        with self.database.session() as session:
            offer = JobOffer(
                title=analysis.get("title") or title or "Oferta sin título",
                company=analysis.get("company") or company or None,
                area=analysis.get("area") or area or None,
                raw_text=text,
                analysis=analysis,
            )
            OfferRepository(session).create(offer, analysis.get("requirements") or [])
            return OfferResult(
                offer_id=offer.id, analysis=analysis, warnings=warnings, used_ai=used_ai
            )

    def update(
        self,
        offer_id: int,
        text: str | None = None,
        title: str | None = None,
        company: str | None = None,
        area: str | None = None,
        reanalyze: bool = True,
        use_ai: bool = False,
    ) -> OfferResult:
        with self.database.session() as session:
            repo = OfferRepository(session)
            offer = repo.get(offer_id)
            if offer is None:
                raise ValueError("La oferta no existe.")
            if text is not None:
                offer.raw_text = normalize_whitespace(text)
            if title is not None:
                offer.title = title
            if company is not None:
                offer.company = company
            if area is not None:
                offer.area = area
            raw_text = offer.raw_text
            current_title = offer.title
            current_company = offer.company or ""
            current_area = offer.area or ""

        if not reanalyze:
            with self.database.session() as session:
                offer = OfferRepository(session).get(offer_id)
                return OfferResult(
                    offer_id=offer_id,
                    analysis=dict(offer.analysis or {}),
                    used_ai=False,
                )

        analysis = self.analyzer.analyze(raw_text, current_title, current_company)
        if current_area and not analysis.get("area"):
            analysis["area"] = current_area
        warnings: list[str] = []
        used_ai = False
        if use_ai:
            analysis, warning, used_ai = self._enrich_with_ai(raw_text, analysis)
            if warning:
                warnings.append(warning)

        with self.database.session() as session:
            repo = OfferRepository(session)
            offer = repo.get(offer_id)
            offer.analysis = analysis
            offer.title = analysis.get("title") or current_title or "Oferta sin título"
            offer.company = analysis.get("company") or current_company or None
            offer.area = analysis.get("area") or current_area or None
            repo.replace_requirements(offer, analysis.get("requirements") or [])
            return OfferResult(
                offer_id=offer_id, analysis=analysis, warnings=warnings, used_ai=used_ai
            )

    def reanalyze(self, offer_id: int, use_ai: bool = False) -> OfferResult:
        return self.update(offer_id, reanalyze=True, use_ai=use_ai)

    def _enrich_with_ai(
        self, text: str, heuristic: dict[str, Any]
    ) -> tuple[dict[str, Any], str | None, bool]:
        ready, reason = self.ai.is_ready()
        if not ready:
            return heuristic, f"IA local no disponible: {reason}", False
        try:
            system, prompt = self.ai.prompts.job_analysis(text)
            data, _result = self.ai.generate_structured("job_analysis", system, prompt)
            validated = self.ai.validator.validate_job_analysis(data)
            if not validated.get("requirements"):
                return heuristic, (
                    "La IA no devolvió requisitos utilizables; se conservó el análisis "
                    "heurístico."
                ), False
            merged = {
                **heuristic,
                **{key: value for key, value in validated.items() if value},
                "source": "ai",
                "keywords": heuristic.get("keywords") or [],
            }
            return merged, None, True
        except Exception as exc:
            return heuristic, (
                f"No se pudo enriquecer la oferta con IA: {exc}. Se usó el análisis heurístico."
            ), False
