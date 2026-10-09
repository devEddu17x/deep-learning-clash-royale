# CR Annotator

Herramienta aislada (sin notebooks ni descargas) para calibrar cada video: el equipo marca **dos cajas** sobre un frame y se guarda en Cloudflare D1. Es lo único que se hace a mano antes del pipeline.

- Cloudflare Pages: `public/` (interfaz) + `functions/api/*` (API)
- Cloudflare D1: cola de videos y calibraciones
- Reparto sin conflictos: `/api/next` reclama el siguiente video de forma atómica; los reclamos inactivos >30 min se liberan.

## Despliegue (una vez)

```bash
cd annotator
wrangler d1 create cr-annotator                 # copia el database_id a wrangler.toml
wrangler d1 execute cr-annotator --remote --file=schema.sql
wrangler pages project create cr-annotator --production-branch main
wrangler pages deploy public --project-name cr-annotator
wrangler pages secret put ADMIN_TOKEN --project-name cr-annotator
wrangler pages secret put YOUTUBE_API_KEY --project-name cr-annotator   # opcional: duración y validación de IDs
```

Después, en el panel de Cloudflare: Pages → Settings → Functions → D1 bindings → `DB` = `cr-annotator`.
Recomendado: protege el dominio con **Cloudflare Access** (gratis hasta 50 usuarios) para que solo entren los 5.

## Uso

1. Busca videos y pulsa **+ Agregar URLs**: pega una o varias (una por línea). Quedan *pendientes*; los duplicados se ignoran.
2. Para etiquetar, escribe tu nombre y pulsa **Siguiente video**.
3. Si el video es solo la partida (lo habitual): **Todo el video es la partida**. Un clic, sin dibujar. Si trae algo más (barras, otra proporción), pausa en una partida, pulsa `D`, dibuja **una** caja sobre la pantalla del juego y *Guardar caja*.
4. Si el video no sirve (youtuber, cortes, baja resolución), **Rechazar**.

Se puede agregar y etiquetar al mismo tiempo; no hace falta tener todos los videos cargados antes.

5. **Videos** muestra todos los agregados, la duración total acumulada y permite **borrar** (también borra su calibración). No hay edición.

`YOUTUBE_API_KEY` (YouTube Data API v3, gratis) es opcional: sin ella se agregan los videos pero sin duración.

## Exportar para el pipeline

```bash
curl -H "x-admin-token: $ADMIN_TOKEN" https://TU-DOMINIO/api/export > calibrations.json
```

Cada fila trae `game_full` (todo el frame es el juego) o `game_box` `{x,y,w,h}` en 0..1 sobre el área 16:9 del reproductor.
Para `game_box`, el pipeline calcula el rectángulo real del video dentro del reproductor (ajuste centrado según su proporción) y convierte la caja a coordenadas del video.

## Desarrollo local

```bash
wrangler d1 execute cr-annotator --local --file=schema.sql
wrangler pages dev public --d1 DB=<database_id> --persist-to .wrangler/state --binding ADMIN_TOKEN=dev
```


## Migraciones

`schema.sql` crea todo desde cero. Si tu base ya existía con un esquema anterior, aplica las migraciones pendientes de `migrations/`:

```bash
wrangler d1 execute cr-annotator --local --file=migrations/0002_added_by.sql    # base local
wrangler d1 execute cr-annotator --local --file=migrations/0003_single_game_box.sql  # una sola caja (borra calibraciones previas)
wrangler d1 execute cr-annotator --remote --file=migrations/0002_added_by.sql   # producción (si ya existía)
```
