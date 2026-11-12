# Reconciliación del estado comercial de marcas con evidencia incorporada

**Fecha de revisión:** 2026-11-12  
**Ámbito territorial de las auditorías:** Barcelona, Málaga, Cádiz, Alicante y Murcia.

## Objetivo

Corregir el estado del catálogo maestro cuando ya existe evidencia comercial actual incorporada al repositorio. El estado `under_review` se reserva para marcas cuya actividad actual sigue pendiente de contraste; no debe mantenerse por inercia después de una auditoría documentada.

## Cambios

Se actualizan seis marcas a `established`:

| Marca | Evidencia incorporada | Cobertura documentada | Cautela |
|---|---|---|---|
| Honda | Directorio oficial Honda | 15 entradas: 14 de venta y una de servicio | La entrada de servicio no se cuenta como punto de venta |
| Yamaha | Localizador oficial Yamaha | 5 puntos de venta en Barcelona, Málaga, Cádiz y Alicante | No se ha acreditado una ficha individual de venta en Murcia; no implica ausencia |
| CFMOTO | Localizador público del distribuidor oficial Jets Marivent | 19 puntos de venta en las cinco provincias | El localizador no desglosa servicio por sede |
| KYMCO | Localizador y comunicaciones oficiales más evidencia individual de operadores | 8 puntos de venta en las cinco provincias; 3 con servicio publicado | Francisco Belmonte (Murcia) se conserva como autodeclaración, no como autorización confirmada independientemente |
| SYM | Declaración del importador español Motos Bordoy y páginas de tiendas/oferta | 3 puntos de venta en Barcelona, con servicio publicado | La declaración de importador/operador no se extrapola a otras provincias |
| Voge | Directorio publicado en vogospain.com | 3 puntos de venta declarados en Barcelona, Málaga y Cádiz | Correspondencia societaria del dominio y autorización individual no confirmadas independientemente |

El conjunto suma **56 entradas de establecimiento** en las seis marcas, de las que **55 tienen función de venta** y una corresponde exclusivamente a servicio. No se trata de 56 puntos necesariamente independientes entre marcas, ni de ventas realizadas, cuotas, ni de un censo nacional.

## Criterio de clasificación

- `established` indica evidencia suficiente de actividad comercial actual en España; no certifica que toda la red esté auditada ni que cada punto tenga autorización oficial confirmada.
- La presencia comercial y la autorización del fabricante/importador son dimensiones separadas.
- Una declaración del importador/operador o un directorio de operador puede acreditar oferta comercial, pero no debe elevarse automáticamente a autorización oficial independiente.
- Las funciones de venta y servicio se mantienen separadas. Un taller sin evidencia de venta no se cuenta como punto de venta.
- La ausencia de una ficha en una provincia o en una captura no acredita ausencia de actividad.
- Los recuentos son mínimos documentales de las cinco provincias prioritarias, no estimaciones de cobertura nacional.

## Ficheros probatorios existentes

- `evidencias/red_comercial/establecimientos_prioridad_2026-11-12.json` — Honda y Yamaha.
- `evidencias/red_comercial/establecimientos_cfmoto_2026-11-12.json` — CFMOTO.
- `evidencias/red_comercial/establecimientos_kymco_2026-11-12.json` — KYMCO.
- `evidencias/red_comercial/establecimientos_autodeclarados_2026-11-12.json` — Zontes, SYM y Voge.
- Informes de auditoría asociados en `informes/`.

## Resultado

El catálogo maestro queda alineado con la evidencia ya integrada. Las marcas sin evidencia comercial actual suficiente permanecen en `under_review`; no se modifica su estado por ausencia de resultados parciales.
