"""Constantes compartidas: identidad visual, catálogos y reglas de negocio."""

from __future__ import annotations

APP_NAME = "CV Analyzer Pro"
APP_VERSION = "1.0.0"
APP_ORGANIZATION = "CV Analyzer Pro"
APP_DESCRIPTION = (
    "Evaluación integral de CV con inteligencia artificial local, análisis ATS, "
    "perspectiva de Recursos Humanos y generación de documentos profesionales."
)

# ---------------------------------------------------------------------------
# Identidad visual
# ---------------------------------------------------------------------------
COLOR_PRIMARY = "#FF5500"
COLOR_PRIMARY_DARK = "#D94800"
COLOR_PRIMARY_SOFT = "#FFF0E8"
COLOR_DARK = "#3B3B3B"
COLOR_TEXT = "#2B2B2B"
COLOR_MUTED = "#6B7280"
COLOR_BORDER = "#E5E7EB"
COLOR_BACKGROUND = "#F5F6F8"
COLOR_CARD = "#FFFFFF"
COLOR_SUCCESS = "#1E8E5A"
COLOR_SUCCESS_SOFT = "#E8F6EF"
COLOR_WARNING = "#B45309"
COLOR_WARNING_SOFT = "#FEF3C7"
COLOR_DANGER = "#B42318"
COLOR_DANGER_SOFT = "#FEE4E2"
COLOR_INFO = "#1D4ED8"
COLOR_INFO_SOFT = "#E8EEFF"

NAV_ITEMS: list[tuple[str, str, str]] = [
    ("dashboard", "Dashboard", "Resumen general"),
    ("candidates", "Candidatos", "Gestión de candidatos"),
    ("cvs", "Mis CV", "Documentos y versiones"),
    ("offers", "Ofertas laborales", "Vacantes y requisitos"),
    ("evaluations", "Evaluaciones", "ATS, RR. HH. y técnico"),
    ("quick_match", "Match rápido", "CV frente a una vacante"),
    ("comparison", "Comparación", "Versiones y candidatos"),
    ("optimizer", "Optimización IA", "Mejora de redacción"),
    ("generator", "Generador de CV", "Plantilla Harvard"),
    ("history", "Historial", "Evaluaciones guardadas"),
    ("settings", "Configuración", "Modelos y preferencias"),
]

# ---------------------------------------------------------------------------
# Secciones curriculares
# ---------------------------------------------------------------------------
SECTION_LABELS: dict[str, str] = {
    "personal": "Datos personales",
    "perfil": "Perfil profesional",
    "experiencia": "Experiencia profesional",
    "educacion": "Educación",
    "competencias_tecnicas": "Competencias técnicas",
    "competencias_blandas": "Competencias blandas",
    "certificaciones": "Certificaciones",
    "idiomas": "Idiomas",
    "proyectos": "Proyectos",
    "logros": "Logros",
    "adicional": "Información adicional",
}

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "perfil": (
        "perfil profesional", "perfil", "resumen profesional", "resumen",
        "objetivo profesional", "objetivo", "about me", "professional summary",
        "summary", "profile", "acerca de",
    ),
    "experiencia": (
        "experiencia profesional", "experiencia laboral", "experiencia",
        "trayectoria profesional", "historial laboral", "work experience",
        "experience", "employment history", "professional experience",
    ),
    "educacion": (
        "educación", "educacion", "formación académica", "formacion academica",
        "formación", "estudios", "education", "academic background",
    ),
    "competencias_tecnicas": (
        "competencias técnicas", "competencias tecnicas", "habilidades técnicas",
        "habilidades tecnicas", "conocimientos técnicos", "conocimientos",
        "herramientas", "tecnologías", "technical skills", "skills", "hard skills",
    ),
    "competencias_blandas": (
        "competencias blandas", "habilidades blandas", "soft skills",
        "habilidades personales", "competencias", "aptitudes",
    ),
    "certificaciones": (
        "certificaciones", "certificados", "certifications", "licencias",
    ),
    "idiomas": ("idiomas", "languages", "lenguas"),
    "proyectos": ("proyectos", "projects", "portafolio", "portfolio"),
    "logros": (
        "logros", "logros profesionales", "achievements", "reconocimientos",
        "premios", "awards",
    ),
    "adicional": (
        "información adicional", "informacion adicional", "otros datos",
        "additional information", "referencias", "intereses",
    ),
}

