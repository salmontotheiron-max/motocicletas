-- Extensión aditiva para registrar el resultado de cada fuente en cada captura.
-- No modifica ni sobrescribe observaciones históricas.
CREATE TABLE IF NOT EXISTS source_capture (
  source_capture_id TEXT PRIMARY KEY,
  capture_id TEXT NOT NULL REFERENCES capture(capture_id),
  source_id TEXT NOT NULL REFERENCES source(source_id),
  observed_at TEXT NOT NULL,
  result TEXT NOT NULL CHECK (result IN
    ('success','changed','unchanged','not_found','unavailable','error')),
  http_status INTEGER,
  final_url TEXT,
  content_type TEXT,
  content_length INTEGER CHECK (content_length IS NULL OR content_length >= 0),
  content_hash TEXT,
  excerpt TEXT,
  error_category TEXT,
  error_message TEXT,
  UNIQUE (capture_id, source_id),
  CHECK (
    (result IN ('success','changed','unchanged') AND http_status BETWEEN 200 AND 299
      AND content_hash IS NOT NULL AND error_category IS NULL)
    OR result IN ('not_found','unavailable','error')
  )
);
CREATE INDEX IF NOT EXISTS idx_source_capture_source_time
  ON source_capture(source_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_source_capture_capture_result
  ON source_capture(capture_id, result);
