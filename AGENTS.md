# AGENTS.md

Contexto completo y actualizado para agentes que trabajen en este repositorio. El usuario habla español: responde siempre en español y de forma concisa.

## 1. Proyecto y Visión General

Modelo Vision-Language (VLM con salida en **texto libre**, no clasificación ni predicción de victoria/derrota) que recibe 4 frames de una partida de Clash Royale (−6 s, −4 s, −2 s y actual) y genera en lenguaje natural qué carta jugar y en qué zona de la arena.
Ejemplo de salida esperada: `"Juega Valquiria detrás del puente izquierdo."` o `"esperar"`.
Detalles en [`docs/project-idea.md`](file:///home/eddu/dev/reinforcement-learning-clash-royale/docs/project-idea.md).

**Etapa actual:** Únicamente **construcción del dataset** (pipeline modular de 5 notebooks). No se entrena ningún modelo todavía.
**Regla explícita:** Ignorar por completo la carpeta `/to-verify`.

---

## 2. Dataset, Reglas Físicas y Decisiones Clave

- **Fuente de datos:** Videos de YouTube con **solo partida** (sin youtubers, cortes ni cofres), verticales con la pantalla del juego completa. Recolectados manualmente por un equipo de 5 personas (52 videos / ~73 partidas ya segmentadas en R2).
- **Frame actual ($t_{\text{decision}}$):** El frame justo **antes** de colocar la carta ($t_{\text{drop}} - 0.8\text{ s}$), evitando filtración de la acción (*data leakage*). Los 4 frames de cada muestra son $[t_{\text{decision}} - 6\text{s}, t_{\text{decision}} - 4\text{s}, t_{\text{decision}} - 2\text{s}, t_{\text{decision}}]$.
- **Descarte definitivo de `next_card_box` y `emote_button_box`:** En el lote de 52 videos se comprobó que `next_card_box` y `emote_button_box` solo quedan bien centradas en ~20% de las resoluciones. Por tanto, **los Notebooks 03 y 04 NUNCA usan `next_card_box` ni `emote_button_box`**: operan exclusivamente con `arena_box`, `elixir_bar_box` y los 4 `card_slots` (que tienen 100% de precisión).
- **Velocidades oficiales de elixir y `start_clock`:**
  - Las partidas en `segmented_matches.json` no inician en `3:00` exactos sino en `start_clock` (`2:57`, `2:56`, `2:55`). Se compensa con `clock_offset_sec = 180 - parse_clock(start_clock)`.
  - Tasas de regeneración: **1x** ($0.357\text{ elixir/s}$, primeros 2 min), **2x** ($0.714\text{ elixir/s}$, último min regular + 1er min Overtime), **3x** ($1.429\text{ elixir/s}$, último min Overtime).
- **Trabajo distribuido en equipo:** Los Notebooks 03 y 04 soportan que varios compañeros procesen listas distintas de `video_id` en `VIDEO_FILTER` en paralelo. Cada video guarda su JSON individual en R2 y la función de consolidación une **todos** los JSON existentes en el bucket sin pisar el trabajo de los demás. Además, las celdas de visualización y video H.264 de debug están acotadas a `selected_videos` y leen directamente de R2 sin reprocesar.

---

## 3. Infraestructura y Notebooks en Producción

### A. Herramienta de Anotación (`annotator/`) y Sincronización (`scripts/sync_to_r2.py`)
- Desplegada en Cloudflare Pages (`https://cr-dataset.eddux.dev`) con base D1 (`cr-annotator`): **NO BORRAR NI RESETEAR LA BASE EN REMOTO**.
- Bucket Cloudflare R2: `cr-videos` servido por CDN en `https://cdn-cr.eddux.dev/videos/<video_id>.mp4`.
- `uv run scripts/sync_to_r2.py` descarga de YouTube en H.264 (`avc1`) y sube a R2.

### B. Catálogo Oficial de Cartas (`scripts/sync_cards_to_r2.py` + `notebooks/00-cards.ipynb`) — [100% COMPLETADO]
- Sincroniza 204 iconos PNG (`150×180` RGBA) en `s3://cr-videos/assets/cards/<key>.png` y el manifiesto `s3://cr-videos/metadata/cards_catalog.json`.
- Filtra las 44 cartas especiales/eventos (`is_standard_deck_card: false`), dejando exactamente las **160 cartas de mazo estándar** (121 cartas base + 39 evoluciones `-ev1`) con sus nombres en español, coste de elixir y tipo (`Troop`, `Building`, `Spell`).

### C. Segmentación de Partidas (`notebooks/01-segmentation.ipynb`) — [100% COMPLETADO]
- Especificación en [`docs/segmentation-spec.md`](file:///home/eddu/dev/reinforcement-learning-clash-royale/docs/segmentation-spec.md).
- Checkpoints en `s3://cr-videos/metadata/segments/<video_id>.json` y consolidado en `s3://cr-videos/metadata/segmented_matches.json`.

### D. Calibración Espacial de UI (`notebooks/02-ui-bounding-box.ipynb`) — [100% COMPLETADO]
- Especificación en [`docs/ui-bounding-box-spec.md`](file:///home/eddu/dev/reinforcement-learning-clash-royale/docs/ui-bounding-box-spec.md).
- Checkpoints en `s3://cr-videos/metadata/layouts/<video_id>.json` y consolidado en `s3://cr-videos/metadata/ui_layouts.json`.

### E. Detección Temporal e Identificación de Cartas (`notebooks/03-action-extraction.ipynb`) — [100% COMPLETADO Y VALIDADO EN VIDEO]
- Especificación en [`docs/action-extraction-spec.md`](file:///home/eddu/dev/reinforcement-learning-clash-royale/docs/action-extraction-spec.md).
- Escaneo secuencial a **5 FPS (`dt = 0.20s`)** midiendo caída de elixir compensada por regeneración (`1x/2x/3x`) + rotación de slot invariante a elevación vertical (`compute_slot_rotation_score`) + filtro de oclusión de menú de chat azul.
- Identificación de carta en 2 pasadas con **restricción física estricta de elixir** (`card.elixir <= elixir_before + 0.85`) e **inferencia del mazo de 8 cartas** de la partida.
- Checkpoints en `s3://cr-videos/metadata/events/<video_id>.json` y consolidado en `s3://cr-videos/metadata/extracted_events.json`.
- Incluye gráfica limpia de elixir (Celda 6) y generador de video H.264 con HUD de verificación (Celda 7) leyendo desde R2.

### F. Localización en Arena y Ensamble del Dataset (`notebooks/04-arena-and-dataset.ipynb`) — [EN AJUSTE FINO DE DETECCIÓN ESPACIAL]
- Especificación en [`docs/arena-and-dataset-spec.md`](file:///home/eddu/dev/reinforcement-learning-clash-royale/docs/arena-and-dataset-spec.md).
- Consume `extracted_events.json` y detecta dónde cayó cada carta en `arena_box` (`x_norm, y_norm`, cuadrícula `18×32` y zona textual según [`posiciones.txt`](file:///home/eddu/dev/reinforcement-learning-clash-royale/posiciones.txt)).
- **Hallazgos críticos del dominio visual en la arena (implementados/en refinamiento):**
  1. **Texto flotante de despliegue (Blanco o Dorado Estelar) + Reloj blanco:** Al soltar una carta en la arena no aparece inmediatamente la bolita azul de nivel, sino el **nombre de la carta** (en blanco o en **dorado brillante** si tiene nivel estelar/Pass Royale) junto al reloj circular de despliegue.
  2. **Cartas subterráneas/viajeras (`goblin-drill`, `miner`, `goblin-barrel`):** Hacen su recorrido subterráneo o aéreo desde el centro/puente hacia la torre rival. Si se mide la diferencia de píxeles muy temprano ($0.1\text{s}-0.5\text{s}$), se detecta erróneamente la estela en el medio entre los dos puentes en vez de la emergencia tardía en la torre rival ($+0.65\text{s}\text{ a }+1.30\text{s}$).
  3. **Estructuras defensivas (`Building` como `inferno-tower`, `cannon`, `tesla`):** Se colocan en el centro del campo propio (Zona 5) a menudo mientras hay tropas peleando en los puentes. Se distinguen del combate en el puente por su **persistencia estática** (aparecen respecto a $t_{\text{pre}}$ y permanecen inmóviles entre $t+0.4\text{s}$ y $t+0.9\text{s}$) dentro del rectángulo central válido de construcción.
- Checkpoints en `s3://cr-videos/metadata/placements/<video_id>.json` y consolidado en `s3://cr-videos/metadata/arena_placements.json`. Detector actual: etiqueta flotante del nombre de la carta (principal) + aparición neta (fallback). **Estado y pendientes en [`docs/HANDOFF-nb04.md`](file:///home/eddu/dev/reinforcement-learning-clash-royale/docs/HANDOFF-nb04.md).**

---

## 4. Convenciones para Agentes

- **Nota técnica sobre `.ipynb`:** No se pueden editar archivos `.ipynb` directamente con `replace_file_content`; usar scripts Python con `json` o reescribir con `write_to_file`, verificando siempre con `compile()` todas las celdas de código.
- Mantener docstrings y comentarios existentes no relacionados con los cambios.
- Rutas absolutas en los enlaces (`file:///...`).
- Respuestas en español, directas y al grano.
