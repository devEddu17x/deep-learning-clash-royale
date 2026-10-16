# Especificación de Localización en Arena y Ensamble del Dataset VLM (Paso 4B — Parte 2)

Este documento detalla la arquitectura técnica, la mecánica visual de anclaje por etiqueta flotante del nombre de la carta, el fallback por aparición neta, y el formato del manifiesto consolidado en [`notebooks/04-arena-and-dataset.ipynb`](file:///home/eddu/dev/reinforcement-learning-clash-royale/notebooks/04-arena-and-dataset.ipynb).

---

## 1. Responsabilidad del Notebook 04

El Notebook 04 consume los tres manifiestos previamente validados en Cloudflare R2:
- `s3://cr-videos/metadata/segmented_matches.json` (Notebook 01)
- `s3://cr-videos/metadata/ui_layouts.json` (Notebook 02 — usando únicamente `arena_box`)
- `s3://cr-videos/metadata/events/<video_id>.json` / `extracted_events.json` (Notebook 03 — `t_drop_sec`, `t_decision_sec`, `card_key`, `hand_slot`, etc.)

Y resuelve las siguientes tareas:
1. **Localizar la coordenada normalizada `(x_norm, y_norm)`** donde se colocó la carta dentro de `arena_box`.
2. **Proyectar la coordenada a las zonas estratégicas** ([`posiciones.txt`](file:///home/eddu/dev/reinforcement-learning-clash-royale/posiciones.txt) en campo propio + zonas ofensivas rivales para cartas de alcance global) y generar la instrucción en lenguaje natural (`target_text`).
3. **Muestrear ejemplos pasivos de `"esperar"`** en ventanas de inactividad ($\ge 6.5\text{s}$) manteniendo un ratio balanceado (~15–20%).
4. **Persistencia atómica y consolidación en R2:** Checkpoint individual por video en `s3://cr-videos/metadata/placements/<video_id>.json` y manifiesto consolidado en `s3://cr-videos/metadata/arena_placements.json`.

---

## 2. Fundamento Visual: El Anclaje por Etiqueta Flotante (`locate_card_drop`)

Durante las pruebas empíricas sobre videos reales (`Qy18H5V-nbE` y `soLMMwrsFIo`), se comprobó que la resta de movimiento ingenua falla en dos casos comunes:
- **Cartas subterráneas/viajeras (`goblin-drill`, `miner`, `goblin-barrel`):** El movimiento inicial ocurre en el río/centro mientras viajan, pero su impacto real es en la torre rival.
- **Estructuras defensivas (`inferno-tower`, `cannon`, `tesla`):** Se juegan en el centro (Zona 5) mientras en el puente izquierdo o derecho hay combates simultáneos intensos con más movimiento.

### Señal Principal: La Etiqueta Flotante de Despliegue
En Clash Royale, cada vez que el jugador arrastra o suelta una carta propia:
1. Aparece el **nombre de la carta flotando** (en blanco puro o dorado estelar con contorno negro) junto al indicador `Nvl. XX` **directamente sobre la baldosa objetivo**.
2. Esta etiqueta es **exclusiva de nuestras cartas** (el rival no muestra etiquetas flotantes con contorno negro al tirar tropas) y **aparece en el destino real desde el primer instante**, siendo totalmente inmune a peleas en los puentes o a la trayectoria de viaje de túneles y barriles.
3. El punto de despliegue se calcula como:
   $$\text{deploy\_y} = \text{label\_top\_y} + 0.07 \cdot \text{frame\_width}$$
   centrado horizontalmente en la palabra.

### Ventana Temporal y Compensación de Latencia
- En el Notebook 03, la confirmación de la caída de elixir (`t_drop_sec`) ocurre con un desfase de $\approx +0.3\text{ a }+0.5\text{ s}$ respecto al momento físico en que la carta se posa en la arena.
- Por tanto, el detector de etiquetas busca texto nuevo en la ventana:
  $$t \in [t_{\text{drop}} - 0.45\text{ s}, t_{\text{drop}} + 0.35\text{ s}]$$
  comparando contra un fondo de referencia anterior ($t_{\text{drop}} - 1.60\text{ s}$ y $t_{\text{drop}} - 1.25\text{ s}$) para no restar la propia etiqueta ni confundirla con textos estáticos de vida de torres.

### Señal Secundaria (Fallback por Aparición Neta)
Si no se detecta ninguna etiqueta con suficiente confianza (p. ej. ocluida por hechizos densos como *Furia* o cartas instantáneas):
- Se activa el fallback `detect_arena_spawn_by_motion()`, que mide la diferencia de fotogramas restando la actividad previa e integrando el reloj circular blanco de despliegue y el cartel azul de nivel.

---

## 3. Control de Fuga de Datos (*Data Leakage*)

Cada evento enriquecido incluye el flag booleano `label_visible_at_decision`:
- Verifica si en $t_{\text{decision}} = t_{\text{drop}} - 0.80\text{s}$ (el frame final que el VLM recibe como entrada) la etiqueta de la carta ya era visible en pantalla (debido a que el jugador la estuvo arrastrando antes de soltarla).
- En caso afirmativo, permite al pipeline de ensamble descartar la muestra o atrasar $t_{\text{decision}}$ a un instante previo seguro para evitar que el modelo aprenda a leer el texto flotante en vez de analizar el tablero.

---

## 4. Mapeo a las 6 Zonas Propias (`posiciones.txt`) y Zonas Ofensivas Globales

La arena calibrada (`arena_box`) se normaliza a $(x_{\text{norm}}, y_{\text{norm}}) \in [0, 1]^2$.

### A. Campo Propio ($y_{\text{norm}} \ge 0.42$) — [`posiciones.txt`](file:///home/eddu/dev/reinforcement-learning-clash-royale/posiciones.txt)
- **Zona 1:** `detrás del puente izquierdo` ($y \in [0.42, 0.62)$, $x < 0.50$)
- **Zona 2:** `detrás del puente derecho` ($y \in [0.42, 0.62)$, $x \ge 0.50$)
- **Zona 3:** `frente a la torre izquierda` ($y \in [0.62, 0.85)$, $x < 0.50$)
- **Zona 4:** `frente a la torre derecha` ($y \in [0.62, 0.85)$, $x \ge 0.50$)
- **Zona 5 (Prioridad Central):** `en el centro del campo propio` ($y \in [0.56, 0.83)$, $x \in [0.33, 0.67]$)
- **Zona 6:** `detrás de la torre del rey` ($y \ge 0.85$)

### B. Campo Rival ($y_{\text{norm}} < 0.42$) — Cartas Globales / Hechizos
- **Zona 7:** `sobre la torre izquierda rival` ($x < 0.50$)
- **Zona 8:** `sobre la torre derecha rival` ($x \ge 0.50$)
- **Zona 9:** `sobre la torre del rey rival` ($y < 0.20$, $x \in [0.35, 0.65]$)

---

## 5. Muestreo de `"esperar"` y Persistencia en R2

1. **Muestras Pasivas de `"esperar"` (`sample_wait_actions`):**
   - Identifica intervalos estables $\ge 6.5\text{s}$ sin jugadas.
   - Extrae el punto medio de la ventana y asigna la etiqueta textual objetivo: `"esperar"`.
   - Mantiene una proporción del ~15–20% de muestras pasivas para evitar sobre-agresividad en el modelo.
2. **Persistencia Atómica y Consolidación Aditiva:**
   - Checkpoint individual: `s3://cr-videos/metadata/placements/<video_id>.json`.
   - Manifiesto global: `s3://cr-videos/metadata/arena_placements.json`.
   - Soporta procesamiento paralelo distribuido en equipo sin pisar datos.
