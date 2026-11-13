# Especificación del cuadro de mando de mercado

**Fecha de corte:** 13-11-2026  
**Ámbito:** mercado español de motocicletas. El dashboard distingue motocicletas (DGT 50/51) de ciclomotores (90/91) y otros vehículos ligeros.

## Objetivo

Publicar un entorno web responsive, sencillo y dinámico para analizar el mercado por marca, provincia, segmento y periodo.

Se elimina del alcance el informe narrativo por distribuidor o establecimiento. Los registros de red comercial y sus evidencias permanecen archivados, pero no condicionan el cierre del análisis de mercado.

## Indicadores requeridos

### Volumen de marca y modelo

- Matriculaciones nuevas por marca y periodo.
- Desglose por segmento DGT.
- Cuota de cada marca sobre el universo filtrado.
- Evolución mensual, ranking y exportación.
- Desglose por modelo dentro de marca, cuando el campo de modelo esté disponible y validado.

MATRABA registra matriculaciones, no ventas netas, facturación ni entregas comerciales. El dashboard etiquetará el indicador como matriculaciones nuevas observadas. No se denominará ventas sin una fuente comercial independiente.

### Nuevos: matriculación frente a circulación

La fuente actual permite cruzar la provincia de matriculación (COD_PROVINCIA_MAT) con la provincia del domicilio registral del vehículo (COD_PROVINCIA_VEH).

El domicilio registral se utilizará únicamente como proxy territorial de localización/circulación. No acredita el lugar de uso habitual.

Para cada provincia de matriculación se mostrarán:
- Registros con domicilio en la misma provincia.
- Registros con domicilio en otra provincia.
- Registros con domicilio conocido.
- Ratio de coincidencia = mismo domicilio / domicilios conocidos × 100.
- Ratio de dispersión = otro domicilio / domicilios conocidos × 100.

Los domicilios no informados se excluyen del denominador y se muestran como cobertura pendiente. Ambos ratios suman 100% cuando hay domicilios conocidos.

### Usados: provincia de venta frente a circulación

La serie de transferencias (CLAVE_TRAMITE=2) permite aproximar el volumen de cambios de titularidad. Sin embargo, el agregado publicado no proporciona una provincia de compraventa fiable y diferenciada de la provincia de matriculación histórica y del domicilio registral.

No se calculará todavía un ratio provincia de venta → provincia de circulación. Para habilitarlo se requiere validar en el diseño del microdato qué campo representa la provincia donde se tramita/realiza la transferencia y qué campo representa el domicilio registral posterior. No se reutilizará COD_PROVINCIA_MAT como provincia de venta sin prueba documental.

Hasta disponer de esa validación, el dashboard mostrará por separado el volumen de transferencias (no un censo exhaustivo de compraventas), la provincia de domicilio registral como proxy territorial y el estado del indicador venta→circulación como no calculable con la variable territorial validada actualmente.

## Segmentación

- DGT 50: motocicleta de dos ruedas sin sidecar.
- DGT 51: motocicleta con sidecar.
- DGT 90: ciclomotor de dos ruedas.
- DGT 91: ciclomotor de tres ruedas.
- Otros códigos se mantienen separados y no se incorporan automáticamente al mercado de motocicletas.

No mezclar motocicletas y ciclomotores en rankings sin etiqueta.

## Estado de datos a 13-11-2026

| Necesidad | Estado | Fuente / limitación |
|---|---|---|
| Marca × periodo × segmento | Disponible | marcas_candidatas_revision.json; nuevas matriculaciones observadas |
| Provincia × periodo × segmento (nuevos) | Disponible | matriculaciones_motocicletas_por_provincia.csv |
| Matriculación × domicilio registral (nuevos) | Disponible | matriculaciones_motocicletas_cruce_provincias_nuevas.csv |
| Ratio mismo domicilio / otro domicilio (nuevos) | Derivable | Cruce anterior |
| Transferencias de usados | Disponible parcialmente | Serie de operación y agregados por domicilio; no equivale a todas las ventas |
| Provincia de venta de usados | Pendiente de validación | No hay campo territorial semánticamente validado en el agregado actual |
| Modelo × marca × periodo | Pendiente de extracción | No publicado todavía en los agregados del dashboard |
| Marca × provincia | Pendiente de extracción | Requiere agregación de microdatos y validación de campos |

