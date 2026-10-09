import { json, boxesOk } from '../_lib.js';

// POST /api/submit
//   calibrar: {video_id, annotator, game_full:true | game_box:{x,y,w,h}, notes?}
//   rechazar: {video_id, annotator, reject: "motivo"}
export async function onRequestPost({ request, env }) {
  const b = await request.json();
  const { video_id, annotator } = b;
  if (!video_id || !annotator) return json({ error: 'video_id y annotator requeridos' }, 400);

  const v = await env.DB.prepare(`SELECT status, claimed_by FROM videos WHERE id=?`).bind(video_id).first();
  if (!v) return json({ error: 'video no existe' }, 404);
  if (v.status !== 'claimed' || v.claimed_by !== annotator)
    return json({ error: 'este video no está reclamado por ti' }, 409);

  if (b.reject) {
    await env.DB.prepare(`UPDATE videos SET status='rejected', reject_reason=? WHERE id=?`)
      .bind(String(b.reject).slice(0, 200), video_id).run();
    return json({ ok: true });
  }

  if (!b.game_full && !boxesOk(b.game_box)) return json({ error: 'caja inválida' }, 400);
  await env.DB.batch([
    env.DB.prepare(
      `INSERT OR REPLACE INTO calibrations (video_id, game_full, game_box, annotator, notes) VALUES (?,?,?,?,?)`
    ).bind(video_id, b.game_full ? 1 : 0, b.game_full ? null : JSON.stringify(b.game_box),
           annotator, b.notes ? String(b.notes).slice(0, 500) : null),
    env.DB.prepare(`UPDATE videos SET status='done' WHERE id=?`).bind(video_id),
  ]);
  return json({ ok: true });
}
