-- Piloto documental de eventos de red comercial.
-- Ejecutar después de esquema_red_comercial.sql.
-- Datos idempotentes: INSERT OR IGNORE.
-- Las fechas de publicación no se convierten automáticamente en fechas de vigencia.
-- No se inventan operadores societarios cuando las fuentes no los identifican.

INSERT OR IGNORE INTO brand
  (brand_id, canonical_name, country_scope, created_at)
VALUES
  ('brand-suzuki-es','Suzuki','ES','2026-11-11'),
  ('brand-zontes-es','Zontes','ES','2026-11-11'),
  ('brand-zxmoto-es','ZXMOTO','ES','2026-11-11');

INSERT OR IGNORE INTO company
  (company_id, legal_name, country, created_at)
VALUES
  ('company-desmotron-es','Desmotrón S.L.U.','ES','2026-11-11');

INSERT OR IGNORE INTO outlet
  (outlet_id,display_name,address,municipality_code,province_code,created_at)
VALUES
  ('outlet-motos-copa-valladolid','Motos Copa',NULL,NULL,'47','2026-11-11'),
  ('outlet-zontes-centro-madrid','Zontes Centro Madrid','Plaza Juan de Zorrilla, 4, Madrid',NULL,'28','2026-11-11'),
  ('outlet-zontes-posventa-madrid','Servicio oficial Zontes Madrid','Calle García de Paredes, 3, Madrid',NULL,'28','2026-11-11');

INSERT OR IGNORE INTO entity_alias
  (alias_id,entity_type,entity_id,alias_text,normalized_alias,valid_from,valid_to)
VALUES
  ('alias-motorcity-zontes-madrid','outlet','outlet-zontes-centro-madrid',
   'Motorcity Madrid','motorcity madrid',NULL,'2026-06-10');

INSERT OR IGNORE INTO source
  (source_id,publisher,source_type,url,title,reliability_class,notes)
VALUES
  ('src-motos-copa-elespanol','EL ESPAÑOL','press',
   'https://www.elespanol.com/castilla-y-leon/region/valladolid/20250930/cierre-sorpresa-concesionario-motos-valladolid-afectados-vigilan-evitar-lleve/1003743947325_0.html',
   'Cierre de Motos Copa en Valladolid','secondary_reputable',
   'Noticia sobre cierre; la fecha efectiva se conserva como aproximada.'),
  ('src-motos-copa-suzuki','El Motoblog','press',
   'https://www.elmotoblog.es/donde-comprar-una-suzuki-en-valladolid-en-2026/',
   'Situación de Suzuki en Valladolid en 2026','secondary_reputable',
   'Referencia posterior sobre la relación comercial previa; no fija fecha exacta de terminación.'),
  ('src-zontes-motociclismo','Motociclismo','press',
   'https://www.motociclismo.es/noticias/zontes-inaugura-nuevo-concesionario-en-pleno-centro-madrid_328379_102.html',
   'Inauguración de Zontes Centro Madrid','secondary_reputable',
   'Apertura anunciada el 10-06-2026; identifica ubicación del punto de venta.'),
  ('src-zontes-tumoto','Revista Tu Moto','press',
   'https://revistatumoto.com/zontes-centro-madrid/',
   'Zontes Centro Madrid','secondary_reputable',
   'Referencia sectorial complementaria sobre el centro y su servicio.'),
  ('src-zxmoto-soymotero','SoyMotero','press',
   'https://soymotero.net/noticia/zxmoto-inicia-operaciones-en-espana/',
   'ZXMOTO inicia operaciones en España','secondary_reputable',
   'Anuncio publicado el 26-02-2026 sobre inicio de operaciones y distribución.'),
  ('src-zxmoto-legal','ZXMOTO España','company_page',
   'https://zxmoto.es/aviso-legal/',
   'Aviso legal ZXMOTO España','primary_business',
   'Identifica a Desmotrón S.L.U. como titular del sitio; por sí solo no acredita el contrato de distribución.');

INSERT OR IGNORE INTO observation
  (observation_id,source_id,observed_at,source_published_at,source_effective_date,
   evidence_excerpt,evidence_location,notes)
