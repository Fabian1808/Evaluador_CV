"""Modelos de resultado compartidos por los evaluadores."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config.constants import CONFIDENCE_LABELS, SCORE_DISCLAIMER


@dataclass
class CriterionResult:
    criterion: str
    score: float
    max_score: float
    status: str = ""
    severity: str = "info"
    explanation: str = ""
    evidence: str | None = None
    recommendation: str | None = None

    def __post_init__(self) -> None:
        if not self.status:
            ratio = self.score / self.max_score if self.max_score else 0
            if ratio >= 0.85:
                self.status = "Cumple"
            elif ratio >= 0.6:
                self.status = "Parcial"
            else:
                self.status = "No cumple"

    @property
    def ratio(self) -> float:
        return self.score / self.max_score if self.max_score else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion": self.criterion,
            "score": round(self.score, 1),
            "max_score": self.max_score,
            "status": self.status,
            "severity": self.severity,
            "explanation": self.explanation,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


@dataclass
class DimensionResult:
    dimension: str
    score: float
    criteria: list[CriterionResult] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    confidence: str = "media"
    summary: str = ""

    @property
    def confidence_label(self) -> str:
        return CONFIDENCE_LABELS.get(self.confidence, self.confidence)

    def add_disclaimer(self) -> None:
        if SCORE_DISCLAIMER not in self.limitations:
            self.limitations.append(SCORE_DISCLAIMER)


@dataclass
class RequirementMatch:
    requirement_text: str
    requirement_type: str
    status: str
    explanation: str
    evidence: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    score: float | None = None


@dataclass
class CompatibilityResult:
    score: float
    mandatory_score: float | None
    desirable_score: float | None
    matches: list[RequirementMatch] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    confidence: str = "media"

    @property
    def counts(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for match in self.matches:
            result[match.status] = result.get(match.status, 0) + 1
        return result


@dataclass
class EvaluationBundle:
    ats: DimensionResult
    hr: DimensionResult
    technical: DimensionResult
    compatibility: CompatibilityResult | None
    overall_score: float
    quality_score: float
    confidence: str
    weights: dict[str, float]
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    summary: str = ""
    ai_model: str | None = None
    technical_profile_name: str | None = None
