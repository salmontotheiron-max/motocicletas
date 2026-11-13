# Reconciliación transversal de cobertura comercial — 51 marcas

**Fecha de revisión:** 13-11-2026  
**Repositorio:** `fuentes_red_comercial.json` y artefactos de `evidencias/red_comercial/`  
**Ámbito de auditoría territorial:** Barcelona, Málaga, Cádiz, Alicante y Murcia.

## 1. Resultado ejecutivo

El registro maestro contiene 51 marcas y las 51 figuran actualmente como `established`. Esta etiqueta acredita evidencia de actividad comercial actual en España; no equivale a una auditoría exhaustiva de la red, ni confirma la autorización individual de cada establecimiento.

El registro contiene 382 fuentes con identificadores únicos: 125 de seguimiento primario y 257 de descubrimiento. Las 51 marcas tienen al menos una fuente primaria. No se detectaron identificadores duplicados, fuentes de seguimiento primario asociadas a marcas inexistentes ni fuentes `market_discovery` con `brand_id` distinto de `null`.

La auditoría documental cuenta con artefactos de establecimientos para las 51 marcas. Parte de ellos se conserva en ficheros agregados compartidos, por lo que el número de ficheros no equivale al número de marcas ni al número de puntos de venta. La presencia de un fichero tampoco significa que todos sus candidatos estén confirmados o que el inventario sea exhaustivo.

## 2. Registro de fuentes

| Indicador | Resultado |
|---|---:|
| Marcas en el catálogo maestro | 51 |
| Marcas con estado `established` | 51 |
| Fuentes totales | 382 |
| Fuentes `primary_monitoring` | 125 |
| Fuentes `market_discovery` | 257 |
| IDs de fuente duplicados | 0 |
| Marcas sin fuente primaria | 0 |
| Fuentes de descubrimiento con `brand_id` no nulo | 0 |
| Fuentes primarias con `brand_id` desconocido | 0 |

La clasificación `established` debe leerse como presencia comercial actual acreditada. No debe convertirse en “red oficial verificada” sin comprobar por separado la relación fabricante/importador–operador de cada punto.

## 3. Inventario documental

El árbol del repositorio contiene 50 ficheros JSON con prefijo `establecimientos_`. Incluye snapshots individuales, ficheros agregados para Honda/Yamaha y Zontes/SYM/Voge, y ficheros auxiliares de Suzuki. La correspondencia entre snapshots y marcas se ha comprobado por identificador y denominación, evitando sumar ficheros como si fueran establecimientos.

Los snapshots mantienen criterios heterogéneos según la evidencia disponible: directorio oficial, ficha individual de fabricante, catálogo/oferta del operador, autodeclaración de oficialidad, servicio/taller separado y candidatos secundarios no contabilizados. No se deben sumar sus recuentos sin normalizar primero el rol de cada registro y deduplicar ubicaciones compartidas entre marcas y grupos de concesionarios.

## 4. Desfase de la matriz técnica anterior

La matriz `auditoria_cobertura.json/csv` se generó el 12-11-2026, antes de la última reconciliación del registro maestro. Por ello conservaba estados `under_review` y filas sin fuente primaria para marcas que ya tenían fuentes y snapshots incorporados. El problema era de sincronización del artefacto, no evidencia de que esas marcas carecieran de red.

Se regenera la matriz desde el registro actual y la última captura disponible. También se corrige la selección de fuente representativa: se prioriza un `official_directory` y, entre ellos, un localizador/directorio, en lugar de seleccionar una nota de prensa o página corporativa por orden alfabético. Una marca con evidencia primaria pero sin directorio oficial queda `pending` con una causa específica.

## 5. Estado de captura técnica

La última captura registrada es del **12-11-2026 11:03:44 UTC** y contiene ocho registros. Tres corresponden a fuentes `primary_monitoring`: Suzuki, Zontes y ZXMOTO. Dos se capturaron correctamente (Suzuki y ZXMOTO) y una fue bloqueada por la política `robots.txt` (Zontes). Los otros cinco registros corresponden a fuentes de descubrimiento y páginas de operadores.

De las 125 fuentes primarias del registro, 83 están configuradas como `http_html`, 16 como `manual`, 21 como `browser_required` y 5 como `dynamic_unextractable`. La última captura no representa una ejecución completa de las 83 fuentes HTTP: solo incluye tres fuentes primarias. La matriz técnica resultante clasifica dos marcas como `partial` y 49 como `pending`. Esto **no** significa que 49 marcas carezcan de establecimientos: significa que el directorio oficial representativo no tiene una captura técnica evaluable en ese lote.

## 6. Cambios incorporados

- Sincroniza `market_status` con el catálogo maestro actual.
- Añade fecha de revisión del registro y fecha de la captura usada.
- Expone el número de fuentes primarias por marca y de directorios oficiales.
- Prioriza directorios/localizadores oficiales sobre notas y páginas corporativas.
- Reconoce `dynamic_unextractable` como estado dinámico cuando la fuente se ha capturado.
- Distingue “sin directorio oficial registrado” de “directorio no capturado”.
- Mantiene `verified_outlets_count: null`: esta matriz no calcula establecimientos.
- Amplía las pruebas para cubrir selección de fuente, estados dinámicos y ausencia de directorio.

## 7. Pendientes de siguiente fase

1. Extender el capturador a las fuentes primarias `http_html` autorizadas, respetando `robots.txt`, límites de tamaño y controles de redirección.
2. Mantener la captura manual y de navegador como tareas explícitas, sin convertir fallos de extracción en ausencias.
3. Construir un índice normalizado de establecimientos a partir de snapshots, con identificadores estables, dirección normalizada y operador/grupo.
4. Deduplicar puntos compartidos por varias marcas y separar venta, exposición, taller y servicio.
5. Revisar por separado las autorizaciones oficiales individuales y las autodeclaraciones de los operadores.

## Limitaciones

Esta reconciliación es estructural y documental. No certifica actividad física observada, ventas, cuota, inventario disponible, cobertura nacional completa ni contratos de distribución. Los recuentos por provincia siguen siendo mínimos documentales de las cinco provincias prioritarias.
