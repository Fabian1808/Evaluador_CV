# CV Analyzer Pro

Aplicación de escritorio en Python para organizar CV y ofertas, evaluarlos con criterios ATS, de RR. HH. y técnicos, y generar documentos profesionales.

## Estado del proyecto

El repositorio contiene una base amplia de servicios, persistencia SQLite y componentes reutilizables de interfaz PySide6. Ya cuenta con una ventana inicial y navegación; la mayoría de los flujos de trabajo todavía no están conectados. Tampoco hay manifiesto de dependencias ni suite de pruebas.

## Componentes presentes

- `app/services/`: análisis y parseo de CV/ofertas, evaluación, comparación, optimización y generación de documentos.
- `app/database/`: modelos SQLAlchemy, repositorios, sesión, migración inicial y respaldo.
- `app/ai/`: proveedor compatible con Ollama, gestión de modelos y validación de respuestas.
- `app/ui/`: widgets, diálogos, vista de evaluación y tareas de fondo (PySide6).
- `app/core/context.py`: composición de servicios y configuración de aplicación.
- `resources/`: estilos, iconos y plantillas.

## Requisitos detectados

Python 3.10 o posterior. Las dependencias principales y de lectura/generación documental están declaradas en `requirements.txt`. OCR requiere además una instalación del ejecutable Tesseract en el sistema.

## Próximos pasos

1. Añadir y fijar dependencias del proyecto, además de instrucciones de instalación.
2. Completar los flujos de importación de CV y oferta y verificar evaluación de extremo a extremo.
3. Añadir pruebas de parser, puntuación y persistencia.
4. Preparar empaquetado y una guía de usuario.

## Inicio

Con Python instalado, crea un entorno virtual, instala dependencias con `pip install -r requirements.txt` y ejecuta `python -m app` (o `python main.py`) desde la raíz. La aplicación incluye panel, gestión de candidatos y ofertas, importación PDF/DOCX, edición versionada, exportación PDF/DOCX, comparación, optimización con aplicación revisada, evaluación con historial y ajustes de conexión IA/pesos. La gestión guiada de preguntas de información pendiente sigue en desarrollo.

### Flujo rápido de postulación

1. Abre **Match rápido**.
2. Sube tu CV en PDF o DOCX y pega el texto de la oferta laboral.
3. Pulsa **Analizar match y sugerir cambios**.
4. Revisa el porcentaje de compatibilidad, la evaluación ATS/RR. HH./técnica y la pestaña **Qué cambiar**.

El sistema guarda el CV, el puesto y el resultado en el equipo. Las sugerencias de IA local usan Ollama y Qwen 3.5 4B; si Ollama no responde, muestra las sugerencias del motor de reglas y avisa. El modelo ya viene descargado en este equipo y Ollama está configurado para iniciarse con Windows.

### Usar el ejecutable

Abre `dist\CV Analyzer Pro.exe`, entra en **Match rápido**, selecciona tu CV y pega la oferta. No necesitas instalar Python. La IA local ya está activa en este equipo. La primera respuesta completa puede tardar alrededor de 2–3 minutos en este portátil porque el modelo se ejecuta con CPU; el porcentaje de match y las sugerencias de reglas quedan disponibles como respaldo.

## Crear ejecutable para Windows

En Windows, abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
.\build_windows.ps1
```

El script instala los requisitos de compilación y genera `dist\CV Analyzer Pro.exe`. El ejecutable es de un solo archivo y no necesita Python instalado. Los datos persistentes se guardan en `%LOCALAPPDATA%\CV Analyzer Pro`; las plantillas y recursos se empaquetan junto con la aplicación. La primera compilación puede tardar varios minutos y producir un archivo grande.

Se generó un ejecutable de prueba de 98 MB en `dist/CV Analyzer Pro.exe`. Para usar OCR, cada equipo debe tener Tesseract instalado; Ollama también es un servicio opcional independiente para las funciones de IA local.

Consulta [docs/BITACORA.md](docs/BITACORA.md) para el registro paso a paso.