# ---------------------------------------------------------------------------
# Origen y estado de los datos
# ---------------------------------------------------------------------------
ORIGIN_ORIGINAL = "ORIGINAL_DOCUMENT"
ORIGIN_USER = "USER_PROVIDED"
ORIGIN_CONFIRMED = "USER_CONFIRMED"
ORIGIN_AI = "AI_SUGGESTED"
ORIGIN_ILLUSTRATIVE = "ILLUSTRATIVE_EXAMPLE"
ORIGIN_RULE = "RULE_BASED"

DATA_ORIGINS: dict[str, str] = {
    ORIGIN_ORIGINAL: "Documento original",
    ORIGIN_USER: "Proporcionado por el usuario",
    ORIGIN_CONFIRMED: "Confirmado por el usuario",
    ORIGIN_AI: "Sugerido por IA (requiere confirmación)",
    ORIGIN_ILLUSTRATIVE: "Ejemplo ilustrativo — NO VERIFICADO",
    ORIGIN_RULE: "Sugerencia del motor de reglas (requiere confirmación)",
}

REQUIREMENT_STATUSES: dict[str, str] = {
    "DEMOSTRADO": "Demostrado",
    "PARCIALMENTE_DEMOSTRADO": "Parcialmente demostrado",
    "MENCIONADO_SIN_EVIDENCIA": "Mencionado sin evidencia suficiente",
    "NO_IDENTIFICADO": "No identificado",
    "PENDIENTE_CONFIRMACION": "Pendiente de confirmación",
}

PROPOSAL_STATUSES: dict[str, str] = {
    "pending": "Pendiente",
    "accepted": "Aceptada",
    "rejected": "Rechazada",
    "edited": "Editada",
}

# ---------------------------------------------------------------------------
# Puntuación
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS: dict[str, float] = {"ats": 25.0, "hr": 35.0, "technical": 40.0}

SCORE_DISCLAIMER = (
    "La puntuación es una estimación orientativa basada en criterios documentados. "
    "No garantiza superar los filtros ATS de una empresa: cada sistema ATS utiliza "
    "algoritmos y configuraciones diferentes."
)

CONFIDENCE_LABELS: dict[str, str] = {
    "alta": "Confianza alta",
    "media": "Confianza media",
    "baja": "Confianza baja",
}

# ---------------------------------------------------------------------------
# Catálogo de modelos locales recomendados (Ollama)
# ---------------------------------------------------------------------------
KNOWN_MODELS: list[dict] = [
    {
        "name": "qwen3.5:4b",
        "family": "Qwen 3.5",
        "parameters": "4B",
        "size_gb": 3.6,
        "ram_gb": 7.0,
        "quality": "Muy buena",
        "note": "Modelo compacto con buen seguimiento de instrucciones y soporte multilingüe.",
    },
    {
        "name": "qwen2.5:3b",
        "family": "Qwen 2.5",
        "parameters": "3B",
        "size_gb": 2.0,
        "ram_gb": 4.0,
        "quality": "Buena",
        "note": "Opción ligera para equipos con 8 GB de RAM. Rápida y correcta en español.",
    },
    {
        "name": "qwen2.5:7b",
        "family": "Qwen 2.5",
        "parameters": "7B",
        "size_gb": 4.7,
        "ram_gb": 8.0,
        "quality": "Muy buena",
        "note": "Equilibrio recomendado entre calidad de redacción y recursos.",
    },
    {
        "name": "gemma2:2b",
        "family": "Gemma 2",
        "parameters": "2B",
        "size_gb": 1.6,
        "ram_gb": 3.5,
        "quality": "Aceptable",
        "note": "Muy ligera. Útil para extracción simple, con menor profundidad analítica.",
    },
    {
        "name": "gemma2:9b",
        "family": "Gemma 2",
        "parameters": "9B",
        "size_gb": 5.5,
        "ram_gb": 10.0,
        "quality": "Muy buena",
        "note": "Buena redacción en español; requiere al menos 16 GB de RAM.",
    },
    {
        "name": "llama3.1:8b",
        "family": "Llama 3.1",
        "parameters": "8B",
        "size_gb": 4.7,
        "ram_gb": 9.0,
        "quality": "Muy buena",
        "note": "Sólida en instrucciones estructuradas y análisis de textos largos.",
    },
    {
        "name": "llama3.2:3b",
        "family": "Llama 3.2",
        "parameters": "3B",
        "size_gb": 2.0,
        "ram_gb": 4.5,
        "quality": "Buena",
        "note": "Ligera y rápida; adecuada para equipos modestos.",
    },
]

# ---------------------------------------------------------------------------
# Documento Harvard
# ---------------------------------------------------------------------------
HARVARD_FONTS: tuple[str, ...] = (
    "Arial", "Calibri", "Aptos", "Cambria", "Times New Roman",
)

