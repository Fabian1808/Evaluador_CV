"""Plantillas de instrucciones para la IA local.

Todas las plantillas obligan a responder en español, a no inventar información y
a respetar el protocolo de datos faltantes. Los prompts son deliberadamente
explícitos para compensar las limitaciones de los modelos pequeños.
"""

from __future__ import annotations

import json

SYSTEM_RULES = """Eres un asistente experto en reclutamiento, sistemas ATS y redacción de CV.
Trabajas para CV Analyzer Pro y respondes siempre en español neutro y profesional.

REGLAS OBLIGATORIAS:
1. No inventes empresas, cargos, fechas, títulos, universidades, certificaciones,
   herramientas, proyectos, responsabilidades, resultados, porcentajes ni métricas.
2. Usa únicamente la información presente en el CV o en las respuestas confirmadas
   del usuario. Si falta un dato, indícalo como pendiente; no lo completes.
3. No conviertas actividades rutinarias en logros extraordinarios sin evidencia.
4. No añadas tecnologías que el candidato no mencione.
5. No incluyas criterios discriminatorios ni datos personales protegidos.
6. No prometas que un CV superará un ATS: los ATS tienen algoritmos distintos.
7. Cuando se solicite JSON, responde SOLO con JSON válido, sin texto adicional ni
   bloques de código Markdown.
"""

OPTIMIZATION_PROMPT = """Analiza el siguiente CV y propone mejoras de redacción puntuales.

{offer_context}

PERFIL TÉCNICO OBJETIVO: {profile}

CV (texto extraído del documento original):
---
{cv_text}
---

Devuelve un objeto JSON con esta estructura exacta:
{{
  "proposals": [
    {{
      "section": "Perfil | Experiencia | Competencias | Educación | Otro",
      "original_text": "fragmento textual exacto del CV que se propone cambiar",
      "problem": "problema concreto de redacción, claridad, evidencia o keywords",
      "proposed_text": "nueva redacción profesional, sin inventar datos",
      "justification": "por qué la propuesta mejora el CV",
      "evidence": "fragmento del CV que respalda la propuesta"
    }}
  ]
}}

Reglas específicas:
- Propón exactamente 1 cambio concreto y prioritario; no reescribas todo el CV.
- Mantén cada campo en una frase breve y conserva literalmente los fragmentos del CV.
- Cada propuesta debe basarse en un fragmento que exista literalmente en el CV.
- Si falta una métrica, usa un marcador como [añadir métrica verificable] en lugar
  de inventar un número.
- Diferencia responsabilidades de logros.
- No agregues palabras clave que no estén respaldadas por la experiencia.
- Prioriza verbos de acción, frases directas y resultados verificables.
"""

MISSING_INFO_PROMPT = """Detecta información relevante que falta en este CV para evaluarlo
profesionalmente. No inventes datos.

{offer_context}

CV:
---
{cv_text}
---

Devuelve JSON con esta estructura:
{{
  "questions": [
    {{
      "topic": "tema breve",
      "question": "pregunta concreta y fácil de responder",
      "why_important": "por qué un reclutador o ATS necesita este dato",
      "example_text": "ejemplo hipotético de cómo podría redactarse, sin afirmar que sea real"
    }}
  ]
}}

Incluye exactamente 1 pregunta prioritaria sobre un vacío real: resultados sin métricas,
herramientas sin contexto de uso, periodos sin fechas, alcance de
responsabilidades, certificaciones o idiomas incompletos. No preguntes datos
protegidos (edad, estado civil, nacionalidad, fotografía).
"""

JOB_ANALYSIS_PROMPT = """Extrae la estructura de la siguiente oferta laboral.

OFERTA:
---
{offer_text}
---

Devuelve JSON con esta estructura:
{{
  "title": "puesto",
  "company": "empresa o cadena vacía",
  "area": "área o cadena vacía",
  "requirements": [
    {{
      "text": "requisito textual y concreto",
      "requirement_type": "mandatory | desirable",
      "category": "herramienta | experiencia | formacion | certificacion | idioma | competencia | otro",
      "keywords": ["términos verificables del requisito"]
    }}
  ]
}}

No inventes requisitos. Si un dato no aparece, usa cadena vacía. Distingue
requisitos obligatorios de deseables cuando la oferta lo indique.
"""

