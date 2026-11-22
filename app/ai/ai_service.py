"""Servicio de IA: orquesta proveedor, prompts, validación y caché local."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from app.ai.prompt_manager import PromptManager
from app.ai.provider import AIProvider, AIResponse, ProviderStatus
from app.ai.response_validator import ResponseValidator
from app.core.errors import AIProviderError, AIUnavailableError, CancelledError
from app.database.repositories import AIRequestRepository, SettingsRepository
from app.database.session import Database
from app.utils.text import hash_text


@dataclass
class AIResult:
    text: str
    model: str
    provider: str
    cached: bool = False
    duration_ms: int = 0
    prompt_type: str = ""


class AIService:
    def __init__(
        self,
        database: Database,
        provider: AIProvider,
        prompt_manager: PromptManager | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None:
        self.database = database
        self.provider = provider
        self.prompts = prompt_manager or PromptManager()
        self.validator = ResponseValidator()
        self.settings = settings or {}

    # ----------------------------------------------------------- configuración
    def reload_settings(self) -> None:
        with self.database.session() as session:
            self.settings = SettingsRepository(session).get("ai", {}) or {}

    @property
    def provider_name(self) -> str:
        return self.provider.name

    @property
    def model(self) -> str:
        return str(self.settings.get("model", "") or "")

    def status(self) -> ProviderStatus:
        return self.provider.check_available()

    def list_models(self):
        return self.provider.list_models()

    def is_ready(self) -> tuple[bool, str]:
        status = self.status()
        if not status.available:
            return False, status.error or "Ollama no está disponible."
        if not self.model:
            return False, "No hay un modelo activo seleccionado."
        try:
            installed = {model.name for model in self.provider.list_models()}
        except Exception as exc:
            return False, str(exc)
        if self.model not in installed:
            return False, f"El modelo '{self.model}' no está instalado."
        return True, ""

    # ------------------------------------------------------------- generación
    def generate_text(
        self,
        prompt_type: str,
        system: str,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
        cancel_event: threading.Event | None = None,
        use_cache: bool | None = None,
        stream_callback=None,  # type: ignore[no-untyped-def]
    ) -> AIResult:
        active_model = model or self.model
        if not active_model:
            raise AIUnavailableError(
                "No hay un modelo de IA configurado. Abra Configuración → IA local."
            )
        temperature = float(
            temperature if temperature is not None else self.settings.get("temperature", 0.3)
        )
        timeout = float(
            timeout if timeout is not None else self.settings.get("timeout_seconds", 180)
        )
        cache_enabled = (
            bool(self.settings.get("use_cache", True)) if use_cache is None else use_cache
        )
        prompt_hash = hash_text(f"{self.provider.name}|{active_model}|{prompt_type}|{prompt}")

        if cache_enabled:
            with self.database.session() as session:
                cached = AIRequestRepository(session).find_cached(prompt_hash)
                if cached and cached.response_text:
                    return AIResult(
                        text=cached.response_text,
                        model=cached.model,
                        provider=cached.provider,
                        cached=True,
                        duration_ms=0,
                        prompt_type=prompt_type,
                    )

        try:
            response: AIResponse = self.provider.generate(
                prompt=prompt,
                model=active_model,
                system=system,
                temperature=temperature,
                top_p=float(self.settings.get("top_p", 0.9)),
                timeout=timeout,
                cancel_event=cancel_event,
                stream_callback=stream_callback,
                num_predict={
                    "optimization": 512,
                    "missing_information": 256,
                }.get(prompt_type, 1024),
            )
        except Exception as exc:
            self._record_request(
                prompt_type, prompt_hash, active_model, None, 0, False, str(exc)
            )
            raise

        if response.cancelled:
            self._record_request(
                prompt_type, prompt_hash, active_model, None, response.duration_ms,
                False, "Cancelado por el usuario",
            )
            raise CancelledError("Operación cancelada por el usuario.")

        self._record_request(
            prompt_type, prompt_hash, active_model, response.text,
            response.duration_ms, True, None,
        )
        return AIResult(
            text=response.text,
            model=response.model,
            provider=response.provider,
            cached=False,
            duration_ms=response.duration_ms,
            prompt_type=prompt_type,
        )

    def generate_structured(
        self,
        prompt_type: str,
        system: str,
        prompt: str,
        model: str | None = None,
        cancel_event: threading.Event | None = None,
        use_cache: bool | None = None,
    ) -> tuple[Any, AIResult]:
        result = self.generate_text(
            prompt_type=prompt_type,
            system=system,
            prompt=prompt,
            model=model,
            cancel_event=cancel_event,
            use_cache=use_cache,
        )
        data = self.validator.extract_json(result.text)
        return data, result

    def _record_request(
        self,
        prompt_type: str,
        prompt_hash: str,
        model: str,
        response_text: str | None,
        duration_ms: int,
        success: bool,
        error: str | None,
    ) -> None:
        try:
            with self.database.session() as session:
                AIRequestRepository(session).create(
                    provider=self.provider.name,
                    model=model,
                    prompt_type=prompt_type,
                    prompt_hash=prompt_hash,
                    response_text=response_text,
                    duration_ms=duration_ms,
                    success=success,
                    error=error,
                )
        except Exception:
            # El registro de auditoría nunca debe interrumpir la operación principal.
            pass

    # -------------------------------------------------------------- descarga
    def pull_model(self, model: str, progress_callback=None, cancel_event=None) -> None:  # type: ignore[no-untyped-def]
        self.provider.pull_model(
            model, progress_callback=progress_callback, cancel_event=cancel_event
        )

    # -------------------------------------------------------------- resumen
    def evaluation_summary(
        self,
        ats: float,
        hr: float,
        technical: float,
        overall: float,
        strengths: list[str],
        weaknesses: list[str],
        missing: list[str],
        offer: str = "",
        cancel_event: threading.Event | None = None,
    ) -> str | None:
        ready, _reason = self.is_ready()
        if not ready:
            return None
        system, prompt = self.prompts.evaluation_summary(
            ats, hr, technical, overall, strengths, weaknesses, missing, offer
        )
        try:
            result = self.generate_text(
                "evaluation_summary", system, prompt, cancel_event=cancel_event
            )
            return result.text.strip()
        except (AIProviderError, AIUnavailableError, CancelledError):
            return None
