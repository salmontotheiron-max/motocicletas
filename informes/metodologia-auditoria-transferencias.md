# Metodología de auditoría de transferencias MATRABA

## Objetivo

La salida `auditoria_campos_transferencias.csv` verifica la distribución de los campos semánticos directamente sobre cada TXT original de transferencias, antes de construir los agregados por marca, modelo y provincia.

La auditoría incluye los valores observados de:

- `COD_TIPO`: clase administrativa del vehículo.
- `COD_PROVINCIA_VEH`: provincia asociada al domicilio registral del vehículo.
- `COD_PROVINCIA_MAT`: provincia de matriculación.
- `CLAVE_TRAMITE`: código del trámite.
- `IND_NUEVO_USADO`: condición nuevo/usado del vehículo en el contexto de su matriculación; no identifica por sí sola el carácter comercial de una transferencia.
- `COD_POSESION`: clasificación declarada de la operación; `V` se etiqueta como venta y `S` como subasta. Los valores vacíos o distintos se mantienen sin clasificar.

## Ámbitos del recuento

Para cada campo se publican dos ámbitos:

- `todos_los_registros`: todos los registros del TXT mensual.
- `solo_CLAVE_TRAMITE_2`: registros cuyo trámite es una transferencia.

El CSV conserva periodo, nombre del snapshot, campo, ámbito, valor y recuento. No incluye matrículas, bastidores, titulares, domicilios individuales ni otros identificadores personales.

## Interpretación y límites

1. El número de registros con `COD_POSESION=V` es el número de transferencias con esa clasificación declarada en el fichero; no debe confundirse con el total de compraventas del mercado.
2. Las transferencias con código vacío o no catalogado no se imputan a ventas.
3. `IND_NUEVO_USADO` no se utiliza para decidir si la transferencia es una venta de vehículo nuevo o usado.
4. `COD_PROVINCIA_VEH` describe el domicilio registral, no el lugar físico de venta, entrega o circulación observada.
5. `COD_PROVINCIA_MAT` describe la provincia de matriculación; no debe presentarse como provincia de venta.
6. Las diferencias territoriales conocidas por matriculaciones de flotas en Segovia con destino a otras provincias se consideran un flujo operativo ya comprobado, no una anomalía automática.

La auditoría de distribución de campos confirma qué valores aparecen en los TXT y permite detectar desplazamientos o anomalías de extracción. No acredita por sí sola que todas las operaciones clasificadas como venta sean ventas minoristas, ni permite estimar ventas no declaradas como tales.
