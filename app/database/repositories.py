"""Repositorios de acceso a datos.

Los repositorios encapsulan las consultas y devuelven objetos ORM con las
relaciones necesarias ya cargadas (``selectinload``) para que la interfaz no
dispare consultas perezosas después de cerrar la sesión.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database.models import (
    AIRequest,
    Candidate,
    CandidateProfile,
    CV,
    CVSection,
    CVVersion,
    Evaluation,
    EvaluationDetail,
    Evidence,
    JobOffer,
    JobRequirement,
    MissingInformation,
    OptimizationProposal,
    OptimizationSession,
    Recommendation,
    Setting,
    TechnicalProfile,
    Template,
)


class CandidateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Candidate]:
        stmt = (
            select(Candidate)
            .options(selectinload(Candidate.cvs), selectinload(Candidate.profiles))
            .order_by(Candidate.full_name)
        )
        return list(self.session.scalars(stmt).unique())

    def get(self, candidate_id: int) -> Candidate | None:
        stmt = (
            select(Candidate)
            .where(Candidate.id == candidate_id)
            .options(selectinload(Candidate.cvs), selectinload(Candidate.profiles))
        )
        return self.session.scalar(stmt)

    def create(self, **data) -> Candidate:
        candidate = Candidate(**data)
        self.session.add(candidate)
        self.session.flush()
        return candidate

    def update(self, candidate: Candidate, **data) -> Candidate:
        for key, value in data.items():
            setattr(candidate, key, value)
        self.session.flush()
        return candidate

    def delete(self, candidate: Candidate) -> None:
        self.session.delete(candidate)
        self.session.flush()

    def count(self) -> int:
        return int(self.session.scalar(select(func.count(Candidate.id))) or 0)

    def add_profile(self, candidate_id: int, **data) -> CandidateProfile:
        profile = CandidateProfile(candidate_id=candidate_id, **data)
        self.session.add(profile)
        self.session.flush()
        return profile


class CVRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[CV]:
        stmt = (
            select(CV)
            .options(
                selectinload(CV.candidate),
                selectinload(CV.versions),
            )
            .order_by(CV.created_at.desc())
        )
        return list(self.session.scalars(stmt).unique())

    def get(self, cv_id: int) -> CV | None:
        stmt = (
            select(CV)
            .where(CV.id == cv_id)
            .options(
                selectinload(CV.candidate),
                selectinload(CV.versions).selectinload(CVVersion.sections),
            )
        )
        return self.session.scalar(stmt)

    def create(self, **data) -> CV:
        cv = CV(**data)
        self.session.add(cv)
        self.session.flush()
        return cv

    def update(self, cv: CV, **data) -> CV:
        for key, value in data.items():
            setattr(cv, key, value)
        self.session.flush()
        return cv

    def delete(self, cv: CV) -> None:
        self.session.delete(cv)
        self.session.flush()

    def count(self) -> int:
        return int(self.session.scalar(select(func.count(CV.id))) or 0)

    def count_versions(self) -> int:
        return int(self.session.scalar(select(func.count(CVVersion.id))) or 0)

    def list_versions(self, cv_id: int | None = None) -> list[CVVersion]:
        stmt = select(CVVersion).options(
            selectinload(CVVersion.cv).selectinload(CV.candidate),
            selectinload(CVVersion.sections),
        )
        if cv_id is not None:
            stmt = stmt.where(CVVersion.cv_id == cv_id)
        stmt = stmt.order_by(CVVersion.created_at.desc())
        return list(self.session.scalars(stmt).unique())

    def get_version(self, version_id: int) -> CVVersion | None:
        stmt = (
            select(CVVersion)
            .where(CVVersion.id == version_id)
            .options(
                selectinload(CVVersion.cv).selectinload(CV.candidate),
                selectinload(CVVersion.sections),
            )
        )
        return self.session.scalar(stmt)

    def create_version(
        self,
        cv_id: int,
        label: str,
        content: dict,
        raw_text: str,
        source: str = "user_edit",
        parent_version_id: int | None = None,
        sections: Sequence[dict] | None = None,
    ) -> CVVersion:
        # Solo una versión actual por CV.
        for version in self.session.scalars(
            select(CVVersion).where(CVVersion.cv_id == cv_id)
        ):
            version.is_current = False
        version = CVVersion(
            cv_id=cv_id,
            label=label,
            content=content,
            raw_text=raw_text,
            source=source,
            parent_version_id=parent_version_id,
            is_current=True,
        )
        self.session.add(version)
        self.session.flush()
        if sections:
            for index, section in enumerate(sections):
                self.session.add(
                    CVSection(
                        cv_version_id=version.id,
                        section_type=section.get("section_type", "adicional"),
                        title=section.get("title", ""),
                        content=section.get("content", ""),
                        data=section.get("data"),
                        order_index=index,
                        data_origin=section.get("data_origin", "ORIGINAL_DOCUMENT"),
                    )
                )
        self.session.flush()
        return version

    def delete_version(self, version: CVVersion) -> None:
        self.session.delete(version)
        self.session.flush()


class OfferRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[JobOffer]:
        stmt = (
            select(JobOffer)
            .options(selectinload(JobOffer.requirements))
            .order_by(JobOffer.created_at.desc())
        )
        return list(self.session.scalars(stmt).unique())

    def get(self, offer_id: int) -> JobOffer | None:
        stmt = (
            select(JobOffer)
            .where(JobOffer.id == offer_id)
            .options(selectinload(JobOffer.requirements))
        )
        return self.session.scalar(stmt)

    def create(self, offer: JobOffer, requirements: Iterable[dict]) -> JobOffer:
        self.session.add(offer)
        self.session.flush()
        for requirement in requirements:
            self.session.add(
                JobRequirement(offer_id=offer.id, **requirement)
            )
        self.session.flush()
        return offer

    def replace_requirements(self, offer: JobOffer, requirements: Iterable[dict]) -> None:
        for existing in list(offer.requirements):
            self.session.delete(existing)
        self.session.flush()
        for requirement in requirements:
            self.session.add(JobRequirement(offer_id=offer.id, **requirement))
        self.session.flush()

    def update(self, offer: JobOffer, **data) -> JobOffer:
        for key, value in data.items():
            setattr(offer, key, value)
        self.session.flush()
        return offer

    def delete(self, offer: JobOffer) -> None:
        self.session.delete(offer)
        self.session.flush()

    def count(self) -> int:
        return int(self.session.scalar(select(func.count(JobOffer.id))) or 0)


class EvaluationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _base(self):
        return select(Evaluation).options(
            selectinload(Evaluation.cv_version)
            .selectinload(CVVersion.cv)
            .selectinload(CV.candidate),
            selectinload(Evaluation.offer),
            selectinload(Evaluation.details),
            selectinload(Evaluation.evidence),
            selectinload(Evaluation.recommendations),
        )

    def list_all(self, limit: int | None = None) -> list[Evaluation]:
        stmt = self._base().order_by(Evaluation.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt).unique())

    def get(self, evaluation_id: int) -> Evaluation | None:
        return self.session.scalar(self._base().where(Evaluation.id == evaluation_id))

    def create(
        self,
        evaluation: Evaluation,
        details: Iterable[EvaluationDetail],
        evidence: Iterable[Evidence],
        recommendations: Iterable[Recommendation],
    ) -> Evaluation:
        self.session.add(evaluation)
        self.session.flush()
        for detail in details:
            detail.evaluation_id = evaluation.id
            self.session.add(detail)
        for item in evidence:
            item.evaluation_id = evaluation.id
            self.session.add(item)
        for recommendation in recommendations:
            recommendation.evaluation_id = evaluation.id
            self.session.add(recommendation)
        self.session.flush()
        return evaluation

    def delete(self, evaluation: Evaluation) -> None:
        self.session.delete(evaluation)
        self.session.flush()

    def count(self) -> int:
        return int(self.session.scalar(select(func.count(Evaluation.id))) or 0)

    def average_score(self) -> float | None:
        value = self.session.scalar(select(func.avg(Evaluation.overall_score)))
        return float(value) if value is not None else None

    def count_for_offer(self, offer_id: int) -> int:
        return int(
            self.session.scalar(
                select(func.count(Evaluation.id)).where(Evaluation.job_offer_id == offer_id)
            )
            or 0
        )

    def list_for_offer(self, offer_id: int) -> list[Evaluation]:
        stmt = (
            self._base()
            .where(Evaluation.job_offer_id == offer_id)
            .order_by(Evaluation.overall_score.desc())
        )
        return list(self.session.scalars(stmt).unique())


class OptimizationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_session(self, **data) -> OptimizationSession:
        session = OptimizationSession(**data)
        self.session.add(session)
        self.session.flush()
        return session

    def add_proposals(
        self, session_id: int, proposals: Iterable[dict]
    ) -> list[OptimizationProposal]:
        created = []
        for proposal in proposals:
            item = OptimizationProposal(session_id=session_id, **proposal)
            self.session.add(item)
            created.append(item)
        self.session.flush()
        return created

    def get_session(self, session_id: int) -> OptimizationSession | None:
        stmt = (
            select(OptimizationSession)
            .where(OptimizationSession.id == session_id)
            .options(selectinload(OptimizationSession.proposals))
        )
        return self.session.scalar(stmt)

    def list_sessions(self, cv_version_id: int | None = None) -> list[OptimizationSession]:
        stmt = select(OptimizationSession).options(
            selectinload(OptimizationSession.proposals)
        )
        if cv_version_id:
            stmt = stmt.where(OptimizationSession.cv_version_id == cv_version_id)
        return list(
            self.session.scalars(stmt.order_by(OptimizationSession.created_at.desc())).unique()
        )

    def get_proposal(self, proposal_id: int) -> OptimizationProposal | None:
        return self.session.get(OptimizationProposal, proposal_id)

    def update_proposal(self, proposal: OptimizationProposal, **data) -> OptimizationProposal:
        for key, value in data.items():
            setattr(proposal, key, value)
        self.session.flush()
        return proposal

    def count_sessions(self) -> int:
        return int(self.session.scalar(select(func.count(OptimizationSession.id))) or 0)


class MissingInformationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def replace_for_version(
        self, version_id: int, offer_id: int | None, items: Iterable[dict]
    ) -> list[MissingInformation]:
        existing = list(
            self.session.scalars(
                select(MissingInformation).where(
                    MissingInformation.cv_version_id == version_id
                )
            )
        )
        answered = {item.question: item for item in existing if item.status == "answered"}
        for item in existing:
            if item.status != "answered":
                self.session.delete(item)
        self.session.flush()
        created = []
        for data in items:
            if data["question"] in answered:
                continue
            item = MissingInformation(
                cv_version_id=version_id, job_offer_id=offer_id, **data
            )
            self.session.add(item)
            created.append(item)
        self.session.flush()
        return created

    def list_for_version(self, version_id: int) -> list[MissingInformation]:
        stmt = (
            select(MissingInformation)
            .where(MissingInformation.cv_version_id == version_id)
            .order_by(MissingInformation.id)
        )
        return list(self.session.scalars(stmt))

    def answer(self, item_id: int, answer: str) -> MissingInformation | None:
        item = self.session.get(MissingInformation, item_id)
        if item:
            item.answer = answer.strip()
            item.status = "answered" if item.answer else "open"
            item.answered_at = datetime.now(timezone.utc) if item.answer else None
            self.session.flush()
        return item


class TechnicalProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[TechnicalProfile]:
        return list(
            self.session.scalars(select(TechnicalProfile).order_by(TechnicalProfile.name))
        )

    def get(self, profile_id: int) -> TechnicalProfile | None:
        return self.session.get(TechnicalProfile, profile_id)

    def create(self, **data) -> TechnicalProfile:
        profile = TechnicalProfile(**data)
        self.session.add(profile)
        self.session.flush()
        return profile

    def delete(self, profile: TechnicalProfile) -> None:
        self.session.delete(profile)
        self.session.flush()


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: str, default=None):
        setting = self.session.get(Setting, key)
        return setting.value if setting is not None else default

    def set(self, key: str, value) -> None:
        setting = self.session.get(Setting, key)
        if setting is None:
            self.session.add(Setting(key=key, value=value))
        else:
            setting.value = value
        self.session.flush()

    def all(self) -> dict:
        return {item.key: item.value for item in self.session.scalars(select(Setting))}


class TemplateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Template]:
        return list(self.session.scalars(select(Template).order_by(Template.name)))

    def default(self) -> Template | None:
        return self.session.scalar(select(Template).where(Template.is_default.is_(True)))


class AIRequestRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_cached(self, prompt_hash: str) -> AIRequest | None:
        stmt = (
            select(AIRequest)
            .where(AIRequest.prompt_hash == prompt_hash, AIRequest.success.is_(True))
            .order_by(AIRequest.created_at.desc())
        )
        return self.session.scalar(stmt)

    def create(self, **data) -> AIRequest:
        request = AIRequest(**data)
        self.session.add(request)
        self.session.flush()
        return request
