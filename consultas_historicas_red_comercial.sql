-- Consultas de referencia para el histórico de red comercial.
-- Ejecutar con parámetros nombrados desde SQLite.
-- Los intervalos de vigencia son semiabiertos [valid_from, valid_to).
-- Un extremo NULL es DESCONOCIDO, no un inicio remoto ni una vigencia indefinida.
-- Las consultas 2 y 3 solo devuelven intervalos acotados y confirmados.
-- No confundir fecha de publicación, fecha de observación y fecha efectiva.

-- 1. Cronología de eventos asociados a un establecimiento.
-- Parámetro: :outlet_id
-- Las listas se agregan por separado para evitar multiplicaciones entre marcas,
-- empresas y fuentes cuando un evento afecta a varias entidades.
SELECT
  e.event_id,
  e.event_type,
  e.effective_date,
  e.detected_at,
  e.event_status,
  e.notes,
  (
    SELECT group_concat(x.canonical_name, '; ')
    FROM (
      SELECT DISTINCT b.canonical_name
      FROM change_event_brand eb
      JOIN brand b ON b.brand_id = eb.brand_id
      WHERE eb.event_id = e.event_id
      ORDER BY b.canonical_name
    ) x
  ) AS brands,
  (
    SELECT group_concat(x.legal_name, '; ')
    FROM (
      SELECT DISTINCT c.legal_name
      FROM change_event_company ec
      JOIN company c ON c.company_id = ec.company_id
      WHERE ec.event_id = e.event_id AND c.legal_name IS NOT NULL
      ORDER BY c.legal_name
    ) x
  ) AS companies,
  (
    SELECT group_concat(x.display_name, '; ')
    FROM (
      SELECT DISTINCT o.display_name
      FROM change_event_outlet eo2
      JOIN outlet o ON o.outlet_id = eo2.outlet_id
      WHERE eo2.event_id = e.event_id
      ORDER BY o.display_name
    ) x
  ) AS outlets,
  (
    SELECT group_concat(x.source_label, '; ')
    FROM (
      SELECT DISTINCT s.publisher || ' — ' || coalesce(s.url, '') AS source_label
      FROM change_event_observation ceo
      JOIN observation obs ON obs.observation_id = ceo.observation_id
      JOIN source s ON s.source_id = obs.source_id
      WHERE ceo.event_id = e.event_id
      ORDER BY source_label
    ) x
  ) AS sources
FROM change_event e
JOIN change_event_outlet eo ON eo.event_id = e.event_id
WHERE eo.outlet_id = :outlet_id
ORDER BY
  CASE WHEN e.effective_date IS NULL THEN 1 ELSE 0 END,
  e.effective_date,
  e.detected_at;

-- 2. Marcas asociadas a un establecimiento en una fecha.
-- Parámetros: :outlet_id, :as_of_date
SELECT
  o.display_name AS outlet,
  b.canonical_name AS brand,
  r.activity,
  r.valid_from,
  r.valid_to,
  r.status
FROM outlet_brand_relation r
JOIN outlet o ON o.outlet_id = r.outlet_id
JOIN brand b ON b.brand_id = r.brand_id
WHERE r.outlet_id = :outlet_id
  AND r.valid_from IS NOT NULL
  AND r.valid_from <= :as_of_date
  AND r.valid_to IS NOT NULL
  AND :as_of_date < r.valid_to
  AND r.status IN ('active_confirmed','historical_confirmed')
ORDER BY b.canonical_name, r.activity;

-- 3. Importador/distribuidor de una marca en una fecha.
-- Parámetros: :brand_id, :as_of_date
SELECT
  b.canonical_name AS brand,
  c.legal_name AS company,
  r.role,
  r.territory,
  r.valid_from,
  r.valid_to,
  r.status
FROM brand_company_relation r
JOIN brand b ON b.brand_id = r.brand_id
JOIN company c ON c.company_id = r.company_id
WHERE r.brand_id = :brand_id
  AND r.valid_from IS NOT NULL
  AND r.valid_from <= :as_of_date
  AND r.valid_to IS NOT NULL
  AND :as_of_date < r.valid_to
  AND r.status IN ('active_confirmed','historical_confirmed')
ORDER BY r.role, c.legal_name;

