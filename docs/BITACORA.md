# Bitácora del proyecto

Registro incremental del trabajo y de las decisiones para que podamos retomar el proyecto sin perder contexto.

## 2026-11-21 — Revisión inicial y documentación base

1. Se inspeccionó el árbol del proyecto y se confirmó que hay módulos para servicios, base de datos, IA, componentes UI y recursos.
2. Se revisaron `app/core/context.py`, `app/database/migrations.py`, `app/services/evaluation_service.py` y los componentes de `app/ui/` para ubicar el flujo principal.
3. Se identificó que la capa de UI usa PySide6 y que hay una vista de resultados, widgets y diálogos reutilizables.
4. Se constató que en la carpeta raíz no hay README, manifiesto de dependencias, pruebas visibles ni módulo de inicio (`main.py`/ventana principal). Tampoco hay metadatos Git en esta carpeta.
5. Se creó el README con el estado conocido, los módulos y una secuencia de próximos pasos.
6. Siguiente avance recomendado: implementar el punto de entrada y la ventana principal con navegación mínima, reutilizando el contexto y componentes existentes.

### Alcance de esta revisión

Esta revisión fue estática; no se ejecutó la aplicación ni se verificaron flujos funcionales. Las dependencias listadas en README se infieren de imports presentes y deben concretarse con versiones al preparar el entorno.

## 2026-11-21 — Punto de entrada y navegación inicial

1. Se agregó `app/__main__.py` para iniciar la app como módulo y `main.py` como alternativa directa.
2. Se creó `app/ui/main_window.py` con barra lateral basada en el catálogo de navegación ya existente, encabezado y páginas en un contenedor apilado.
3. Se conectó el panel a `DashboardService` para mostrar candidatos, CV, ofertas, evaluaciones, promedio y actividad reciente.
4. Se añadieron páginas de estado para las secciones cuyo flujo todavía no está conectado, indicando claramente que se implementarán en pasos posteriores.
5. Se actualizó README con los comandos de inicio y se expuso el servicio del panel desde `AppContext`.

### Verificación y siguiente paso

No se ejecutó la interfaz en este paso. El inicio requiere las dependencias de Python que aún no están declaradas en un archivo de instalación. Siguiente paso: definir esas dependencias y después abrir la aplicación para corregir incompatibilidades de ejecución observadas.

## 2026-11-21 — Instalación y gestión básica

1. Se creó `requirements.txt` con PySide6, SQLAlchemy, Pydantic v2, PyMuPDF, python-docx, ReportLab y dependencias opcionales de OCR.
2. Se añadieron vistas CRUD de candidatos y ofertas usando los diálogos y servicios/repositorios existentes.
3. Se conectó la importación de CV PDF/DOCX a candidato, con presentación de diagnósticos y advertencias del parser.
4. Se actualizó el README con instalación e inicio y se conectaron esas vistas al menú.

### Pendiente

Las pantallas de comparación, optimización y generación siguen como marcadores de posición. No se había ejecutado la aplicación cuando se registró este paso; a continuación se hizo una comprobación de arranque en memoria y se conectó evaluación/historial.

## 2026-11-21 — Evaluación e historial conectados

1. Se integraron las vistas existentes de resultado y detalle con una selección de versión de CV, oferta opcional y perfil técnico.
2. La evaluación corre con el mecanismo de tareas de fondo y muestra progreso/cancelación; el usuario puede activar el resumen de IA local.
3. Se conectó el historial a las evaluaciones persistidas y se habilitó abrir el detalle con doble clic o botón.
4. Se hizo una comprobación de inicio Qt en modo offscreen con SQLite en memoria: se creó la ventana, cargaron las 10 secciones y el panel devolvió métricas vacías sin error.
5. Esa comprobación detectó un import incorrecto de `restyle` en los diálogos; se corrigió importándolo desde el módulo de widgets, que es donde está definido.

### Pendiente

Comparación, optimización y ajustes siguen sin flujos de interfaz. La importación documental real, evaluación con CV/oferta y exportación deben comprobarse con archivos de muestra antes de considerar la app lista para uso completo.

## 2026-11-21 — Edición de CV y exportación

1. Se habilitó editar el contenido estructurado de un CV con el diálogo existente; guardar genera una versión hija y conserva el archivo original.
2. Se añadió generación de documentos desde cualquier versión estructurada, con exportación a PDF y DOCX usando la configuración Harvard.
3. Se conectó la página Generador del menú a esta nueva vista.
4. Se amplió el smoke check Qt para abrir las diez páginas e incluir registros de prueba en memoria; las pantallas de candidatos, ofertas, evaluación e historial se cargaron correctamente.

### Pendiente

Falta conectar configuración y edición/respuesta de preguntas de información pendiente. Conviene probar importación, edición, evaluación y exportación con CV de muestra en Windows, incluido OCR opcional.

## 2026-11-21 — Comparación y optimización revisada

