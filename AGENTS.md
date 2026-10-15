# AGENTS.md

Contexto completo y actualizado para agentes que trabajen en este repositorio. El usuario habla español: responde siempre en español y de forma concisa.

## 1. Proyecto y Visión General

Modelo Vision-Language (VLM con salida en **texto libre**, no clasificación ni predicción de victoria/derrota) que recibe 4 frames de una partida de Clash Royale (−6 s, −4 s, −2 s y actual) y genera en lenguaje natural qué carta jugar y en qué zona de la arena.
Ejemplo de salida esperada: `"Juega Valquiria detrás del puente izquierdo"`.
Detalles en `docs/project-idea.md`.

**Etapa actual:** Únicamente **construcción del dataset**. No se entrena ningún modelo todavía.

---

## 2. Dataset y Decisiones Clave

- **Fuente de datos:** Videos de YouTube con **solo partida** (sin youtubers, cortes ni cofres), preferentemente verticales con la pantalla del juego completa. Recolectados manualmente por un equipo de 5 personas.
- **Objetivo:** ≈ 240 partidas, ≈ 10K jugadas, muestreo base a 1 fps.
- **Frame actual:** El último frame justo **antes** de colocar la carta (≈ $t_{\text{jugada}} - 0.5\text{ a }1\text{ s}$), para evitar filtración de la acción.
- **Acciones:** `jugar(carta, zona)` y `esperar` (ejemplos donde la decisión óptima es no tirar cartas).
- **Zonas y Cuadrícula:** Coordenadas preliminares en `posiciones.txt` (6 zonas propias). La arena se mapeará a una cuadrícula fija (≈ 18×32) y luego a texto con plantillas variadas. La cuadrícula NO es la salida del modelo, solo metadato interno del dataset.
- **Heterogeneidad:** Videos de diferentes dispositivos (iPhone, Android, iPad). Se normalizan a un lienzo canónico a partir de la calibración.

---

## 3. Infraestructura Actual en Producción

### A. Herramienta de Anotación y Calibración (`annotator/`)

- Desplegada en **Cloudflare Pages**: `https://cr-dataset.eddux.dev` (también `https://cr-annotator.pages.dev`).
- Base de datos **Cloudflare D1** (`cr-annotator` en producción): **NO BORRAR NI RESETEAR LA BASE EN REMOTO**, el equipo del usuario ya está cargando y aprobando videos en vivo.
- Autenticación administrativa: Header `x-admin-token` con `ADMIN_TOKEN` para endpoints privados.
- Endpoints clave:
  - `POST /api/add`: Agrega URLs de YouTube a la cola (limpia automáticamente parámetros como `&t=`, consulta duración con YouTube API v3 si existe `YOUTUBE_API_KEY`).
  - `POST /api/next`: Reclamo atómico del siguiente video para que los 5 anotadores no se pisen.
  - `POST /api/submit`: Guarda calibración (`game_full=1` si es solo pantalla, o `game_box` si tiene bordes) o rechaza video.
  - `GET /api/export`: Devuelve todos los videos aprobados (`status = 'done'`) con su calibración y duración (`duration_s`).
  - `GET /api/videos`: Listado y estadísticas de videos agregados y duración acumulada.
  - `PUT /api/cookies` y `GET /api/cookies`: Sincronización de cookies filtradas de YouTube.

### B. Almacenamiento y CDN de Videos (Cloudflare R2)

- Bucket R2: `cr-videos` en Cloudflare.
- **Subdominio público CDN:** `https://cdn-cr.eddux.dev`.
- Ruta pública de cada video: `https://cdn-cr.eddux.dev/videos/<video_id>.mp4`.
- En Kaggle / notebooks los videos `.mp4` se descargan directamente mediante HTTP desde este CDN, sin saturar YouTube.

### C. Sincronización Local a R2 (`scripts/sync_to_r2.py`)

- Los videos de YouTube se descargan en la máquina local del usuario (usando conexión residencial limpia) y se suben a R2.
- Entorno local gestionado con **`uv`** (CPython 3.14). Dependencias en `pyproject.toml` (`boto3`, `requests`, `yt-dlp`).
- Configuración en archivo local `.env`:
  ```ini
  R2_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
  R2_ACCESS_KEY=...
  R2_SECRET_KEY=...
  R2_BUCKET=cr-videos
  ADMIN_TOKEN=...
  CDN_URL=https://cdn-cr.eddux.dev
  ANNOTATOR_URL=https://cr-dataset.eddux.dev
  ```
- Comando de ejecución:
  ```bash
  uv run scripts/sync_to_r2.py
  ```
  El script consulta `/api/export`, muestra la duración de cada video, descarga a máxima calidad los videos que falten en R2 (forzando códec H.264 / AVC1), los sube y elimina el archivo temporal local.

### D. Segmentación en Notebook (`notebooks/01-segmentation.ipynb`)

