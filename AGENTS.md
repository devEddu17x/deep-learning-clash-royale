# AGENTS.md

Contexto para agentes que trabajen en este repo. El usuario habla español: responde en español, conciso.

## Proyecto
Modelo (VLM, salida en **texto libre**, no clasificación) que recibe 4 frames de una partida de Clash Royale (−6 s, −4 s, −2 s y actual) y dice en lenguaje natural qué carta jugar y dónde. Ej.: "Juega Valquiria detrás del puente izquierdo". Detalle en `docs/project-idea.md`.

**Etapa actual: solo construcción del dataset. No se entrena nada.**

## Dataset (decisiones tomadas)
- Fuente: videos de YouTube de **solo partida** (sin youtubers, cortes, cofres), preferentemente verticales con solo la pantalla del juego. Los busca el equipo (5 personas) a mano. Meta ≈ 240 partidas, ≈ 10K jugadas, 1 fps.
- Etiquetado automático por visión por computadora: detectar carta jugada y posición. Pistas útiles: el elixir baja, la mano rota, la carta aparece "levantada" al arrastrarla, el reloj (`Time left`) sirve para segmentar partidas dentro de un video largo.
- Se prefieren herramientas ya hechas (YOLO/Roboflow, OCR, VLM para preetiquetar) a construir todo desde cero.
- Frame "actual" = último frame **antes** de que aparezca la carta (≈ t_jugada − 0.5–1 s), para no filtrar la respuesta.
- Acciones: `jugar(carta, zona)` y `esperar` (ejemplos de "no jugar" incluidos).
- Zonas preliminares en `posiciones.txt` (6, todas del lado propio). Plan: cuadrícula fija sobre la arena → mapear celda a zona nombrada → plantilla de texto. Guardar siempre carta y celda `(x,y)` como metadatos además del texto. La cuadrícula NO es salida del modelo.
- Sin aspectos legales por ahora (decisión del usuario).
- Los videos pueden variar en resolución, duración y proporción (iPhone, Android, iPad…).

## Hallazgos técnicos
- El video de ejemplo `LRX8zTKrrt4` es vertical, máx. **592×1280** (AV1, 30 fps). Un selector `height<=720` en videos verticales limita el lado largo y baja a 332×720; el selector correcto es `bestvideo[vcodec^=avc1][height<=1920]/bestvideo[height<=1920]/best`.
- Descargar el video completo con `concurrent_fragment_downloads=8` y recortar con `ffmpeg -c copy` es rápido (11 s para 40 min). Usar `download_ranges` + `force_keyframes_at_cuts` fue muy lento.
- Un video largo contiene varias partidas, a veces cortadas; el recorte por `START_S` manual no alinea con una partida. Segmentar por reloj/OCR.
- UI observada en el piloto: elixir como número junto a la barra, costo en cada carta, siguiente carta a la izquierda, `x2` de elixir doble, pantalla roja en overtime.

## Infraestructura
- Código en este repo; el notebook `notebooks/01-generate-dataset.ipynb` se ejecuta en un **kernel de Kaggle** conectado desde VS Code (no hay GPU activada; no hace falta aún). Kaggle: internet activado, `/kaggle/working` ~20 GB; YouTube puede bloquear IPs de Kaggle (alternativa: descargar fuera y subir como Dataset/R2).
- Cloudflare gratuito (Pages, D1, R2), AWS créditos, Colab, Kaggle, VPS en Oracle disponibles.
- No se pueden editar `.ipynb` con `replace_file_content`; usar un script (Python/json) o `write_to_file` con overwrite.

## annotator/ (herramienta de calibración, Cloudflare Pages + D1)
Aislada de los notebooks. Ver `annotator/README.md`.
- Los 5 anotadores agregan URLs (botón **+ Agregar URLs**, se guarda `https://youtu.be/<id>` limpia sin `&t=`), ven la lista con duración total y pueden borrar (CRUD sin update), y etiquetan con **Siguiente video** (reclamo atómico, reclamos inactivos >30 min se liberan).
- Reproductor de YouTube incrustado (16:9). Por video se guarda **una** calibración: `game_full=1` (todo el video es la pantalla del juego, caso habitual, un clic) o `game_box {x,y,w,h}` normalizada sobre el área 16:9 del reproductor (caso raro: bordes, decoración, otra proporción). Se puede rechazar con motivo.
- `YOUTUBE_API_KEY` opcional (duración y validación de IDs). `ADMIN_TOKEN` protege `/api/export`.
- Migraciones en `annotator/migrations/` (0002 `added_by`, 0003 caja única). `schema.sql` crea desde cero.
- **Pendiente: desplegar y proteger con Cloudflare Access** (no configurado; hoy cualquiera con la URL puede agregar/borrar).
- Probado solo por API local con `wrangler`; la UI no se ha probado en navegador por el agente.