1. Se conectó la comparación entre dos versiones para mostrar similitud, cambios de experiencia, competencias, palabras clave y diff.
2. Se conectó la optimización con motor de reglas e IA local opcional, muestra sugerencias y preguntas faltantes.
3. El usuario puede marcar sugerencias concretas; estas se aplican como nueva versión hija sin modificar la versión de origen.
4. Se conectaron las dos vistas a la navegación y se actualizó la guía de funcionalidades.

## 2026-11-21 — Ajustes iniciales

1. Se añadieron controles para actualizar URL, nombre de modelo y tiempo máximo del servicio Ollama.
2. Se añadieron pesos editables para ATS, RR. HH. y evaluación técnica; el servicio existente los normaliza al usarlos.
3. Se conectó Configuración al menú y se documentaron las opciones disponibles.
4. Se hizo una prueba de integración manual en SQLite en memoria: se creó un candidato y un CV sintético, se evaluó y se generaron PDF y DOCX dentro de una carpeta temporal. La evaluación devolvió 32.3/100 y ambos archivos se crearon correctamente.

### Validación pendiente

La comprobación usa texto sintético y no prueba la extracción de archivos reales, el OCR, la disponibilidad real de Ollama ni las decisiones de optimización aplicadas a CVs variados. Queda pendiente la interfaz para contestar preguntas de información faltante y una validación manual con documentos representativos.

## 2026-11-21 — Ejecutable Windows

1. Se ajustó la resolución de recursos para PyInstaller y la persistencia para guardar los datos del ejecutable bajo `%LOCALAPPDATA%\CV Analyzer Pro`, fuera de la carpeta temporal de extracción.
2. Se añadieron `requirements-build.txt`, el archivo de configuración PyInstaller y `build_windows.ps1` para recrear el ejecutable.
3. Se fijó PyMuPDF a la rama 1.x para evitar dependencias opcionales voluminosas que llegaron con la 2.x.
4. Se compiló `dist/CV Analyzer Pro.exe` como archivo único. Tamaño observado: 98 MB.
5. Se inició el ejecutable en modo offscreen con una carpeta temporal aislada; creó correctamente la base SQLite y permaneció activo en el bucle de la interfaz. Después se cerró el proceso de prueba y se limpió su carpeta temporal.

### Consideraciones de distribución

El ejecutable se compiló en Windows 11 con Python 3.14.6. La primera apertura puede tardar mientras se extrae el contenido. OCR necesita que Tesseract esté instalado en el equipo; no se empaquetó ese ejecutable externo. La prueba de arranque no sustituye una validación visual de la ventana ni pruebas con documentos reales.

## 2026-11-21 — IA local y flujo Match rápido

1. Se comprobó que Ollama no estaba instalado; se instaló desde el instalador oficial de Windows. Se verificó que su acceso directo está en el inicio de Windows.
2. El equipo dispone de 24 GB de RAM, 124 GB libres y gráficos Intel integrados.
3. Se descargó y probó `qwen3.5:4b` (3.3 GB). Ollama quedó activo en `http://127.0.0.1:11434` y respondió a la aplicación.
4. Se agregó `qwen3.5:4b` como modelo predeterminado/recomendado en la configuración del proyecto.
5. Se creó **Match rápido**: subir PDF/DOCX, pegar oferta, crear o reutilizar candidato, guardar CV/vacante, evaluar compatibilidad y mostrar propuestas de optimización.
6. Se previno duplicar importaciones cuando se analiza de nuevo el mismo archivo para el mismo candidato.
7. Se documentó el flujo de postulación en el README.

8. Se guardó `qwen3.5:4b` como modelo activo en la base de datos de usuario del ejecutable (`%LOCALAPPDATA%\CV Analyzer Pro`).
9. Se validó de punta a punta un CV DOCX sintético: importación, oferta, evaluación (match 60/100), sugerencia de IA local, preguntas y ventana de resultados. La optimización con IA tardó 142 segundos en esta máquina.
10. Se ajustaron las llamadas a Ollama para desactivar razonamiento extendido y limitar los JSON de optimización; las reglas locales completan las propuestas y preguntas.
11. Se recompiló el ejecutable Windows con estos cambios. Abrir `dist\CV Analyzer Pro.exe`; los datos se guardan en `%LOCALAPPDATA%\CV Analyzer Pro`.

### Pasos de uso

1. Abre `dist\CV Analyzer Pro.exe`.
2. En **Match rápido**, pulsa **Subir CV** y elige un PDF o DOCX.
3. Pega la descripción del puesto y, si quieres, completa el cargo y la empresa.
4. Pulsa **Analizar match y sugerir cambios**.
5. Revisa el match y la evaluación; abre **Qué cambiar** para ver propuestas y preguntas de seguimiento.

La prueba se hizo con texto sintético, no con un CV personal. Los PDF escaneados pueden necesitar Tesseract para OCR; un PDF con texto seleccionable o un DOCX evita ese requisito. El análisis sigue funcionando con reglas si Ollama no está disponible.
