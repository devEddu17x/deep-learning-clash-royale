# Clash Royale Vision-Language Dataset & Model

Pipeline de visión por computadora y aprendizaje profundo para construir un modelo **Vision-Language (VLM)** capaz de asistir a jugadores de Clash Royale en tiempo real. 

A diferencia de modelos clasificadores o predictores de victoria/derrota, el modelo recibe **4 fotogramas consecutivos** (−6 s, −4 s, −2 s y actual) y genera una recomendación táctica en **lenguaje natural**:
> *"Juega Valquiria detrás del puente izquierdo"*

---

## 🎯 Objetivo del Dataset

- **Volumen:** ≈ 240 partidas completas (≈ 12 horas de juego), ≈ 10K decisiones/jugadas.
- **Entrada:** 4 frames espaciados en el tiempo que capturan la trayectoria de tropas, estado de torres, cartas en mano y barra de elixir.
- **Frame actual:** Instante inmediatamente anterior a colocar la carta ($t_{\text{jugada}} - 0.5\text{ a }1\text{ s}$) para evitar filtración de la acción.
- **Acciones:** `jugar(carta, zona)` y `esperar` (decisión de no tirar cartas para acumular elixir o reaccionar).
- **Zonas:** La arena se mapea a una cuadrícula canónica (≈ 18×32) y se traduce a texto variado.

---

## 🏗 Arquitectura del Pipeline

El proyecto está organizado en etapas secuenciales modulares:

```
[Videos YouTube]
       │
       ▼
 1. Anotador & Calibración (Cloudflare Pages + D1)
    └─ Valida videos y calibra pantalla (`cr-dataset.eddux.dev`)
       │
       ▼
 2. Ingesta a Cloudflare R2 (scripts/sync_to_r2.py)
    └─ Descarga en H.264 (AVC1), almacena en R2 y sirve vía CDN (`cdn-cr.eddux.dev`)
       │
       ▼
 3. Segmentación de Partidas (notebooks/01-segmentation.ipynb) [COMPLETADO]
    ├─ Fase 1: Anclaje universal del temporizador (agnóstico a resolución y notch)
    ├─ Fase 2: Escaneo a 1 fps con lookahead anti-glitch, unión con Overtime y fin por meseta
    └─ Resiliencia: Checkpointing atómico en R2 (S3 API) y limpieza de .mp4 por video
       │
       ▼
 4. Calibración Espacial de UI (notebooks/02-ui-calibration.ipynb) [COMPLETADO]
    ├─ Anclaje de arena, dock, 4 slots de cartas (con elevación), elixir y emotes
    ├─ Blindaje para 16:9, notch / Dynamic Island, Android alto y tablets
    └─ Persistencia: metadata/layouts/<video_id>.json y ui_layouts.json en R2
       │
       ▼
 5. Extracción de Jugadas y Pares (notebooks/03-action-extraction.ipynb) [SIGUIENTE PASO]
    └─ Detección de $t_{\text{jugada}}$, extracción de 4 frames y etiquetado a texto
```

---

## 📂 Estructura del Repositorio

```text
├── annotator/                     # Herramienta web en Cloudflare Pages + D1
│   ├── functions/api/             # Endpoints D1 (/api/next, /api/submit, /api/export)
│   └── public/                    # Frontend de anotación y marcado de cajas
├── docs/                          # Documentación técnica
│   ├── project-idea.md            # Visión general y definición del problema
│   └── segmentation-spec.md       # Especificación del anclaje de reloj y máquina de estados
├── notebooks/                     # Procesamiento en Kaggle / Jupyter
│   ├── 01-segmentation.ipynb      # Pipeline de segmentación con persistencia atómica en R2
│   └── 02-ui-calibration.ipynb    # Calibración espacial de UI (slots, elixir, arena, emotes)
├── scripts/                       # Herramientas de automatización local
│   └── sync_to_r2.py              # Descarga de YouTube en H.264 y subida directa a R2
├── AGENTS.md                      # Contexto integral y reglas de desarrollo para agentes IA
└── pyproject.toml                 # Gestión de entorno local con uv (Python 3.14)
```

---

## 🚀 Puesta en Marcha Rápida

### 1. Entorno Local (`uv`)
```bash
# Instalar dependencias locales
uv sync

# Sincronizar videos aprobados desde YouTube a Cloudflare R2
uv run scripts/sync_to_r2.py
```

### 2. Segmentación en Kaggle (`01-segmentation.ipynb`)
Configurar los secretos del entorno (Kaggle Secrets o `.env`):
- `R2_ENDPOINT`: Endpoint S3 de Cloudflare R2.
- `R2_ACCESS_KEY` & `R2_SECRET_KEY`: Credenciales de lectura/escritura en R2.
- `R2_BUCKET`: `cr-videos`.
- `ADMIN_TOKEN`: Token para consultar `/api/export` del annotator.
- `CDN_URL`: `https://cdn-cr.eddux.dev`.

Al ejecutarse, el notebook procesa video por video de forma incremental, respalda cada segmentación en `metadata/segments/<video_id>.json`, compila `metadata/segmented_matches.json` y libera espacio en disco automáticamente.

