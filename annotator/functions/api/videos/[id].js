import { json } from '../../_lib.js';

// DELETE /api/videos/:id -> borra el video y su calibración
export async function onRequestDelete({ params, env }) {
  const id = params.id;
  if (!/^[\w-]{11}$/.test(id)) return json({ error: 'id inválido' }, 400);
  const [, del] = await env.DB.batch([
    env.DB.prepare(`DELETE FROM calibrations WHERE video_id=?`).bind(id),
    env.DB.prepare(`DELETE FROM videos WHERE id=?`).bind(id),
  ]);
  return del.meta.changes ? json({ ok: true }) : json({ error: 'no existe' }, 404);
}
