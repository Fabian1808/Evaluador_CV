"""Utilidades comunes para construir contextos de evaluación."""

from __future__ import annotations

import re
from typing import Any

from app.utils.text import (
    normalize_for_match,
    sentences,
    split_bullets,
    word_count,
)


def section_contexts(content: dict[str, Any]) -> dict[str, str]:
    """Devuelve el texto de cada sección estructurada del CV."""
    personal = content.get("personal") or {}
    experience_parts: list[str] = []
    for entry in content.get("experience") or []:
        title = " | ".join(filter(None, [entry.get("role", ""), entry.get("company", "")]))
        period = entry.get("period", "")
        experience_parts.append(f"{title} {period}".strip())
        experience_parts.extend(entry.get("bullets") or [])
        if not entry.get("bullets") and entry.get("description"):
            experience_parts.append(str(entry["description"]))

    education_parts: list[str] = []
    for entry in content.get("education") or []:
        education_parts.append(
            " | ".join(
                filter(None, [entry.get("degree", ""), entry.get("institution", "")])
            )
        )
        if entry.get("details"):
            education_parts.append(str(entry["details"]))

    skills = content.get("skills") or {}
    project_parts = [
        f"{project.get('name', '')}: {project.get('description', '')}"
        for project in content.get("projects") or []
    ]
    return {
        "summary": str(content.get("summary") or ""),
        "experience": "\n".join(filter(None, experience_parts)),
        "education": "\n".join(filter(None, education_parts)),
        "skills": "\n".join(
            [
                ", ".join(skills.get("technical") or []),
                ", ".join(skills.get("soft") or []),
            ]
        ).strip(),
        "projects": "\n".join(project_parts),
        "certifications": "\n".join(content.get("certifications") or []),
        "languages": "\n".join(
            f"{item.get('language', '')} {item.get('level', '')}".strip()
            for item in content.get("languages") or []
        ),
        "achievements": "\n".join(content.get("achievements") or []),
        "additional": "\n".join(content.get("additional") or []),
        "personal": "\n".join(
            str(value) for value in personal.values() if value
        ),
        "headline": str(personal.get("headline") or ""),
    }


def experience_sentences(content: dict[str, Any]) -> list[tuple[str, str]]:
    """Oraciones de experiencia/proyectos con una etiqueta de contexto."""
    result: list[tuple[str, str]] = []
    for entry in content.get("experience") or []:
        label = " | ".join(filter(None, [entry.get("role", ""), entry.get("company", "")]))
        for bullet in entry.get("bullets") or []:
            for sentence in sentences(str(bullet)):
                if sentence.strip():
                    result.append((sentence.strip(), label or "Experiencia"))
        if not entry.get("bullets") and entry.get("description"):
            for sentence in sentences(str(entry["description"])):
                if sentence.strip():
                    result.append((sentence.strip(), label or "Experiencia"))
    for project in content.get("projects") or []:
        text = f"{project.get('name', '')}: {project.get('description', '')}"
        for sentence in sentences(text):
            if sentence.strip():
                result.append((sentence.strip(), "Proyectos"))
    return result


def all_experience_text(content: dict[str, Any]) -> str:
    return "\n".join(text for text, _label in experience_sentences(content))


def technical_skills(content: dict[str, Any]) -> list[str]:
    return list((content.get("skills") or {}).get("technical") or [])


def soft_skills(content: dict[str, Any]) -> list[str]:
    return list((content.get("skills") or {}).get("soft") or [])


def all_bullets(content: dict[str, Any]) -> list[str]:
    bullets: list[str] = []
    for entry in content.get("experience") or []:
        bullets.extend(entry.get("bullets") or [])
    return bullets


def offer_keyword_list(
    requirements: list[dict[str, Any]] | None,
    offer_text: str = "",
    offer_keywords: list[str] | None = None,
) -> list[str]:
    keywords: list[str] = []
    for item in requirements or []:
        keywords.extend(item.get("keywords") or [])
    keywords.extend(offer_keywords or [])
    if not keywords and offer_text:
        from app.utils.text import extract_tech_keywords

        keywords = extract_tech_keywords(offer_text)
    seen: set[str] = set()
    result = []
    for keyword in keywords:
        key = normalize_for_match(keyword)
        if key and key not in seen:
            seen.add(key)
            result.append(keyword)
    return result


def contains_keyword(text: str, keyword: str) -> bool:
    normalized = normalize_for_match(text)
    needle = normalize_for_match(keyword)
    if not needle:
        return False
    return bool(
        re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", normalized)
    )


def find_context(text: str, keyword: str) -> str | None:
    for sentence in sentences(text):
        if contains_keyword(sentence, keyword):
            return sentence.strip()[:260]
    return None


def text_metrics(content: dict[str, Any], raw_text: str) -> dict[str, Any]:
    bullets = all_bullets(content)
    return {
        "words": word_count(raw_text),
        "bullets": len(bullets),
        "experience_entries": len(content.get("experience") or []),
        "technical_skills": len(technical_skills(content)),
        "soft_skills": len(soft_skills(content)),
        "has_summary": bool(str(content.get("summary") or "").strip()),
        "summary_words": word_count(str(content.get("summary") or "")),
    }
