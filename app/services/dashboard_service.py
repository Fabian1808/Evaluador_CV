"""Servicio de métricas del panel principal."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.database.models import Candidate, CV, CVVersion, Evaluation, JobOffer
from app.database.repositories import EvaluationRepository
from app.database.session import Database


class DashboardService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def stats(self) -> dict[str, Any]:
        with self.database.session() as session:
            candidates = int(session.scalar(select(func.count(Candidate.id))) or 0)
            cvs = int(session.scalar(select(func.count(CV.id))) or 0)
            versions = int(session.scalar(select(func.count(CVVersion.id))) or 0)
            offers = int(session.scalar(select(func.count(JobOffer.id))) or 0)
            evaluations = int(session.scalar(select(func.count(Evaluation.id))) or 0)
            average = session.scalar(select(func.avg(Evaluation.overall_score)))
            best = session.scalar(select(func.max(Evaluation.overall_score)))
            recent = list(
                session.scalars(
                    select(Evaluation)
                    .order_by(Evaluation.created_at.desc())
                    .limit(5)
                )
            )
            evaluations_by_offer = list(
                session.execute(
                    select(JobOffer.title, func.count(Evaluation.id))
                    .join(Evaluation, Evaluation.job_offer_id == JobOffer.id)
                    .group_by(JobOffer.id)
                    .order_by(func.count(Evaluation.id).desc())
                    .limit(5)
                )
            )
        return {
            "candidates": candidates,
            "cvs": cvs,
            "versions": versions,
            "offers": offers,
            "evaluations": evaluations,
            "average": float(average) if average is not None else None,
            "best": float(best) if best is not None else None,
            "recent_count": len(recent),
            "offers_with_evaluations": [
                {"title": title, "count": count} for title, count in evaluations_by_offer
            ],
        }

    def recent_evaluations(self, limit: int = 8) -> list[dict[str, Any]]:
        with self.database.session() as session:
            items = EvaluationRepository(session).list_all(limit=limit)
            return [
                {
                    "id": item.id,
                    "created_at": item.created_at,
                    "candidate_name": (
                        item.cv_version.cv.candidate.full_name
                        if item.cv_version and item.cv_version.cv
                        else "—"
                    ),
                    "cv_label": item.cv_version.label if item.cv_version else "—",
                    "offer_title": item.offer.title if item.offer else "Sin oferta",
                    "overall": item.overall_score,
                    "ats": item.ats_score,
                    "hr": item.hr_score,
                    "technical": item.technical_score,
                    "compatibility": item.compatibility_score,
                    "confidence": item.confidence,
                }
                for item in items
            ]
