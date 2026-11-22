"""Utilidades de procesamiento de texto compartidas por todos los módulos."""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from collections import Counter
from typing import Iterable, Sequence

from app.config.constants import ACTION_VERBS, GENERIC_PHRASES, STOPWORDS, TECH_KEYWORDS

_WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9+#./-]*")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_BULLET_RE = re.compile(r"^\s*(?:[•▪◦●○‣·*\-–—]|\d+[.)])\s+")
_METRIC_RE = re.compile(
    r"(?<![\w.])(?:\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*"
    r"(?:%|por\s*ciento|puntos?|mil|millones?|k\b|m\b|usuarios?|clientes?|"
    r"registros?|transacciones?|reportes?|informes?|personas?|empleados?|"
    r"horas?|días?|dias?|semanas?|meses?|años?|proyectos?|países?|paises?|"
    r"sedes?|áreas?|areas?|equipos?|tiendas?|productos?|facturas?|cuentas?)",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}")
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/[\w/%-]+", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)
_DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}\.?\s*(?:de\s*)?)?(?:19|20)\d{2}"
    r"|\d{1,2}[/-](?:19|20)\d{2})"
    r"\s*(?:-|–|—|a|hasta|to)\s*"
    r"(?P<end>actualidad|presente|actual|hoy|current|present|"
    r"(?:[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}\.?\s*(?:de\s*)?)?(?:19|20)\d{2}"
    r"|\d{1,2}[/-](?:19|20)\d{2})",
    re.IGNORECASE,
)

SENSITIVE_PATTERNS: dict[str, re.Pattern[str]] = {
    "edad": re.compile(r"\b(?:edad|años de edad)\s*[:\-]?\s*\d{1,2}\b", re.IGNORECASE),
    "fecha de nacimiento": re.compile(
        r"\b(?:fecha de nacimiento|nacido el|nacida el)\b", re.IGNORECASE
    ),
    "estado civil": re.compile(
        r"\b(?:estado civil|soltero|soltera|casado|casada|divorciado|divorciada|viudo|viuda)\b",
        re.IGNORECASE,
    ),
    "nacionalidad": re.compile(r"\bnacionalidad\b", re.IGNORECASE),
    "documento de identidad": re.compile(
        r"\b(?:dni|nie|rut|curp|documento nacional de identidad|pasaporte)\b",
        re.IGNORECASE,
    ),
    "fotografía": re.compile(r"\bfotograf[ií]a\b", re.IGNORECASE),
}


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_whitespace(value: str) -> str:
    value = value.replace("\xa0", " ").replace("\u200b", "")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def normalize_for_match(value: str) -> str:
    return strip_accents(value).lower()


def tokenize(text: str, remove_stopwords: bool = True, min_length: int = 3) -> list[str]:
    tokens = [match.group(0).lower() for match in _WORD_RE.finditer(text)]
    result = []
    for token in tokens:
        cleaned = token.strip(".-/")
        if len(cleaned) < min_length and not cleaned.isdigit():
            continue
        if remove_stopwords and cleaned in STOPWORDS:
            continue
        result.append(cleaned)
    return result


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_RE.split(text) if part.strip()]


def split_bullets(text: str) -> list[str]:
    """Extrae viñetas y líneas con contenido de un bloque de texto."""
    bullets: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _BULLET_RE.match(line):
            bullets.append(_BULLET_RE.sub("", line).strip())
        elif len(line) > 25 and not line.endswith(":"):
            bullets.append(line)
    return bullets


def extract_emails(text: str) -> list[str]:
    return sorted(set(_EMAIL_RE.findall(text)))


def extract_phones(text: str) -> list[str]:
    candidates = []
    for match in _PHONE_RE.finditer(text):
        value = match.group(0).strip()
        digits = re.sub(r"\D", "", value)
        if 7 <= len(digits) <= 15:
            candidates.append(value)
    return list(dict.fromkeys(candidates))


def extract_linkedin(text: str) -> str | None:
    match = _LINKEDIN_RE.search(text)
    return match.group(0) if match else None


def extract_urls(text: str) -> list[str]:
    return list(dict.fromkeys(_URL_RE.findall(text)))


def find_date_ranges(text: str) -> list[tuple[str, str]]:
    return [(m.group("start").strip(), m.group("end").strip()) for m in _DATE_RANGE_RE.finditer(text)]


def has_metric(text: str) -> bool:
    return bool(_METRIC_RE.search(text))


