"""Optimizador de CV: propuestas de redacción con IA local y motor de reglas.

Nunca se modifica el documento original. Cada propuesta conserva texto original,
problema, propuesta, justificación, evidencia y estado de aprobación. Los cambios
solo se aplican a una versión nueva cuando el usuario los acepta explícitamente.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from app.ai.ai_service import AIService
from app.config.constants import (
    ORIGIN_AI,
    ORIGIN_ILLUSTRATIVE,
    ORIGIN_RULE,
    SECTION_LABELS,
    WEAK_PHRASES,
)
from app.core.errors import AIValidationError
from app.database.repositories import (
    CVRepository,
    MissingInformationRepository,
    OfferRepository,
    OptimizationRepository,
)
from app.database.session import Database
from app.services.cv_parser import content_to_text
from app.services.evaluation_utils import offer_keyword_list
from app.utils.text import (
    extract_tech_keywords,
    find_generic_phrases,
    find_weak_phrases,
    has_metric,
    normalize_for_match,
    normalize_whitespace,
    truncate,
    word_count,
)

Progress = Callable[[int, str], None]


@dataclass
class OptimizationOutcome:
    session_id: int
    proposals: list[dict[str, Any]]
    missing: list[dict[str, Any]]
    provider: str
    model: str
    summary: str
    used_ai: bool
    warnings: list[str] = field(default_factory=list)


class RuleBasedOptimizer:
    """Sugerencias deterministas que no inventan datos."""

    def propose(
        self,
        content: dict[str, Any],
        raw_text: str,
        offer_text: str = "",
        offer_keywords: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        proposals: list[dict[str, Any]] = []
        summary = str(content.get("summary") or "")
        personal = content.get("personal") or {}
        experience = content.get("experience") or []
        skills = (content.get("skills") or {}).get("technical") or []
        soft = (content.get("skills") or {}).get("soft") or []

        def add(
            section: str,
            original: str,
            problem: str,
            proposed: str,
            justification: str,
            evidence: str = "",
        ) -> None:
            if not original.strip() or not proposed.strip():
                return
            if normalize_for_match(original) == normalize_for_match(proposed):
                return
            if any(
                normalize_for_match(item["original_text"]) == normalize_for_match(original)
                for item in proposals
            ):
                return
            proposals.append(
                {
                    "section": section,
                    "original_text": original,
                    "problem": problem,
                    "proposed_text": proposed,
                    "justification": justification,
                    "evidence": evidence or original,
                    "origin": ORIGIN_RULE,
                    "status": "pending",
                    "issues": [],
                }
            )

        # 1. Perfil profesional débil o ausente.
        generic = find_generic_phrases(summary)
        if not summary.strip() or word_count(summary) < 25 or generic:
            role = str(personal.get("headline") or "").strip()
            if not role and experience:
                role = str(experience[0].get("role") or "").strip()
            tech_text = ", ".join(str(item) for item in skills[:4])
            proposed_parts = []
            if role:
                proposed_parts.append(role)
            if tech_text:
                proposed_parts.append(f"con experiencia en {tech_text}")
            proposed = " ".join(proposed_parts).strip()
            if proposed:
                proposed += (
                    ". [Añadir años de experiencia, especialidad y un resultado "
                    "verificable del CV]."
                )
            else:
                proposed = (
                    "[Escribir perfil profesional: especialidad, años de experiencia, "
                    "herramientas principales y resultado aportado]."
                )
            original = summary.strip() or "(Sin perfil profesional)"
            problem = (
                "El perfil es inexistente o demasiado genérico; no explica la "
                "especialidad ni el valor diferencial."
                if not generic else
                "El perfil contiene expresiones genéricas: " + ", ".join(generic[:3]) + "."
            )
            add(
                "Perfil",
                original,
                problem,
                proposed,
                "Un perfil concreto permite al reclutador identificar en segundos la "
                "especialidad y la evidencia que respalda al candidato.",
                evidence=summary or role,
            )

        # 2. Viñetas con frases débiles.
        for entry in experience:
            for bullet in entry.get("bullets") or []:
                weak = find_weak_phrases(bullet)
                if not weak:
                    continue
                proposed = self._rewrite_weak(bullet)
                if proposed and normalize_for_match(proposed) != normalize_for_match(bullet):
                    if not has_metric(proposed):
                        proposed = proposed.rstrip(" .") + (
                            " [añadir alcance o resultado verificable]."
                        )
                    add(
                        "Experiencia",
                        bullet,
                        "La viñeta usa una frase débil o pasiva ('"
                        + weak[0]
                        + "') que resta protagonismo a la acción.",
                        proposed,
                        "Comenzar con un verbo de acción y mantener el contenido real "
                        "mejora la claridad y la lectura ATS.",
                        evidence=bullet,
                    )

        # 3. Viñetas sin evidencia de resultado (máximo 3).
        count = 0
        for entry in experience:
            for bullet in entry.get("bullets") or []:
                if count >= 3:
                    break
                if has_metric(bullet) or find_weak_phrases(bullet):
                    continue
                if len(bullet.split()) < 6:
                    continue
                proposed = bullet.rstrip(" .") + (
                    " [añadir resultado verificable: alcance, magnitud y periodo]."
                )
                add(
                    "Experiencia",
                    bullet,
                    "La viñeta describe una actividad, pero no evidencia el resultado "
                    "ni el alcance de la responsabilidad.",
                    proposed,
                    "Los reclutadores buscan evidencia de impacto. El marcador indica "
                    "dónde debe añadirse un dato real, sin inventarlo.",
                    evidence=bullet,
                )
                count += 1

        # 4. Palabras clave de la oferta sin evidencia.
        if offer_keywords:
            normalized_experience = normalize_for_match(
                "\n".join(
                    " ".join(entry.get("bullets") or [])
                    for entry in experience
                )
            )
            missing = [
                keyword for keyword in offer_keywords
                if normalize_for_match(keyword) not in normalized_experience
            ][:4]
            if missing:
                original = "Competencias técnicas: " + (
                    ", ".join(skills) if skills else "(sin competencias declaradas)"
                )
                proposed = original + " — [confirmar si domina: " + ", ".join(missing) + "]"
                add(
                    "Competencias",
                    original,
                    "La oferta solicita términos que no aparecen respaldados por la "
                    "experiencia del CV: " + ", ".join(missing) + ".",
                    proposed,
                    "Solo deben incorporarse tecnologías que el candidato pueda demostrar. "
                    "El marcador exige confirmación explícita.",
                    evidence=original,
                )

        # 5. Competencias blandas genéricas.
        generic_soft = [
            item for item in soft
            if any(
                phrase in normalize_for_match(item)
                for phrase in ("proactivo", "proactiva", "trabajo en equipo", "responsable", "puntual", "dinámico", "dinamico")
            )
        ][:3]
        if generic_soft:
            add(
                "Competencias",
                ", ".join(generic_soft),
                "Las competencias blandas genéricas no aportan evidencia y suelen "
                "considerarse relleno.",
                "[Sustituir por evidencia en la experiencia: colaboración con equipos, "
                "liderazgo de personas o resolución de conflictos].",
                "Es preferible demostrar la competencia con un hecho que enumerarla.",
                evidence=", ".join(generic_soft),
            )

        # 6. Perfil sin las tecnologías principales del CV.
        if summary and skills and not any(
            normalize_for_match(str(skill)) in normalize_for_match(summary)
            for skill in skills[:6]
        ):
            proposed = summary.rstrip(" .") + (
                ". Herramientas principales: " + ", ".join(str(item) for item in skills[:5]) + "."
            )
            add(
                "Perfil",
                summary,
                "El perfil no menciona las herramientas que sí aparecen en el resto del CV.",
                proposed,
                "Alinear el perfil con las competencias reales mejora la coherencia y la "
                "coincidencia de palabras clave.",
                evidence=summary,
            )

        # 7. Redundancia entre perfil y experiencia.
        if summary and experience:
            summary_sentences = [
                part.strip() for part in re.split(r"(?<=[.!?])\s+", summary) if part.strip()
            ]
            experience_text = normalize_for_match(
                " ".join(
                    bullet
                    for entry in experience
                    for bullet in (entry.get("bullets") or [])
                )
            )
            for sentence in summary_sentences:
                if len(sentence.split()) < 6:
                    continue
                if normalize_for_match(sentence)[:70] in experience_text:
                    new_summary = summary.replace(sentence, "").strip()
                    new_summary = re.sub(r"\s{2,}", " ", new_summary)
                    if new_summary:
                        add(
                            "Perfil",
                            summary,
                            "El perfil repite una idea que ya aparece en la experiencia.",
                            new_summary,
                            "Eliminar redundancias hace que cada sección aporte información nueva.",
                            evidence=sentence,
                        )
                    break

        return proposals[:12]

    @staticmethod
    def _rewrite_weak(text: str) -> str:
        result = text
        for weak, replacement in sorted(WEAK_PHRASES, key=lambda item: len(item[0]), reverse=True):
            if normalize_for_match(weak) in normalize_for_match(result):
                pattern = re.compile(re.escape(weak), re.IGNORECASE)
                result = pattern.sub(replacement, result, count=1)
                break
        result = normalize_whitespace(result)
        if result:
            result = result[0].upper() + result[1:]
        return result


class MissingInfoDetector:
    """Genera preguntas concretas para completar información sin inventar datos."""

    def detect(
        self,
        content: dict[str, Any],
        raw_text: str,
        offer_text: str = "",
        offer_keywords: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        questions: list[dict[str, Any]] = []
        personal = content.get("personal") or {}
        summary = str(content.get("summary") or "")
        experience = content.get("experience") or []
        skills = (content.get("skills") or {}).get("technical") or []

        def add(topic: str, question: str, why: str, example: str) -> None:
            if any(item["question"] == question for item in questions):
                return
            questions.append(
                {
                    "topic": topic,
                    "question": question,
                    "why_important": why,
                    "example_text": example,
                    "origin": ORIGIN_ILLUSTRATIVE,
                }
            )

        if not summary.strip() or word_count(summary) < 25:
            add(
                "Perfil profesional",
                "¿Cuál es su especialidad principal, cuántos años de experiencia tiene y "
                "qué tipo de resultados ha logrado?",
                "El perfil es lo primero que lee un reclutador y ayuda al ATS a identificar "
                "el cargo objetivo.",
                "EJEMPLO ILUSTRATIVO — NO VERIFICADO: Analista de datos con X años de "
                "experiencia en SQL y Power BI, enfocado en reportes para áreas comerciales.",
            )

        if not personal.get("email") or not personal.get("phone"):
            add(
                "Datos de contacto",
                "¿Cuál es su correo profesional y teléfono de contacto?",
                "Sin datos de contacto el reclutador no puede iniciar el proceso.",
                "EJEMPLO ILUSTRATIVO — NO VERIFICADO: nombre@dominio.com | +00 000 000 000",
            )

        if experience and not any(
            entry.get("start_date") or entry.get("end_date") for entry in experience
        ):
            add(
                "Fechas de experiencia",
                "¿Qué fechas de inicio y fin corresponden a cada puesto?",
                "Los ATS y reclutadores necesitan calcular la trayectoria y detectar "
                "periodos sin actividad.",
                "EJEMPLO ILUSTRATIVO — NO VERIFICADO: marzo 2021 – actualidad.",
            )

        if not content.get("education"):
            add(
                "Formación académica",
                "¿Qué formación académica posee (título, institución y periodo)?",
                "Muchas ofertas exigen un nivel mínimo de formación y los ATS lo verifican.",
                "EJEMPLO ILUSTRATIVO — NO VERIFICADO: Licenciatura en Administración, "
                "Universidad de ejemplo, 2016 – 2020.",
            )

        # Resultados sin métricas por puesto (máximo 2).
        metric_count = 0
        for entry in experience[:4]:
            if metric_count >= 2:
                break
            bullets = entry.get("bullets") or []
            if bullets and not any(has_metric(bullet) for bullet in bullets):
                role = str(entry.get("role") or "su puesto")
                add(
                    f"Resultados en {role}",
                    f"¿Qué resultado concreto obtuvo en {role}? ¿Puede indicar alcance, "
                    "magnitud o periodo?",
                    "La evidencia de resultados diferencia una responsabilidad de un logro.",
                    "EJEMPLO ILUSTRATIVO — NO VERIFICADO: Reduje el tiempo de elaboración "
                    "de reportes de X a Y horas mediante la automatización de Z.",
                )
                metric_count += 1

        # Herramientas declaradas sin uso en experiencia (máximo 3).
        experience_text = normalize_for_match(
            "\n".join(
                " ".join(entry.get("bullets") or []) + " " + str(entry.get("description", ""))
                for entry in experience
            )
        )
        unused = [
            skill for skill in skills
            if normalize_for_match(str(skill)) not in experience_text
        ][:3]
        for skill in unused:
            add(
                f"Uso de {skill}",
                f"¿En qué proyecto o responsabilidad utilizó {skill} y qué resultado obtuvo?",
                f"La mención de {skill} sin contexto no demuestra dominio y puede ser "
                "cuestionada en una entrevista.",
                f"EJEMPLO ILUSTRATIVO — NO VERIFICADO: Utilicé {skill} para [proceso] "
                "en [área], obteniendo [resultado verificable].",
            )

        # Brechas frente a la oferta.
        if offer_keywords:
            missing = [
                keyword for keyword in offer_keywords
                if normalize_for_match(keyword) not in normalize_for_match(raw_text)
            ][:3]
            for keyword in missing:
                add(
                    f"Requisito de la oferta: {keyword}",
                    f"La oferta solicita {keyword}. ¿Tiene experiencia real con esta "
                    "tecnología o conocimiento?",
                    "Agregar requisitos no demostrados reduce la credibilidad y puede "
                    "fallar en la entrevista técnica.",
                    f"EJEMPLO ILUSTRATIVO — NO VERIFICADO: Experiencia con {keyword} en "
                    "[proyecto real], aplicada a [objetivo].",
                )

        if not content.get("languages"):
            add(
                "Idiomas",
                "¿Qué idiomas habla y cuál es su nivel real (A1–C2 o equivalente)?",
                "Algunas vacantes exigen un nivel mínimo de idioma y el ATS lo busca "
                "explícitamente.",
                "EJEMPLO ILUSTRATIVO — NO VERIFICADO: Inglés — B2.",
            )

        return questions[:8]


class OptimizerService:
    def __init__(self, database: Database, ai_service: AIService) -> None:
        self.database = database
        self.ai = ai_service
        self.rules = RuleBasedOptimizer()
        self.missing_detector = MissingInfoDetector()

    # ------------------------------------------------------------------ run
    def run(
        self,
        version_id: int,
        offer_id: int | None = None,
        use_ai: bool = True,
        cancel_event=None,  # type: ignore[no-untyped-def]
        progress: Progress | None = None,
    ) -> OptimizationOutcome:
        with self.database.session() as session:
            version = CVRepository(session).get_version(version_id)
            if version is None:
                raise ValueError("La versión de CV no existe.")
            offer = OfferRepository(session).get(offer_id) if offer_id else None
            content = copy.deepcopy(version.content or {})
            raw_text = version.raw_text or content_to_text(content)
            offer_text = offer.raw_text if offer else ""
            requirement_dicts = (
                [
                    {"keywords": list(requirement.keywords or []), "text": requirement.text}
                    for requirement in offer.requirements
                ]
                if offer else []
            )
            offer_keywords = offer_keyword_list(requirement_dicts, offer_text)

        warnings: list[str] = []
        if progress:
            progress(10, "Analizando el CV con el motor de reglas…")
        proposals = self.rules.propose(content, raw_text, offer_text, offer_keywords)

        if progress:
            progress(30, "Detectando información faltante…")
        missing = self.missing_detector.detect(
            content, raw_text, offer_text, offer_keywords
        )

        provider = "rules"
        model = ""
        used_ai = False
        if use_ai:
            ready, reason = self.ai.is_ready()
            if ready:
                try:
                    if progress:
                        progress(45, "Generando propuestas con el modelo local…")
                    system, prompt = self.ai.prompts.optimization(
                        raw_text, offer_text, "Perfil profesional del CV"
                    )
                    data, _result = self.ai.generate_structured(
                        "optimization", system, prompt, cancel_event=cancel_event
                    )
                    ai_proposals = self.ai.validator.validate_proposals(data, raw_text)
                    used_ai = True
                    provider = self.ai.provider.name
                    model = self.ai.model
                    if progress:
                        progress(75, "Validando que no se inventen datos…")
                    merged: dict[str, dict[str, Any]] = {}
                    for proposal in ai_proposals + proposals:
                        key = normalize_for_match(proposal["original_text"])[:160]
                        if key not in merged:
                            merged[key] = proposal
                    proposals = list(merged.values())[:20]

                    if progress:
                        progress(82, "Buscando información faltante con IA…")
                    system, prompt = self.ai.prompts.missing_information(
                        raw_text, offer_text
                    )
                    data, _result = self.ai.generate_structured(
                        "missing_information", system, prompt, cancel_event=cancel_event
                    )
                    ai_questions = self.ai.validator.validate_missing_information(data)
                    seen = {normalize_for_match(item["question"]) for item in missing}
                    for item in ai_questions:
                        key = normalize_for_match(item["question"])
                        if key not in seen:
                            missing.append(item)
                            seen.add(key)
                    missing = missing[:10]
                except AIValidationError as exc:
                    warnings.append(
                        "La IA devolvió una respuesta no utilizable; se conservaron las "
                        f"sugerencias del motor de reglas. Detalle: {exc}"
                    )
                except Exception as exc:
                    warnings.append(
                        f"No se pudo completar la optimización con IA: {exc}. "
                        "Se muestran las sugerencias del motor de reglas."
                    )
            else:
                warnings.append(
                    "La IA local no está disponible: " + (reason or "Ollama no está activo.")
                    + " Se usaron las sugerencias del motor de reglas."
                )

        summary = (
            f"Se generaron {len(proposals)} propuestas y {len(missing)} preguntas de "
            f"información faltante. Motor: {'IA local (' + model + ')' if used_ai else 'reglas'}."
        )
        if progress:
            progress(92, "Guardando la sesión de optimización…")

        with self.database.session() as session:
            repo = OptimizationRepository(session)
            opt_session = repo.create_session(
                cv_version_id=version_id,
                job_offer_id=offer_id,
                provider=provider,
                model=model or None,
                status="completed",
                summary=summary,
            )
            repo.add_proposals(opt_session.id, proposals)
            MissingInformationRepository(session).replace_for_version(
                version_id, offer_id, missing
            )
            session_id = opt_session.id
            stored = repo.get_session(session_id)
            proposal_dicts = [self._proposal_to_dict(item) for item in stored.proposals]
            missing_items = [
                self._missing_to_dict(item)
                for item in MissingInformationRepository(session).list_for_version(version_id)
            ]

        if progress:
            progress(100, "Optimización completada.")
        return OptimizationOutcome(
            session_id=session_id,
            proposals=proposal_dicts,
            missing=missing_items,
            provider=provider,
            model=model,
            summary=summary,
            used_ai=used_ai,
            warnings=warnings,
        )

    # --------------------------------------------------------------- aplicar
    def apply(
        self,
        version_id: int,
        proposal_ids: list[int],
        label: str | None = None,
    ) -> tuple[int, int, list[str]]:
        with self.database.session() as session:
            version = CVRepository(session).get_version(version_id)
            if version is None:
                raise ValueError("La versión de CV no existe.")
            repo = OptimizationRepository(session)
            selected = [
                repo.get_proposal(proposal_id)
                for proposal_id in proposal_ids
            ]
            selected = [
                item for item in selected
                if item is not None and item.status in {"accepted", "edited"}
            ]
            if not selected:
                raise ValueError("No hay propuestas aceptadas para aplicar.")

            content = copy.deepcopy(version.content or {})
            applied = 0
            skipped: list[str] = []
            for proposal in selected:
                new_text = (
                    proposal.edited_text
                    if proposal.status == "edited" and proposal.edited_text
                    else proposal.proposed_text
                )
                if self._replace_in_content(content, proposal.original_text, new_text):
                    applied += 1
                else:
                    skipped.append(truncate(proposal.original_text, 100))

            if applied == 0:
                raise ValueError(
                    "No se pudo aplicar ninguna propuesta: el texto original ya no "
                    "coincide con el contenido de la versión."
                )

            new_raw = content_to_text(content)
            new_label = label or f"Optimizada — {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            new_version = CVRepository(session).create_version(
                cv_id=version.cv_id,
                label=new_label,
                content=content,
                raw_text=new_raw,
                source="optimized",
                parent_version_id=version.id,
                sections=self.content_to_sections(content),
            )
            return new_version.id, applied, skipped

    @staticmethod
    def _replace_in_content(content: dict[str, Any], original: str, new_text: str) -> bool:
        original = original.strip()
        if not original:
            return False
        replaced = False

        if original in str(content.get("summary") or ""):
            content["summary"] = str(content["summary"]).replace(original, new_text, 1)
            replaced = True

        for entry in content.get("experience") or []:
            bullets = entry.get("bullets") or []
            for index, bullet in enumerate(bullets):
                if original in bullet:
                    bullets[index] = bullet.replace(original, new_text, 1)
                    replaced = True
            if original in str(entry.get("description") or ""):
                entry["description"] = str(entry["description"]).replace(original, new_text, 1)
                replaced = True

        for key in ("projects", "education"):
            for entry in content.get(key) or []:
                for field in ("description", "details"):
                    if original in str(entry.get(field) or ""):
                        entry[field] = str(entry[field]).replace(original, new_text, 1)
                        replaced = True

        for key in ("certifications", "achievements", "additional"):
            items = content.get(key) or []
            for index, item in enumerate(items):
                if original in str(item):
                    items[index] = str(item).replace(original, new_text, 1)
                    replaced = True

        skills = content.get("skills") or {}
        for group in ("technical", "soft"):
            items = skills.get(group) or []
            for index, item in enumerate(items):
                if original in str(item):
                    items[index] = str(item).replace(original, new_text, 1)
                    replaced = True
        return replaced

    @staticmethod
    def content_to_sections(content: dict[str, Any]) -> list[dict[str, Any]]:
        personal = content.get("personal") or {}
        sections = [
            {
                "section_type": "personal",
                "title": SECTION_LABELS["personal"],
                "content": "\n".join(str(value) for value in personal.values() if value),
                "data": personal,
                "data_origin": "USER_CONFIRMED",
            },
            {
                "section_type": "perfil",
                "title": SECTION_LABELS["perfil"],
                "content": str(content.get("summary") or ""),
                "data_origin": "USER_CONFIRMED",
            },
        ]
        experience_lines = []
        for entry in content.get("experience") or []:
            title = " | ".join(filter(None, [entry.get("role", ""), entry.get("company", "")]))
            experience_lines.append(f"{title} {entry.get('period', '')}".strip())
            experience_lines.extend(f"• {bullet}" for bullet in entry.get("bullets") or [])
        sections.append(
            {
                "section_type": "experiencia",
                "title": SECTION_LABELS["experiencia"],
                "content": "\n".join(experience_lines),
                "data_origin": "USER_CONFIRMED",
            }
        )
        skills = content.get("skills") or {}
        if skills.get("technical"):
            sections.append(
                {
                    "section_type": "competencias_tecnicas",
                    "title": SECTION_LABELS["competencias_tecnicas"],
                    "content": ", ".join(skills["technical"]),
                    "data_origin": "USER_CONFIRMED",
                }
            )
        if skills.get("soft"):
            sections.append(
                {
                    "section_type": "competencias_blandas",
                    "title": SECTION_LABELS["competencias_blandas"],
                    "content": ", ".join(skills["soft"]),
                    "data_origin": "USER_CONFIRMED",
                }
            )
        if content.get("education"):
            sections.append(
                {
                    "section_type": "educacion",
                    "title": SECTION_LABELS["educacion"],
                    "content": "\n".join(
                        " | ".join(
                            filter(None, [item.get("degree", ""), item.get("institution", "")])
                        )
                        for item in content["education"]
                    ),
                    "data_origin": "USER_CONFIRMED",
                }
            )
        return sections

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _proposal_to_dict(item) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        return {
            "id": item.id,
            "session_id": item.session_id,
            "section": item.section,
            "original_text": item.original_text,
            "problem": item.problem,
            "proposed_text": item.proposed_text,
            "justification": item.justification,
            "evidence": item.evidence,
            "origin": item.origin,
            "status": item.status,
            "edited_text": item.edited_text,
            "issues": item.issues or [],
        }

    @staticmethod
    def _missing_to_dict(item) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        return {
            "id": item.id,
            "topic": item.topic,
            "question": item.question,
            "why_important": item.why_important,
            "example_text": item.example_text,
            "origin": item.origin,
            "answer": item.answer,
            "status": item.status,
        }
