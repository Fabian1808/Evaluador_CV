"""Modelo de datos relacional de CV Analyzer Pro (SQLAlchemy 2.0)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Candidate(Base, TimestampMixin):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(60))
    location: Mapped[str | None] = mapped_column(String(200))
    linkedin: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)

    cvs: Mapped[list[CV]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", passive_deletes=True
    )
    profiles: Mapped[list[CandidateProfile]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover - depuración
        return f"<Candidate {self.id} {self.full_name!r}>"


class CandidateProfile(Base):
    """Perfil profesional objetivo declarado por el candidato."""

    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    target_role: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    candidate: Mapped[Candidate] = relationship(back_populates="profiles")


class CV(Base, TimestampMixin):
    __tablename__ = "cvs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(40), default="text", nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    diagnostics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    warnings: Mapped[list[str] | None] = mapped_column(JSON)
    is_master: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    candidate: Mapped[Candidate] = relationship(back_populates="cvs")
    versions: Mapped[list[CVVersion]] = relationship(
        back_populates="cv", cascade="all, delete-orphan", passive_deletes=True,
        order_by="CVVersion.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CV {self.id} {self.title!r}>"


class CVVersion(Base):
    __tablename__ = "cv_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_id: Mapped[int] = mapped_column(
        ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="original", nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    parent_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("cv_versions.id", ondelete="SET NULL")
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    cv: Mapped[CV] = relationship(back_populates="versions")
    sections: Mapped[list[CVSection]] = relationship(
        back_populates="version", cascade="all, delete-orphan", passive_deletes=True,
        order_by="CVSection.order_index",
    )
    evaluations: Mapped[list[Evaluation]] = relationship(
        back_populates="cv_version", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CVVersion {self.id} {self.label!r}>"


class CVSection(Base):
    __tablename__ = "cv_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_version_id: Mapped[int] = mapped_column(
        ForeignKey("cv_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    data_origin: Mapped[str] = mapped_column(
        String(30), default="ORIGINAL_DOCUMENT", nullable=False
    )

    version: Mapped[CVVersion] = relationship(back_populates="sections")


class JobOffer(Base, TimestampMixin):
    __tablename__ = "job_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    company: Mapped[str | None] = mapped_column(String(250))
    area: Mapped[str | None] = mapped_column(String(150))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(300))
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    requirements: Mapped[list[JobRequirement]] = relationship(
        back_populates="offer", cascade="all, delete-orphan", passive_deletes=True,
        order_by="JobRequirement.id",
    )
    evaluations: Mapped[list[Evaluation]] = relationship(back_populates="offer")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<JobOffer {self.id} {self.title!r}>"


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_type: Mapped[str] = mapped_column(
        String(20), default="mandatory", nullable=False
    )
    category: Mapped[str] = mapped_column(String(40), default="otro", nullable=False)
    keywords: Mapped[list[str] | None] = mapped_column(JSON)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    offer: Mapped[JobOffer] = relationship(back_populates="requirements")


class TechnicalProfile(Base):
    __tablename__ = "technical_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    competencies: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_version_id: Mapped[int] = mapped_column(
        ForeignKey("cv_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_offers.id", ondelete="SET NULL"), index=True
    )
    technical_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("technical_profiles.id", ondelete="SET NULL")
    )
    technical_profile_name: Mapped[str | None] = mapped_column(String(150))
    ats_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hr_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    technical_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    compatibility_score: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(20), default="media", nullable=False)
    weights: Mapped[dict[str, float] | None] = mapped_column(JSON)
    ai_model: Mapped[str | None] = mapped_column(String(150))
    summary: Mapped[str | None] = mapped_column(Text)
    strengths: Mapped[list[str] | None] = mapped_column(JSON)
    weaknesses: Mapped[list[str] | None] = mapped_column(JSON)
    missing: Mapped[list[str] | None] = mapped_column(JSON)
    limitations: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    cv_version: Mapped[CVVersion] = relationship(back_populates="evaluations")
    offer: Mapped[JobOffer | None] = relationship(back_populates="evaluations")
    details: Mapped[list[EvaluationDetail]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan", passive_deletes=True,
        order_by="EvaluationDetail.id",
    )
    evidence: Mapped[list[Evidence]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan", passive_deletes=True
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan", passive_deletes=True
    )


class EvaluationDetail(Base):
    __tablename__ = "evaluation_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="SET NULL")
    )
    dimension: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    criterion: Mapped[str] = mapped_column(String(200), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)

    evaluation: Mapped[Evaluation] = relationship(back_populates="details")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section: Mapped[str] = mapped_column(String(150), default="", nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str] = mapped_column(
        String(30), default="ORIGINAL_DOCUMENT", nullable=False
    )
    confidence: Mapped[str] = mapped_column(String(20), default="media", nullable=False)

    evaluation: Mapped[Evaluation] = relationship(back_populates="evidence")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    area: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="media", nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pendiente", nullable=False)

    evaluation: Mapped[Evaluation] = relationship(back_populates="recommendations")


class AIRequest(Base):
    __tablename__ = "ai_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(150), nullable=False)
    prompt_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    response_text: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    template_type: Mapped[str] = mapped_column(String(40), default="harvard", nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class OptimizationSession(Base):
    __tablename__ = "optimization_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_version_id: Mapped[int] = mapped_column(
        ForeignKey("cv_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_offers.id", ondelete="SET NULL")
    )
    provider: Mapped[str] = mapped_column(String(40), default="rules", nullable=False)
    model: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), default="completed", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    proposals: Mapped[list[OptimizationProposal]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True,
        order_by="OptimizationProposal.id",
    )


class OptimizationProposal(Base):
    __tablename__ = "optimization_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("optimization_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    section: Mapped[str] = mapped_column(String(100), default="general", nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_text: Mapped[str] = mapped_column(Text, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(30), default="AI_SUGGESTED", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    edited_text: Mapped[str | None] = mapped_column(Text)
    issues: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    session: Mapped[OptimizationSession] = relationship(back_populates="proposals")


class MissingInformation(Base):
    __tablename__ = "missing_information"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_version_id: Mapped[int] = mapped_column(
        ForeignKey("cv_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_offers.id", ondelete="SET NULL")
    )
    topic: Mapped[str] = mapped_column(String(150), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    why_important: Mapped[str] = mapped_column(Text, nullable=False)
    example_text: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(
        String(30), default="ILLUSTRATIVE_EXAMPLE", nullable=False
    )
    answer: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# Índices compuestos útiles para consultas de la interfaz.
Index("ix_evaluations_created_score", Evaluation.created_at, Evaluation.overall_score)
Index("ix_cv_versions_cv_created", CVVersion.cv_id, CVVersion.created_at)
Index("ix_details_evaluation_dimension", EvaluationDetail.evaluation_id, EvaluationDetail.dimension)
