"""Excepciones de dominio de la aplicación."""

from __future__ import annotations


class CVAnalyzerError(Exception):
    """Error base controlado por la aplicación."""


class UnsupportedDocumentError(CVAnalyzerError):
    pass


class DocumentExtractionError(CVAnalyzerError):
    pass


class OCRError(CVAnalyzerError):
    pass


class AIProviderError(CVAnalyzerError):
    pass


class AIUnavailableError(AIProviderError):
    pass


class AIValidationError(AIProviderError):
    pass


class CancelledError(CVAnalyzerError):
    pass


class EvaluationError(CVAnalyzerError):
    pass


class ExportError(CVAnalyzerError):
    pass