## Historial de decisión sobre cajas (para no repetir el error)
Primero se pedían dos cajas (VIDEO y ARENA). Se simplificó a una (`game_full` / `game_box`) porque (a) en videos que ya son solo pantalla no hay nada que delimitar y dibujar introduce error; (b) las barras negras que se veían eran del reproductor 16:9 de YouTube, y el pipeline puede calcularlas al conocer la proporción real del video. El usuario duda de esto: ver la pregunta abierta más abajo.

## Secretos y despliegue del annotator
- `ADMIN_TOKEN` (obligatorio para exportar): cadena larga aleatoria (`openssl rand -hex 32`) que el usuario inventa. Solo protege `/api/export` (header `x-admin-token`), que descarga las calibraciones para el pipeline. Si falta, `/api/export` responde 401 (el resto de la app funciona). Se guarda con `wrangler pages secret put ADMIN_TOKEN --project-name cr-annotator` y el usuario lo conserva para usarlo en el pipeline.
- `YOUTUBE_API_KEY` (opcional): API key de Google Cloud con "YouTube Data API v3" (gratis). Da duración total y valida IDs. Sin ella no hay duración. `wrangler pages secret put YOUTUBE_API_KEY --project-name cr-annotator`.
- No hay más secretos. D1 se enlaza por binding `DB` (Pages → Settings → Functions → D1 bindings), no por secreto. Nunca commitear tokens.
- Orden de despliegue: `wrangler d1 create cr-annotator` → pegar `database_id` en `annotator/wrangler.toml` → `wrangler d1 execute cr-annotator --remote --file=schema.sql` → crear proyecto Pages y `wrangler pages deploy public` → secretos → binding D1 → Cloudflare Access (Zero Trust → Access → Applications → Self-hosted, dominio `cr-annotator.pages.dev` y `*.cr-annotator.pages.dev`, política Allow con los correos del equipo).
- Si se activa Access sobre todo el dominio, un pipeline remoto (Kaggle) necesita un *service token* de Access para llamar a `/api/export`; alternativa: descargar el JSON a mano y subirlo.

## Estado y decisiones recientes
- Los anotadores usan casi siempre **"Todo el video es la partida"** (videos como el de ejemplo, solo pantalla). `game_box` solo en casos raros.
- Los videos de ejemplo traen varias partidas seguidas (47 min): el annotator acepta el video completo; la segmentación en partidas es del pipeline.
- Artefactos locales de `wrangler` (`annotator/.wrangler/`) están en `.gitignore`. Bases locales previas pueden necesitar migraciones `0002` y `0003`.

## Pregunta abierta
- Confirmar con el usuario si la caja manual (`game_box`) debe cubrir la **pantalla de juego completa** (reloj → cartas, lo implementado) o solo la **arena** sin el mazo. Las regiones de elixir, mano y reloj se derivarán por proporciones de esa caja; esa suposición no está verificada.

## Plan de próximos pasos (en orden)
1. **Desplegar** annotator (ver sección de secretos) y proteger con Access. El usuario ejecuta los comandos; el agente guía.
2. **Pipeline de descarga y R2**:
   - `scripts/sync_to_r2.py` corre localmente o en VPS: consulta `/api/export`, descarga con IP limpia y sube a Cloudflare R2 (`cr-videos`).
   - El notebook en Kaggle descarga desde R2 vía `boto3` a máxima velocidad de red sin depender de YouTube ni cookies. Para `game_box`, convertir de coordenadas del reproductor 16:9 a coordenadas del video (ajuste centrado según proporción real). Recorte → lienzo canónico.
3. **Segmentación de partidas** por reloj (`Time left`, OCR con PaddleOCR/EasyOCR o plantillas): detectar inicio/fin de cada partida, descartar menús y repeticiones. Muestrear a 1 fps.
4. **Medir regiones UI** (elixir, mano, siguiente carta, reloj, arena) sobre frames reales y fijar proporciones (verificar la pregunta abierta). Derivar celdas de cuadrícula sobre la arena (≈18×32).
5. **Detector de jugadas**: caída de elixir + rotación de la mano + carta "levantada". Probar detectores públicos (Roboflow/YOLO) antes de entrenar nada. Identificar carta por template matching/clasificador pequeño con el catálogo de íconos.
6. **Plantillas de texto**: celda → zona de `posiciones.txt` → frase variada; incluir ejemplos de `esperar`. Guardar siempre carta, celda `(x,y)`, timestamps y texto.
7. **Ensamblado**: muestras de 4 frames (t−6, t−4, t−2, t_pre-jugada), splits por video (no por frame), control de calidad manual de una muestra y métricas.

## Convenciones
- Conservar comentarios y docstrings existentes que no estén relacionados con el cambio.
- Rutas absolutas en enlaces; respuestas concisas y en español.

