-- Esquema inicial SQLite para seguimiento histórico de red comercial.
-- Los UUID se generan en la aplicación. Fechas de vigencia son DATE ISO-8601;
-- observed_at es timestamp ISO-8601 con zona horaria.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS brand (
  brand_id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL CHECK (length(trim(canonical_name)) > 0),
  country_scope TEXT NOT NULL DEFAULT 'ES',
  created_at TEXT NOT NULL,
  retired_at TEXT
);

CREATE TABLE IF NOT EXISTS company (
  company_id TEXT PRIMARY KEY,
  legal_name TEXT,
  country TEXT NOT NULL DEFAULT 'ES',
  created_at TEXT NOT NULL,
  CHECK (legal_name IS NULL OR length(trim(legal_name)) > 0)
);

CREATE TABLE IF NOT EXISTS outlet (
  outlet_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL CHECK (length(trim(display_name)) > 0),
  address TEXT,
  municipality_code TEXT,
  province_code TEXT,
  latitude REAL CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
  longitude REAL CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source (
  source_id TEXT PRIMARY KEY,
  publisher TEXT NOT NULL CHECK (length(trim(publisher)) > 0),
  source_type TEXT NOT NULL CHECK (source_type IN
    ('official_directory','company_page','official_statement','public_record',
     'press','aggregator','social','other')),
  url TEXT,
  title TEXT NOT NULL,
  reliability_class TEXT NOT NULL CHECK (reliability_class IN
    ('primary_official','primary_business','secondary_reputable','community','unverified')),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS capture (
  capture_id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL CHECK (status IN ('running','completed','partial','failed')),
  notes TEXT,
  CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE IF NOT EXISTS observation (
  observation_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES source(source_id),
  capture_id TEXT REFERENCES capture(capture_id),
  observed_at TEXT NOT NULL,
  source_published_at TEXT,
  source_effective_date TEXT,
  content_hash TEXT,
  evidence_excerpt TEXT,
  evidence_location TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS entity_alias (
  alias_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('brand','company','outlet')),
  entity_id TEXT NOT NULL,
  alias_text TEXT NOT NULL CHECK (length(trim(alias_text)) > 0),
  normalized_alias TEXT NOT NULL,
  valid_from TEXT,
  valid_to TEXT,
  source_observation_id TEXT REFERENCES observation(observation_id),
  CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_to > valid_from)
);

CREATE TABLE IF NOT EXISTS brand_company_relation (
  relation_id TEXT PRIMARY KEY,
  brand_id TEXT NOT NULL REFERENCES brand(brand_id),
  company_id TEXT NOT NULL REFERENCES company(company_id),
  role TEXT NOT NULL CHECK (role IN
    ('importer','national_distributor','commercializer','official_agent','other')),
  territory TEXT NOT NULL DEFAULT 'ES',
  valid_from TEXT,
  valid_to TEXT,
  status TEXT NOT NULL CHECK (status IN
    ('active_confirmed','historical_confirmed','pending','disputed','not_confirmed')),
  created_at TEXT NOT NULL,
  supersedes_relation_id TEXT REFERENCES brand_company_relation(relation_id),
  CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_to > valid_from)
);

CREATE TABLE IF NOT EXISTS outlet_company_relation (
  relation_id TEXT PRIMARY KEY,
  outlet_id TEXT NOT NULL REFERENCES outlet(outlet_id),
  company_id TEXT NOT NULL REFERENCES company(company_id),
  role TEXT NOT NULL CHECK (role IN
    ('sales_dealer','service_center','parts_only','sales_and_service','agent','other')),
  valid_from TEXT,
  valid_to TEXT,
  status TEXT NOT NULL CHECK (status IN
    ('active_confirmed','historical_confirmed','pending','disputed','not_confirmed')),
  created_at TEXT NOT NULL,
  supersedes_relation_id TEXT REFERENCES outlet_company_relation(relation_id),
  CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_to > valid_from)
);

CREATE TABLE IF NOT EXISTS outlet_brand_relation (
  relation_id TEXT PRIMARY KEY,
  outlet_id TEXT NOT NULL REFERENCES outlet(outlet_id),
  brand_id TEXT NOT NULL REFERENCES brand(brand_id),
  activity TEXT NOT NULL CHECK (activity IN
    ('new_sales','used_sales','service','parts','official_showroom','other')),
  valid_from TEXT,
  valid_to TEXT,
  status TEXT NOT NULL CHECK (status IN
    ('active_confirmed','historical_confirmed','pending','disputed','not_confirmed')),
  created_at TEXT NOT NULL,
  supersedes_relation_id TEXT REFERENCES outlet_brand_relation(relation_id),
  CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_to > valid_from)
);

