"""Sistema de puntuación configurable.

El puntaje global sigue la fórmula solicitada:
    SCORE = ATS * 0.25 + RR. HH. * 0.35 + TÉCNICO * 0.40
Las ponderaciones se pueden modificar desde Configuración.
"""

from __future__ import annotations

from app.config.constants import DEFAULT_WEIGHTS, SCORE_DISCLAIMER


class ScoringService:
    @staticmethod
    def normalize_weights(weights: dict[str, float] | None) -> dict[str, float]:
        raw = dict(DEFAULT_WEIGHTS)
        if weights:
            for key in ("ats", "hr", "technical"):
                try:
                    raw[key] = max(0.0, float(weights.get(key, raw[key])))
                except (TypeError, ValueError):
                    pass
        total = sum(raw.values())
        if total <= 0:
            return dict(DEFAULT_WEIGHTS)
        if abs(total - 100.0) > 0.01:
            raw = {key: value * 100.0 / total for key, value in raw.items()}
        return {key: round(value, 2) for key, value in raw.items()}

    @classmethod
    def weighted_score(
        cls,
        ats: float,
        hr: float,
        technical: float,
        weights: dict[str, float] | None = None,
    ) -> float:
        normalized = cls.normalize_weights(weights)
        score = (
            ats * normalized["ats"]
            + hr * normalized["hr"]
            + technical * normalized["technical"]
        ) / 100.0
        return round(max(0.0, min(100.0, score)), 1)

    @staticmethod
    def confidence_label(value: str) -> str:
        return {"alta": "Alta", "media": "Media", "baja": "Baja"}.get(value, value)

    @staticmethod
    def score_band(score: float) -> str:
        if score >= 85:
            return "Excelente"
        if score >= 70:
            return "Bueno"
        if score >= 55:
            return "Mejorable"
        if score >= 40:
            return "Débil"
        return "Crítico"

    @staticmethod
    def disclaimer() -> str:
        return SCORE_DISCLAIMER
