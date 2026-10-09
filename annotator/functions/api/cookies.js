import { json, isAdmin } from '../_lib.js';

export async function onRequestGet({ request, env }) {
  if (!isAdmin(request, env)) return json({ error: 'no autorizado' }, 401);
  const row = await env.DB.prepare("SELECT value FROM kv_store WHERE key = 'youtube_cookies'").first();
  if (!row) return new Response('', { status: 404 });
  return new Response(row.value, { headers: { 'content-type': 'text/plain; charset=utf-8' } });
}

export async function onRequestPut({ request, env }) {
  if (!isAdmin(request, env)) return json({ error: 'no autorizado' }, 401);
  const body = await request.text();
  if (!body) return json({ error: 'cuerpo vacío' }, 400);

  // Filtrar solo líneas de youtube para mantenerlo ligero
  const ytLines = body.split('\n').filter(l => l.includes('.youtube.com') || l.startsWith('#')).join('\n');

  await env.DB.prepare(
    "INSERT INTO kv_store (key, value, updated_at) VALUES ('youtube_cookies', ?, datetime('now')) " +
    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at"
  ).bind(ytLines).run();

  return json({ ok: true, bytes: ytLines.length });
}
