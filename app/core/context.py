"""Contexto de aplicación: construye y comparte servicios."""

from __future__ import annotations

from typing import Any

from app.ai.ai_service import AIService
from app.ai.model_manager import ModelManager
from app.ai.prompt_manager import PromptManager
from app.ai.provider import OllamaProvider
from app.config import constants, paths
from app.database.migrations import initialize_database
from app.database.repositories import SettingsRepository
from app.database.session import Database
from app.services.ats_evaluator import ATSEvaluator
from app.services.comparison import ComparisonService
from app.services.cv_parser import CVParser
from app.services.cv_service import CVService
from app.services.dashboard_service import DashboardService
from app.services.document_generator import HarvardGenerator
from app.services.document_service import DocumentService
from app.services.evaluation_service import EvaluationService
from app.services.hr_evaluator import HREvaluator
from app.services.job_analyzer import JobAnalyzer
from app.services.offer_service import OfferService
from app.services.optimizer import OptimizerService
from app.services.scoring import ScoringService
from app.services.technical_evaluator import TechnicalEvaluator


class AppContext:
    """Contenedor de dependencias de la aplicación (composition root)."""

    def __init__(self, database: Database | None = None) -> None:
        paths.ensure_directories()
        self.database = database or Database()
        initialize_database(self.database)
        self.settings: dict[str, Any] = self._load_settings()

        self.ai_provider = OllamaProvider(
            str(self.settings.get("ai", {}).get("base_url", constants.DEFAULT_OLLAMA_URL))
        )
        self.ai_service = AIService(
            self.database,
            self.ai_provider,
            PromptManager(
                max_context_chars=int(
                    self.settings.get("ai", {}).get("max_context_chars", 18000)
                )
            ),
            self.settings.get("ai", {}),
        )
        self.model_manager = ModelManager(self.ai_service)

        self.document_service = DocumentService()
        self.parser = CVParser()
        self.cv_service = CVService(self.database, self.document_service, self.parser)
        self.job_analyzer = JobAnalyzer()
        self.offer_service = OfferService(self.database, self.ai_service, self.job_analyzer)
        self.scoring = ScoringService()
        self.evaluation_service = EvaluationService(
            self.database,
            self.ai_service,
            ats=ATSEvaluator(),
            hr=HREvaluator(),
            technical=TechnicalEvaluator(),
            scoring=self.scoring,
        )
        self.optimizer = OptimizerService(self.database, self.ai_service)
        self.generator = HarvardGenerator()
        self.comparison = ComparisonService()
        self.dashboard = DashboardService(self.database)

    # ----------------------------------------------------------- settings
    def _load_settings(self) -> dict[str, Any]:
        with self.database.session() as session:
            stored = SettingsRepository(session).all()
        defaults = {
            "ai": dict(constants.DEFAULT_AI_SETTINGS),
            "weights": dict(constants.DEFAULT_WEIGHTS),
            "document": dict(constants.DEFAULT_DOCUMENT_CONFIG),
            "app": {"language": "es", "last_page": "dashboard", "show_disclaimer": True},
        }
        for key, value in defaults.items():
            if isinstance(value, dict):
                defaults[key] = {**value, **(stored.get(key) or {})}
            else:
                defaults[key] = stored.get(key, value)
        return defaults

    def reload_settings(self) -> None:
        self.settings = self._load_settings()
        self._rebuild_ai()

    def save_section(self, section: str, value: dict[str, Any]) -> None:
        with self.database.session() as session:
            SettingsRepository(session).set(section, value)
        self.settings[section] = value
        if section == "ai":
            self._rebuild_ai()
        elif section == "weights":
            self.settings["weights"] = self.scoring.normalize_weights(value)

    def _rebuild_ai(self) -> None:
        ai_settings = self.settings.get("ai", {})
        self.ai_provider = OllamaProvider(
            str(ai_settings.get("base_url", constants.DEFAULT_OLLAMA_URL))
        )
        self.ai_service = AIService(
            self.database,
            self.ai_provider,
            PromptManager(max_context_chars=int(ai_settings.get("max_context_chars", 18000))),
            ai_settings,
        )
        self.model_manager = ModelManager(self.ai_service)
        self.offer_service.ai = self.ai_service
        self.evaluation_service.ai = self.ai_service
        self.optimizer.ai = self.ai_service

    # ------------------------------------------------------------- helpers
    @property
    def weights(self) -> dict[str, float]:
        return self.scoring.normalize_weights(self.settings.get("weights"))

    @property
    def document_config(self) -> dict[str, Any]:
        return dict(self.settings.get("document") or constants.DEFAULT_DOCUMENT_CONFIG)

    @property
    def ai_settings(self) -> dict[str, Any]:
        return dict(self.settings.get("ai") or constants.DEFAULT_AI_SETTINGS)

    def ai_ready(self) -> tuple[bool, str]:
        return self.ai_service.is_ready()

    def close(self) -> None:
        self.database.dispose()
