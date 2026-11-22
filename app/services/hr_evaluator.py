"""Evaluador desde la perspectiva de Recursos Humanos.

Evalúa claridad, coherencia, evidencia de logros y propuesta de valor. No evalúa
características personales protegidas y recomienda eliminar datos sensibles.
"""

from __future__ import annotations

from typing import Any

from app.config.constants import SCORE_DISCLAIMER
from app.services.evaluation_models import CriterionResult, DimensionResult
from app.services.evaluation_utils import (
    all_bullets,
    experience_sentences,
    offer_keyword_list,
    section_contexts,
    technical_skills,
)
from app.utils.dates import months_between, parse_date_token
from app.utils.text import (
    detect_sensitive_data,
    find_generic_phrases,
    find_weak_phrases,
    has_metric,
    keyword_coverage,
    normalize_for_match,
    remove_repeated_sentences,
    similarity,
    starts_with_action_verb,
    truncate,
    word_count,
)


def _severity(ratio: float) -> str:
    if ratio >= 0.85:
        return "info"
    if ratio >= 0.6:
        return "medium"
    if ratio >= 0.35:
        return "high"
    return "critical"


class HREvaluator:
    dimension = "HR"

    def evaluate(
        self,
        raw_text: str,
        content: dict[str, Any],
        offer_text: str = "",
        offer_keywords: list[str] | None = None,
    ) -> DimensionResult:
        criteria: list[CriterionResult] = []
        missing: list[str] = []
        limitations: list[str] = [SCORE_DISCLAIMER]
        contexts = section_contexts(content)
        bullets = all_bullets(content)
        experience = content.get("experience") or []
        summary = str(content.get("summary") or "")
        summary_words = word_count(summary)
        skills = technical_skills(content)
        sensitive = detect_sensitive_data(raw_text)

        # 1. Claridad del perfil profesional (15)
        profile_score = 0.0
        if summary:
            if 30 <= summary_words <= 160:
                profile_score = 12.0
            elif 15 <= summary_words < 30 or 160 < summary_words <= 220:
                profile_score = 8.0
            else:
                profile_score = 5.0
            if any(
                keyword.lower() in normalize_for_match(summary)
                for keyword in skills[:8]
            ) or any(
                token in normalize_for_match(summary)
                for token in ("año", "años", "experiencia", "especialista", "analista", "desarrollador")
            ):
                profile_score += 3.0
        generic = find_generic_phrases(summary)
        if generic:
            profile_score = max(0.0, profile_score - 3.0)
        profile_score = min(15.0, profile_score)
        if not summary:
            missing.append("Perfil profesional que explique el valor del candidato")
        criteria.append(
            CriterionResult(
                criterion="Claridad del perfil profesional",
                score=profile_score,
                max_score=15,
                severity=_severity(profile_score / 15),
                explanation=(
                    f"El perfil tiene {summary_words} palabras."
                    if summary else "No se identificó un perfil profesional."
                )
                + (
                    " Contiene expresiones genéricas que restan credibilidad: "
                    + ", ".join(generic[:4]) + "." if generic else ""
                ),
                evidence=truncate(summary, 240) if summary else None,
                recommendation=(
                    "Escriba un perfil de 3 a 5 líneas que indique especialidad, años de "
                    "experiencia, herramientas principales y tipo de resultados aportados."
                    if profile_score < 12 else None
                ),
            )
        )

        # 2. Coherencia de la trayectoria (15)
        trajectory_score = 0.0
        trajectory_notes: list[str] = []
        dated = [entry for entry in experience if entry.get("start_date") or entry.get("end_date")]
        if len(dated) >= 3:
            trajectory_score = 13.0
        elif len(dated) == 2:
            trajectory_score = 11.0
        elif len(dated) == 1:
            trajectory_score = 7.0
        if experience and len(experience) >= 2:
            trajectory_score += 2.0 if len(dated) == len(experience) else 0.0
        periods = []
        for entry in dated:
            start = parse_date_token(str(entry.get("start_date", "")))
            end = parse_date_token(str(entry.get("end_date", "")))
            if start and end:
                periods.append((start, end))
        periods.sort()
        overlaps = 0
        gaps = 0
        for index in range(1, len(periods)):
            previous_end = periods[index - 1][1]
            current_start = periods[index][0]
            overlap = months_between(current_start, previous_end)
            if overlap > 3:
                overlaps += 1
            else:
                gap = months_between(previous_end, current_start)
                if gap > 12:
                    gaps += 1
        if overlaps:
            trajectory_score -= 2.0
            trajectory_notes.append(f"{overlaps} periodo(s) solapado(s)")
        if gaps:
            trajectory_score -= 1.0
            trajectory_notes.append(f"{gaps} brecha(s) mayor(es) a 12 meses")
        if summary and experience:
            latest = experience[0]
            latest_text = " ".join(
                filter(None, [latest.get("role", ""), latest.get("company", "")])
            )
            if similarity(summary, latest_text) > 0.05 or normalize_for_match(
                str(latest.get("role", ""))
            ) in normalize_for_match(summary):
                trajectory_score += 1.0
        trajectory_score = max(0.0, min(15.0, trajectory_score))
        if not experience:
            missing.append("Experiencia profesional con fechas y responsabilidades")
        criteria.append(
            CriterionResult(
                criterion="Coherencia de la trayectoria",
                score=trajectory_score,
                max_score=15,
                severity=_severity(trajectory_score / 15),
                explanation=(
                    f"Se identificaron {len(experience)} puestos, {len(dated)} con fechas."
                    + (" Observaciones: " + ", ".join(trajectory_notes) + "." if trajectory_notes else "")
                ),
                recommendation=(
                    "Ordene la experiencia en forma cronológica inversa y explique brevemente "
                    "los cambios de puesto o las brechas relevantes."
                    if trajectory_score < 12 else None
                ),
            )
        )

        # 3. Relevancia de la experiencia (10)
        if offer_text.strip():
            keywords = offer_keyword_list(None, offer_text, offer_keywords)
            experience_text = contexts["experience"]
            present, _absent = keyword_coverage(experience_text, keywords) if keywords else ([], [])
            relevance = 10.0 * (len(present) / max(1, len(keywords))) if keywords else 0.0
            relevance_explanation = (
                f"La experiencia menciona {len(present)} de {len(keywords)} palabras clave "
                "de la oferta."
            )
        else:
            action_bullets = sum(1 for bullet in bullets if starts_with_action_verb(bullet))
            ratio = action_bullets / max(1, len(bullets))
            relevance = min(10.0, ratio * 10.0 + (2.0 if len(bullets) >= 8 else 0.0))
            relevance_explanation = (
                f"{action_bullets} de {len(bullets)} viñetas comienzan con un verbo de acción."
            )
        criteria.append(
            CriterionResult(
                criterion="Relevancia de la experiencia",
                score=relevance,
                max_score=10,
                severity=_severity(relevance / 10),
                explanation=relevance_explanation,
                recommendation=(
                    "Relacione cada responsabilidad con el puesto objetivo y elimine tareas "
                    "que no aporten evidencia de valor."
                    if relevance < 7 else None
                ),
            )
        )

        # 4. Calidad de redacción (15)
        writing = 15.0
        writing_issues: list[str] = []
        if generic:
            writing -= min(5.0, 1.5 * len(generic))
            writing_issues.append("expresiones genéricas")
        weak = find_weak_phrases(raw_text)
        if weak:
            writing -= min(4.0, 1.2 * len(weak))
            writing_issues.append("frases débiles o pasivas")
        _clean, repeated = remove_repeated_sentences(contexts["experience"])
        if repeated:
            writing -= min(4.0, 2.0 * len(repeated))
            writing_issues.append("ideas repetidas")
        long_sentences = 0
        for text, _label in experience_sentences(content):
            if word_count(text) > 45:
                long_sentences += 1
        if long_sentences:
            writing -= min(3.0, float(long_sentences))
            writing_issues.append("oraciones demasiado largas")
        if any(phrase in normalize_for_match(raw_text) for phrase in (
            "fue realizado", "fue elaborado", "fue desarrollado", "se realizó", "se realizo",
        )):
            writing -= 1.0
            writing_issues.append("voz pasiva")
        writing = max(0.0, min(15.0, writing))
        criteria.append(
            CriterionResult(
                criterion="Calidad de redacción y comunicación",
                score=writing,
                max_score=15,
                severity=_severity(writing / 15),
                explanation=(
                    "La redacción es directa y profesional."
                    if not writing_issues else
                    "Aspectos a mejorar: " + ", ".join(writing_issues) + "."
                ),
                evidence="; ".join(weak[:3]) if weak else None,
                recommendation=(
                    "Use frases breves con verbo de acción, elimine adjetivos genéricos y "
                    "evite repetir la misma idea en perfil y experiencia."
                    if writing < 12 else None
                ),
            )
        )

        # 5. Evidencia de logros (20)
        metric_bullets = [bullet for bullet in bullets if has_metric(bullet)]
        action_bullets = [bullet for bullet in bullets if starts_with_action_verb(bullet)]
        if len(metric_bullets) >= 5:
            achievement_score = 18.0
        elif len(metric_bullets) >= 3:
            achievement_score = 15.0
        elif len(metric_bullets) >= 1:
            achievement_score = 9.0
        else:
            achievement_score = 3.0
        if bullets and len(action_bullets) / len(bullets) >= 0.5:
            achievement_score += 2.0
        achievement_score = min(20.0, achievement_score)
        if not metric_bullets:
            missing.append(
                "Resultados cuantificados o evidencia verificable de logros (sin inventar métricas)"
            )
        criteria.append(
            CriterionResult(
                criterion="Evidencia de logros y resultados",
                score=achievement_score,
                max_score=20,
                severity=_severity(achievement_score / 20),
                explanation=(
                    f"{len(metric_bullets)} de {len(bullets)} viñetas incluyen una métrica o "
                    f"resultado verificable. {len(action_bullets)} comienzan con verbo de acción."
                ),
                evidence=truncate(metric_bullets[0], 240) if metric_bullets else None,
                recommendation=(
                    "Añada resultados reales con alcance, magnitud y periodo. Si no dispone "
                    "de la cifra exacta, describa el impacto cualitativo sin inventar números."
                    if achievement_score < 15 else None
                ),
            )
        )

        # 6. Organización de la información (10)
        organization = 0.0
        for present in (
            bool(summary), bool(experience), bool(content.get("education")), bool(skills)
        ):
            if present:
                organization += 2.0
        personal = content.get("personal") or {}
        if personal.get("email") and personal.get("phone"):
            organization += 1.0
        total_words = word_count(raw_text)
        if 250 <= total_words <= 1000:
            organization += 1.0
        organization = min(10.0, organization)
        criteria.append(
            CriterionResult(
                criterion="Organización de la información",
                score=organization,
                max_score=10,
                severity=_severity(organization / 10),
                explanation=(
                    "El CV contiene las secciones esenciales y una extensión adecuada "
                    f"({total_words} palabras)."
                    if organization >= 8 else
                    "Faltan secciones esenciales o la extensión no es la adecuada "
                    f"({total_words} palabras)."
                ),
                recommendation=(
                    "Mantenga el CV entre una y dos páginas, con secciones claras y datos "
                    "de contacto visibles." if organization < 8 else None
                ),
            )
        )

        # 7. Propuesta de valor (10)
        value_elements = 0
        value_notes = []
        if summary and len(summary.split()) >= 15:
            value_elements += 1
            value_notes.append("perfil")
        if skills:
            value_elements += 1
            value_notes.append("competencias")
        if metric_bullets:
            value_elements += 1
            value_notes.append("resultados")
        if offer_text.strip() and similarity(summary, offer_text) > 0.08:
            value_elements += 1
            value_notes.append("alineación con la oferta")
        value_score = min(10.0, value_elements * 2.5)
        criteria.append(
            CriterionResult(
                criterion="Propuesta de valor",
                score=value_score,
                max_score=10,
                severity=_severity(value_score / 10),
                explanation=(
                    "El CV comunica valor mediante: " + ", ".join(value_notes) + "."
                    if value_notes else
                    "El CV no comunica con claridad qué aporta el candidato."
                ),
                recommendation=(
                    "Explique qué problemas resuelve el candidato, con qué herramientas y "
                    "con qué resultados demostrables." if value_score < 7 else None
                ),
            )
        )

        # 8. Presentación profesional (5)
        presentation = 0.0
        if personal.get("email"):
            presentation += 1.5
        if personal.get("phone"):
            presentation += 1.5
        if dated and len(dated) == len(experience):
            presentation += 1.0
        if personal.get("linkedin") or personal.get("location"):
            presentation += 0.5
        if sensitive:
            presentation = max(0.0, presentation - 0.5)
        presentation = min(5.0, presentation)
        if sensitive:
            limitations.append(
                "Se detectaron datos personales protegidos ("
                + ", ".join(sensitive)
                + "). Se recomienda eliminarlos; no se usaron para puntuar ni discriminar."
            )
        criteria.append(
            CriterionResult(
                criterion="Presentación profesional",
                score=presentation,
                max_score=5,
                severity=_severity(presentation / 5),
                explanation=(
                    "Los datos de contacto y la presentación general son adecuados."
                    if presentation >= 4 else
                    "La presentación puede mejorar: datos de contacto incompletos o "
                    "inconsistencias de fechas."
                ),
                recommendation=(
                    "Incluya un encabezado limpio con nombre, cargo objetivo, correo, "
                    "teléfono y LinkedIn. Evite edad, estado civil, fotografía y documento "
                    "de identidad." if presentation < 4 or sensitive else None
                ),
            )
        )

        score = round(sum(item.score for item in criteria), 1)
        strengths = [
            f"{item.criterion}: {item.status.lower()}"
            for item in criteria if item.ratio >= 0.85
        ]
        weaknesses = [
            f"{item.criterion}: {item.explanation}"
            for item in criteria if item.ratio < 0.6
        ]
        limitations.extend(
            [
                "La evaluación se basa exclusivamente en el texto del CV; no sustituye una "
                "entrevista ni la verificación de referencias.",
                "No se evalúan edad, género, estado civil, nacionalidad, fotografía ni "
                "cualquier otra característica personal protegida.",
            ]
        )
        confidence = self._confidence(total_words, len(bullets), bool(summary), bool(dated))
        summary_text = (
            f"Perspectiva de Recursos Humanos: {score:.1f}/100. "
            + (
                "Priorice: " + "; ".join(item.criterion.lower() for item in criteria if item.ratio < 0.6) + "."
                if any(item.ratio < 0.6 for item in criteria)
                else "El CV comunica de forma clara y ordenada."
            )
        )
        return DimensionResult(
            dimension=self.dimension,
            score=score,
            criteria=criteria,
            strengths=strengths,
            weaknesses=weaknesses,
            missing=list(dict.fromkeys(missing)),
            limitations=limitations,
            confidence=confidence,
            summary=summary_text,
        )

    @staticmethod
    def _confidence(words: int, bullets: int, has_summary: bool, has_dates: bool) -> str:
        points = 0
        if words >= 300:
            points += 1
        if words >= 500:
            points += 1
        if bullets >= 6:
            points += 1
        if has_summary:
            points += 1
        if has_dates:
            points += 1
        if points >= 4:
            return "alta"
        if points >= 2:
            return "media"
        return "baja"
