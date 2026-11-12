# Registro abierto de fuentes y alcance de vigilancia del mercado motociclista

**Corte:** 12-11-2026  
**Ámbito:** España  
**Estado:** diseño de registro ampliado; la PR sigue en borrador y no se ha fusionado.

## Objetivo

El registro no representa un censo cerrado de marcas. Define fuentes para vigilar la red comercial conocida y mecanismos para descubrir fabricantes, marcas y establecimientos aún no registrados.

Se separan dos funciones:
- **Seguimiento primario:** fuentes oficiales de una marca para observar sus puntos de venta, posventa, operadores e implantación.
- **Descubrimiento de mercado:** fuentes que pueden revelar marcas, fabricantes, importadores, distribuidores o establecimientos nuevos. Pueden ser secundarias y generan pistas, no hechos históricos automáticos.

## Cobertura de acontecimientos

El registro declara cobertura abierta para:
- entrada y salida de fabricantes y marcas en España;
- apertura, cierre y traslado de puntos de venta;
- cambio de operador, importador o distribuidor;
- incorporación o retirada de marcas en establecimientos;
- cambios de alcance de venta y servicio posventa.

El catálogo inicial de tres marcas es solo un piloto. Se permiten marcas y fabricantes desconocidos y se mantiene una lista separada de fabricantes para no confundir marca comercial con entidad fabricante.

## Fuentes primarias iniciales

- Suzuki: https://moto.suzuki.es/concesionarios
- Zontes: https://zontesmotos.es/puntos-de-venta/
- ZXMOTO: https://zxmoto.es/puntos-de-venta/

## Fuentes de descubrimiento iniciales

| Fuente | URL | Utilidad | Limitación |
|---|---|---|---|
| ANESDOR - notas de prensa | https://www.anesdor.com/category/notas-de-prensa/ | Contexto sectorial, fabricantes e importadores, evolución del mercado | Representa a empresas asociadas; no es un censo completo ni prueba única de actividad individual |
| MOTOCICLISMO - industria | https://www.motociclismo.es/industria | Entradas de marcas, cambios de distribución y aperturas de concesionarios | Fuente periodística; contrastar con fuentes primarias |
| Posventa.com | https://www.posventa.com/ | Pista para movimientos empresariales y de distribución | Fuente candidata; sección y cobertura específica pendientes de evaluación |

Estas fuentes se registran con rol market_discovery, sin exigir una marca previamente conocida. Se clasifican como evidencia secundaria reputada y no sustituyen los directorios oficiales. La fuente de Posventa.com queda en estado not_assessed y con captura manual hasta completar su evaluación.

## Estados y regla probatoria

Los estados de marca distinguen anuncio, entrada reciente, actividad establecida, revisión, cese confirmado, inactividad no verificada y situación desconocida.

Un anuncio de lanzamiento no prueba actividad comercial efectiva. La ausencia de una marca en un directorio no prueba su retirada. Los errores de captura y los cambios de web son incidencias técnicas. Los candidatos se someten a revisión antes de actualizar el histórico.

## Próximos pasos

1. Evaluar cobertura, términos y estabilidad de cada fuente de descubrimiento.
2. Investigar carga dinámica de los localizadores Zontes y ZXMOTO.
3. Implementar capturas con fecha, URL final, estado HTTP, tipo de contenido, hash y evidencia.
4. Comparar capturas y generar candidatos, sin actualización automática del histórico.
5. Incorporar marcas y fabricantes nuevos conforme se descubran y verifiquen.

## Hallazgos iniciales de fuentes de establecimientos (12-11-2026)

La revisión de fuentes públicas ha identificado páginas de establecimientos que se presentan como representantes de marca:

- Zontes Murcia declara ser distribuidor y punto de venta oficial, con atención comercial y técnica, en Av. del Progreso, 232 B, Murcia: https://zontesmurcia.com/.
- Zontes BCN declara ser distribuidor y punto de venta oficial en Barcelona: https://zontesbarcelona.com/.
- ZXMOTO ASBA Barcelona se presenta como franquicia de la marca, identifica a Comercial Impala, S.A. y señala Carrer de Calvet 51: https://zxmotoasba.com/dealership.

Estas páginas se han incorporado como fuentes de descubrimiento de tipo company_page y fiabilidad primary_business. Son declaraciones de los propios establecimientos, no confirmaciones del fabricante ni eventos históricos aprobados. Deben contrastarse con el directorio oficial, el operador legal y la evidencia de actividad efectiva antes de crear o actualizar entidades del histórico.

La página oficial de ZXMOTO continúa mostrando «Próximas aperturas» en la vista textual del localizador, mientras existen páginas de establecimientos que declaran operar con la marca. Esta discrepancia justifica el seguimiento paralelo de directorios oficiales y evidencia empresarial secundaria; no se resolverá inventando una lista oficial.

## Captura periódica: primera implementación

El script capturar_fuentes_red_comercial.py realiza peticiones HTTPS de lectura con User-Agent identificable, timeout, límite de tamaño y comprobación de robots.txt. No ejecuta JavaScript ni automatiza formularios o geolocalización. Extrae texto visible, registra fecha UTC, URL solicitada/final, estado HTTP, tipo de contenido, SHA-256 y resultado técnico. Conserva el HTML original comprimido cuando el contenido es nuevo y mantiene un registro JSONL de observaciones.

El workflow .github/workflows/capturar-red-comercial.yml permite ejecución manual y programa barridos semanales los lunes a las 06:40 UTC. Tras la integración en la rama predeterminada, persistirá snapshots y metadatos mediante commits versionados. Las fuentes con captura manual quedan fuera de la ejecución automática.

La captura es una observación de fuente, no una extracción fiable de establecimientos. Los localizadores dinámicos pueden devolver una carcasa HTML sin sus registros; el resultado se marca y se mantiene como evidencia técnica, sin interpretar una lista vacía como cese. La comparación semántica y la generación de candidatos quedan para la siguiente fase.

## Ampliación de cobertura oficial (12-11-2026)

Se incorporan al registro tres marcas adicionales con fuentes primarias oficiales:

| Marca | Fuente oficial | Estado de captura inicial |
|---|---|---|
| Honda | https://www.honda.es/motorcycles/concesionarios.html | Directorio textual visible; validar integridad del listado al capturar |
| CFMOTO | https://cfmoto.es/concesionarios | Localizador con filtros; contenido parcialmente dinámico |
| Voge | https://vogespain.es/puntos-de-venta-espana/ | Localizador cartográfico; HTML estático sin establecimientos |

La selección se apoya en los directorios publicados por las propias marcas/importadores. Honda muestra nombres de concesionarios y localidades en el contenido indexado; CFMOTO publica su localizador oficial y parte de sus establecimientos; Voge identifica explícitamente sus puntos de venta y el responsable del canal en España. Las fuentes se registran como seguimiento primario, pero el estado de captura distingue entre contenido visible y localizadores dinámicos.

Referencias consultadas:
- Honda: https://www.honda.es/motorcycles/concesionarios.html
- CFMOTO: https://cfmoto.es/concesionarios
- Voge: https://vogespain.es/puntos-de-venta-espana/
- ANESDOR, asociados: https://www.anesdor.com/asociados/

La ampliación eleva el registro a seis marcas y doce fuentes. No equivale todavía a seis directorios operativos comparables: la captura automatizada y la validación de cobertura deben completarse antes de considerar estas redes como observables. No se extraen establecimientos ni se modifica el histórico de puntos de venta en esta fase.

