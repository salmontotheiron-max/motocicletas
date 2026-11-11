# Diseño del seguimiento histórico de la red comercial de motocicletas

**Fecha:** 11-11-2026  
**Estado:** propuesta de modelo v1, pendiente de validación  
**Issue:** [#18](https://github.com/salmontotheiron-max/motocicletas/issues/18)  
**Rama:** `diseno-seguimiento-historico-red-comercial`

## 1. Decisión de arquitectura

El sistema será un registro histórico de entidades, relaciones y evidencias. No será una hoja de cálculo que se sobrescribe en cada consulta ni un directorio que se presente automáticamente como vigente.

Se separan dos tiempos:

- **Tiempo de observación (sistema):** cuándo se consultó o recibió la evidencia.
- **Tiempo de vigencia (negocio):** desde cuándo y hasta cuándo se afirma que una relación o situación fue válida.

Esta separación permite responder dos preguntas distintas:

1. ¿Qué red creemos, con la evidencia disponible, que existía en una fecha?
2. ¿Qué información conocíamos en una fecha concreta sobre la red que existía entonces?

Las fechas de vigencia desconocidas se mantienen como desconocidas. La fecha de consulta nunca se utiliza como sustituto de la fecha de inicio de una relación.

## 2. Entidades e identificadores

Todas las entidades tendrán un identificador interno estable (UUID). El nombre comercial, la razón social, la dirección, el teléfono o la URL no serán claves primarias.

### 2.1 Marca (`brand`)

Representa la marca comercial de motocicletas (por ejemplo, Honda o Zontes). Campos mínimos:

- `brand_id`
- `canonical_name`
- `country_scope` (si una marca necesita distinguir ámbitos jurídicos o comerciales)
- `created_at`, `retired_at` (solo para gestión del registro; no equivalen a vigencia comercial)

Los cambios de denominación se guardan como alias con periodo y evidencia; no generan automáticamente una marca nueva.

### 2.2 Empresa (`company`)

Representa una persona jurídica o entidad empresarial que interviene en la cadena comercial:

- `company_id`
- `legal_name` (nullable si no se conoce)
- `country`
- `tax_identifier` solo si procede de fuente pública legítima y es necesario; no es requisito para crear el registro
- `created_at`

Una marca puede tener distintas empresas según periodo, territorio o función. Una misma empresa puede representar varias marcas. No se debe asumir que importador, distribuidor, filial, mayorista y concesionario son roles equivalentes.

### 2.3 Establecimiento (`outlet`)

Representa una ubicación física identificable:

- `outlet_id`
- `display_name`
- `address` y componentes geográficos normalizados cuando sean públicos
- `municipality_code`, `province_code`
- `latitude`, `longitude` (opcionales; con fuente)
- `created_at`

La entidad establecimiento identifica el lugar, no al operador. Si cambia el concesionario que trabaja en el mismo local, se mantiene el establecimiento y cambia la relación con la empresa. Si el negocio se traslada a otra ubicación física, se crea otro establecimiento y se registra el cierre/traslado del anterior.

### 2.4 Alias y nombres observados (`entity_alias`)

Conserva denominaciones alternativas, nombres comerciales, errores de escritura conocidos y cambios de nombre:

- `alias_id`, `entity_type`, `entity_id`
- `alias_text`, `normalized_alias`
- `valid_from`, `valid_to` (nullable)
- `source_observation_id`

La normalización (minúsculas, espacios, signos y formas jurídicas) sirve para proponer coincidencias, nunca para fusionar automáticamente entidades.

## 3. Relaciones comerciales

Las relaciones son registros propios, no atributos fijos de las marcas o empresas. Como mínimo:

### 3.1 Representación de marca (`brand_company_relation`)

- `relation_id`
- `brand_id`, `company_id`
- `role`: `importer`, `national_distributor`, `commercializer`, `official_agent`, `other`
- `territory`: ámbito al que se refiere (por defecto España; permitir ámbito autonómico/provincial si la evidencia lo exige)
- `valid_from`, `valid_to` (fechas de vigencia, ambas con semántica explícita; pueden ser desconocidas)
- `status`: `active_confirmed`, `historical_confirmed`, `pending`, `disputed`, `not_confirmed`
- `created_at`, `supersedes_relation_id` (nullable)

No se impone unicidad de una empresa por marca: puede haber coexistencia, distribución regional o transición. Las incompatibilidades se detectan como alertas de revisión, no se resuelven borrando registros.

### 3.2 Operación de establecimiento (`outlet_company_relation`)

- `relation_id`
- `outlet_id`, `company_id`
- `role`: `sales_dealer`, `service_center`, `parts_only`, `sales_and_service`, `agent`, `other`
- `valid_from`, `valid_to`
- `status` y `supersedes_relation_id`

### 3.3 Oferta de marca en establecimiento (`outlet_brand_relation`)

- `relation_id`
- `outlet_id`, `brand_id`
- `activity`: `new_sales`, `used_sales`, `service`, `parts`, `official_showroom`, `other`
- `valid_from`, `valid_to`, `status`

Esta relación permite que un establecimiento represente varias marcas y que la relación de venta sea distinta de la de posventa. La mera aparición de una marca en un taller no acredita que venda motocicletas nuevas.

## 4. Evidencias y observaciones

### 4.1 Fuente (`source`)

Catálogo de fuentes reutilizables:

- `source_id`
- `publisher` (marca, importador, concesionario, asociación, registro público, prensa, etc.)
- `source_type` (directorio oficial, página de empresa, comunicado, documento, llamada, etc.)
- `url` (nullable)
- `title`
- `reliability_class`: `primary_official`, `primary_business`, `secondary_reputable`, `community`, `unverified`
- `notes`

### 4.2 Observación (`observation`)

Cada consulta o captura es inmutable:

- `observation_id`
- `source_id`
- `observed_at` (timestamp con zona horaria)
- `capture_id` (identificador de la ejecución/lote)
- `captured_by` (proceso o revisión manual)
- `source_published_at` (nullable)
- `source_effective_date` (nullable)
- `content_hash` (si se conserva una copia o extracción)
- `evidence_excerpt` (fragmento breve, no una copia indiscriminada)
- `evidence_location` (URL, sección o referencia concreta)
- `notes`

Se conserva la fecha de consulta aunque el contenido no haya cambiado. Para páginas dinámicas, el registro de captura y su hash permiten distinguir una nueva comprobación de una modificación de contenido.

### 4.3 Afirmación respaldada (`claim`)

Una observación puede respaldar una o varias afirmaciones:

- `claim_id`
- `subject_type`, `subject_id`
- `predicate` (por ejemplo, `represents_brand`, `operates_outlet`, `offers_brand_sales`)
- `object_type`, `object_id`
- `asserted_role` o `asserted_value`
- `valid_from`, `valid_to` (nullable; tiempo de vigencia afirmado)
- `claim_status`: `supported`, `contradicted`, `uncertain`, `withdrawn`
- `observation_id`
- `confidence`: `high`, `medium`, `low`
- `review_status`: `unreviewed`, `accepted`, `rejected`, `needs_review`

Las afirmaciones no se eliminan al aparecer una fuente contradictoria. Se añade nueva evidencia y se marca el conflicto para revisión. La confianza es una valoración de la evidencia, no una probabilidad estadística.

## 5. Eventos de cambio

Tabla `change_event` para clasificar diferencias observadas:

- `event_id`
- `event_type`: `brand_importer_change`, `brand_entered_market`, `brand_distributor_appointed`, `dealer_added`, `dealer_removed`, `dealer_operator_change`, `outlet_closed`, `outlet_relocated`, `brand_added_to_outlet`, `brand_removed_from_outlet`, `service_scope_change`, `name_change`, `unverified_disappearance`, `other`
- `entity_ids` / relaciones afectadas
- `effective_date` (nullable)
- `detected_at`
- `event_status`: `candidate`, `confirmed`, `rejected`, `superseded`
- `supporting_observation_ids`
- `notes`

La asociación del evento con las entidades afectadas se mantiene mediante tablas tipadas con claves foráneas: `change_event_brand`, `change_event_company` y `change_event_outlet`. Un evento puede afectar a varias entidades de cada tipo; así se evita una relación polimórfica sin integridad referencial.

Una desaparición de un localizador web genera `unverified_disappearance` candidato; no una baja confirmada. Una baja solo se confirma con evidencia positiva suficiente (por ejemplo, comunicado de cierre, confirmación de la empresa o fuente oficial equivalente).

## 6. Reglas de identidad y deduplicación

1. **No usar nombres como identificadores.** Dos empresas con nombres parecidos no se fusionan solo por similitud textual.
2. **Empresa:** priorizar identificador registral público cuando sea necesario y verificable; en su ausencia, combinar razón social, país, dominio corporativo, dirección y evidencia documental. Mantener coincidencias como candidatas hasta revisión.
3. **Establecimiento:** combinar dirección normalizada, coordenadas, teléfono, dominio y nombre. Una dirección compartida no basta por sí sola: puede albergar varias empresas o actividades.
4. **Marca:** mantener un catálogo canónico; nombres de modelos, submarcas y distribuidores no se convierten en marcas sin criterio explícito.
5. **Alias:** conservar todos los nombres observados y sus periodos; nunca reemplazar el histórico por el nombre actual.
6. **Fusión de duplicados:** no borrar IDs. Marcar un ID como fusionado en otro, guardar motivo, fecha y evidencia, y mantener una tabla de redirección para reproducibilidad.
7. **Separación de funciones:** venta, taller, recambios, agente y showroom se registran como roles/actividades diferenciados.
8. **Cambios de operador:** si cambia la empresa en el mismo local, cerrar la relación anterior solo cuando la fecha esté respaldada y crear una nueva relación. No crear un nuevo establecimiento salvo cambio físico real.
9. **Datos desconocidos:** usar NULL/estado desconocido, nunca completar por intuición ni interpretar ausencia como cero o baja.
10. **Fuentes contradictorias:** conservar ambas afirmaciones y abrir revisión; no elegir automáticamente la más reciente si no es más autorizada o clara.

## 7. Reglas temporales

- Los intervalos de vigencia se interpretan como `[valid_from, valid_to)`: inicio incluido, fin excluido.
- `valid_to = NULL` significa que no se conoce un fin; no demuestra por sí solo que la relación siga activa hoy.
- `valid_from = NULL` significa que se desconoce el inicio; no se sustituye por `observed_at`.
- `observed_at` siempre debe existir y no puede retroceder por una corrección posterior.
- Una corrección se registra como nueva observación/afirmación que referencia la anterior; no se modifica silenciosamente la evidencia original.
- Para informar situación vigente, exigir evidencia reciente dentro de una ventana de revisión definida por tipo de fuente. La ventana se parametrizará y no se codificará como verdad universal.
- Si la fuente deja de estar disponible, se registra el fallo de consulta; no se genera una baja.

## 8. Resolución de conflictos y nivel de evidencia

Jerarquía orientativa, no automática:

1. Comunicación oficial fechada de la marca/importador o empresa afectada.
2. Directorio oficial de marca/importador con fecha de captura.
3. Página oficial del establecimiento/empresa.
4. Registro o documento público verificable pertinente.
5. Fuente sectorial o prensa reputada.
6. Directorios comerciales agregadores y redes sociales.
7. Foros, reseñas y menciones comunitarias.

Una fuente oficial puede estar desactualizada. Por ello, autoridad y actualidad se evalúan por separado. Para cambios relevantes (nuevo importador, baja de distribuidor o cierre) se procurará corroboración independiente o evidencia primaria explícita.

## 9. Capturas y comparación

Cada ciclo genera un `capture_id` con:

- fecha/hora de inicio y fin;
- marcas y fuentes consultadas;
- resultado por fuente: `success`, `changed`, `unchanged`, `not_found`, `unavailable`, `error`;
- hash y localizador de la evidencia conservada;
- número de afirmaciones nuevas, modificadas, contradictorias y pendientes.

El comparador no comparará solo listas de nombres. Comparará entidades y relaciones normalizadas, y clasificará:

- alta confirmada / alta candidata;
- baja confirmada / desaparición no confirmada;
- cambio de operador;
- cambio de representación/importador;
- cambio de actividad (venta frente a posventa);
- cambio de nombre o dirección;
- variación de fuente sin cambio comercial demostrado.

La ausencia en una captura solo será un indicio. Se requerirá regla específica por fuente y confirmación antes de cerrar una relación.

## 10. Consultas que debe soportar el modelo

- Red de una marca en España a fecha determinada.
- Empresa que representaba una marca en una fecha.
- Establecimientos de venta y posventa separados en una provincia a fecha determinada.
- Historial de operadores de un establecimiento.
- Historial de representación/importación de una marca.
- Cambios detectados entre dos capturas.
- Evidencia que sustenta cada relación y fecha.
- Qué se sabía en una fecha determinada (consulta bitemporal).

Toda salida debe mostrar fecha de corte, fecha de última observación, cobertura de fuentes y estado de confirmación. No usar la etiqueta «red completa» salvo que exista un universo verificable y una metodología de cobertura.

## 11. Integración con MATRABA

MATRABA seguirá siendo una fuente de matriculaciones/cambios administrativos, separada del registro comercial.

- No inferir concesionarios a partir del domicilio registral.
- No inferir ventas minoristas, entrega física o residencia del comprador.
- El cruce futuro será agregado y contextual (por ejemplo, evolución de marcas frente a actividad territorial), con definiciones y limitaciones explícitas.
- No almacenar ni exponer bastidores, nombres, domicilios particulares, códigos postales personales ni identificadores de titulares.

## 12. Implementación por etapas

**Etapa A — esquema y catálogo:** definir tablas, vocabularios controlados, claves e integridad referencial.  
**Etapa B — piloto de evidencia:** migrar una pequeña muestra del inventario preliminar, conservando su fecha y marcando como no confirmadas las vigencias desconocidas.  
**Etapa C — captura reproducible:** almacenar capturas y hashes de páginas/documentos públicos, con registro de errores y fuentes.  
**Etapa D — comparador:** generar eventos candidatos y cola de revisión humana.  
**Etapa E — consultas e informes:** reconstrucción temporal, evolución y alertas.

No iniciar un rastreo nacional ni publicar rankings de cobertura hasta superar las etapas A–D y validar el piloto.

## 13. Decisiones pendientes para la implementación

1. Persistencia inicial: SQLite para piloto local y portable, con diseño compatible con migración posterior a PostgreSQL.
2. Formato de captura: HTML/PDF cuando sea lícito y técnicamente viable; además, metadatos y hash. Si no puede conservarse el contenido, guardar URL, fecha, fragmento mínimo y motivo.
3. Ventanas de recencia: parametrizadas por tipo de fuente (no una caducidad única para todos).
4. Umbral de confirmación: definirlo con casos piloto; no automatizar altas/bajas críticas solo por cambios en páginas.
5. Alcance geográfico del piloto: España, con selección acotada de marcas y casos de cambio de comercializador.

## 14. Criterios de aceptación del diseño

- Es posible representar dos importadores sucesivos de una misma marca sin sobrescribir el anterior.
- Es posible distinguir la fecha de vigencia de la fecha en que se descubrió el cambio.
- Una fuente que desaparece no cierra automáticamente una relación.
- Venta y posventa pueden coexistir o diferir para el mismo establecimiento.
- Un cambio de operador no duplica el establecimiento físico.
- Los conflictos entre fuentes permanecen visibles y trazables.
- Cada evento puede vincularse a una o varias marcas, empresas y establecimientos con integridad referencial.
- Cada dato publicado puede remontarse a observaciones y fuentes concretas.
- Las consultas históricas explicitan incertidumbre y fecha de corte.

---
Este documento es una propuesta de diseño. No crea todavía tablas productivas, automatizaciones de captura ni un censo comercial vigente.
