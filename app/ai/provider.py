"""Proveedores de inteligencia artificial local.

La aplicación solo usa por defecto Ollama (http://127.0.0.1:11434). No hay
dependencias de APIs comerciales. ``MockProvider`` existe únicamente para
pruebas automatizadas.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from app.core.errors import AIProviderError, AIUnavailableError


@dataclass
class ProviderStatus:
    available: bool
    provider: str
    base_url: str
    version: str = ""
    error: str = ""
    models_count: int = 0


@dataclass
class AIModel:
    name: str
    size_bytes: int = 0
    digest: str = ""
    modified_at: str = ""
    family: str = ""
    parameter_size: str = ""
    quantization: str = ""

    @property
    def display_name(self) -> str:
        return self.name


@dataclass
class AIResponse:
    text: str
    model: str
    provider: str
    duration_ms: int = 0
    cancelled: bool = False
    prompt_eval_count: int = 0
    eval_count: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


ProgressCallback = Callable[[str, int, int], None]


class AIProvider(ABC):
    """Interfaz desacoplada para motores de IA local."""

    name = "base"

    @abstractmethod
    def check_available(self, timeout: float = 3.0) -> ProviderStatus:
        raise NotImplementedError

    @abstractmethod
    def list_models(self, timeout: float = 10.0) -> list[AIModel]:
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        prompt: str,
        model: str,
        system: str | None = None,
        temperature: float = 0.3,
        top_p: float = 0.9,
        timeout: float = 180.0,
        cancel_event: threading.Event | None = None,
        stream_callback: Callable[[str], None] | None = None,
        num_predict: int = 1024,
    ) -> AIResponse:
        raise NotImplementedError

    @abstractmethod
    def pull_model(
        self,
        model: str,
        progress_callback: ProgressCallback | None = None,
        cancel_event: threading.Event | None = None,
    ) -> None:
        raise NotImplementedError


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://127.0.0.1:11434") -> None:
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------- interno
    def _request(self, path: str, payload: dict | None = None, timeout: float = 10.0):
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
        return urllib.request.urlopen(request, timeout=timeout)

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        if isinstance(exc, urllib.error.HTTPError):
            try:
                body = exc.read().decode("utf-8", errors="replace")
                detail = json.loads(body).get("error", body)
            except Exception:
                detail = str(exc)
            return f"Ollama respondió con error {exc.code}: {detail}"
        if isinstance(exc, urllib.error.URLError):
            return (
                "No se pudo conectar con Ollama. Verifique que esté instalado y en "
                "ejecución (ollama serve) en la dirección configurada."
            )
        if isinstance(exc, TimeoutError):
            return "La operación excedió el tiempo de espera configurado."
        return f"Error de comunicación con Ollama: {exc}"

    # -------------------------------------------------------------- estado
    def check_available(self, timeout: float = 3.0) -> ProviderStatus:
        try:
            with self._request("/api/tags", timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            models = data.get("models", []) if isinstance(data, dict) else []
            version = ""
            try:
                with self._request("/api/version", timeout=timeout) as response:
                    version = str(json.loads(response.read().decode("utf-8")).get("version", ""))
            except Exception:
                pass
            return ProviderStatus(
                available=True,
                provider=self.name,
                base_url=self.base_url,
                version=version,
                models_count=len(models),
            )
        except Exception as exc:
            return ProviderStatus(
                available=False,
                provider=self.name,
                base_url=self.base_url,
                error=self._friendly_error(exc),
            )

    def list_models(self, timeout: float = 10.0) -> list[AIModel]:
        try:
            with self._request("/api/tags", timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise AIUnavailableError(self._friendly_error(exc)) from exc
        models: list[AIModel] = []
        for item in data.get("models", []) if isinstance(data, dict) else []:
            details = item.get("details") or {}
            models.append(
                AIModel(
                    name=str(item.get("name", "")),
                    size_bytes=int(item.get("size", 0) or 0),
                    digest=str(item.get("digest", "")),
                    modified_at=str(item.get("modified_at", "")),
                    family=str(details.get("family", "")),
                    parameter_size=str(details.get("parameter_size", "")),
                    quantization=str(details.get("quantization_level", "")),
                )
            )
        return sorted(models, key=lambda model: model.name)

    # ------------------------------------------------------------ generación
    def generate(
        self,
        prompt: str,
        model: str,
        system: str | None = None,
        temperature: float = 0.3,
        top_p: float = 0.9,
        timeout: float = 180.0,
        cancel_event: threading.Event | None = None,
        stream_callback: Callable[[str], None] | None = None,
        num_predict: int = 1024,
    ) -> AIResponse:
        if not model:
            raise AIProviderError("No hay un modelo de Ollama seleccionado.")
        # Las dos operaciones de optimización se ejecutan seguidas. En equipos
        # solo con CPU, permitir el máximo genérico puede hacer que cada JSON
        # tarde varios minutos. Los resultados de reglas complementan estas
        # respuestas breves.
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            # Qwen activa razonamiento extendido por defecto en Ollama. Para
            # tareas de CV que esperan JSON breve, la salida directa evita
            # agotar el tiempo de espera redactando razonamientos internos.
            "think": False,
            "options": {
                "temperature": max(0.0, min(2.0, float(temperature))),
                "top_p": max(0.0, min(1.0, float(top_p))),
                "num_predict": max(1, int(num_predict)),
            },
        }
        if system:
            payload["system"] = system
        started = time.monotonic()
        deadline = started + max(5.0, timeout)
        collected: list[str] = []
        raw_last: dict[str, Any] = {}

        try:
            with self._request("/api/generate", payload=payload, timeout=timeout) as response:
                for raw_line in response:
                    if cancel_event is not None and cancel_event.is_set():
                        return AIResponse(
                            text="".join(collected),
                            model=model,
                            provider=self.name,
                            duration_ms=int((time.monotonic() - started) * 1000),
                            cancelled=True,
                        )
                    if time.monotonic() > deadline:
                        raise AIProviderError(
                            "La generación excedió el tiempo máximo configurado."
                        )
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("error"):
                        raise AIProviderError(str(chunk["error"]))
                    token = chunk.get("response", "")
                    if token:
                        collected.append(token)
                        if stream_callback:
                            stream_callback("".join(collected))
                    if chunk.get("done"):
                        raw_last = chunk
                        break
        except Exception as exc:
            raise AIUnavailableError(self._friendly_error(exc)) from exc

        text = "".join(collected).strip()
        if not text:
            raise AIProviderError(
                "Ollama devolvió una respuesta vacía. Pruebe con otro modelo o reduzca el contexto."
            )
        return AIResponse(
            text=text,
            model=model,
            provider=self.name,
            duration_ms=int((time.monotonic() - started) * 1000),
            prompt_eval_count=int(raw_last.get("prompt_eval_count", 0) or 0),
            eval_count=int(raw_last.get("eval_count", 0) or 0),
            raw=raw_last,
        )

    # ---------------------------------------------------------- descarga
    def pull_model(
        self,
        model: str,
        progress_callback: ProgressCallback | None = None,
        cancel_event: threading.Event | None = None,
    ) -> None:
        payload = {"model": model, "stream": True}
        try:
            with self._request("/api/pull", payload=payload, timeout=60.0) as response:
                for raw_line in response:
                    if cancel_event is not None and cancel_event.is_set():
                        return
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("error"):
                        raise AIProviderError(str(chunk["error"]))
                    status = str(chunk.get("status", "descargando"))
                    completed = int(chunk.get("completed", 0) or 0)
                    total = int(chunk.get("total", 0) or 0)
                    if progress_callback:
                        progress_callback(status, completed, total)
                    if chunk.get("status") == "success":
                        return
        except Exception as exc:
            raise AIUnavailableError(self._friendly_error(exc)) from exc

    def delete_model(self, model: str) -> None:
        payload = {"model": model}
        try:
            with self._request("/api/delete", payload=payload, timeout=30.0) as response:
                response.read()
        except Exception as exc:
            raise AIUnavailableError(self._friendly_error(exc)) from exc


class MockProvider(AIProvider):
    """Proveedor determinista para pruebas. No se usa en producción."""

    name = "mock"

    def __init__(self, responses: list[str] | None = None, available: bool = True) -> None:
        self.responses = list(responses or ["Respuesta simulada."])
        self.available = available
        self.calls: list[dict[str, Any]] = []

    def check_available(self, timeout: float = 3.0) -> ProviderStatus:
        return ProviderStatus(
            available=self.available,
            provider=self.name,
            base_url="mock://local",
            error="" if self.available else "Proveedor simulado no disponible.",
        )

    def list_models(self, timeout: float = 10.0) -> list[AIModel]:
        if not self.available:
            raise AIUnavailableError("Proveedor simulado no disponible.")
        return [AIModel(name="mock-model", size_bytes=1_000_000, family="Mock")]

    def generate(self, prompt: str, model: str, system: str | None = None,
                 temperature: float = 0.3, top_p: float = 0.9, timeout: float = 180.0,
                 cancel_event: threading.Event | None = None,
                 stream_callback: Callable[[str], None] | None = None,
                 num_predict: int = 1024) -> AIResponse:
        if not self.available:
            raise AIUnavailableError("Proveedor simulado no disponible.")
        self.calls.append({"prompt": prompt, "model": model, "system": system})
        text = self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]
        if stream_callback:
            stream_callback(text)
        return AIResponse(text=text, model=model, provider=self.name, duration_ms=1)

    def pull_model(self, model: str, progress_callback: ProgressCallback | None = None,
                   cancel_event: threading.Event | None = None) -> None:
        if progress_callback:
            progress_callback("success", 1, 1)