CREATE TABLE IF NOT EXISTS claim (
  claim_id TEXT PRIMARY KEY,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('brand','company','outlet')),
  subject_id TEXT NOT NULL,
  predicate TEXT NOT NULL,
  object_type TEXT,
  object_id TEXT,
  asserted_value TEXT,
  valid_from TEXT,
  valid_to TEXT,
  claim_status TEXT NOT NULL CHECK (claim_status IN
    ('supported','contradicted','uncertain','withdrawn')),
  observation_id TEXT NOT NULL REFERENCES observation(observation_id),
  confidence TEXT NOT NULL CHECK (confidence IN ('high','medium','low')),
  review_status TEXT NOT NULL CHECK (review_status IN
    ('unreviewed','accepted','rejected','needs_review')),
  CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_to > valid_from)
);

CREATE TABLE IF NOT EXISTS change_event (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL CHECK (event_type IN
    ('brand_importer_change','dealer_added','dealer_removed','dealer_operator_change',
     'outlet_relocated','brand_added_to_outlet','brand_removed_from_outlet',
     'service_scope_change','name_change','unverified_disappearance','other')),
  effective_date TEXT,
  detected_at TEXT NOT NULL,
  event_status TEXT NOT NULL CHECK (event_status IN
    ('candidate','confirmed','rejected','superseded')),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS change_event_observation (
  event_id TEXT NOT NULL REFERENCES change_event(event_id),
  observation_id TEXT NOT NULL REFERENCES observation(observation_id),
  PRIMARY KEY (event_id, observation_id)
);

-- Asociaciones tipadas: mantienen integridad referencial real con cada entidad.
-- Un evento puede afectar a varias marcas, empresas y establecimientos.
CREATE TABLE IF NOT EXISTS change_event_brand (
  event_id TEXT NOT NULL REFERENCES change_event(event_id),
  brand_id TEXT NOT NULL REFERENCES brand(brand_id),
  role_in_event TEXT,
  PRIMARY KEY (event_id, brand_id)
);

CREATE TABLE IF NOT EXISTS change_event_company (
  event_id TEXT NOT NULL REFERENCES change_event(event_id),
  company_id TEXT NOT NULL REFERENCES company(company_id),
  role_in_event TEXT,
  PRIMARY KEY (event_id, company_id)
);

CREATE TABLE IF NOT EXISTS change_event_outlet (
  event_id TEXT NOT NULL REFERENCES change_event(event_id),
  outlet_id TEXT NOT NULL REFERENCES outlet(outlet_id),
  role_in_event TEXT,
  PRIMARY KEY (event_id, outlet_id)
);

CREATE TABLE IF NOT EXISTS entity_merge (
  merge_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('brand','company','outlet')),
  source_entity_id TEXT NOT NULL,
  target_entity_id TEXT NOT NULL,
  merged_at TEXT NOT NULL,
  reason TEXT NOT NULL,
  evidence_observation_id TEXT REFERENCES observation(observation_id),
  CHECK (source_entity_id <> target_entity_id),
  UNIQUE (entity_type, source_entity_id)
);

CREATE INDEX IF NOT EXISTS idx_observation_source_time
  ON observation(source_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_brand_company_lookup
  ON brand_company_relation(brand_id, role, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_outlet_company_lookup
  ON outlet_company_relation(outlet_id, role, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_outlet_brand_lookup
  ON outlet_brand_relation(outlet_id, brand_id, activity, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_claim_subject
  ON claim(subject_type, subject_id, predicate);
CREATE INDEX IF NOT EXISTS idx_change_event_status
  ON change_event(event_status, detected_at);
CREATE INDEX IF NOT EXISTS idx_event_brand_entity
  ON change_event_brand(brand_id, event_id);
CREATE INDEX IF NOT EXISTS idx_event_company_entity
  ON change_event_company(company_id, event_id);
CREATE INDEX IF NOT EXISTS idx_event_outlet_entity
  ON change_event_outlet(outlet_id, event_id);

-- La evidencia observada es append-only: las correcciones se añaden como nuevas
-- observaciones y afirmaciones, nunca se reescribe el registro original.
CREATE TRIGGER IF NOT EXISTS observation_no_update
BEFORE UPDATE ON observation
BEGIN
  SELECT RAISE(ABORT, 'observation is immutable; append a new observation');
END;

CREATE TRIGGER IF NOT EXISTS observation_no_delete
BEFORE DELETE ON observation
BEGIN
  SELECT RAISE(ABORT, 'observation is immutable');
END;