-- 4. Eventos con fecha efectiva conocida dentro de un intervalo.
-- Parámetros: :date_from, :date_to (fin exclusivo)
SELECT event_id, event_type, effective_date, event_status, notes
FROM change_event
WHERE effective_date >= :date_from
  AND effective_date < :date_to
ORDER BY effective_date, event_type;

-- 5. Eventos sin fecha efectiva conocida: no deben desaparecer de los informes.
SELECT event_id, event_type, detected_at, event_status, notes
FROM change_event
WHERE effective_date IS NULL
ORDER BY detected_at, event_type;

-- 6. Evidencias de un evento, conservando fuente y fecha de observación.
-- Parámetro: :event_id
SELECT
  e.event_id,
  s.publisher,
  s.title,
  s.url,
  s.reliability_class,
  obs.source_published_at,
  obs.source_effective_date,
  obs.observed_at,
  obs.evidence_excerpt,
  obs.notes
FROM change_event e
JOIN change_event_observation ceo ON ceo.event_id = e.event_id
JOIN observation obs ON obs.observation_id = ceo.observation_id
JOIN source s ON s.source_id = obs.source_id
WHERE e.event_id = :event_id
ORDER BY obs.observed_at, s.publisher;

-- 7. Relaciones que no pueden afirmarse vigentes en una fecha.
-- Distingue extremos desconocidos, intervalos fuera de fecha y estados no confirmados.
-- Parámetros: :outlet_id, :as_of_date
SELECT
  o.display_name AS outlet,
  b.canonical_name AS brand,
  r.activity,
  r.valid_from,
  r.valid_to,
  r.status,
  CASE
    WHEN r.valid_from IS NULL AND r.valid_to IS NULL THEN 'ambos_extremos_desconocidos'
    WHEN r.valid_from IS NULL THEN 'inicio_desconocido'
    WHEN r.valid_from > :as_of_date THEN 'inicio_posterior_a_fecha_consultada'
    WHEN r.valid_to IS NOT NULL AND :as_of_date >= r.valid_to THEN 'vigencia_terminada_antes_de_fecha'
    WHEN r.valid_to IS NULL THEN 'fin_desconocido'
    WHEN r.status NOT IN ('active_confirmed','historical_confirmed') THEN 'estado_no_confirmado'
    ELSE 'requiere_revision'
  END AS motivo_indeterminacion
FROM outlet_brand_relation r
JOIN outlet o ON o.outlet_id = r.outlet_id
JOIN brand b ON b.brand_id = r.brand_id
WHERE r.outlet_id = :outlet_id
  AND (
    r.valid_from IS NULL
    OR r.valid_to IS NULL
    OR r.status NOT IN ('active_confirmed','historical_confirmed')
    OR r.valid_from > :as_of_date
    OR :as_of_date >= r.valid_to
  )
ORDER BY b.canonical_name, r.activity;

-- 8. Relaciones marca-empresa que no pueden afirmarse vigentes en una fecha.
-- Parámetros: :brand_id, :as_of_date
SELECT
  b.canonical_name AS brand,
  c.legal_name AS company,
  r.role,
  r.territory,
  r.valid_from,
  r.valid_to,
  r.status,
  CASE
    WHEN r.valid_from IS NULL AND r.valid_to IS NULL THEN 'ambos_extremos_desconocidos'
    WHEN r.valid_from IS NULL THEN 'inicio_desconocido'
    WHEN r.valid_to IS NULL THEN 'fin_desconocido'
    WHEN r.valid_from > :as_of_date THEN 'inicio_posterior_a_fecha_consultada'
    WHEN :as_of_date >= r.valid_to THEN 'vigencia_terminada_antes_de_fecha'
    WHEN r.status NOT IN ('active_confirmed','historical_confirmed') THEN 'estado_no_confirmado'
    ELSE 'requiere_revision'
  END AS motivo_indeterminacion
FROM brand_company_relation r
JOIN brand b ON b.brand_id = r.brand_id
JOIN company c ON c.company_id = r.company_id
WHERE r.brand_id = :brand_id
  AND (
    r.valid_from IS NULL
    OR r.valid_to IS NULL
    OR r.status NOT IN ('active_confirmed','historical_confirmed')
    OR r.valid_from > :as_of_date
    OR :as_of_date >= r.valid_to
  )
ORDER BY r.role, c.legal_name;
