# Auditoría de red comercial Yamaha en España — cinco provincias prioritarias

**Fecha de corte:** 2026-11-12  
**Ámbito:** Barcelona, Málaga, Cádiz, Alicante, Murcia  
**Fuente de datos:** extracción de las entradas Yamaha del snapshot agregado `establecimientos_prioridad_2026-11-12.json`.

## Resultado

Se individualizan **5 ubicaciones Yamaha** documentadas:

- **5 puntos de venta**.
- **0 puntos de servicio independientes** en este snapshot.
- **2 ubicaciones de venta** cuyas fichas también mencionan taller o servicio en el mismo emplazamiento.
- **4 provincias** con presencia documentada.
- **5 grupos operadores** identificados.

| Provincia | Ubicaciones |
|---|---:|
| Barcelona | 2 |
| Málaga | 1 |
| Cádiz | 1 |
| Alicante | 1 |
| Murcia | 0 |

## Criterio de inclusión

Se conservan únicamente las fichas Yamaha identificadas en el snapshot agregado como establecimientos de la categoría **Motocicletas y Scooters**. El localizador oficial puede mezclar categorías de otros productos Yamaha; por ello, no se incorporan fichas de eBike ni de otras actividades.

Las ubicaciones de un mismo operador se mantienen como establecimientos distintos y comparten `operator_group_id`. Cuando una ficha de venta menciona taller, se conserva esa información en las notas, sin crear una segunda ubicación de servicio.

## Alcance y limitaciones

- Este trabajo **individualiza** las entradas del snapshot agregado; no representa una nueva consulta en tiempo real del localizador.
- El corte documental es 2026-11-12 y se limita a cinco provincias prioritarias.
- La ausencia de una entrada en Murcia no demuestra ausencia de red Yamaha.
- No se extrapola la cobertura al resto de España ni se afirma que el inventario sea exhaustivo.
- La inclusión en el directorio acredita la relación publicada por Yamaha en la fecha observada, no ventas efectivas ni actividad física observada.

## Artefacto

El detalle por establecimiento, URL de evidencia, rol, estado de verificación y grupo operador queda en `evidencias/red_comercial/establecimientos_yamaha_2026-11-12.json`.
