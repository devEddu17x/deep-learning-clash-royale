# Especificación de Segmentación de Partidas (Paso 3 del Pipeline)

Este documento registra las reglas visuales, invariantes y la máquina de estados desarrollada para segmentar automáticamente partidas completas de Clash Royale desde videos de YouTube.

---

## 1. Características e Invariantes del Reloj en Batalla

El temporizador del juego es el anclaje más robusto para delimitar partidas completas (inmune a emotes y paneles de cartas):

1. **Ubicación Canónica (Esquina Superior Derecha):**
   - **Caja externa:** Ocupa típicamente `x: [60%, 99.5%]`, y su posición vertical varía según el dispositivo:
     - En pantallas estándar 16:9 vertical: `y: [2.0%, 10.0%]`.
     - En dispositivos modernos con notch, Dynamic Island o barra de estado alta (iPhone 13/14/15, Android 20:9 con ratio $W/H < 0.49$): `y: [5.0%, 13.5%]`.
   - **Sub-región de dígitos (`M:SS`):** Ubicada simétricamente en `dy: [35%, 96%]`, `dx: [8%, 95%]` de la caja, evitando el texto superior de estado (`Termina en:` o `Time left:`).

2. **Comportamiento Visual de Colores:**
   - **Tiempo regular (0–2 min):** Caja de fondo gris/negro oscuro con dígitos blancos y borde negro.
   - **Últimos 60s regulares:** Cartel *"¡Doble de elixir!"*, el reloj alterna a dígitos rojos con borde negro.
   - **Muerte Súbita (Overtime):**
     - La caja cambia a **fondo rojizo/vino**.
     - Texto superior: `Tiempo extra` / `Overtime`.
     - El reloj salta a `2:00` (o `1:00`) y desciende.
     - En los últimos 30s de Overtime, los números son de un **rojo intenso**.

3. **Particularidades Críticas del OCR:**
   - En números rojos gruesos de Overtime, EasyOCR a menudo confunde los dos puntos `:` con caracteres como `'b'`, `'B'`, `'8'`, `'o'`, `.` o `-`. Por ejemplo: `0:26` se lee como `0b26` o `0826`.
   - El parser utiliza un regex flexible: `r'([0-5])[\s:\.-bBoO8]?([0-5][0-9])'`.
   - En fuentes redondeadas de Supercell, a veces el dígito `6` rojo puede confundirse visualmente con un `8`.

---

## 2. Detección de Inicio y Fin de Partida

### A. Inicio de Partida (`t_start`)
- **Realidad en gameplay:** Tras la animación de presentación de jugadores y el cartel *"¡A luchar!"*, el reloj no es visible sino hasta que marca **$\approx 2:56$ a $2:54$** (rara vez $2:58$, prácticamente nunca $2:59+$).
- **Regla:** Se registra inicio de partida cuando el reloj marca un valor $\ge 2:20$ ($140\text{ s}$).

### B. Fin de Partida (`t_end`)

Existen dos tipos de desenlace:

1. **Sin Overtime (Partida regular de 3 minutos):**
   - Si la partida termina por tiempo, el reloj llega a `0:01` / `0:00`.
   - Si una torre es destruida antes de los 3 minutos (victoria por 3 coronas), **la caja del reloj desaparece inmediatamente**.
   - Si la caja del reloj no se detecta durante más de 5 segundos seguidos, la partida se da por terminada en el último fotograma visible.

2. **Con Muerte Súbita (Overtime):**
   - Al llegar a `0:01`, el reloj pasa inmediatamente a `2:00` / `1:59`. La máquina de estados mantiene la continuidad (`in_overtime = True`).
   - **Comportamiento del reloj al caer la torre en Overtime:**
     - A diferencia del tiempo regular, **el reloj no desaparece de inmediato**, sino que **SE CONGELA** en el valor exacto en que cayó la torre (ej. `0:30` o `0:26`).
     - Se mantiene congelado durante 5 a 8 segundos mientras aparecen animaciones de confeti, coronas y podio de victoria.
     - En ocasiones, el confeti azul o las coronas pueden tapar parcialmente el reloj durante 1 segundo produciendo lecturas erráticas.
   - **Algoritmo de Fin Exacto por Detección de Meseta:**
     - En la recta final (últimos 20s de lecturas), se busca de izquierda a derecha la **primera racha de 3 o más lecturas idénticas consecutivas**:
       `reads[i] == reads[i+1] == reads[i+2]`
     - El segundo `i` corresponde con precisión milimétrica ($\approx \pm 0.5\text{ s}$) al momento en que cayó la torre y concluyó el combate, descartando por completo el confeti posterior.

---

## 3. Arquitectura del Pipeline en el Notebook (`01-segmentation.ipynb`)

El procesamiento se divide en dos fases modulares y celdas secuenciales limpias:

