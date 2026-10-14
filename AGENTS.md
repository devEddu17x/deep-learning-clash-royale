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
- En Kaggle / notebooks se descarga directamente mediante HTTP desde este CDN, **sin necesitar credenciales de S3 ni interactuar con YouTube**.

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
  El script consulta `/api/export`, muestra la duración de cada video, descarga a máxima calidad los videos que falten en R2, los sube y elimina el archivo temporal local.

### D. Procesamiento en Notebook (`notebooks/01-generate-dataset.ipynb`)

- Se ejecuta en un kernel de **Kaggle** conectado por Jupyter Server a VS Code.
- No descarga de YouTube (para evitar los bloqueos `Sign in to confirm you're not a bot` de las IPs de Google/Kaggle).
- Descarga directo desde el CDN: `https://cdn-cr.eddux.dev/videos/<video_id>.mp4`.
- **Nota técnica:** No se pueden editar archivos `.ipynb` directamente con `replace_file_content`; usar scripts Python/json o reescribir con `write_to_file`.

---

## 4. Estado Actual y Siguiente Tarea Pendiente

- **Infraestructura de datos y sync a R2:** 100% completada y funcionando. Códec de descarga fijado a H.264/AVC1 en `scripts/sync_to_r2.py`.
- **Paso 3 del plan (Segmentación de partidas por reloj en notebook):** **100% COMPLETADO Y VALIDADO**.
  - Implementado en `notebooks/01-generate-dataset.ipynb` mediante un pipeline modular y resiliente:
    - **Fase 1:** Anclaje inmutable universal de la caja en el cuadrante superior derecho amplio (independiente de aspect ratio y notch).
    - **Fase 2:** Máquina de estados a 1 fps con anti-glitch por *lookahead*, unión con Overtime, separación en cortes rápidos de edición, fin exacto por meseta congelada de torre y salida en `MM:SS` con enlaces a YouTube.
    - **Persistencia y Resiliencia en R2:** Pipeline incremental video por video. Guarda cada segmentación de forma atómica directo en Cloudflare R2 vía API S3 (`metadata/segments/<video_id>.json`), salta videos ya procesados (idempotencia) y limpia los `.mp4` locales para procesar 12h+ en Kaggle sin saturar disco. Compila el manifiesto consolidado `metadata/segmented_matches.json`.
  - Reglas visuales y detalles técnicos documentados a fondo en `docs/segmentation-spec.md`.
- **Siguiente paso prioritario:** **Paso 4 del plan: Extracción de jugadas y construcción del dataset de pares (4 frames -> acción)**.
  - Diseñar el detector de jugada: identificar en qué instante $t$ se suelta una carta a la arena (reducción de cartas en mano, caída del contador de elixir o aparición del sprite de la tropa).
  - Tomar el frame actual justo antes de colocar la carta ($t_{\text{jugada}} - 0.5\text{ a }1\text{ s}$) y los 3 frames previos ($-6\text{s}, -4\text{s}, -2\text{s}$).
  - Detectar qué carta se jugó y en qué cuadrícula de la arena se soltó (mapeo a lenguaje natural).
  - Detector de oclusión de emotes: descartar instantes donde el panel de mensajes tapa las cartas en mano.

---

## 5. Convenciones para Agentes

- Mantener docstrings y comentarios existentes no relacionados con los cambios.
- Rutas absolutas en los enlaces (`file:///...`).
- Respuestas en español, directas y al grano.