VALUES
  ('obs-motos-copa-close','src-motos-copa-elespanol',
   '2026-11-11T18:00:00+01:00','2025-09-30',NULL,
   'La noticia informa del cierre del concesionario de Valladolid.',
   'Artículo completo',
   'Fecha efectiva aproximada: finales de septiembre de 2025; no fijar el 30-09 como fecha contractual exacta.'),
  ('obs-motos-copa-suzuki','src-motos-copa-suzuki',
   '2026-11-11T18:00:00+01:00','2026-01-25',NULL,
   'La publicación indica que Suzuki había dejado de considerar a Motos Copa proveedor oficial meses antes.',
   'Artículo completo',
   'No se conoce la fecha exacta de fin de representación.'),
  ('obs-zontes-opening','src-zontes-motociclismo',
   '2026-11-11T18:00:00+01:00','2026-06-15','2026-06-10',
   'Inauguración de Zontes Centro Madrid el 10 de junio de 2026 en Plaza Juan de Zorrilla, 4.',
   'Artículo completo',
   'No identifica de forma suficiente la continuidad societaria del operador anterior Motorcity.'),
  ('obs-zontes-service','src-zontes-tumoto',
   '2026-11-11T18:00:00+01:00',NULL,NULL,
   'Referencia a servicio oficial Zontes en García de Paredes, 3.',
   'Artículo completo',
   'Posventa separada de la ubicación de venta/exposición; verificar vigencia en capturas posteriores.'),
  ('obs-zxmoto-distributor','src-zxmoto-soymotero',
   '2026-11-11T18:00:00+01:00','2026-02-26',NULL,
   'Anuncio de inicio de operaciones de ZXMOTO en España con Desmotrón como distribuidor exclusivo.',
   'Artículo completo',
   'La fecha efectiva contractual del nombramiento no se deduce automáticamente de la fecha de publicación.'),
  ('obs-zxmoto-legal','src-zxmoto-legal',
   '2026-11-11T18:00:00+01:00',NULL,NULL,
   'El aviso legal identifica a Desmotrón S.L.U. como titular del sitio español.',
   'Aviso legal',
   'Corroboración de identidad del titular del sitio; no es prueba autónoma del alcance de distribución.');

INSERT OR IGNORE INTO outlet_brand_relation
  (relation_id,outlet_id,brand_id,activity,valid_from,valid_to,status,created_at)
VALUES
  ('rel-zontes-sales-madrid','outlet-zontes-centro-madrid','brand-zontes-es',
   'new_sales','2026-06-10',NULL,'active_confirmed','2026-11-11'),
  ('rel-zontes-service-madrid','outlet-zontes-posventa-madrid','brand-zontes-es',
   'service',NULL,NULL,'pending','2026-11-11');

INSERT OR IGNORE INTO brand_company_relation
  (relation_id,brand_id,company_id,role,territory,valid_from,valid_to,status,created_at)
VALUES
  ('rel-zxmoto-desmotron','brand-zxmoto-es','company-desmotron-es',
   'national_distributor','ES',NULL,NULL,'active_confirmed','2026-11-11');

INSERT OR IGNORE INTO claim
  (claim_id,subject_type,subject_id,predicate,object_type,object_id,asserted_value,
   valid_from,valid_to,claim_status,observation_id,confidence,review_status)
