"""Inicialización, versionado y datos semilla de la base de datos."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select, text

from app.config import constants
from app.database.models import Setting, TechnicalProfile, Template
from app.database.session import Database

SCHEMA_VERSION = 1


def initialize_database(database: Database) -> None:
    """Crea el esquema y siembra la configuración inicial de forma idempotente."""
    database.create_all()
    with database.session() as session:
        _apply_migrations(session)
        _seed_settings(session)
        _seed_templates(session)
        _seed_technical_profiles(session)


def _apply_migrations(session) -> None:  # type: ignore[no-untyped-def]
    current = session.execute(text("PRAGMA user_version")).scalar_one()
    if current < SCHEMA_VERSION:
        # Las migraciones futuras se añaden aquí de forma incremental.
        session.execute(text(f"PRAGMA user_version = {SCHEMA_VERSION}"))


def _seed_settings(session) -> None:  # type: ignore[no-untyped-def]
    defaults = {
        "ai": constants.DEFAULT_AI_SETTINGS,
        "weights": constants.DEFAULT_WEIGHTS,
        "document": constants.DEFAULT_DOCUMENT_CONFIG,
        "app": {
            "language": "es",
            "last_page": "dashboard",
            "show_disclaimer": True,
        },
    }
    for key, value in defaults.items():
        existing = session.get(Setting, key)
        if existing is None:
            session.add(Setting(key=key, value=value))
        elif isinstance(value, dict) and isinstance(existing.value, dict):
            merged = {**value, **existing.value}
            existing.value = merged


def _seed_templates(session) -> None:  # type: ignore[no-untyped-def]
    exists = session.scalar(select(Template).where(Template.template_type == "harvard"))
    if exists is None:
        session.add(
            Template(
                name="Harvard profesional",
                template_type="harvard",
                config=dict(constants.DEFAULT_DOCUMENT_CONFIG),
                is_default=True,
            )
        )


def _seed_technical_profiles(session) -> None:  # type: ignore[no-untyped-def]
    for profile in constants.DEFAULT_TECHNICAL_PROFILES:
        existing = session.scalar(
            select(TechnicalProfile).where(TechnicalProfile.name == profile["name"])
        )
        if existing is None:
            session.add(
                TechnicalProfile(
                    name=profile["name"],
                    description=profile["description"],
                    competencies=profile["competencies"],
                    is_builtin=True,
                )
            )


def export_database_summary(database: Database) -> dict:
    """Resumen legible del contenido de la base, útil para diagnóstico."""
    from app.database.models import (
        Candidate, CV, Evaluation, JobOffer, OptimizationSession,
    )

    with database.session() as session:
        return {
            "candidates": session.query(Candidate).count(),
            "cvs": session.query(CV).count(),
            "offers": session.query(JobOffer).count(),
            "evaluations": session.query(Evaluation).count(),
            "optimizations": session.query(OptimizationSession).count(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
