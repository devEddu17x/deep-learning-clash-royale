# Especificación de Extracción Temporal de Jugadas e Identificación de Cartas (Paso 4B — Parte 1)

Este documento detalla la arquitectura técnica, las invariantes físicas de Clash Royale, los supuestos antiguos descartados y la implementación validada para:
1. **Catálogo Oficial de Cartas en R2:** [`scripts/sync_cards_to_r2.py`](file:///home/eddu/dev/reinforcement-learning-clash-royale/scripts/sync_cards_to_r2.py) y [`notebooks/00-cards.ipynb`](file:///home/eddu/dev/reinforcement-learning-clash-royale/notebooks/00-cards.ipynb).
2. **Detección Temporal ($t_{\text{drop}}$) e Identificación de Carta Jugada:** [`notebooks/03-action-extraction.ipynb`](file:///home/eddu/dev/reinforcement-learning-clash-royale/notebooks/03-action-extraction.ipynb).

> [!NOTE]
> **Desacoplamiento Modular (Principio de Responsabilidad Única):**
> Originalmente se pensó hacer la detección de cartas y la localización en la arena dentro de un único notebook. En la arquitectura actual se separaron en:
> - **Notebook 03 ([`03-action-extraction.ipynb`](file:///home/eddu/dev/reinforcement-learning-clash-royale/notebooks/03-action-extraction.ipynb)):** Responde únicamente **¿CUÁNDO se jugó?**, **¿QUÉ SLOT rotó?** y **¿QUÉ CARTA fue?**.
> - **Notebook 04 ([`04-arena-and-dataset.ipynb`](file:///home/eddu/dev/reinforcement-learning-clash-royale/notebooks/04-arena-and-dataset.ipynb)):** Responde **¿DÓNDE cayó en la arena?**, muestrea los ejemplos de `"esperar"` y ensambla el manifiesto final del VLM (ver [`docs/arena-and-dataset-spec.md`](file:///home/eddu/dev/reinforcement-learning-clash-royale/docs/arena-and-dataset-spec.md)).

---

## 1. Supuestos Antiguos Descartados

1. **Uso de `next_card_box` y `emote_button_box` (DESCARTADO):**
   - *Supuesto antiguo:* Confirmar una jugada verificando que el icono de `next_card_box` pasa al slot jugado, o vigilar `emote_button_box`.
   - *Realidad en producción:* Esas dos cajas solo están bien ubicadas en ~20% de los videos debido a cambios no lineales en la UI según el dispositivo.
   - *Solución implementada:* Todo el pipeline del Notebook 03 utiliza **exclusivamente `elixir_bar_box` y los 4 `card_slots`**.

2. **Inicio de partida fijo en `3:00` y muestreo a 1 FPS (DESCARTADO):**
   - *Supuesto antiguo:* Asumir que el segundo `start_sec` de la segmentación equivale siempre a `3:00` del reloj y muestrear a 1 FPS.
   - *Realidad en producción:* Las partidas en `segmented_matches.json` inician cuando desaparece el cartel de presentación, con el reloj ya en `2:57`, `2:56` o `2:55` (`start_clock`). Además, en doble/triple elixir el jugador gasta y regenera elixir tan rápido que a 1 FPS una carta de coste 1 o 2 queda enmascarada por la regeneración natural.
   - *Solución implementada:* Se calcula `clock_offset_sec = 180 - parse_clock(start_clock)` y se escanea secuencialmente a **5 FPS (`dt = 0.20s`)**, compensando la regeneración exacta según la fase del reloj.

3. **Comparación simple de píxeles en el slot (DESCARTADO):**
   - *Supuesto antiguo:* Medir $|I_{\text{post}} - I_{\text{pre}}|$ directamente sobre el slot de la carta.
   - *Realidad en producción:* Los jugadores tocan y alternan cartas en mano constantemente sin soltarlas. Al seleccionar una carta, esta se **eleva verticalmente** dentro de su caja y brilla con un borde blanco, disparando una diferencia de píxeles altísima sin que haya jugada.
   - *Solución implementada:* Métrica de **Rotación de Slot Invariante a Elevación** (`compute_slot_rotation_score`), que desliza verticalmente el parche central de la carta en $t - 0.8\text{s}$ contra $t + 1.0\text{s}$ buscando la mejor alineación. Si es la misma carta solo que elevada o seleccionada, la distancia cae a un valor bajo; solo es alta cuando entra una ilustración distinta tras el cooldown de rotación.

---

## 2. Catálogo Oficial de Cartas en R2 (`00-cards.ipynb`)

Mediante [`scripts/sync_cards_to_r2.py`](file:///home/eddu/dev/reinforcement-learning-clash-royale/scripts/sync_cards_to_r2.py) se sincronizó el banco de referencia oficial en Cloudflare R2:
- **Imágenes:** `s3://cr-videos/assets/cards/<key>.png` (`150×180` RGBA).
- **Manifiesto:** `s3://cr-videos/metadata/cards_catalog.json` con nombres en español e inglés, coste de elixir, tipo (`Troop`, `Building`, `Spell`), rareza y banderas de filtrado.
- **Filtrado del pool jugable (`deck_pool`):**
  - De las 204 cartas existentes en los datos del juego, **44 son cartas especiales/temporales** (super-tropas de eventos, modos festivos, habilidades de campeones o tropas de torres con `elixir: null` o `id >= 26000900`).
  - Se marcan con `is_standard_deck_card: false` y se excluyen del identificador, dejando exactamente las **160 cartas de mazo estándar** (121 cartas base + 39 evoluciones `-ev1`).

---

## 3. Algoritmo del Detector Temporal (`03-action-extraction.ipynb`)

### A. Velocidades Oficiales de Regeneración de Elixir y `start_clock`
Para cada instante $t$ del video dentro de una partida segmentada (`[start_sec, end_sec]`):
1. Se obtiene el tiempo real transcurrido en el reloj de la partida:
   $$\text{match\_elapsed}(t) = (t - \text{start\_sec}) + (180 - \text{clock\_to\_sec}(\text{start\_clock}))$$
2. Se aplica la tasa de regeneración $r(t)$ oficial:
   - **1x Elixir** ($0 \le \text{match\_elapsed} < 120\text{s}$, primeros 2 min): $r = \frac{1}{2.8} \approx 0.357\text{ elixir/s}$.
   - **2x Elixir** ($120 \le \text{match\_elapsed} < 240\text{s}$, último minuto regular + 1er minuto de Overtime): $r = \frac{1}{1.4} \approx 0.714\text{ elixir/s}$.
   - **3x Elixir** ($\text{match\_elapsed} \ge 240\text{s}$, último minuto de Overtime): $r = \frac{1}{0.7} \approx 1.429\text{ elixir/s}$.

### B. Medición Sub-píxel de la Barra de Elixir (`measure_elixir_fill`)
- Se aísla la sub-región de los 10 segmentos de la barra dentro de `elixir_bar_box` ($x \in [13.5\% W, 98.5\% W]$, $y \in [35\% H, 82\% H]$), ignorando la gota izquierda donde está el número `0–10`.
- Se detectan tanto los píxeles magenta normales como el destello blanco/rosado de barra llena o sobrecarga.
- Se aplica suavizado por mediana (`kernel = 3`, $0.6\text{s}$) sobre la serie a 5 FPS para eliminar parpadeos de partículas.

### C. Gasto Real Compensado y Confirmación por Slot
En cada paso $i$ ($dt = 0.20\text{s}$), se evalúa una ventana de $\Delta t = 0.80\text{s}$ (4 pasos):
$$\text{regenerated} = r(t_i) \cdot \Delta t$$
$$\text{estimated\_spend} = (E_{\text{smooth}}[t_i - 0.2\text{s}] - E_{\text{smooth}}[t_i + 0.6\text{s}]) + \text{regenerated}$$

Una jugada en $t_{\text{drop}}$ se confirma si y solo si:
1. $\text{estimated\_spend} \ge 1.15$ de elixir.
2. Ninguno de los 4 slots está cubierto por el **panel azul de menú de chat/emotes** (`is_chat_menu_occluding_slots`).
3. Al menos uno de los 4 slots presenta **rotación real** (`best_rot_score >= 0.135`) acompañada de oscurecimiento/cooldown gris post-jugada o cambio neto alto.
4. Instante seguro de decisión sin filtración (*data leakage*):
   $$t_{\text{decision}} = \max(\text{start\_sec}, t_{\text{drop}} - 0.80\text{s})$$

---

## 4. Identificación de Carta en Dos Pasadas (Restricción Física + Mazo de 8 Cartas)

Para identificar qué carta había en el slot `hand_slot` en $t_{\text{decision}} = t_{\text{drop}} - 0.80\text{s}$:

1. **Alineación multi-recorte del Slot contra el Catálogo:**
   - Como la carta en $t_{\text{decision}}$ puede estar en reposo o elevada (seleccionada por el jugador), se extraen 5 recortes verticales del interior de la ilustración del slot y se comparan contra las 160 plantillas mediante descriptor combinado **HSV 2D (Hue-Saturation) + plantilla RGB normalizada + bordes de luminancia**.
2. **Restricción Física Estricta de Elixir:**
   - Una carta de coste $C$ **jamás puede jugarse** si el jugador tenía menos de $C$ de elixir antes de soltarla.
   - Toda carta con `elixir > elixir_before + 0.85` queda **físicamente prohibida** (y se penaliza además según $|C - \text{estimated\_spend}|$).
3. **Inferencia en 2 Pasadas del Mazo de 8 Cartas (`inferred_deck_base_keys`):**
   - En una partida de Clash Royale el jugador solo tiene **8 cartas únicas** en su mazo.
   - **Pasada 1:** Se evalúan todas las jugadas de la partida y se acumula la evidencia de las cartas más confiables para descubrir las 8 `base_key` del mazo.
   - **Pasada 2:** Se re-clasifican todas las jugadas dando prioridad a las 8 cartas del mazo descubierto (tanto en su versión normal como evolucionada `-ev1`).

---

## 5. Ejecución Distribuida en Equipo y Persistencia en R2

El Notebook 03 está diseñado para que varios compañeros procesen lotes distintos de videos en paralelo sin pisarse:

- **`VIDEO_FILTER` (Celda 1):** Acepta `'all'`, un `video_id` único o una lista de IDs asignada a cada integrante (`['id1', 'id2', ...]`).
- **Checkpointing Atómico Individual:** Cada video procesado se sube a `s3://cr-videos/metadata/events/<video_id>.json`.
- **Consolidación Aditiva (`consolidate_events_manifest()`):** Lista todos los objetos existentes en `s3://cr-videos/metadata/events/` y construye `s3://cr-videos/metadata/extracted_events.json` **sumando el trabajo acumulado de todo el equipo**.
- **Gráfica de Elixir (Celda 6) y Video de Verificación H.264 (Celda 7):**
  - Operan exclusivamente sobre `selected_videos` y leen directamente los JSON ya guardados en R2 (`load_or_fetch_video_result(vid)`), permitiendo generar gráficas o videos de auditoría en cualquier momento sin reprocesar la detección.