- Se ejecuta en un kernel de **Kaggle** conectado por Jupyter Server a VS Code.
- Descarga los `.mp4` desde el CDN (`https://cdn-cr.eddux.dev/videos/<video_id>.mp4`).
- Para la persistencia y lectura de metadatos, se conecta directamente a Cloudflare R2 vía la **API S3** (`boto3`), evitando inconsistencias por caché del CDN:
  - Lee los videos ya procesados: `s3.list_objects_v2(Prefix='metadata/segments/')`.
  - Checkpointing atómico por video: `metadata/segments/<video_id>.json`.
  - Manifiesto global consolidado: `metadata/segmented_matches.json`.
- **Nota técnica:** No se pueden editar archivos `.ipynb` directamente con `replace_file_content`; usar scripts Python/json o reescribir con `write_to_file`.

### E. Calibración Espacial de UI (`notebooks/02-ui-bounding-box.ipynb`)

- Desacopla la calibración espacial de la extracción de jugadas (Principio de Responsabilidad Única).
- Aprovecha los segmentos del Notebook 01 tomando un segundo seguro de gameplay confirmado ($t_{\text{start}} + 8\text{ s}$).
- Algoritmo de calibración multi-dispositivo afinado y blindado (16:9 estándar, notch / Dynamic Island en iPhone, Android alto 20:9 y videos con bandas negras laterales):
  - **Detección de pillarbox:** Detecta bandas negras laterales y recorta al lienzo de juego activo (`gw`, `gx_min`).
  - **Anclaje infalible por pico de densidad magenta:** En lugar de umbrales estáticos que fallaban cuando el jugador tenía poco elixir (1 o 2), detecta el pico de magenta en el 15% inferior de la pantalla. Inmune al nivel de elixir y a los círculos de coste de las cartas.
  - **Caja de elixir completa:** Abarca el número blanco superior (0–10), la gota de elixir y el texto `"Máx.: 10"`.
  - **Anclaje canónico de cartas en mano:** Los 4 slots se posicionan estrictamente a partir de la barra de elixir con dimensiones proporcionales fijas ($0.180 W \times 0.240 W$). Incluyen holgura superior para elevación de carta cuando el jugador la selecciona con el borde blanco brillante, y base para el círculo de coste.
  - **Cuadrícula jugable de la arena:** Delimitada desde justo debajo del HUD superior (cubriendo por completo las torres de princesas enemigas) hasta justo detrás de la base del rey propio (donde terminan los cuadrados de piedra), descartando la zona muerta decorativa de arbustos y tejados inferiores.
  - **Oclusión de emotes:** Se descartó el recuadro naranja flotante. Cuando se abre el menú de chat, el panel azul con frases ("¡Buena suerte!", etc.) cubre el 100% de la mano y bloquea las jugadas; la oclusión se detectará directamente sobre los 4 slots de cartas en el Notebook 03.
  - **Persistencia atómica:** Checkpointing en R2 vía API S3: `metadata/layouts/<video_id>.json` y consolidado `metadata/ui_layouts.json`.
  - **Galería visual:** Grilla de verificación con cajas de colores (cian = arena, verde = 4 cartas, magenta = elixir, amarillo = siguiente, azul = emote) ejecutada y validada en Kaggle.

---

## 4. Estado Actual y Siguiente Tarea Pendiente

- **Infraestructura de datos y sync a R2:** 100% completada y funcionando.
- **Paso 3 del plan (Segmentación de partidas):** **100% COMPLETADO Y VALIDADO** en `notebooks/01-segmentation.ipynb`.
- **Paso 4A (Calibración Espacial de UI):** **100% COMPLETADO Y VALIDADO** en `notebooks/02-ui-bounding-box.ipynb` con los metadatos consolidados en R2 (`metadata/ui_layouts.json`).
- **Siguiente paso prioritario:** **Paso 4B: Extracción de jugadas y construcción del dataset de pares (`notebooks/03-action-extraction.ipynb`)**.
  - Consume los segmentos de `metadata/segmented_matches.json` y los bounding boxes espaciales de `metadata/ui_layouts.json`.
  - Monitorear el gameplay en las ROIs calibradas: caída neta de elixir ($\Delta E \le -1.5$), consumo y rotación del slot de carta en mano, y elevación previa de la carta (borde blanco).
  - Identificación de carta jugada mediante banco de plantillas (incluyendo versiones evolucionadas).
  - Detección de despliegue en la arena (cluster de cambio en $[t_{\text{drop}} - 0.2\text{s}, t_{\text{drop}} + 0.4\text{s}]$) y mapeo a lenguaje natural según `posiciones.txt`.
  - Descarte de muestras con oclusión de emotes en mano (panel de texto cubriendo las cartas) y generación de ejemplos de "esperar".

---

## 5. Convenciones para Agentes

- Mantener docstrings y comentarios existentes no relacionados con los cambios.
- Rutas absolutas en los enlaces (`file:///...`).
- Respuestas en español, directas y al grano.
