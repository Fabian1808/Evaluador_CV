"""Utilidades de fechas para el análisis de trayectorias laborales."""

from __future__ import annotations

import re
from datetime import date

from app.config.constants import MONTHS_ES
from app.utils.text import normalize_for_match, strip_accents

_PRESENT_TOKENS = {"actualidad", "presente", "actual", "hoy", "current", "present"}
_MONTH_PATTERN = "|".join(sorted(MONTHS_ES, key=len, reverse=True))
_DATE_TOKEN_RE = re.compile(
    rf"(?:(?P<month>{_MONTH_PATTERN})\.?\s*(?:de\s*)?(?P<year>19|20)\d{{2}})"
    r"|(?:(?P<month_num>\d{1,2})[/-](?P<year_num>19|20)\d{2})"
    r"|(?P<year_only>(?:19|20)\d{2})",
    re.IGNORECASE,
)


def parse_date_token(token: str) -> tuple[int, int] | None:
    """Devuelve (año, mes) a partir de un token de fecha; mes 1 si es desconocido."""
    cleaned = token.strip().lower().replace(".", "")
    if cleaned in _PRESENT_TOKENS:
        today = date.today()
        return today.year, today.month
    match = _DATE_TOKEN_RE.search(cleaned)
    if not match:
        return None
    if match.group("month"):
        month = MONTHS_ES.get(normalize_for_match(match.group("month")), 1)
        year = int(re.search(r"(19|20)\d{2}", cleaned).group(0))  # type: ignore[union-attr]
        return year, month
    if match.group("month_num"):
        year = int(re.search(r"(19|20)\d{2}", cleaned).group(0))  # type: ignore[union-attr]
        month = int(match.group("month_num"))
        return year, max(1, min(12, month))
    year = int(re.search(r"(19|20)\d{2}", cleaned).group(0))  # type: ignore[union-attr]
    return year, 1


def is_current(token: str) -> bool:
    return strip_accents(token).lower().strip(" .") in _PRESENT_TOKENS


def format_period(start: str | None, end: str | None) -> str:
    start = (start or "").strip()
    end = (end or "").strip()
    if not start and not end:
        return ""
    if not end:
        return start
    if not start:
        return end
    return f"{start} – {end}"


def months_between(start: tuple[int, int], end: tuple[int, int]) -> int:
    return max(0, (end[0] - start[0]) * 12 + (end[1] - start[1]))


def experience_duration_months(periods: list[tuple[str, str]]) -> int:
    total = 0
    for start, end in periods:
        parsed_start = parse_date_token(start)
        parsed_end = parse_date_token(end)
        if parsed_start and parsed_end:
            total += months_between(parsed_start, parsed_end)
    return total


def detect_date_format(token: str) -> str:
    cleaned = token.strip().lower()
    if re.search(r"\d{1,2}[/-](?:19|20)\d{2}", cleaned):
        return "numérica (MM/AAAA)"
    if re.search(r"(?:19|20)\d{2}", cleaned) and re.search(r"[a-záéíóúñ]{3,}", cleaned):
        return "textual (Mes AAAA)"
    if re.fullmatch(r"(?:19|20)\d{2}", cleaned):
        return "solo año"
    return "otro"


def date_format_consistency(tokens: list[str]) -> tuple[bool, list[str]]:
    formats = sorted({detect_date_format(token) for token in tokens if token.strip()})
    formats = [fmt for fmt in formats if fmt != "otro"]
    return len(formats) <= 1, formats


def years_of_experience(periods: list[tuple[str, str]]) -> float:
    return round(experience_duration_months(periods) / 12, 1)


def parse_year(value: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", value)
    return int(match.group(0)) if match else None
