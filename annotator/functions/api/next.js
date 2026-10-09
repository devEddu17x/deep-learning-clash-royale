import { json, releaseStale } from '../_lib.js';

// POST /api/next {annotator} -> video asignado (reutiliza el que ya tenía reclamado).
export async function onRequestPost({ request, env }) {
  const { annotator } = await request.json();
  if (!annotator || typeof annotator !== 'string') return json({ error: 'annotator requerido' }, 400);
  await releaseStale(env);

  const mine = await env.DB.prepare(
    `SELECT * FROM videos WHERE status='claimed' AND claimed_by=? LIMIT 1`
  ).bind(annotator).first();
  if (mine) return json(mine);

  // Un único UPDATE ... RETURNING es atómico en D1.
  const claimed = await env.DB.prepare(
    `UPDATE videos SET status='claimed', claimed_by=?, claimed_at=datetime('now')
     WHERE id = (SELECT id FROM videos WHERE status='pending' ORDER BY created_at, id LIMIT 1)
     RETURNING *`
  ).bind(annotator).first();
  return json(claimed ?? { empty: true });
}

