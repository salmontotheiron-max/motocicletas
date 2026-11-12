# Registro inicial de fuentes oficiales de red comercial

**Corte de revisión:** 12-11-2026  
**Ámbito:** España  
**Estado:** primera versión operativa del registro; no es un censo de establecimientos.

## Objetivo y criterio

El registro identifica las páginas oficiales que se utilizarán como fuentes primarias para observar cambios en las redes de distribución, venta y posventa. Se conserva una fuente por marca y función documental; las URL no se consideran permanentes y deberán revisarse cuando la marca cambie su web o su operador en España.

Una fuente oficial puede contener un directorio completo, un localizador dinámico o únicamente una página de próximas aperturas. Estos estados no son equivalentes. Que una página no muestre establecimientos en el HTML o en una captura no demuestra que no existan puntos de venta.

## Fuentes registradas

| Marca | Fuente oficial | URL | Estado observado el 12-11-2026 |
|---|---|---|---|
| Suzuki | Directorio de concesionarios Suzuki Moto España | https://moto.suzuki.es/concesionarios | Contenido visible, agrupado por provincia; distingue exposición y taller. |
| Zontes | Puntos de venta Zontes España | https://zontesmotos.es/puntos-de-venta/ | Existe localizador; la página textual muestra buscador/mapa, sin lista completa extraíble en la vista consultada. |
| ZXMOTO | Puntos de venta ZXMOTO España | https://zxmoto.es/puntos-de-venta/ | Existe localizador; la página muestra «Próximas aperturas» y no expone todavía establecimientos identificables en la vista consultada. |

La página de Suzuki identifica expresamente su red oficial y publica establecimientos por provincia, con funciones de exposición y taller.

La página de Zontes está enlazada desde la web oficial como «Puntos de venta». El aviso legal identifica a TURBIMOT, S.L.U. como titular del sitio español.

La página de ZXMOTO está enlazada desde la web oficial como «Puntos de venta». Su aviso legal identifica a DESMOTRÓN, S.L.U. como titular del sitio español.

## Registro estructurado

El fichero fuentes_red_comercial.json es el registro maestro de fuentes y marcas. Cada fuente tiene identificador estable, marca asociada, editor, URL, tipo, clase de fiabilidad, alcance territorial, funciones cubiertas, modo de captura, estado de descubrimiento, fecha de verificación y periodicidad prevista.

La periodicidad inicial es semanal. Es una frecuencia de vigilancia, no una afirmación de que las marcas actualicen sus directorios semanalmente. Podrá ajustarse por fuente según su volatilidad y el coste/estabilidad de captura.

## Límites de esta primera versión

- Se han registrado inicialmente las tres marcas del piloto histórico: Suzuki, Zontes y ZXMOTO. La cobertura se ampliará marca a marca; no se presenta como un registro exhaustivo del mercado español.
- El registro no incorpora todavía concesionarios individuales extraídos de las páginas.
- Zontes y ZXMOTO utilizan páginas de localización que pueden cargar datos mediante JavaScript o servicios externos. Antes de automatizar extracción estructurada se debe identificar la fuente de datos y verificar que su acceso es público y estable.
- No se usarán directorios comunitarios, agregadores ni páginas de concesionarios como si fueran fuentes primarias oficiales. Podrán incorporarse después como evidencia secundaria separada.
- No se ejecutan aún capturas periódicas ni se generan candidatos. Esas son las fases siguientes.

## Regla de no inferencia

Una desaparición en un directorio, un error HTTP, un cambio de URL, una página vacía o una modificación del buscador se registra como incidencia/observación de la fuente. No se convierte automáticamente en dealer_removed, outlet_closed ni baja histórica. Para actualizar el histórico se exigirá revisar evidencia, distinguir venta de posventa y conservar fecha efectiva solo cuando esté respaldada.
