# Auditoría de red comercial Honda en España — cinco provincias prioritarias

**Fecha de corte:** 12-11-2026  
**Ámbito:** Barcelona, Málaga, Cádiz, Alicante y Murcia  
**Fuente de datos:** extracción de las entradas Honda del snapshot agregado `establecimientos_prioridad_2026-11-12.json`.

## Resultado

Se individualizan **15 ubicaciones Honda** documentadas:

- **14 puntos de venta**.
- **1 punto de servicio** separado, no computado como venta.
- **5 provincias** con presencia documentada.
- **7 grupos operadores** identificados.

| Provincia | Ubicaciones |
|---|---:|
| Barcelona | 2 |
| Málaga | 5 |
| Cádiz | 3 |
| Alicante | 3 |
| Murcia | 2 |

## Criterio de inclusión

Se mantienen las entradas con ficha individual del directorio oficial Honda España. Cuando la dirección y la oferta comercial se documentaron mediante la página del operador, la inclusión se conserva únicamente si la entrada también figura en el índice oficial Honda.

Las ubicaciones de un mismo operador se mantienen como establecimientos distintos y comparten `operator_group_id`. La ubicación de taller se registra separadamente y no se suma a los puntos de venta.

## Alcance y limitaciones

- Este trabajo **separa** las entradas Honda del snapshot agregado; no representa una nueva consulta en tiempo real del localizador.
- El corte documental es 12-11-2026 y se limita a cinco provincias prioritarias.
- La inclusión en el directorio acredita la relación publicada por Honda en la fecha observada, no ventas efectivas ni actividad física observada.
- No se extrapola la cobertura al resto de España ni se interpreta la ausencia de una provincia como ausencia de red.
- El inventario no debe confundirse con un censo nacional exhaustivo.

## Artefacto

El detalle por establecimiento, URL de evidencia, rol, estado de verificación y grupo operador queda en `evidencias/red_comercial/establecimientos_honda_2026-11-12.json`.
