"""Comparación de versiones de CV."""

from __future__ import annotations

import difflib
from typing import Any

from app.services.cv_parser import content_to_text
from app.utils.text import (
    extract_keywords,
    extract_tech_keywords,
    similarity,
    word_count,
)


class ComparisonService:
    def compare_versions(self, version_a, version_b) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        text_a = version_a.raw_text or content_to_text(version_a.content or {})
        text_b = version_b.raw_text or content_to_text(version_b.content or {})
        content_a = version_a.content or {}
        content_b = version_b.content or {}

        skills_a = set((content_a.get("skills") or {}).get("technical") or [])
        skills_b = set((content_b.get("skills") or {}).get("technical") or [])
        keywords_a = set(extract_keywords(text_a, 30))
        keywords_b = set(extract_keywords(text_b, 30))

        diff_lines = list(
            difflib.unified_diff(
                text_a.splitlines(),
                text_b.splitlines(),
                fromfile=str(version_a.label),
                tofile=str(version_b.label),
                lineterm="",
                n=1,
            )
        )
        added = [line[1:] for line in diff_lines if line.startswith("+") and not line.startswith("+++")]
        removed = [line[1:] for line in diff_lines if line.startswith("-") and not line.startswith("---")]

        return {
            "similarity": round(similarity(text_a, text_b) * 100, 1),
            "words_a": word_count(text_a),
            "words_b": word_count(text_b),
            "words_delta": word_count(text_b) - word_count(text_a),
            "experience_a": len(content_a.get("experience") or []),
            "experience_b": len(content_b.get("experience") or []),
            "skills_added": sorted(skills_b - skills_a, key=str.lower),
            "skills_removed": sorted(skills_a - skills_b, key=str.lower),
            "keywords_added": sorted(keywords_b - keywords_a, key=str.lower)[:25],
            "keywords_removed": sorted(keywords_a - keywords_b, key=str.lower)[:25],
            "lines_added": added[:120],
            "lines_removed": removed[:120],
            "diff": diff_lines[:250],
            "version_a": version_a,
            "version_b": version_b,
        }

    @staticmethod
    def keyword_gap(cv_text: str, offer_text: str) -> dict[str, list[str]]:
        cv_keywords = set(extract_tech_keywords(cv_text))
        offer_keywords = set(extract_tech_keywords(offer_text))
        return {
            "present": sorted(cv_keywords & offer_keywords, key=str.lower),
            "missing": sorted(offer_keywords - cv_keywords, key=str.lower),
            "extra": sorted(cv_keywords - offer_keywords, key=str.lower),
        }