DEFAULT_DOCUMENT_CONFIG: dict = {
    "template": "harvard",
    "font_family": "Calibri",
    "name_size": 19,
    "headline_size": 10.5,
    "heading_size": 11.5,
    "body_size": 10.5,
    "date_size": 9.5,
    "contact_size": 9.5,
    "line_spacing": 1.08,
    "margin_top_cm": 1.8,
    "margin_bottom_cm": 1.8,
    "margin_left_cm": 2.0,
    "margin_right_cm": 2.0,
    "space_after_pt": 4,
    "section_space_pt": 10,
    "uppercase_headings": True,
    "show_separator": True,
    "separator_style": "line",
    "alignment": "left",
    "include_photo": False,
}

# ---------------------------------------------------------------------------
# Utilidades lingüísticas
# ---------------------------------------------------------------------------
ACTION_VERBS: tuple[str, ...] = (
    "lideré", "lideré", "desarrollé", "implementé", "diseñé", "construí",
    "automaticé", "optimicé", "reduje", "aumenté", "mejoré", "gestioné",
    "coordiné", "dirigí", "analicé", "modelé", "creé", "migré", "integré",
    "desplegué", "documenté", "capacité", "negocié", "logré", "impulsé",
    "transformé", "estandaricé", "audité", "validé", "automatizé", "rediseñé",
    "supervisé", "administré", "ejecuté", "planifiqué", "consolidé",
    "led", "developed", "implemented", "designed", "built", "automated",
    "optimized", "reduced", "increased", "improved", "managed", "coordinated",
    "analyzed", "created", "migrated", "deployed", "documented", "trained",
)

WEAK_PHRASES: tuple[tuple[str, str], ...] = (
    ("responsable de realizar", "Realicé"),
    ("responsable de la realización de", "Realicé"),
    ("responsable de", "Gestioné"),
    ("encargado de realizar", "Ejecuté"),
    ("encargado de", "Gestioné"),
    ("encargada de", "Gestioné"),
    ("funciones de", "Ejecuté"),
    ("funciones:", ""),
    ("participé en", "Contribuí a"),
    ("participé activamente en", "Contribuí a"),
    ("ayudé en", "Apoyé en"),
    ("ayudé a", "Apoyé en"),
    ("apoyé en la realización de", "Apoyé la ejecución de"),
    ("me desempeñé como", "Ejercí como"),
    ("tuve a cargo", "Gestioné"),
    ("a cargo de", "Responsable de"),
    ("realicé labores de", "Ejecuté"),
    ("realización de", "Ejecución de"),
    ("manejo de", "Gestión de"),
    ("encargado del", "Gestioné el"),
)

GENERIC_PHRASES: tuple[str, ...] = (
    "profesional proactivo", "persona proactiva", "trabajo en equipo",
    "orientado a resultados", "orientada a resultados", "alto compromiso",
    "capacidad de aprendizaje", "adaptación al cambio", "pensamiento crítico",
    "excelente comunicación", "liderazgo", "responsable", "puntual",
    "dinámico", "dinámica", "proactivo", "proactiva", "multitarea",
    "hard worker", "team player", "go-getter", "rockstar", "ninja",
)

STOPWORDS: frozenset[str] = frozenset(
    """
    de la el los las un una unos unas y o u en con por para sin sobre entre
    al del a e que se su sus es son fue fueron ser estar está están como más
    pero sus le les lo mi mis tu tus nuestro nuestra sus este esta estos estas
    ese esa esos esas aquel aquella aquellos aquellas y/o mediante desde hasta
    durante todo toda todos todas otro otra otros otras mismo misma también
    muy sin cada vez año años mes meses día días experiencia trabajo empresa
    puesto cargo área área funciones responsabilidades conocimiento manejo
    the and of to in for with on at by from as is are was were be been being
    this that these those an or not no it its their our your my we you they
    he she his her have has had do does did will would can could should may
    """.split()
)

MONTHS_ES: dict[str, int] = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_AI_SETTINGS: dict = {
    "provider": "ollama",
    "base_url": DEFAULT_OLLAMA_URL,
    "model": "qwen3.5:4b",
    "temperature": 0.3,
    "top_p": 0.9,
    "timeout_seconds": 180,
    "use_cache": True,
    "max_context_chars": 18000,
}

