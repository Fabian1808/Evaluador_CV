"""Normalización de la configuración del documento Harvard."""

from __future__ import annotations

from typing import Any

from app.config.constants import DEFAULT_DOCUMENT_CONFIG, HARVARD_FONTS


def normalize_config(config: dict[str, Any] | None) -> dict[str, Any]:
    result = {**DEFAULT_DOCUMENT_CONFIG, **(config or {})}
    result["font_family"] = (
        result.get("font_family") if result.get("font_family") in HARVARD_FONTS else "Calibri"
    )
    ranges = {
        "name_size": (17.0, 20.0),
        "headline_size": (10.0, 11.0),
        "heading_size": (11.0, 12.0),
        "body_size": (10.0, 11.0),
        "date_size": (9.0, 10.0),
        "contact_size": (9.0, 10.0),
        "line_spacing": (0.9, 1.5),
        "margin_top_cm": (1.0, 3.0),
        "margin_bottom_cm": (1.0, 3.0),
        "margin_left_cm": (1.0, 3.0),
        "margin_right_cm": (1.0, 3.0),
        "space_after_pt": (0.0, 12.0),
        "section_space_pt": (4.0, 20.0),
    }
    for key, (minimum, maximum) in ranges.items():
        try:
            value = float(result.get(key, DEFAULT_DOCUMENT_CONFIG[key]))
        except (TypeError, ValueError):
            value = float(DEFAULT_DOCUMENT_CONFIG[key])
        result[key] = max(minimum, min(maximum, value))
    result["uppercase_headings"] = bool(result.get("uppercase_headings", True))
    result["show_separator"] = bool(result.get("show_separator", True))
    result["alignment"] = (
        "center" if str(result.get("alignment", "left")) == "center" else "left"
    )
    return result
