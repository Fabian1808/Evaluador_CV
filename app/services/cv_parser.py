"""Parser heurístico de CV: detecta secciones y estructura la información.

No inventa datos: todo lo que devuelve proviene del texto extraído. Cuando un
campo no puede determinarse se deja vacío y se registra una advertencia para
que el usuario lo complete.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.config.constants import (
    LANGUAGE_LEVELS,
    SECTION_ALIASES,
    SECTION_LABELS,
    SOFT_SKILL_HINTS,
    TECH_KEYWORDS,
)
from app.utils.dates import format_period, is_current, parse_date_token
from app.utils.text import (
    extract_emails,
    extract_linkedin,
    extract_phones,
    extract_tech_keywords,
    extract_urls,
    find_date_ranges,
    normalize_for_match,
    normalize_whitespace,
    split_bullets,
    truncate,
    word_count,
)

_DEGREE_HINTS = (
    "licenciatura", "ingeniería", "ingenieria", "técnico", "tecnico", "maestría",
    "maestria", "máster", "master", "mba", "bachiller", "doctorado", "diplomado",
    "curso", "certificación", "certificacion", "grado", "título", "titulo",
    "bachelor", "degree", "phd",
)
_INSTITUTION_HINTS = (
    "universidad", "instituto", "escuela", "colegio", "politécnico", "politecnico",
    "academia", "centro de estudios", "university", "college", "school",
)
_LANGUAGE_NAMES = (
    "inglés", "ingles", "español", "espanol", "francés", "frances", "alemán",
    "aleman", "portugués", "portugues", "italiano", "mandarín", "mandarin",
    "japonés", "japones", "ruso", "árabe", "arabe", "coreano", "neerlandés",
    "neerlandes", "catalán", "catalan", "english", "spanish", "french", "german",
)
_SECTION_NUMBER_RE = re.compile(r"^\s*(?:\d{1,2}[.)]|[IVX]{1,4}[.)])\s*", re.IGNORECASE)
_DATE_IN_LINE_RE = re.compile(
    r"(?:[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}\.?\s*(?:de\s*)?)?(?:19|20)\d{2}"
    r"(?:\s*(?:-|–|—|a|hasta)\s*(?:[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}\.?\s*(?:de\s*)?)?"
    r"(?:19|20)\d{2}|actualidad|presente|actual)?",
    re.IGNORECASE,
)


@dataclass
class ParsedCV:
    content: dict[str, Any]
    sections: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.content.get("personal", {}).get("name", "")


def _clean_heading(line: str) -> str:
    value = _SECTION_NUMBER_RE.sub("", line.strip())
    value = value.strip(" :|·-–—")
    return value


def detect_heading(line: str) -> str | None:
    """Devuelve la clave de sección si la línea es un encabezado convencional."""
    if len(line.strip()) > 80 or len(line.split()) > 8:
        return None
    normalized = normalize_for_match(_clean_heading(line))
    if not normalized:
        return None
    for key, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            if normalized == normalize_for_match(alias):
                return key
    return None


def _is_contact_line(line: str) -> bool:
    normalized = line.lower()
    return (
        "@" in line
        or "http" in normalized
        or "linkedin" in normalized
        or bool(re.fullmatch(r"[\d\s()+\-./]{7,}", line.strip()))
    )


def _looks_like_phone(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if not (7 <= len(digits) <= 15):
        return False
    if re.fullmatch(r"(19|20)\d{2}[\s-]*(19|20)\d{2}", value.strip()):
        return False
    return True


class CVParser:
    """Convierte texto plano de un CV en un diccionario estructurado."""

    def parse(self, text: str, fallback_name: str | None = None) -> ParsedCV:
        text = normalize_whitespace(text)
        lines = [line.strip() for line in text.splitlines()]
        warnings: list[str] = []

        headings: list[tuple[int, str, str]] = []
        for index, line in enumerate(lines):
            if not line:
                continue
            key = detect_heading(line)
            if key:
                headings.append((index, key, _clean_heading(line)))

        # Evita encabezados duplicados consecutivos.
        filtered: list[tuple[int, str, str]] = []
        for item in headings:
            if filtered and filtered[-1][1] == item[1]:
                continue
            filtered.append(item)
        headings = filtered

        header_end = headings[0][0] if headings else min(len(lines), 25)
        header_lines = [line for line in lines[:header_end] if line]

        personal = self._parse_personal(header_lines, text, fallback_name)
        sections: list[dict[str, Any]] = []
        section_map: dict[str, str] = {}

        for idx, (line_index, key, title) in enumerate(headings):
            end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
            body = "\n".join(line for line in lines[line_index + 1 : end] if line.strip())
            body = normalize_whitespace(body)
            section_map[key] = body
            sections.append(
                {
                    "section_type": key,
                    "title": SECTION_LABELS.get(key, title),
                    "content": body,
                    "data": None,
                    "data_origin": "ORIGINAL_DOCUMENT",
                }
            )

        if not headings:
            warnings.append(
                "No se detectaron encabezados de sección convencionales. "
                "La estructura del CV puede dificultar la lectura por parte de un ATS."
            )

        content: dict[str, Any] = {
            "personal": personal,
            "summary": "",
            "experience": [],
            "education": [],
            "skills": {"technical": [], "soft": [], "tools": []},
            "certifications": [],
            "languages": [],
            "projects": [],
            "achievements": [],
            "additional": [],
            "section_order": [item[1] for item in headings],
        }

        # Perfil profesional.
        summary = section_map.get("perfil", "").strip()
        if not summary:
            summary = self._fallback_summary(lines, header_end)
            if summary:
                warnings.append(
                    "No se encontró una sección de perfil profesional. Se usó el primer "
                    "párrafo como referencia; confirme que corresponde al perfil."
                )
        content["summary"] = truncate(summary, 2000) if summary else ""

        # Experiencia.
        if "experiencia" in section_map:
            content["experience"] = self._parse_experience(section_map["experiencia"])
        else:
            inferred = self._infer_experience(text)
            if inferred:
                content["experience"] = inferred
                warnings.append(
                    "No se encontró una sección de experiencia claramente delimitada. "
                    "Se detectaron bloques por fechas; revise la estructura."
                )

        # Educación.
        if "educacion" in section_map:
            content["education"] = self._parse_education(section_map["educacion"])

        # Competencias.
        technical, soft = self._parse_skills(
            "\n".join(
                filter(
                    None,
                    [
                        section_map.get("competencias_tecnicas", ""),
                        section_map.get("competencias_blandas", ""),
                    ],
                )
            )
        )
        if not technical:
            technical = extract_tech_keywords(text)
        content["skills"]["technical"] = technical
        content["skills"]["soft"] = soft
        content["skills"]["tools"] = [
            item for item in technical if normalize_for_match(item) in {
                normalize_for_match(k) for k in TECH_KEYWORDS
            }
        ]

        # Idiomas.
        content["languages"] = self._parse_languages(
            section_map.get("idiomas", ""), text if "idiomas" in section_map else ""
        )

        # Certificaciones.
        content["certifications"] = self._parse_list_section(
            section_map.get("certificaciones", "")
        )

        # Proyectos.
        content["projects"] = self._parse_projects(section_map.get("proyectos", ""))

        # Logros.
        content["achievements"] = self._parse_list_section(
            section_map.get("logros", "")
        )[:12]

        # Información adicional.
        content["additional"] = self._parse_list_section(
            section_map.get("adicional", "")
        )[:20]

        # Advertencias de completitud.
        if not personal.get("email") and not personal.get("phone"):
            warnings.append(
                "No se detectaron datos de contacto. Un CV sin correo o teléfono "
                "dificulta el seguimiento por parte del reclutador."
            )
        if not content["experience"]:
            warnings.append(
                "No se pudo estructurar experiencia laboral. Revise que las fechas y "
                "los cargos estén presentes en el documento."
            )
        if content["experience"] and not any(
            entry.get("start_date") or entry.get("end_date")
            for entry in content["experience"]
        ):
            warnings.append(
                "La experiencia no incluye fechas legibles. Los ATS suelen requerir "
                "periodos claros (mes y año)."
            )
        if not content["education"]:
            warnings.append("No se detectó formación académica.")
        if not content["skills"]["technical"]:
            warnings.append("No se detectaron competencias técnicas.")
        if word_count(text) < 150:
            warnings.append(
                "El contenido extraído es muy breve. Verifique que el documento no sea "
                "una imagen o que la extracción haya sido completa."
            )

        # Secciones sintéticas para persistencia y edición.
        synthetic = [
            {
                "section_type": "personal",
                "title": SECTION_LABELS["personal"],
                "content": "\n".join(
                    filter(
                        None,
                        [
                            personal.get("name", ""),
                            personal.get("headline", ""),
                            personal.get("email", ""),
                            personal.get("phone", ""),
                            personal.get("location", ""),
                            personal.get("linkedin", ""),
                        ],
                    )
                ),
                "data": personal,
                "data_origin": "ORIGINAL_DOCUMENT",
            },
            {
                "section_type": "perfil",
                "title": SECTION_LABELS["perfil"],
                "content": content["summary"],
                "data": None,
                "data_origin": "ORIGINAL_DOCUMENT",
            },
        ]
        for key in ("experiencia", "educacion", "competencias_tecnicas",
                    "competencias_blandas", "certificaciones", "idiomas",
                    "proyectos", "logros", "adicional"):
            if key in section_map:
                synthetic.append(
                    {
                        "section_type": key,
                        "title": SECTION_LABELS.get(key, key),
                        "content": section_map[key],
                        "data": None,
                        "data_origin": "ORIGINAL_DOCUMENT",
                    }
                )

        return ParsedCV(content=content, sections=synthetic, warnings=warnings)

    # ------------------------------------------------------------- Personal
    def _parse_personal(
        self, header_lines: list[str], full_text: str, fallback_name: str | None
    ) -> dict[str, Any]:
        emails = extract_emails(full_text)
        phones = [phone for phone in extract_phones(full_text) if _looks_like_phone(phone)]
        linkedin = extract_linkedin(full_text)
        urls = [url for url in extract_urls(full_text) if "linkedin.com" not in url.lower()]

        name = ""
        headline = ""
        location = ""

        for line in header_lines:
            normalized = normalize_for_match(line)
            if normalized.startswith(("nombre:", "nombre ")):
                name = re.split(r"[:：]", line, maxsplit=1)[-1].strip()
            if normalized.startswith(("título:", "titulo:", "puesto:", "cargo:", "headline:")):
                headline = re.split(r"[:：]", line, maxsplit=1)[-1].strip()
            if normalized.startswith(("ubicación:", "ubicacion:", "ciudad:", "location:")):
                location = re.split(r"[:：]", line, maxsplit=1)[-1].strip()

        candidates = [
            line for line in header_lines
            if line
            and not _is_contact_line(line)
            and not detect_heading(line)
            and not line.lower().startswith(("currículum", "curriculum", "cv ", "hoja de vida"))
            and 1 <= len(line.split()) <= 7
            and len(line) <= 70
            and re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", line)
        ]
        if not name and candidates:
            name = candidates[0].strip(" |·-–—")
        if not headline:
            for line in candidates[1:3]:
                if normalize_for_match(line) != normalize_for_match(name) and len(line) <= 80:
                    headline = line.strip(" |·-–—")
                    break
        if not name and fallback_name:
            name = fallback_name

        if not location:
            for line in header_lines[:8]:
                if "|" in line:
                    parts = [part.strip() for part in line.split("|")]
                    for part in parts:
                        if (
                            part
                            and not _is_contact_line(part)
                            and 2 <= len(part.split()) <= 4
                            and len(part) <= 45
                            and normalize_for_match(part) not in {"disponible", "remoto", "híbrido", "hibrido"}
                        ):
                            location = part
                            break

        return {
            "name": normalize_whitespace(name),
            "headline": normalize_whitespace(headline),
            "email": emails[0] if emails else "",
            "phone": phones[0] if phones else "",
            "location": normalize_whitespace(location),
            "linkedin": linkedin or "",
            "website": urls[0] if urls else "",
        }

    def _fallback_summary(self, lines: list[str], header_end: int) -> str:
        for line in lines[header_end : header_end + 8]:
            if len(line.split()) >= 18 and not detect_heading(line):
                return line
        return ""

    # ----------------------------------------------------------- Experiencia
    def _parse_experience(self, body: str) -> list[dict[str, Any]]:
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        entries: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        buffer: list[str] = []

        def finalize() -> None:
            nonlocal current, buffer
            if current is None:
                return
            bullets = [line for line in buffer if line]
            if bullets:
                current["bullets"] = [self._clean_bullet(item) for item in bullets]
                current["description"] = " ".join(current["bullets"])
            entries.append(current)
            current = None
            buffer = []

        for line in lines:
            ranges = find_date_ranges(line)
            if ranges:
                finalize()
                start, end = ranges[0]
                header = self._remove_date_text(line)
                parts = self._split_header(header)
                role = parts[0] if parts else ""
                company = parts[1] if len(parts) > 1 else ""
                location = parts[2] if len(parts) > 2 else ""
                if not role and buffer:
                    role = buffer[-1]
                current = {
                    "role": role,
                    "company": company,
                    "location": location,
                    "start_date": start,
                    "end_date": end,
                    "current": is_current(end),
                    "bullets": [],
                    "description": "",
                }
            else:
                if current is None:
                    buffer.append(line)
                elif not current["role"] and len(line.split()) <= 8:
                    current["role"] = line
                elif not current["company"] and len(line) <= 90 and not line.startswith(
                    ("•", "-", "–", "*")
                ):
                    current["company"] = line
                else:
                    buffer.append(line)
        finalize()

        # Bloques sin fechas: separa por líneas de título con formato.
        if not entries:
            blocks = [block for block in re.split(r"\n\s*\n", body) if block.strip()]
            for block in blocks:
                block_lines = [line.strip() for line in block.splitlines() if line.strip()]
                if not block_lines:
                    continue
                header = block_lines[0]
                parts = self._split_header(header)
                entries.append(
                    {
                        "role": parts[0] if parts else header,
                        "company": parts[1] if len(parts) > 1 else "",
                        "location": parts[2] if len(parts) > 2 else "",
                        "start_date": "",
                        "end_date": "",
                        "current": False,
                        "bullets": [self._clean_bullet(item) for item in block_lines[1:]],
                        "description": " ".join(block_lines[1:]),
                    }
                )

        for entry in entries:
            if not entry.get("start_date") and not entry.get("end_date"):
                period = ""
            else:
                period = format_period(entry.get("start_date"), entry.get("end_date"))
            entry["period"] = period
            entry["role"] = normalize_whitespace(entry.get("role", ""))
            entry["company"] = normalize_whitespace(entry.get("company", ""))
        return [entry for entry in entries if entry["role"] or entry["company"]][:25]

    def _infer_experience(self, text: str) -> list[dict[str, Any]]:
        ranges = find_date_ranges(text)
        if len(ranges) < 1:
            return []
        # Reutiliza el parser sobre las líneas que contienen fechas y sus viñetas.
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        collected: list[str] = []
        active = False
        for line in lines:
            if find_date_ranges(line):
                active = True
            if active:
                collected.append(line)
        return self._parse_experience("\n".join(collected)) if collected else []

    def _remove_date_text(self, line: str) -> str:
        return normalize_whitespace(_DATE_IN_LINE_RE.sub(" ", line)).strip(" |·-–—")

    def _split_header(self, header: str) -> list[str]:
        header = header.strip(" |·-–—")
        if not header:
            return []
        for separator in (" | ", " · ", " — ", " – ", " @ ", " en "):
            if separator in header:
                parts = [part.strip(" |·-–—") for part in header.split(separator)]
                return [part for part in parts if part]
        if " - " in header and header.count(" - ") <= 2:
            parts = [part.strip() for part in header.split(" - ")]
            if all(len(part) <= 80 for part in parts):
                return parts
        return [header]

    @staticmethod
    def _clean_bullet(value: str) -> str:
        value = re.sub(r"^\s*(?:[•▪◦●○‣·*\-–—]|\d+[.)])\s*", "", value)
        return normalize_whitespace(value)

    # -------------------------------------------------------------- Educación
    def _parse_education(self, body: str) -> list[dict[str, Any]]:
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        entries: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None

        def new_entry(line: str) -> dict[str, Any]:
            ranges = find_date_ranges(line)
            header = self._remove_date_text(line) if ranges else line
            parts = self._split_header(header)
            degree = parts[0] if parts else header
            institution = parts[1] if len(parts) > 1 else ""
            details = " ".join(parts[2:]) if len(parts) > 2 else ""
            return {
                "degree": degree.strip(),
                "institution": institution.strip(),
                "location": "",
                "start_date": ranges[0][0] if ranges else "",
                "end_date": ranges[0][1] if ranges else "",
                "details": details,
            }

        for line in lines:
            normalized = normalize_for_match(line)
            is_degree = any(hint in normalized for hint in _DEGREE_HINTS)
            is_institution = any(hint in normalized for hint in _INSTITUTION_HINTS)
            has_date = bool(find_date_ranges(line))
            if current is None or (is_degree and current.get("degree") and len(line) < 160):
                if current is not None:
                    entries.append(current)
                current = new_entry(line)
            elif is_institution and not current.get("institution"):
                current["institution"] = self._clean_bullet(line)
            elif has_date and not current.get("start_date"):
                ranges = find_date_ranges(line)
                current["start_date"], current["end_date"] = ranges[0]
            else:
                current["details"] = normalize_whitespace(
                    (current.get("details", "") + " " + self._clean_bullet(line)).strip()
                )
        if current is not None:
            entries.append(current)

        for entry in entries:
            entry["period"] = format_period(entry.get("start_date"), entry.get("end_date"))
        return [entry for entry in entries if entry["degree"]][:10]

    # -------------------------------------------------------------- Skills
    def _parse_skills(self, body: str) -> tuple[list[str], list[str]]:
        if not body.strip():
            return [], []
        chunks: list[str] = []
        for line in body.splitlines():
            line = re.sub(r"^\s*(?:[•▪◦●○‣·*\-–—]|\d+[.)])\s*", "", line.strip())
            for part in re.split(r"[,;|/·•]", line):
                cleaned = part.strip(" .:-–—")
                if cleaned and len(cleaned) <= 60:
                    chunks.append(cleaned)
        technical: list[str] = []
        soft: list[str] = []
        for item in chunks:
            normalized = normalize_for_match(item)
            if any(hint in normalized for hint in SOFT_SKILL_HINTS):
                soft.append(item)
            else:
                technical.append(item)
        return self._dedupe(technical)[:60], self._dedupe(soft)[:30]

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        result = []
        for item in items:
            key = normalize_for_match(item)
            if key and key not in seen:
                seen.add(key)
                result.append(item)
        return result

    # -------------------------------------------------------------- Idiomas
    def _parse_languages(self, body: str, fallback_text: str) -> list[dict[str, str]]:
        text = body or fallback_text
        if not text:
            return []
        languages: list[dict[str, str]] = []
        seen: set[str] = set()
        for line in text.splitlines():
            normalized = normalize_for_match(line)
            for language in _LANGUAGE_NAMES:
                if normalize_for_match(language) in normalized:
                    display = language.capitalize()
                    key = normalize_for_match(language)
                    if key in seen:
                        continue
                    level = self._detect_language_level(normalized)
                    languages.append({"language": display, "level": level})
                    seen.add(key)
        return languages[:8]

    @staticmethod
    def _detect_language_level(normalized_line: str) -> str:
        for level in sorted(LANGUAGE_LEVELS, key=len, reverse=True):
            pattern = r"(?<![a-z0-9])" + re.escape(normalize_for_match(level)) + r"(?![a-z0-9])"
            if re.search(pattern, normalized_line):
                return level
        if "nativo" in normalized_line:
            return "Nativo"
        return ""

    # ------------------------------------------------------- Listas simples
    def _parse_list_section(self, body: str) -> list[str]:
        if not body.strip():
            return []
        items = []
        for line in body.splitlines():
            cleaned = self._clean_bullet(line)
            if cleaned and len(cleaned) > 2:
                items.append(cleaned)
        return self._dedupe(items)[:20]

    # -------------------------------------------------------------- Proyectos
    def _parse_projects(self, body: str) -> list[dict[str, Any]]:
        if not body.strip():
            return []
        blocks = [block.strip() for block in re.split(r"\n\s*\n", body) if block.strip()]
        if len(blocks) <= 1:
            blocks = [line.strip() for line in body.splitlines() if line.strip()]
        projects = []
        for block in blocks[:10]:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            name = self._clean_bullet(lines[0])
            description = normalize_whitespace(" ".join(lines[1:]))
            projects.append(
                {
                    "name": name,
                    "description": description,
                    "technologies": extract_tech_keywords(block),
                }
            )
        return projects


def content_to_text(content: dict[str, Any]) -> str:
    """Serializa el contenido estructurado a texto legible para evaluadores/IA."""
    personal = content.get("personal", {}) or {}
    parts: list[str] = []
    header = [
        personal.get("name", ""),
        personal.get("headline", ""),
        " | ".join(
            filter(
                None,
                [
                    personal.get("email", ""),
                    personal.get("phone", ""),
                    personal.get("location", ""),
                    personal.get("linkedin", ""),
                ],
            )
        ),
    ]
    parts.extend(line for line in header if line)

    if content.get("summary"):
        parts.append("\nPERFIL PROFESIONAL\n" + str(content["summary"]))

    experience = content.get("experience") or []
    if experience:
        lines = ["\nEXPERIENCIA PROFESIONAL"]
        for entry in experience:
            title = " | ".join(
                filter(None, [entry.get("role", ""), entry.get("company", "")])
            )
            period = entry.get("period") or format_period(
                entry.get("start_date"), entry.get("end_date")
            )
            lines.append(f"{title}{' — ' + period if period else ''}")
            for bullet in entry.get("bullets", []):
                lines.append(f"• {bullet}")
            if not entry.get("bullets") and entry.get("description"):
                lines.append(str(entry["description"]))
        parts.append("\n".join(lines))

    education = content.get("education") or []
    if education:
        lines = ["\nEDUCACIÓN"]
        for entry in education:
            line = " | ".join(
                filter(None, [entry.get("degree", ""), entry.get("institution", "")])
            )
            period = entry.get("period") or format_period(
                entry.get("start_date"), entry.get("end_date")
            )
            lines.append(f"{line}{' — ' + period if period else ''}")
            if entry.get("details"):
                lines.append(str(entry["details"]))
        parts.append("\n".join(lines))

    skills = content.get("skills") or {}
    if skills.get("technical"):
        parts.append("\nCOMPETENCIAS TÉCNICAS\n" + ", ".join(skills["technical"]))
    if skills.get("soft"):
        parts.append("\nCOMPETENCIAS BLANDAS\n" + ", ".join(skills["soft"]))

    if content.get("certifications"):
        parts.append("\nCERTIFICACIONES\n" + "\n".join(
            f"• {item}" for item in content["certifications"]
        ))

    if content.get("languages"):
        parts.append(
            "\nIDIOMAS\n"
            + "\n".join(
                f"• {item.get('language', '')}"
                + (f" — {item.get('level')}" if item.get("level") else "")
                for item in content["languages"]
            )
        )

    if content.get("projects"):
        lines = ["\nPROYECTOS"]
        for project in content["projects"]:
            lines.append(f"• {project.get('name', '')}: {project.get('description', '')}")
        parts.append("\n".join(lines))

    if content.get("achievements"):
        parts.append("\nLOGROS\n" + "\n".join(f"• {item}" for item in content["achievements"]))

    if content.get("additional"):
        parts.append("\nINFORMACIÓN ADICIONAL\n" + "\n".join(
            f"• {item}" for item in content["additional"]
        ))

    return normalize_whitespace("\n\n".join(parts))


def content_statistics(content: dict[str, Any]) -> dict[str, Any]:
    experience = content.get("experience") or []
    bullets = [bullet for entry in experience for bullet in entry.get("bullets", [])]
    return {
        "experience_entries": len(experience),
        "experience_bullets": len(bullets),
        "education_entries": len(content.get("education") or []),
        "technical_skills": len((content.get("skills") or {}).get("technical", [])),
        "soft_skills": len((content.get("skills") or {}).get("soft", [])),
        "languages": len(content.get("languages") or []),
        "certifications": len(content.get("certifications") or []),
        "projects": len(content.get("projects") or []),
        "achievements": len(content.get("achievements") or []),
    }


def sections_from_content(
    content: dict[str, Any], origin: str = "USER_CONFIRMED"
) -> list[dict[str, Any]]:
    """Construye la lista de secciones persistibles a partir del contenido."""
    personal = content.get("personal") or {}
    sections: list[dict[str, Any]] = [
        {
            "section_type": "personal",
            "title": SECTION_LABELS["personal"],
            "content": "\n".join(str(value) for value in personal.values() if value),
            "data": personal,
            "data_origin": origin,
        },
        {
            "section_type": "perfil",
            "title": SECTION_LABELS["perfil"],
            "content": str(content.get("summary") or ""),
            "data_origin": origin,
        },
    ]

    experience_lines: list[str] = []
    for entry in content.get("experience") or []:
        title = " | ".join(
            filter(None, [str(entry.get("role") or ""), str(entry.get("company") or "")])
        )
        period = entry.get("period") or format_period(
            entry.get("start_date"), entry.get("end_date")
        )
        experience_lines.append(f"{title}{' — ' + period if period else ''}")
        experience_lines.extend(f"• {bullet}" for bullet in entry.get("bullets") or [])
    if experience_lines:
        sections.append(
            {
                "section_type": "experiencia",
                "title": SECTION_LABELS["experiencia"],
                "content": "\n".join(experience_lines),
                "data_origin": origin,
            }
        )

    education_lines: list[str] = []
    for entry in content.get("education") or []:
        line = " | ".join(
            filter(None, [str(entry.get("degree") or ""), str(entry.get("institution") or "")])
        )
        period = entry.get("period") or format_period(
            entry.get("start_date"), entry.get("end_date")
        )
        education_lines.append(f"{line}{' — ' + period if period else ''}")
    if education_lines:
        sections.append(
            {
                "section_type": "educacion",
                "title": SECTION_LABELS["educacion"],
                "content": "\n".join(education_lines),
                "data_origin": origin,
            }
        )

    skills = content.get("skills") or {}
    if skills.get("technical"):
        sections.append(
            {
                "section_type": "competencias_tecnicas",
                "title": SECTION_LABELS["competencias_tecnicas"],
                "content": ", ".join(str(item) for item in skills["technical"]),
                "data_origin": origin,
            }
        )
    if skills.get("soft"):
        sections.append(
            {
                "section_type": "competencias_blandas",
                "title": SECTION_LABELS["competencias_blandas"],
                "content": ", ".join(str(item) for item in skills["soft"]),
                "data_origin": origin,
            }
        )

    for key, items in (
        ("certificaciones", content.get("certifications") or []),
        ("logros", content.get("achievements") or []),
        ("adicional", content.get("additional") or []),
    ):
        if items:
            sections.append(
                {
                    "section_type": key,
                    "title": SECTION_LABELS.get(key, key),
                    "content": "\n".join(f"• {item}" for item in items),
                    "data_origin": origin,
                }
            )

    if content.get("languages"):
        sections.append(
            {
                "section_type": "idiomas",
                "title": SECTION_LABELS["idiomas"],
                "content": "\n".join(
                    f"{item.get('language', '')}"
                    + (f" — {item.get('level')}" if item.get("level") else "")
                    for item in content["languages"]
                ),
                "data_origin": origin,
            }
        )

    if content.get("projects"):
        sections.append(
            {
                "section_type": "proyectos",
                "title": SECTION_LABELS["proyectos"],
                "content": "\n".join(
                    f"• {project.get('name', '')}: {project.get('description', '')}"
                    for project in content["projects"]
                ),
                "data_origin": origin,
            }
        )
    return sections
