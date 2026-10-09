import { json } from '../../_lib.js';

// GET /api/videos -> lista de videos + totales de duración
export async function onRequestGet({ env }) {
  const { results } = await env.DB.prepare(
    `SELECT id, url, title, duration_s, status, added_by, claimed_by, reject_reason, created_at
     FROM videos ORDER BY created_at DESC, id`
  ).all();
  const { results: totals } = await env.DB.prepare(
    `SELECT status, COUNT(*) AS n, COALESCE(SUM(duration_s),0) AS duration_s,
            SUM(duration_s IS NULL) AS without_duration
     FROM videos GROUP BY status`
  ).all();
  return json({ videos: results, totals });
}
