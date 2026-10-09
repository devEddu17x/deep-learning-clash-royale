-- Cola de videos. `status` controla el reparto entre anotadores.
CREATE TABLE IF NOT EXISTS videos (
  id           TEXT PRIMARY KEY,             -- ID de YouTube
  url          TEXT NOT NULL,
  title        TEXT,
  duration_s   INTEGER,
  width        INTEGER,                      -- resolución máxima disponible
  height       INTEGER,
  status       TEXT NOT NULL DEFAULT 'pending'
               CHECK (status IN ('pending','claimed','done','rejected')),
  claimed_by   TEXT,
  claimed_at   TEXT,
  reject_reason TEXT,
  added_by     TEXT,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status, created_at);

-- Una calibración por video.
-- game_full=1: todo el video es la pantalla del juego (caso habitual, game_box NULL).
-- game_full=0: game_box = JSON {x,y,w,h} normalizado (0..1) sobre el área 16:9 del reproductor.
CREATE TABLE IF NOT EXISTS calibrations (
  video_id    TEXT PRIMARY KEY REFERENCES videos(id),
  game_full   INTEGER NOT NULL DEFAULT 0 CHECK (game_full IN (0,1)),
  game_box    TEXT,
  annotator   TEXT NOT NULL,
  notes       TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK (game_full = 1 OR game_box IS NOT NULL)
);

-- Tabla simple clave-valor para configuraciones globales (ej. cookies)
CREATE TABLE IF NOT EXISTS kv_store (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
