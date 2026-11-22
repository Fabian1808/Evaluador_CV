"""Orquestación de la evaluación integral y persistencia de resultados."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.ai.ai_service import AIService
from app.config.constants import SCORE_DISCLAIMER
from app.database.models import Evaluation, EvaluationDetail, Evidence, Recommendation
from app.database.repositories import (
    CVRepository,
    EvaluationRepository,
    OfferRepository,
    TechnicalProfileRepository,
)
from app.database.session import Database
from app.services.ats_evaluator import ATSEvaluator
from app.services.compatibility import CompatibilityEvaluator
from app.services.evaluation_models import (
    CompatibilityResult,
    DimensionResult,
    EvaluationBundle,
    RequirementMatch,
)
from app.services.evaluation_utils import offer_keyword_list
from app.services.hr_evaluator import HREvaluator
from app.services.scoring import ScoringService
from app.services.technical_evaluator import TechnicalEvaluator
from app.utils.text import truncate

Progress = Callable[[int, str], None]

_DIMENSION_LABELS = {"ATS": "ATS", "HR": "Recursos Humanos", "TECHNICAL": "Técnico"}


@dataclass
class EvaluationOutcome:
    evaluation_id: int
    bundle: EvaluationBundle


class EvaluationService:
    def __init__(
        self,
        database: Database,
        ai_service: AIService,
        ats: ATSEvaluator | None = None,
        hr: HREvaluator | None = None,
        technical: TechnicalEvaluator | None = None,
        compatibility: CompatibilityEvaluator | None = None,
        scoring: ScoringService | None = None,
    ) -> None:
        self.database = database
        self.ai = ai_service
        self.ats = ats or ATSEvaluator()
        self.hr = hr or HREvaluator()
        self.technical = technical or TechnicalEvaluator()
        self.compatibility = compatibility or CompatibilityEvaluator()
        self.scoring = scoring or ScoringService()

    def evaluate(
        self,
        cv_version_id: int,
        offer_id: int | None = None,
        technical_profile_id: int | None = None,
        use_ai_summary: bool = False,
        weights: dict[str, float] | None = None,
        cancel_event=None,  # type: ignore[no-untyped-def]
        progress: Progress | None = None,
    ) -> EvaluationOutcome:
        with self.database.session() as session:
            version = CVRepository(session).get_version(cv_version_id)
            if version is None:
                raise ValueError("La versión de CV no existe.")
            offer = OfferRepository(session).get(offer_id) if offer_id else None
            profile = (
                TechnicalProfileRepository(session).get(technical_profile_id)
                if technical_profile_id else None
            )
            raw_text = version.raw_text or ""
            content = version.content or {}
            diagnostics = dict(version.cv.diagnostics or {})
            diagnostics.setdefault("file_type", version.cv.file_type)
            diagnostics.setdefault("page_count", version.cv.page_count)
            requirements = (
                [
                    {
                        "id": requirement.id,
                        "text": requirement.text,
                        "requirement_type": requirement.requirement_type,
                        "keywords": list(requirement.keywords or []),
                    }
                    for requirement in offer.requirements
                ]
                if offer else []
            )
            offer_text = offer.raw_text if offer else ""
            analysis = (offer.analysis or {}) if offer else {}
            offer_keywords = offer_keyword_list(
                requirements, offer_text, analysis.get("keywords") or []
            )
            profile_dict = (
                {
                    "name": profile.name,
                    "description": profile.description,
                    "competencies": list(profile.competencies or []),
                }
                if profile else {}
            )
            profile_name = profile.name if profile else None
            offer_label = offer.title if offer else ""

        if progress:
            progress(10, "Evaluando estructura y compatibilidad ATS…")
        ats_result = self.ats.evaluate(
            raw_text, content, diagnostics, requirements, offer_text, offer_keywords
        )
        if progress:
            progress(35, "Analizando desde la perspectiva de Recursos Humanos…")
        hr_result = self.hr.evaluate(raw_text, content, offer_text, offer_keywords)
        if progress:
            progress(60, "Evaluando competencias técnicas con evidencia…")
        technical_result = self.technical.evaluate(raw_text, content, profile_dict)
        compatibility_result = None
        if offer:
            if progress:
                progress(75, "Comparando requisitos de la oferta con el CV…")
            compatibility_result = self.compatibility.evaluate(
                content, requirements, offer_text
            )

        normalized_weights = self.scoring.normalize_weights(weights)
        overall = self.scoring.weighted_score(
            ats_result.score,
            hr_result.score,
            technical_result.score,
            normalized_weights,
        )
        confidence = self._confidence(ats_result, hr_result, technical_result, compatibility_result)

        strengths = self._merge(
            ats_result.strengths, hr_result.strengths, technical_result.strengths,
            compatibility_result.strengths if compatibility_result else [],
        )[:14]
        weaknesses = self._merge(
            ats_result.weaknesses, hr_result.weaknesses, technical_result.weaknesses,
            compatibility_result.weaknesses if compatibility_result else [],
        )[:14]
        missing = self._merge(
            ats_result.missing, hr_result.missing, technical_result.missing,
            [f"Palabra clave faltante: {item}" for item in (
                compatibility_result.missing_keywords if compatibility_result else []
            )],
        )[:20]
        limitations = self._merge(
            ats_result.limitations, hr_result.limitations, technical_result.limitations,
            compatibility_result.limitations if compatibility_result else [],
        )

        summary = (
            f"Calidad general del CV: {overall:.1f}/100. "
            f"ATS {ats_result.score:.1f}, Recursos Humanos {hr_result.score:.1f}, "
            f"Técnico {technical_result.score:.1f}."
        )
        if compatibility_result:
            summary += (
                f" Compatibilidad con la oferta «{offer_label}»: "
                f"{compatibility_result.score:.1f}/100."
            )

        ai_model = None
        if use_ai_summary:
            if progress:
                progress(85, "Redactando resumen ejecutivo con IA local…")
            ai_text = self.ai.evaluation_summary(
                ats_result.score,
                hr_result.score,
                technical_result.score,
                overall,
                strengths,
                weaknesses,
                missing,
                offer_label,
                cancel_event=cancel_event,
            )
            if ai_text:
                summary = ai_text
                ai_model = self.ai.model
            else:
                limitations.append(
                    "No se pudo generar el resumen con IA local; se muestra el resumen "
                    "determinista basado en los criterios."
                )
        else:
            limitations.append(
                "El resumen es determinista. Active 'Resumen con IA local' para una "
                "redacción asistida, manteniendo las mismas puntuaciones."
            )

        if SCORE_DISCLAIMER not in limitations:
            limitations.append(SCORE_DISCLAIMER)

        bundle = EvaluationBundle(
            ats=ats_result,
            hr=hr_result,
            technical=technical_result,
            compatibility=compatibility_result,
            overall_score=overall,
            quality_score=overall,
            confidence=confidence,
            weights=normalized_weights,
            strengths=strengths,
            weaknesses=weaknesses,
            missing=missing,
            limitations=list(dict.fromkeys(limitations)),
            summary=summary,
            ai_model=ai_model,
            technical_profile_name=profile_name,
        )

        if progress:
            progress(95, "Guardando la evaluación…")
        with self.database.session() as session:
            evaluation = Evaluation(
                cv_version_id=cv_version_id,
                job_offer_id=offer_id,
                technical_profile_id=technical_profile_id,
                technical_profile_name=profile_name,
                ats_score=ats_result.score,
                hr_score=hr_result.score,
                technical_score=technical_result.score,
                overall_score=overall,
                quality_score=overall,
                compatibility_score=(
                    compatibility_result.score if compatibility_result else None
                ),
                confidence=confidence,
                weights=normalized_weights,
                ai_model=ai_model,
                summary=summary,
                strengths=strengths,
                weaknesses=weaknesses,
                missing=missing,
                limitations=bundle.limitations,
            )
            details = self._build_details(
                ats_result, hr_result, technical_result, compatibility_result
            )
            evidence = self._build_evidence(
                ats_result, hr_result, technical_result, compatibility_result
            )
            recommendations = self._build_recommendations(
                ats_result, hr_result, technical_result, compatibility_result
            )
            EvaluationRepository(session).create(
                evaluation, details, evidence, recommendations
            )
            evaluation_id = evaluation.id

        if progress:
            progress(100, "Evaluación completada.")
        return EvaluationOutcome(evaluation_id=evaluation_id, bundle=bundle)

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _merge(*groups: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for group in groups:
            for item in group or []:
                key = item.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    result.append(item)
        return result

    @staticmethod
    def _confidence(
        ats: DimensionResult,
        hr: DimensionResult,
        technical: DimensionResult,
        compatibility: CompatibilityResult | None,
    ) -> str:
        levels = [ats.confidence, hr.confidence, technical.confidence]
        if compatibility:
            levels.append(compatibility.confidence)
        if all(level == "alta" for level in levels):
            return "alta"
        if sum(1 for level in levels if level == "baja") >= max(1, len(levels) // 2):
            return "baja"
        return "media"

    def _build_details(
        self,
        ats: DimensionResult,
        hr: DimensionResult,
        technical: DimensionResult,
        compatibility: CompatibilityResult | None,
    ) -> list[EvaluationDetail]:
        details: list[EvaluationDetail] = []
        for dimension, result in (
            ("ATS", ats), ("HR", hr), ("TECHNICAL", technical)
        ):
            for criterion in result.criteria:
                details.append(
                    EvaluationDetail(
                        dimension=dimension,
                        criterion=criterion.criterion,
                        score=criterion.score,
                        max_score=criterion.max_score,
                        status=criterion.status,
                        severity=criterion.severity,
                        explanation=criterion.explanation,
                        evidence=criterion.evidence,
                        recommendation=criterion.recommendation,
                    )
                )
        if compatibility:
            for match in compatibility.matches:
                details.append(
                    EvaluationDetail(
                        dimension="COMPATIBILITY",
                        criterion=truncate(match.requirement_text, 180),
                        score=round((match.score or 0) * 100, 1),
                        max_score=100,
                        status=match.status,
                        severity=self._requirement_severity(match),
                        explanation=match.explanation,
                        evidence=match.evidence,
                        recommendation=self._requirement_recommendation(match),
                    )
                )
        return details

    @staticmethod
    def _requirement_severity(match: RequirementMatch) -> str:
        if match.status == "DEMOSTRADO":
            return "info"
        if match.status == "PARCIALMENTE_DEMOSTRADO":
            return "medium"
        if match.status == "PENDIENTE_CONFIRMACION":
            return "low"
        return "high" if match.requirement_type == "mandatory" else "medium"

    @staticmethod
    def _requirement_recommendation(match: RequirementMatch) -> str | None:
        if match.status == "DEMOSTRADO":
            return None
        if match.status == "NO_IDENTIFICADO":
            return (
                "Si cuenta con experiencia real, documéntela con un ejemplo y un resultado. "
                "Si no, no incorpore el requisito: inventarlo reduce la credibilidad."
            )
        if match.status == "MENCIONADO_SIN_EVIDENCIA":
            return (
                "Añada una evidencia de uso en experiencia o proyectos; una mención en "
                "habilidades no demuestra dominio."
            )
        if match.status == "PENDIENTE_CONFIRMACION":
            return "Confirme este requisito con el candidato antes de puntuarlo."
        return "Refuerce la evidencia con alcance, responsabilidad y resultado verificable."

    def _build_evidence(
        self,
        ats: DimensionResult,
        hr: DimensionResult,
        technical: DimensionResult,
        compatibility: CompatibilityResult | None,
    ) -> list[Evidence]:
        evidence: list[Evidence] = []
        seen: set[str] = set()
        for result in (ats, hr, technical):
            for criterion in result.criteria:
                if criterion.evidence and criterion.evidence.strip():
                    key = criterion.evidence.strip().lower()[:120]
                    if key in seen:
                        continue
                    seen.add(key)
                    evidence.append(
                        Evidence(
                            section=criterion.criterion,
                            quote=truncate(criterion.evidence, 400),
                            origin="ORIGINAL_DOCUMENT",
                            confidence="alta" if len(criterion.evidence) > 40 else "media",
                        )
                    )
        if compatibility:
            for match in compatibility.matches:
                if match.evidence and match.evidence.strip():
                    key = match.evidence.strip().lower()[:120]
                    if key in seen:
                        continue
                    seen.add(key)
                    evidence.append(
                        Evidence(
                            section=truncate(match.requirement_text, 120),
                            quote=truncate(match.evidence, 400),
                            origin="ORIGINAL_DOCUMENT",
                            confidence="alta" if match.status == "DEMOSTRADO" else "media",
                        )
                    )
        return evidence[:60]

    def _build_recommendations(
        self,
        ats: DimensionResult,
        hr: DimensionResult,
        technical: DimensionResult,
        compatibility: CompatibilityResult | None,
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        priority_map = {
            "critical": "alta", "high": "alta", "medium": "media", "low": "baja", "info": "baja",
        }
        for dimension, result in (
            ("ATS", ats), ("RR. HH.", hr), ("Técnico", technical)
        ):
            for criterion in result.criteria:
                if not criterion.recommendation:
                    continue
                recommendations.append(
                    Recommendation(
                        area=dimension,
                        priority=priority_map.get(criterion.severity, "media"),
                        text=criterion.recommendation,
                        status="pendiente",
                    )
                )
        if compatibility:
            for match in compatibility.matches:
                recommendation = self._requirement_recommendation(match)
                if not recommendation:
                    continue
                recommendations.append(
                    Recommendation(
                        area="Compatibilidad",
                        priority="alta" if match.requirement_type == "mandatory" else "media",
                        text=f"{truncate(match.requirement_text, 140)}: {recommendation}",
                        status="pendiente",
                    )
                )
        seen: set[str] = set()
        unique = []
        for item in recommendations:
            key = item.text.strip().lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique[:40]