VALUES
  ('claim-motos-copa-closed','outlet','outlet-motos-copa-valladolid',
   'outlet_closed',NULL,NULL,'Cierre del establecimiento; fecha aproximada: finales de septiembre de 2025',
   NULL,NULL,'supported','obs-motos-copa-close','medium','accepted'),
  ('claim-motos-copa-suzuki-ended','outlet','outlet-motos-copa-valladolid',
   'brand_representation_ended','brand','brand-suzuki-es',
   'La relación oficial con Suzuki habría terminado antes del cierre; fecha exacta desconocida',
   NULL,NULL,'uncertain','obs-motos-copa-suzuki','low','needs_review'),
  ('claim-zontes-madrid-opened','outlet','outlet-zontes-centro-madrid',
   'offers_brand_sales','brand','brand-zontes-es','Apertura/inauguración de punto de venta',
   '2026-06-10',NULL,'supported','obs-zontes-opening','medium','accepted'),
  ('claim-zontes-service-madrid','outlet','outlet-zontes-posventa-madrid',
   'offers_brand_service','brand','brand-zontes-es','Servicio oficial mencionado en fuente sectorial',
   NULL,NULL,'uncertain','obs-zontes-service','low','needs_review'),
  ('claim-zxmoto-desmotron','brand','brand-zxmoto-es',
   'national_distributor','company','company-desmotron-es',
   'Desmotrón anunciado como distribuidor exclusivo en España',
   NULL,NULL,'supported','obs-zxmoto-distributor','medium','accepted');

INSERT OR IGNORE INTO change_event
  (event_id,event_type,effective_date,detected_at,event_status,notes)
VALUES
  ('event-motos-copa-close','outlet_closed',NULL,'2026-11-11T18:00:00+01:00',
   'confirmed','Cierre respaldado por prensa; fecha efectiva aproximada, no normalizada como día exacto.'),
  ('event-motos-copa-suzuki-ended','brand_removed_from_outlet',NULL,'2026-11-11T18:00:00+01:00',
   'candidate','La pérdida de condición de proveedor oficial se sitúa antes del cierre; fecha exacta pendiente.'),
  ('event-zontes-madrid-added','brand_added_to_outlet','2026-06-10','2026-11-11T18:00:00+01:00',
   'confirmed','Nueva implantación Zontes en el local anteriormente ocupado por Motorcity; operador societario no identificado.'),
  ('event-zxmoto-market-entry','brand_entered_market',NULL,'2026-11-11T18:00:00+01:00',
   'confirmed','Entrada anunciada el 26-02-2026; fecha efectiva de inicio comercial no precisada.'),
  ('event-zxmoto-distributor','brand_distributor_appointed',NULL,'2026-11-11T18:00:00+01:00',
   'confirmed','Nombramiento anunciado el 26-02-2026; vigencia contractual exacta no conocida.');

INSERT OR IGNORE INTO change_event_observation VALUES
  ('event-motos-copa-close','obs-motos-copa-close'),
  ('event-motos-copa-suzuki-ended','obs-motos-copa-suzuki'),
  ('event-zontes-madrid-added','obs-zontes-opening'),
  ('event-zontes-madrid-added','obs-zontes-service'),
  ('event-zxmoto-market-entry','obs-zxmoto-distributor'),
  ('event-zxmoto-distributor','obs-zxmoto-distributor'),
  ('event-zxmoto-distributor','obs-zxmoto-legal');

INSERT OR IGNORE INTO change_event_brand VALUES
  ('event-motos-copa-close','brand-suzuki-es','marca asociada en el expediente'),
  ('event-motos-copa-suzuki-ended','brand-suzuki-es','marca cuya representación habría terminado'),
  ('event-zontes-madrid-added','brand-zontes-es','marca incorporada al establecimiento'),
  ('event-zxmoto-market-entry','brand-zxmoto-es','marca que inicia operaciones en España'),
  ('event-zxmoto-distributor','brand-zxmoto-es','marca objeto de distribución');

INSERT OR IGNORE INTO change_event_company VALUES
  ('event-zxmoto-distributor','company-desmotron-es','distribuidor nacional anunciado');

INSERT OR IGNORE INTO change_event_outlet VALUES
  ('event-motos-copa-close','outlet-motos-copa-valladolid','establecimiento cerrado'),
  ('event-motos-copa-suzuki-ended','outlet-motos-copa-valladolid','establecimiento afectado'),
  ('event-zontes-madrid-added','outlet-zontes-centro-madrid','local de venta/exposición'),
  ('event-zontes-madrid-added','outlet-zontes-posventa-madrid','ubicación de posventa mencionada');

-- No se crean registros nominales de nuevos concesionarios ZXMOTO sin fuentes
-- individualizadas. La señal general comunicada por el usuario queda en el informe
-- como pista de investigación, no como censo ni como altas verificadas.