def extract_metrics(text: str) -> list[str]:
    return [match.group(0) for match in _METRIC_RE.finditer(text)]


def extract_numbers(text: str) -> list[str]:
    return re.findall(r"\b\d+(?:[.,]\d+)?\b", text)


def starts_with_action_verb(text: str) -> bool:
    normalized = normalize_for_match(text).strip()
    for verb in ACTION_VERBS:
        if normalized.startswith(normalize_for_match(verb) + " ") or normalized == normalize_for_match(verb):
            return True
    return False


def find_generic_phrases(text: str) -> list[str]:
    normalized = normalize_for_match(text)
    return [phrase for phrase in GENERIC_PHRASES if normalize_for_match(phrase) in normalized]


def find_weak_phrases(text: str) -> list[str]:
    from app.config.constants import WEAK_PHRASES

    normalized = normalize_for_match(text)
    found = []
    for weak, _replacement in WEAK_PHRASES:
        if normalize_for_match(weak) in normalized:
            found.append(weak)
    return list(dict.fromkeys(found))


def extract_tech_keywords(text: str) -> list[str]:
    normalized = normalize_for_match(text)
    found = []
    for keyword in TECH_KEYWORDS:
        pattern = r"(?<![a-z0-9])" + re.escape(normalize_for_match(keyword)) + r"(?![a-z0-9])"
        if re.search(pattern, normalized):
            found.append(keyword)
    return list(dict.fromkeys(found))


def extract_keywords(text: str, top_n: int = 40, vocabulary: Iterable[str] | None = None) -> list[str]:
    """Extrae términos relevantes por frecuencia, priorizando vocabulario técnico."""
    tech = extract_tech_keywords(text)
    counts: Counter[str] = Counter()
    vocabulary_set = {normalize_for_match(v) for v in vocabulary} if vocabulary else None
    for token in tokenize(text):
        if len(token) <= 2 or token.isdigit():
            continue
        if vocabulary_set is not None and normalize_for_match(token) not in vocabulary_set:
            continue
        counts[token] += 1
    ranked = [word for word, count in counts.most_common(top_n * 2) if count >= 1]
    result: list[str] = list(tech)
    for word in ranked:
        if word not in result:
            result.append(word)
        if len(result) >= top_n:
            break
    return result


def similarity(text_a: str, text_b: str) -> float:
    """Similitud coseno TF-IDF; devuelve 0..1. Usa scikit-learn si está disponible."""
    if not text_a.strip() or not text_b.strip():
        return 0.0
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(
            lowercase=True, strip_accents="unicode", ngram_range=(1, 2),
            min_df=1, max_features=5000,
        )
        matrix = vectorizer.fit_transform([text_a, text_b])
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except Exception:
        tokens_a = set(tokenize(text_a))
        tokens_b = set(tokenize(text_b))
        if not tokens_a or not tokens_b:
            return 0.0
        return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def keyword_coverage(cv_text: str, keywords: Sequence[str]) -> tuple[list[str], list[str]]:
    normalized = normalize_for_match(cv_text)
    present, missing = [], []
    for keyword in keywords:
        needle = normalize_for_match(keyword)
        pattern = r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])"
        (present if re.search(pattern, normalized) else missing).append(keyword)
    return present, missing


def quote_for(text: str, needle: str, max_length: int = 220) -> str | None:
    """Devuelve la oración que contiene ``needle`` como evidencia citables."""
    normalized_needle = normalize_for_match(needle)
    for sentence in sentences(text):
        if normalized_needle in normalize_for_match(sentence):
            return truncate(sentence, max_length)
    return None


def truncate(value: str, max_length: int = 200) -> str:
    value = normalize_whitespace(value)
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


def detect_sensitive_data(text: str) -> list[str]:
    return [label for label, pattern in SENSITIVE_PATTERNS.items() if pattern.search(text)]


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def escape_html(value: str) -> str:
    return html.escape(value, quote=True)


def slugify(value: str) -> str:
    value = strip_accents(value).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "archivo"


def remove_repeated_sentences(text: str) -> tuple[str, list[str]]:
    seen: set[str] = set()
    kept: list[str] = []
    repeated: list[str] = []
    for sentence in sentences(text):
        key = normalize_for_match(re.sub(r"\W+", "", sentence))
        if len(key) < 20:
            kept.append(sentence)
            continue
        if key in seen:
            repeated.append(sentence)
        else:
            seen.add(key)
            kept.append(sentence)
    return " ".join(kept), repeated


def split_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