1. **Fase 1: Calibración y Anclaje Inmutable Universal (`c_fase1_algorithms`)**
   - Evalúa los primeros segundos (hasta 60s muestreando cada 2s) sobre todo el **cuadrante superior derecho amplio** (`y: [0, 35%]`, `x: [50%, 100%]`), garantizando compatibilidad total con cualquier dispositivo (iPhone con notch o isla dinámica, Android 16:9, 20:9 o tablets 4:3):
     - **Estrategia 1 (Cluster de Dígitos Rápido, ~5ms):** Agrupa píxeles brillantes o rojos del reloj y valida con OCR la sub-caja recortada.
     - **Estrategia 2 (OCR Completo del Cuadrante con Extracción de Bounding Box):** Si el cluster morfológico no confirma, EasyOCR procesa todo el cuadrante y extrae directamente el polígono/bounding box exacto de cualquier texto con formato de tiempo `M:SS` o cartel `Time left:`. Inmune a contrastes difíciles, fondos oscuros o barras de estado atípicas.
   - Tan pronto como se detecta una lectura válida, esas coordenadas se expanden con márgenes canónicos y quedan **bloqueadas de manera inmutable** para todo el video.

2. **Fase 2: Segmentación Continua a 1 FPS (`c_fase2_algorithms`)**
   - Escanea el video a 1 frame por segundo leyendo exclusivamente en la ROI anclada, sin límite de duración (`max_seconds = None`), con log de progreso en tiempo real (`flush=True`) cada 5 minutos.
   - **Separación de partidas en cortes rápidos de edición:** Si el reloj salta de nuevo a tiempo inicial ($\ge 2:20$) tras haber jugado al menos 40s, se activa la verificación por *lookahead* (`is_confirmed_new_match`).
   - **Anti-Glitch por Lookahead:** Se verifica que las lecturas inmediatamente posteriores confirmen una cuenta regresiva coherente ($\ge 130\text{s}$). Si se confirma, la partida previa se cierra en su meseta y la nueva arranca; si es un fotograma anómalo aislado, se ignora como ruido de OCR.
   - Une tiempo regular con Overtime.
   - Aplica la detección de meseta congelada para encontrar el segundo exacto de la caída de torre.
   - Salida formateada en `MM:SS` con links directos clickeables a YouTube (`https://youtu.be/<id>?t=<segundos>`).

3. **Ejecución y Galerías Visuales (`c_pipeline_execution`, `c_fase1_gallery`, `c_fase2_gallery`)**
   - Bucle video por video tolerante a fallos con guardado atómico en R2.
   - **Galería Visual Fase 1 (`c_fase1_gallery`):** Grilla con el fotograma completo marcado con el recuadro verde, el zoom del reloj y el método de detección empleado (`fast_cluster` o `quadrant_ocr`).
   - **Galería Visual Fase 2 (`c_fase2_gallery`):** Muestra lado a lado el fotograma exacto de inicio vs el fotograma exacto de fin de cada clip desde miniaturas en memoria.

---

## 4. Persistencia Atómica y Resiliencia en Cloudflare R2 (API S3)

Para procesar grandes volúmenes de video (4h a 12h+) en Kaggle sin riesgo de saturar el disco ni perder avances ante caídas de sesión:

1. **Pipeline Incremental (Video por Video):**
   - El bucle procesa un solo video a la vez: descarga $\to$ anclaje $\to$ segmentación $\to$ checkpoint $\to$ liberación de disco.
   - Elimina el archivo `.mp4` local inmediatamente después de procesarlo (`DELETE_VIDEO_AFTER_PROCESSING = True`), manteniendo el uso de disco acotado a un único video (inmune al límite de 20GB de Kaggle).
2. **Checkpointing Atómico por Video:**
   - Cada video genera su propio archivo: `cr-videos/metadata/segments/<video_id>.json`.
   - Se sube inmediatamente a Cloudflare R2 vía la API estándar de S3 (`boto3.client('s3')`), garantizando consistencia inmediata (*Read-After-Write Consistency*) y evitando los problemas de caché de borde del CDN público.
3. **Idempotencia y Detección Previa:**
   - Al arrancar, el notebook consulta `s3.list_objects_v2(Prefix='metadata/segments/')` para obtener el listado exacto de videos ya procesados.
   - Cualquier video completado se salta instantáneamente (`SKIP_ALREADY_PROCESSED = True`), permitiendo reanudar la ejecución sin duplicar cómputo.
4. **Manifiesto Consolidado:**
   - Al finalizar todos los videos de la sesión, se compila un único archivo maestro:
     `cr-videos/metadata/segmented_matches.json`.

---

## 5. Códecs de Video y Compatibilidad en Kaggle
- Algunos videos de YouTube se descargan por defecto en formato **AV1**.
- Las instancias de Kaggle (OpenCV compilado sin decodificación AV1 por hardware) fallan en decodificar videos AV1 al usar `cv2.VideoCapture.set(CAP_PROP_POS_MSEC)`.
- **Regla:** En `scripts/sync_to_r2.py`, `yt-dlp` debe priorizar siempre el códec **H.264 / AVC1**:
  `'format': 'bestvideo[ext=mp4][vcodec^=avc1][height<=1920]/bestvideo[height<=1920]/best'`.

