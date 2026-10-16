# Clash Royale Vision-Language Dataset & Model

Pipeline de visión por computadora y aprendizaje profundo para construir un modelo **Vision-Language (VLM)** capaz de asistir a jugadores de Clash Royale en tiempo real.

A diferencia de modelos clasificadores o predictores de victoria/derrota, el modelo recibe **4 fotogramas consecutivos** (−6 s, −4 s, −2 s y actual) y genera una recomendación táctica en **lenguaje natural**:

> _"Juega Valquiria detrás del puente izquierdo."_

---

## 🎯 Objetivo del Dataset

- **Volumen:** ≈ 240 partidas completas (≈ 12 horas de juego), ≈ 10K decisiones/jugadas.
- **Entrada:** 4 frames espaciados en el tiempo ($t-6\text{s}, t-4\text{s}, t-2\text{s}, t_{\text{decision}}$) que capturan la trayectoria de tropas, estado de torres, cartas en mano y barra de elixir.
- **Frame actual ($t_{\text{decision}}$):** Instante inmediatamente anterior a colocar la carta ($t_{\text{drop}} - 0.8\text{ s}$) para evitar filtración de la acción (_data leakage_).
- **Acciones:** `jugar(carta, zona)` y `esperar` (decisión de no tirar cartas para acumular elixir o reaccionar).
- **Zonas:** La arena se mapea a las 6 zonas estratégicas de [`posiciones.txt`](file:///home/eddu/dev/reinforcement-learning-clash-royale/posiciones.txt) (+ zonas ofensivas globales) y a una cuadrícula canónica (`18×32`).

---

## 🏗 Arquitectura del Pipeline

El proyecto está organizado en etapas secuenciales modulares con persistencia y ejecución distribuida en Cloudflare R2:

```
[Videos YouTube]
       │
       ▼
 1. Anotador & Calibración (Cloudflare Pages + D1)
    └─ Valida videos y calibra pantalla (`cr-dataset.eddux.dev`)
       │
       ▼
 2. Ingesta a Cloudflare R2 (scripts/sync_to_r2.py & scripts/sync_cards_to_r2.py)
    ├─ Videos en H.264 (AVC1) servidos vía CDN (`cdn-cr.eddux.dev`)
    └─ Catálogo oficial de 160 cartas de mazo estándar (`00-cards.ipynb`) [COMPLETADO]
       │
       ▼
 3. Segmentación de Partidas (notebooks/01-segmentation.ipynb) [COMPLETADO]
    ├─ Fase 1: Anclaje universal del temporizador (agnóstico a resolución y notch)
    ├─ Fase 2: Escaneo a 1 fps con lookahead anti-glitch, unión con Overtime y fin por meseta
    └─ Persistencia: `metadata/segments/<video_id>.json` y `segmented_matches.json` en R2
       │
       ▼
 4. Calibración Espacial de UI (notebooks/02-ui-bounding-box.ipynb) [COMPLETADO]
    ├─ Anclaje infalible por pico de elixir, 4 slots de cartas (con elevación) y arena jugable
    ├─ Blindaje para 16:9, notch / Dynamic Island, Android alto y bandas laterales
    └─ Persistencia: `metadata/layouts/<video_id>.json` y `ui_layouts.json` en R2
       │
       ▼
 5. Detección Temporal e Identificación de Cartas (notebooks/03-action-extraction.ipynb) [COMPLETADO]
    ├─ Escaneo a 5 FPS con compensación de regeneración (1x/2x/3x) según `start_clock`
    ├─ Rotación de slot invariante a elevación + inferencia en 2 pasadas del mazo de 8 cartas
    └─ Persistencia: `metadata/events/<video_id>.json` y `extracted_events.json` en R2
       │
       ▼
 6. Localización en Arena y Dataset VLM (notebooks/04-arena-and-dataset.ipynb) [EN CURSO]
    ├─ Detección espacial por etiqueta flotante de la carta (principal) + aparición neta (fallback)
    ├─ Mapeo a las 6 zonas de `posiciones.txt` + muestreo de `"esperar"`
    └─ Persistencia: `metadata/placements/<video_id>.json` y `arena_placements.json` en R2
```

---

## 📂 Estructura del Repositorio

```text
├── annotator/                        # Herramienta web en Cloudflare Pages + D1
│   ├── functions/api/                # Endpoints D1 (/api/next, /api/submit, /api/export)
│   └── public/                       # Frontend de anotación y marcado de cajas
├── docs/                             # Especificaciones técnicas
│   ├── project-idea.md               # Visión general y definición del problema
│   ├── segmentation-spec.md          # Especificación del anclaje de reloj y máquina de estados (01)
│   ├── ui-bounding-box-spec.md       # Especificación de calibración espacial y bounding boxes (02)
│   ├── action-extraction-spec.md     # Especificación de detección temporal e identificación de cartas (00 y 03)
│   └── arena-and-dataset-spec.md     # Especificación de localización en arena y ensamble del dataset (04)
├── notebooks/                        # Procesamiento modular en Kaggle / Jupyter
│   ├── 00-cards.ipynb                # Verificación visual del catálogo de 160 cartas jugables en R2
│   ├── 01-segmentation.ipynb         # Segmentación de inicio/fin de partidas y reloj
│   ├── 02-ui-bounding-box.ipynb      # Calibración espacial de UI (arena, elixir y 4 slots)
│   ├── 03-action-extraction.ipynb    # Detección temporal (t_drop) e identificación de carta jugada
│   └── 04-arena-and-dataset.ipynb    # Detección de coordenada/zona en arena, "esperar" y manifiesto VLM
├── scripts/                          # Herramientas de sincronización local
│   ├── sync_to_r2.py                 # Descarga de YouTube en H.264 y subida directa a R2
│   └── sync_cards_to_r2.py           # Sincronización de iconos PNG y catálogo oficial de cartas a R2
├── posiciones.txt                    # Definición de las 6 zonas estratégicas del campo propio
├── AGENTS.md                         # Contexto integral y reglas de desarrollo para agentes IA
└── pyproject.toml                    # Gestión de entorno local con uv (Python 3.14)
```

---

## 🚀 Puesta en Marcha Rápida

### 1. Entorno Local (`uv`)

```bash
# Instalar dependencias locales
uv sync

# Sincronizar videos aprobados desde YouTube a Cloudflare R2
uv run scripts/sync_to_r2.py

# Sincronizar catálogo e iconos de cartas a Cloudflare R2
uv run scripts/sync_cards_to_r2.py
```

### 2. Ejecución Distribuida en Kaggle (`01` a `04`)

Configurar los secretos del entorno (Kaggle Secrets o `.env`):

- `R2_ENDPOINT`: Endpoint S3 de Cloudflare R2.
- `R2_ACCESS_KEY` & `R2_SECRET_KEY`: Credenciales de lectura/escritura en R2.
- `R2_BUCKET`: `cr-videos`.
- `ADMIN_TOKEN`: Token para consultar `/api/export` del annotator.
- `CDN_URL`: `https://cdn-cr.eddux.dev`.

En los Notebooks `03` y `04`, varios integrantes del equipo pueden procesar en paralelo asignándose distintas listas en `VIDEO_FILTER = ['id1', 'id2', ...]`. Cada ejecución guarda checkpoints individuales en R2 y consolida el manifiesto global sumando todos los videos existentes en el bucket sin sobrescribir el trabajo de los demás.
