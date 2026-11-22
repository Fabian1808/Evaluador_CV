"""Administración de modelos locales y recomendaciones de hardware."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from app.ai.ai_service import AIService
from app.ai.provider import AIModel
from app.config.constants import KNOWN_MODELS
from app.utils.files import human_size


@dataclass
class ModelStatus:
    name: str
    family: str
    parameters: str
    installed: bool
    size_bytes: int
    size_label: str
    ram_required_gb: float
    fit: str
    quality: str
    note: str
    active: bool = False
    modified_at: str = ""


class ModelManager:
    """Combina el catálogo recomendado con los modelos realmente instalados."""

    def __init__(self, ai_service: AIService) -> None:
        self.ai = ai_service

    # ----------------------------------------------------------- hardware
    @staticmethod
    def hardware() -> dict[str, Any]:
        try:
            import psutil

            memory = psutil.virtual_memory()
            return {
                "total_ram_gb": round(memory.total / (1024 ** 3), 1),
                "available_ram_gb": round(memory.available / (1024 ** 3), 1),
                "cpu_count": psutil.cpu_count(logical=True) or 0,
            }
        except Exception:
            return {"total_ram_gb": 0.0, "available_ram_gb": 0.0, "cpu_count": 0}

    @staticmethod
    def _fit(ram_required: float, available: float) -> str:
        if available <= 0:
            return "Desconocido"
        if available >= ram_required * 1.35:
            return "Cómodo"
        if available >= ram_required:
            return "Ajustado"
        return "Insuficiente"

    # -------------------------------------------------------------- catálogo
    def list_status(self, active_model: str | None = None) -> list[ModelStatus]:
        hardware = self.hardware()
        available = hardware["available_ram_gb"]
        installed_models: dict[str, AIModel] = {}
        error = ""
        try:
            installed_models = {model.name: model for model in self.ai.provider.list_models()}
        except Exception as exc:
            error = str(exc)

        active = active_model if active_model is not None else self.ai.model
        rows: list[ModelStatus] = []
        catalog_names = {item["name"] for item in KNOWN_MODELS}

        for item in KNOWN_MODELS:
            installed = item["name"] in installed_models
            model = installed_models.get(item["name"])
            size_bytes = model.size_bytes if model else int(item["size_gb"] * 1024 ** 3)
            rows.append(
                ModelStatus(
                    name=item["name"],
                    family=item["family"],
                    parameters=item["parameters"],
                    installed=installed,
                    size_bytes=size_bytes,
                    size_label=human_size(size_bytes),
                    ram_required_gb=float(item["ram_gb"]),
                    fit=self._fit(float(item["ram_gb"]), available),
                    quality=item["quality"],
                    note=item["note"],
                    active=item["name"] == active,
                    modified_at=model.modified_at if model else "",
                )
            )

        # Modelos instalados que no están en el catálogo recomendado.
        for name, model in sorted(installed_models.items()):
            if name in catalog_names:
                continue
            size_gb = model.size_bytes / (1024 ** 3)
            rows.append(
                ModelStatus(
                    name=name,
                    family=model.family or "Local",
                    parameters=model.parameter_size or "—",
                    installed=True,
                    size_bytes=model.size_bytes,
                    size_label=human_size(model.size_bytes),
                    ram_required_gb=round(size_gb * 1.2 + 1, 1),
                    fit=self._fit(size_gb * 1.2 + 1, available),
                    quality="No evaluada",
                    note="Modelo instalado fuera del catálogo recomendado.",
                    active=name == active,
                    modified_at=model.modified_at,
                )
            )

        self.last_error = error
        return rows

    def installed_names(self) -> list[str]:
        try:
            return [model.name for model in self.ai.provider.list_models()]
        except Exception:
            return []

    def recommend(self) -> ModelStatus | None:
        rows = [row for row in self.list_status() if row.installed]
        if not rows:
            candidates = [
                row for row in self.list_status()
                if row.fit in {"Cómodo", "Ajustado"}
            ]
            return candidates[0] if candidates else None
        order = {"Muy buena": 0, "Buena": 1, "Aceptable": 2, "No evaluada": 3}
        rows.sort(key=lambda row: (order.get(row.quality, 4), row.ram_required_gb))
        return rows[0]

    # ------------------------------------------------------------- descarga
    def pull(
        self,
        model: str,
        progress_callback=None,  # type: ignore[no-untyped-def]
        cancel_event: threading.Event | None = None,
    ) -> None:
        self.ai.pull_model(
            model, progress_callback=progress_callback, cancel_event=cancel_event
        )

    # ------------------------------------------------------------ benchmark
    def benchmark(self, model: str, cancel_event: threading.Event | None = None) -> dict[str, Any]:
        """Prueba comparativa breve de escritura, extracción y JSON estructurado.

        No es un benchmark académico: sirve para descartar modelos que no siguen
        instrucciones o no devuelven JSON válido en este equipo.
        """
        results: list[dict[str, Any]] = []
        checks = [
            ("structured", "Respuesta estructurada"),
            ("extraction", "Extracción de requisitos"),
            ("writing", "Redacción profesional"),
        ]
        for kind, label in checks:
            if cancel_event is not None and cancel_event.is_set():
                break
            system, prompt = self.ai.prompts.benchmark_prompt(kind)
            entry: dict[str, Any] = {"check": label, "kind": kind, "ok": False, "score": 0, "detail": ""}
            try:
                result = self.ai.generate_text(
                    f"benchmark_{kind}", system, prompt, model=model,
                    use_cache=False, cancel_event=cancel_event,
                )
                text = result.text.strip()
                if kind in {"structured", "extraction"}:
                    data = self.ai.validator.extract_json(text)
                    if isinstance(data, dict) and data:
                        entry["ok"] = True
                        entry["score"] = 90 if kind == "structured" else 100
                        entry["detail"] = "JSON válido y utilizable."
                    else:
                        entry["detail"] = "JSON válido pero vacío."
                else:
                    words = len(text.split())
                    if 8 <= words <= 80:
                        entry["ok"] = True
                        entry["score"] = 80
                        entry["detail"] = "Respuesta breve y con formato correcto."
                    else:
                        entry["score"] = 40
                        entry["detail"] = "Longitud poco adecuada para una propuesta de CV."
                entry["duration_ms"] = result.duration_ms
            except Exception as exc:
                entry["detail"] = str(exc)
            results.append(entry)
        total = sum(item["score"] for item in results) / max(1, len(results))
        return {
            "model": model,
            "results": results,
            "average": round(total, 1),
            "verdict": (
                "Recomendado para esta aplicación" if total >= 80
                else "Utilizable con revisión manual" if total >= 50
                else "No recomendado: no sigue bien las instrucciones"
            ),
        }
