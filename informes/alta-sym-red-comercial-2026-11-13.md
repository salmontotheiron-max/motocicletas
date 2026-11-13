# Auditoría de red comercial SYM en España — cinco provincias prioritarias

**Fecha de corte:** 2026-11-12  
**Ámbito:** Barcelona, Málaga, Cádiz, Alicante, Murcia  
**Fuente de datos:** extracción de las entradas SYM del snapshot agregado `establecimientos_autodeclarados_2026-11-12.json`.

## Resultado

Se individualizan **3 ubicaciones SYM** documentadas:

- **3 puntos de venta**.
- **0 puntos de servicio independientes**.
- **3 ubicaciones de venta** cuyas páginas también publican servicio/taller en la misma sede.
- **1 provincia** con presencia documentada.
- **1 grupo operador:** Motos Bordoy, S.A.

| Provincia | Ubicaciones |
|---|---:|
| Barcelona | 3 |
| Málaga | 0 |
| Cádiz | 0 |
| Alicante | 0 |
| Murcia | 0 |

## Criterio de inclusión

Se conservan las tres sedes que Motos Bordoy publica como puntos de venta SYM: Balmes, Valencia y Comte d'Urgell, todas en Barcelona. Motos Bordoy declara ser importador de SYM en España y concesionario oficial; esta condición se registra como declaración del propio importador/operador y no como una verificación independiente adicional.

Las páginas del operador también publican servicios/taller. Se conserva esa información, pero no se generan establecimientos de servicio separados cuando la actividad se atribuye a la misma sede física.

## Localizador oficial y trazabilidad

El registro de fuentes del proyecto identifica el localizador oficial SYM España (`https://www.sym.com.es/concesionarios-scooter`) como fuente primaria de seguimiento. En la observación del 2026-11-12, el HTML público mostraba un buscador dinámico por ciudad o código postal y diferenciaba concesionarios oficiales de servicios oficiales, pero no exponía fichas de establecimientos en la extracción estática.

Por ello, los tres puntos se sustentan en las páginas públicas de Motos Bordoy: tiendas, servicios, oferta SYM y declaración de importador/concesionario. La limitación técnica del localizador no se interpreta como ausencia de red.

## Alcance y limitaciones

- Este trabajo **individualiza** las entradas del snapshot agregado; no representa una nueva consulta en tiempo real.
- El corte documental es 2026-11-12 y se limita a cinco provincias prioritarias.
- La ausencia de entradas en Málaga, Cádiz, Alicante y Murcia no demuestra ausencia de red SYM.
- La autorización oficial queda clasificada como declaración del importador/operador; no se presenta como contraste independiente.
- No se extrapola la cobertura al resto de España ni se afirma que el inventario sea exhaustivo.

## Artefacto

El detalle por establecimiento, URLs de evidencia y apoyo, rol, estados de verificación y grupo operador queda en `evidencias/red_comercial/establecimientos_sym_2026-11-12.json`.
