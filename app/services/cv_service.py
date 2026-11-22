"""Servicio de importación y versionado de CV."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import paths
from app.database.models import Candidate, CV
from app.database.repositories import CVRepository
from app.database.session import Database
from app.services.cv_parser import CVParser, content_to_text, sections_from_content
from app.services.document_service import DocumentService
from app.utils.files import copy_to_storage, delete_file_quietly


@dataclass
class ImportResult:
    cv_id: int
    version_id: int
    warnings: list[str] = field(default_factory=list)
    method: str = ""
    words: int = 0


class CVService:
    def __init__(
        self,
        database: Database,
        document_service: DocumentService | None = None,
        parser: CVParser | None = None,
    ) -> None:
        self.database = database
        self.documents = document_service or DocumentService()
        self.parser = parser or CVParser()

    def import_cv(
        self,
        candidate_id: int,
        file_path: str | Path,
        title: str | None = None,
        use_ocr: bool = True,
    ) -> ImportResult:
        source = Path(file_path)
        if not source.exists():
            raise FileNotFoundError(f"No se encontró el archivo: {source}")
        if source.suffix.lower() not in {".pdf", ".docx"}:
            raise ValueError("Solo se admiten archivos PDF o DOCX.")

        with self.database.session() as session:
            candidate = session.get(Candidate, candidate_id)
            if candidate is None:
                raise ValueError("El candidato seleccionado no existe.")
            candidate_name = candidate.full_name
            stored = copy_to_storage(source, "cvs")
            existing = session.query(CV).filter(
                CV.candidate_id == candidate_id,
                CV.stored_path == str(stored),
            ).first()
            if existing is not None:
                raise ValueError(
                    f"Este documento ya fue importado para el candidato (CV #{existing.id})."
                )

        extraction = self.documents.extract(stored, use_ocr=use_ocr)
        parsed = self.parser.parse(extraction.text, fallback_name=candidate_name)
        quality = self.documents.analyze_text_quality(extraction.text)
        diagnostics = {
            **extraction.diagnostics,
            "extraction_method": extraction.method,
            "avg_line_length": quality["avg_line_length"],
            "lines": quality["lines"],
            "ocr_available": self.documents.ocr_available()
            if hasattr(self.documents, "ocr_available")
            else None,
        }
        warnings = list(dict.fromkeys(extraction.warnings + parsed.warnings))
        default_title = source.stem.replace("_", " ").strip() or "CV sin título"

        with self.database.session() as session:
            repo = CVRepository(session)
            cv = repo.create(
                candidate_id=candidate_id,
                title=title.strip() if title and title.strip() else default_title,
                original_filename=source.name,
                stored_path=str(stored),
                file_type=source.suffix.lower().lstrip("."),
                raw_text=extraction.text,
                extraction_method=extraction.method,
                page_count=extraction.page_count,
                diagnostics=diagnostics,
                warnings=warnings,
                is_master=True,
            )
            version = repo.create_version(
                cv_id=cv.id,
                label="Original importado",
                content=parsed.content,
                raw_text=extraction.text,
                source="original",
                sections=parsed.sections,
            )
            return ImportResult(
                cv_id=cv.id,
                version_id=version.id,
                warnings=warnings,
                method=extraction.method,
                words=extraction.words,
            )

    def create_version(
        self,
        cv_id: int,
        content: dict[str, Any],
        raw_text: str | None = None,
        label: str = "Versión editada",
        source: str = "user_edit",
        parent_version_id: int | None = None,
    ) -> int:
        text = raw_text if raw_text is not None else content_to_text(content)
        with self.database.session() as session:
            cv = CVRepository(session).get(cv_id)
            if cv is None:
                raise ValueError("El CV no existe.")
            version = CVRepository(session).create_version(
                cv_id=cv_id,
                label=label,
                content=content,
                raw_text=text,
                source=source,
                parent_version_id=parent_version_id,
                sections=sections_from_content(content),
            )
            return version.id

    def delete_cv(self, cv_id: int) -> None:
        with self.database.session() as session:
            repo = CVRepository(session)
            cv = repo.get(cv_id)
            if cv is None:
                return
            stored_path = cv.stored_path
            repo.delete(cv)
        delete_file_quietly(stored_path)

    def reparse_version(self, version_id: int, label: str = "Reestructurada") -> int:
        """Crea una nueva versión a partir del texto de una existente."""
        with self.database.session() as session:
            repo = CVRepository(session)
            version = repo.get_version(version_id)
            if version is None:
                raise ValueError("La versión no existe.")
            parsed = self.parser.parse(version.raw_text, fallback_name=None)
            new_version = repo.create_version(
                cv_id=version.cv_id,
                label=label,
                content=parsed.content,
                raw_text=version.raw_text,
                source="reparsed",
                parent_version_id=version.id,
                sections=parsed.sections,
            )
            return new_version.id
