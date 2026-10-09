import { json } from '../_lib.js';

const ID_RE = /(?:youtu\.be\/|[?&]v=|shorts\/|embed\/|live\/)([\w-]{11})(?![\w-])/;
const extractId = (s) => {
  s = s.trim();
  if (/^[\w-]{11}$/.test(s)) return s;
  return s.match(ID_RE)?.[1] ?? null;
};

const isoToSeconds = (d) => {
  const m = /^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/.exec(d ?? '');
  return m ? (+m[1] || 0) * 86400 + (+m[2] || 0) * 3600 + (+m[3] || 0) * 60 + (+m[4] || 0) : null;
};

// id -> {title, duration_s}. Data API v3 si hay YOUTUBE_API_KEY; si no, oEmbed (solo título).
async function fetchMeta(ids, env) {
  const out = new Map();
  if (env.YOUTUBE_API_KEY) {
    for (let i = 0; i < ids.length; i += 50) {
      const q = new URLSearchParams({ part: 'snippet,contentDetails', id: ids.slice(i, i + 50).join(','), key: env.YOUTUBE_API_KEY });
      try {
        const r = await fetch(`https://www.googleapis.com/youtube/v3/videos?${q}`);
        if (!r.ok) continue;
        for (const it of (await r.json()).items ?? [])
          out.set(it.id, { title: it.snippet.title, duration_s: isoToSeconds(it.contentDetails.duration) });
      } catch {}
    }
    return out;
  }
  await Promise.all(ids.map(async (id) => {
    try {
      const r = await fetch(`https://www.youtube.com/oembed?format=json&url=https://youtu.be/${id}`);
      out.set(id, { title: r.ok ? (await r.json()).title : null, duration_s: null });
    } catch { out.set(id, { title: null, duration_s: null }); }
  }));
  return out;
}

// POST /api/add {added_by, urls: "una URL por línea o separadas por espacios"}
// -> {added:[], duplicated:[], invalid:[]}
export async function onRequestPost({ request, env }) {
  const { urls, added_by } = await request.json();
  if (!added_by || typeof urls !== 'string') return json({ error: 'added_by y urls requeridos' }, 400);

  const tokens = urls.split(/[\s,]+/).filter(Boolean);
  const ids = [...new Set(tokens.map(extractId).filter(Boolean))];
  const invalid = tokens.filter((t) => !extractId(t));
  if (ids.length > 200) return json({ error: 'máximo 200 URLs por vez' }, 400);

  const meta = await fetchMeta(ids, env);
  // Con API key, un ID que YouTube no devuelve (borrado/privado) se trata como inválido.
  if (env.YOUTUBE_API_KEY) {
    for (const id of ids) if (!meta.has(id)) invalid.push(id);
  }
  const valid = env.YOUTUBE_API_KEY ? ids.filter((id) => meta.has(id)) : ids;

  const existing = new Set();
  for (let i = 0; i < valid.length; i += 50) {
    const chunk = valid.slice(i, i + 50);
    const { results } = await env.DB.prepare(
      `SELECT id FROM videos WHERE id IN (${chunk.map(() => '?').join(',')})`
    ).bind(...chunk).all();
    results.forEach((r) => existing.add(r.id));
  }

  const stmt = env.DB.prepare(`INSERT OR IGNORE INTO videos (id, url, title, duration_s, added_by) VALUES (?,?,?,?,?)`);
  const fresh = valid.map((id) => ({ id, ...meta.get(id) })).filter((v) => !existing.has(v.id));
  if (fresh.length) {
    await env.DB.batch(fresh.map((v) => stmt.bind(v.id, `https://youtu.be/${v.id}`, v.title ?? null, v.duration_s ?? null, added_by)));
  }
  return json({ added: fresh, duplicated: valid.filter((id) => existing.has(id)), invalid });
}