## Criterios de presentación web

- Diseño responsive para móvil y escritorio.
- Filtros de periodo, provincia y segmento cuando la granularidad lo permita.
- Tablas, rankings, gráficos compactos y exportación CSV.
- Mostrar cobertura temporal, universo, fuente y fecha de actualización.
- Distinguir cero observado de dato no disponible.
- Etiquetar los indicadores proxy y las limitaciones junto al resultado.
- No mostrar datos personales, domicilios privados, matrículas ni identificadores de vehículo.

## Trabajo priorizado para hoy

1. Integrar el ranking de matriculaciones nuevas por marca y segmento usando el agregado existente.
2. Mostrar el cruce provincial nuevo y los ratios basados en domicilio registral.
3. Mantener explícita la limitación del usado: transferencia no equivale automáticamente a venta localizada.
4. Definir la siguiente extracción de microdatos para marca/modelo y segmentación provincial, sin publicar resultados hasta validar los campos.
5. Mantener histórico y trazabilidad; no borrar auditorías de establecimientos ya realizadas.


## Desglose por modelo: extracción técnica incorporada

El diseño oficial de MATRABA identifica `MARCA_ITV` (campo 4, CHAR(30)) y `MODELO_ITV` (campo 5, CHAR(22)). El procesador mensual extrae ambos campos y genera `matriculaciones_marca_modelo_segmento.csv`, agregado por periodo, marca, modelo, código de tipo, tipo de registro y provincia de referencia. No se exportan bastidores ni identificadores de vehículo.

Tipos de registro separados:
- `matriculacion_nueva`: CLAVE_TRAMITE=1, IND_NUEVO_USADO=N; provincia de matriculación.
- `matriculacion_usada`: CLAVE_TRAMITE=1, IND_NUEVO_USADO=U; domicilio registral del vehículo.
- `transferencia`: CLAVE_TRAMITE=2; domicilio registral del vehículo.

El agregado de transferencias mide cambios de titularidad, no compraventas verificadas. Se mantiene separado del conjunto de matriculaciones y se contabiliza una sola vez. En el diseño oficial de transferencias se documentan COD_PROVINCIA_VEH (provincia donde está domiciliado el vehículo) y COD_PROVINCIA_MAT (provincia donde fue matriculado originalmente), pero no una variable que identifique la provincia física de venta o la ubicación del vendedor. Por tanto, la provincia de venta no puede derivarse de esos campos. El domicilio posterior puede usarse como proxy del destino registral, nunca como provincia de compraventa.

Fuentes de diseño:
- DGT, [Diseño de registro de Matriculaciones MATRABA](https://www.dgt.es/export/sites/web-DGT/.galleries/downloads/dgt-en-cifras/matraba/MATRICULACIONES_MATRABA.pdf).
- DGT, [Diseño de registro de Transferencias MATRABA](https://www.dgt.es/export/sites/web-DGT/.galleries/downloads/dgt-en-cifras/matraba/TRANSFERENCIAS_MATRABA.pdf).
- DGT, [Microdatos mensuales de Transferencias](https://www.dgt.es/menusecundario/dgt-en-cifras/dgt-en-cifras-resultados/dgt-en-cifras-detalle/Microdatos-de-Transferencias-de-Vehiculos-mensual/).

El dashboard separa por tanto el volumen de matriculaciones nuevas, matriculaciones usadas y transferencias; no suma los tres como si fueran ventas. Los modelos se presentan con la denominación literal declarada en MATRABA, sin fusionar variantes de escritura automáticamente.
