import { json, isAdmin } from '../_lib.js';

// GET /api/export (header x-admin-token) -> videos aceptados con su calibración
// GET /api/export?stats=1 (público) -> conteo por estado
export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  if (url.searchParams.get('stats')) {
    const { results } = await env.DB.prepare(
      `SELECT status, COUNT(*) AS n FROM videos GROUP BY status`
    ).all();
    return json(results);
  }
  if (!isAdmin(request, env)) return json({ error: 'no autorizado' }, 401);
  const { results } = await env.DB.prepare(
    `SELECT v.id, v.url, v.title, v.duration_s, v.width, v.height,
            c.game_full, c.game_box, c.annotator, c.notes
     FROM videos v JOIN calibrations c ON c.video_id = v.id
     WHERE v.status='done' ORDER BY v.id`
  ).all();
  return json(results.map((r) => ({
    ...r, game_full: !!r.game_full, game_box: r.game_box ? JSON.parse(r.game_box) : null,
  })));
}