EVALUATION_SUMMARY_PROMPT = """Redacta un resumen ejecutivo breve (máximo 120 palabras) de la
siguiente evaluación de CV. No cambies las puntuaciones ni inventes evidencias.

Puntuaciones: ATS {ats}/100, RR. HH. {hr}/100, Técnico {technical}/100,
Global {overall}/100.
Fortalezas: {strengths}
Debilidades: {weaknesses}
Información faltante: {missing}
Oferta: {offer}

El resumen debe ser claro, profesional y accionable. No prometas superar filtros ATS.
"""

BENCHMARK_PROMPT = """Responde en español con un único objeto JSON válido:
{{"resumen": "reescribe en una frase profesional el siguiente texto sin inventar datos: 'Responsable de realizar reportes en Power BI para el área comercial'", "problema": "indica el principal problema de redacción"}}
"""

BENCHMARK_EXTRACTION_PROMPT = """Extrae requisitos de esta oferta y responde SOLO JSON válido:
Oferta: "Buscamos analista de datos con experiencia de 2 años en SQL y Power BI.
Deseable conocimiento de Python y Azure."
Formato: {{"requisitos": [{{"texto": "...", "tipo": "obligatorio|deseable", "categoria": "..."}}]}}
"""

BENCHMARK_WRITING_PROMPT = """Reescribe este logro profesional en una sola frase, sin inventar
métricas ni herramientas: "Encargado de hacer reportes para la gerencia".
Responde solo con la frase."""


class PromptManager:
    def __init__(self, max_context_chars: int = 18000) -> None:
        self.max_context_chars = max_context_chars

    def _truncate(self, value: str) -> str:
        value = value.strip()
        if len(value) <= self.max_context_chars:
            return value
        return value[: self.max_context_chars] + "\n[...texto truncado por longitud...]"

    def optimization(
        self, cv_text: str, offer_text: str = "", profile: str = ""
    ) -> tuple[str, str]:
        offer_context = (
            "OFERTA LABORAL OBJETIVO:\n---\n" + self._truncate(offer_text) + "\n---"
            if offer_text.strip()
            else "No se proporcionó una oferta laboral objetivo."
        )
        prompt = OPTIMIZATION_PROMPT.format(
            cv_text=self._truncate(cv_text),
            offer_context=offer_context,
            profile=profile or "No especificado",
        )
        return SYSTEM_RULES, prompt

    def missing_information(
        self, cv_text: str, offer_text: str = ""
    ) -> tuple[str, str]:
        offer_context = (
            "OFERTA OBJETIVO:\n---\n" + self._truncate(offer_text) + "\n---"
            if offer_text.strip()
            else "Sin oferta específica."
        )
        prompt = MISSING_INFO_PROMPT.format(
            cv_text=self._truncate(cv_text), offer_context=offer_context
        )
        return SYSTEM_RULES, prompt

    def job_analysis(self, offer_text: str) -> tuple[str, str]:
        prompt = JOB_ANALYSIS_PROMPT.format(offer_text=self._truncate(offer_text))
        return SYSTEM_RULES, prompt

    def evaluation_summary(
        self,
        ats: float,
        hr: float,
        technical: float,
        overall: float,
        strengths: list[str],
        weaknesses: list[str],
        missing: list[str],
        offer: str = "",
    ) -> tuple[str, str]:
        prompt = EVALUATION_SUMMARY_PROMPT.format(
            ats=round(ats, 1),
            hr=round(hr, 1),
            technical=round(technical, 1),
            overall=round(overall, 1),
            strengths="; ".join(strengths[:6]) or "No identificadas",
            weaknesses="; ".join(weaknesses[:6]) or "No identificadas",
            missing="; ".join(missing[:6]) or "Ninguna",
            offer=offer or "Sin oferta específica",
        )
        return SYSTEM_RULES, prompt

    def benchmark_prompt(self, kind: str) -> tuple[str, str]:
        mapping = {
            "structured": BENCHMARK_PROMPT,
            "extraction": BENCHMARK_EXTRACTION_PROMPT,
            "writing": BENCHMARK_WRITING_PROMPT,
        }
        return SYSTEM_RULES, mapping.get(kind, BENCHMARK_PROMPT)

    @staticmethod
    def json_schema_hint(schema: dict) -> str:
        return json.dumps(schema, ensure_ascii=False, indent=2)