DEFAULT_TECHNICAL_PROFILES: list[dict] = [
    {
        "name": "Data Analytics",
        "description": (
            "Análisis de datos, SQL, Python, estadística, ETL, modelamiento de datos, "
            "Databricks, calidad de datos y análisis exploratorio."
        ),
        "competencies": [
            {"name": "SQL", "aliases": ["sql", "consultas sql", "t-sql", "pl/sql"]},
            {"name": "Python", "aliases": ["python", "pandas", "numpy"]},
            {"name": "Estadística", "aliases": ["estadística", "estadistica", "regresión", "regresion", "hipótesis", "hipotesis"]},
            {"name": "ETL", "aliases": ["etl", "elt", "extracción transformación", "extraccion transformacion", "pipeline de datos", "pipelines de datos"]},
            {"name": "Modelamiento de datos", "aliases": ["modelamiento de datos", "modelo de datos", "modelo dimensional", "modelado de datos"]},
            {"name": "Databricks", "aliases": ["databricks", "spark", "pyspark"]},
            {"name": "Calidad de datos", "aliases": ["calidad de datos", "data quality", "validación de datos", "validacion de datos", "limpieza de datos"]},
            {"name": "Análisis exploratorio", "aliases": ["análisis exploratorio", "analisis exploratorio", "eda", "exploratory data analysis"]},
        ],
    },
    {
        "name": "Business Intelligence",
        "description": (
            "Power BI, DAX, Power Query, Excel, KPIs, dashboards, modelamiento "
            "dimensional y reporting."
        ),
        "competencies": [
            {"name": "Power BI", "aliases": ["power bi", "powerbi", "pbi"]},
            {"name": "DAX", "aliases": ["dax"]},
            {"name": "Power Query", "aliases": ["power query", "m language", "lenguaje m"]},
            {"name": "Excel", "aliases": ["excel", "hojas de cálculo", "hojas de calculo", "tablas dinámicas", "tablas dinamicas"]},
            {"name": "KPIs", "aliases": ["kpi", "kpis", "indicadores clave", "indicadores de gestión", "indicadores de gestion"]},
            {"name": "Dashboards", "aliases": ["dashboard", "dashboards", "tablero de control", "tableros de control", "cuadro de mando"]},
            {"name": "Modelamiento dimensional", "aliases": ["modelamiento dimensional", "modelo estrella", "esquema estrella", "star schema", "modelo dimensional"]},
            {"name": "Reporting", "aliases": ["reporting", "reportes", "informes", "reportes ejecutivos", "informes ejecutivos"]},
        ],
    },
    {
        "name": "Automatización",
        "description": (
            "Power Apps, Power Automate, VBA, Python, APIs, automatización de "
            "procesos y digitalización."
        ),
        "competencies": [
            {"name": "Power Apps", "aliases": ["power apps", "powerapps"]},
            {"name": "Power Automate", "aliases": ["power automate", "powerautomate", "flow", "flujos"]},
            {"name": "VBA", "aliases": ["vba", "macros", "macro"]},
            {"name": "Python", "aliases": ["python"]},
            {"name": "APIs", "aliases": ["api", "apis", "rest", "webservice", "web service", "integraciones"]},
            {"name": "Automatización de procesos", "aliases": ["automatización de procesos", "automatizacion de procesos", "rpa", "automatización", "automatizacion"]},
            {"name": "Digitalización", "aliases": ["digitalización", "digitalizacion", "transformación digital", "transformacion digital"]},
        ],
    },
]

SOFT_SKILL_HINTS: tuple[str, ...] = (
    "comunicación", "comunicacion", "liderazgo", "trabajo en equipo",
    "negociación", "negociacion", "adaptabilidad", "pensamiento analítico",
    "pensamiento analitico", "resolución de problemas", "resolucion de problemas",
    "organización", "organizacion", "proactividad", "empatía", "empatia",
    "gestión del tiempo", "gestion del tiempo", "colaboración", "colaboracion",
)

LANGUAGE_LEVELS: tuple[str, ...] = (
    "Básico", "Intermedio", "Avanzado", "Fluido", "Nativo",
    "A1", "A2", "B1", "B2", "C1", "C2",
)

TECH_KEYWORDS: tuple[str, ...] = (
    "python", "sql", "power bi", "powerbi", "dax", "power query", "excel",
    "databricks", "spark", "pyspark", "pandas", "numpy", "scikit-learn",
    "machine learning", "etl", "elt", "api", "apis", "rest", "json", "git",
    "github", "docker", "kubernetes", "azure", "aws", "gcp", "tableau",
    "qlik", "sap", "oracle", "postgresql", "mysql", "sql server", "mongodb",
    "power apps", "power automate", "vba", "rpa", "sharepoint", "jira",
    "figma", "java", "javascript", "typescript", "c#", "php", "html", "css",
    "react", "node", "django", "flask", "fastapi", "streamlit", "airflow",
    "dbt", "snowflake", "bigquery", "redshift", "looker", "salesforce",
    "scrum", "kanban", "agile", "lean", "six sigma", "jira", "confluence",
)
