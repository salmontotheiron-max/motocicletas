# Auditoría de composición de motocicletas nuevas

Este módulo complementa el informe territorial de dispersión. Trabaja exclusivamente
con motocicletas nuevas MATRABA (`COD_TIPO` 50/51), operación 1 y
`IND_NUEVO_USADO=N`. La fecha de referencia es `FEC_MATRICULA`,
con exclusión de fechas posteriores a `FEC_PROCESO` y de trámites con
`FEC_TRAMITE` posterior a `FEC_PROCESO`.

## Dimensiones agregadas

Clase de matrícula, marca, modelo, procedencia ITV, tipo de propulsión,
cilindrada, naturaleza física/jurídica del titular, servicio, municipio del
domicilio registral e indicador de renting. La provincia de segmentación es
la provincia de matriculación. Los códigos de clase, procedencia, propulsión y
servicio se decodifican conforme al anexo I del diseño de registro MATRABA DGT.

## Cobertura y privacidad

Se publican el agregado nacional, Segovia y las provincias cuya proporción de
matriculaciones con domicilio registral en otra provincia supera el 20 %,
calculada sobre el CSV de cruce provincial.

Se mantiene el detalle mensual y se añade el acumulado enero-septiembre de 2026.
Los umbrales se aplican por separado a cada periodo: mínimo 10 unidades por
categoría y 20 para municipio. En el acumulado se suman primero los registros
y después se suprimen las categorías por debajo del umbral. Las categorías
pequeñas se agrupan bajo una categoría de supresión; nunca se publican sus
recuentos si el agregado sigue por debajo del umbral.

Antes de exportar, el procesador comprueba que cada dimensión concilia
exactamente con el denominador de su provincia y periodo. No se exportan
bastidores, nombres, identificadores personales, códigos postales ni domicilios
individuales. El municipio identifica el domicilio registral, no el lugar de
compra, entrega o concesionario.

Los códigos de servicio, renting y procedencia son descriptores administrativos:
por sí solos no acreditan uso comercial, flota, concesionario ni causa de la
discrepancia territorial.

## Ejecución

```bash
python auditar_composicion_motocicletas.py \
  --input-dir datos/matraba_mensual \
  --cross datos/matraba_mensual/resultados/matriculaciones_motocicletas_cruce_provincias_nuevas.csv \
  --inventory-file public/data/capturas_mensuales.json \
  --output datos/matraba_mensual/resultados/composicion_motocicletas_nuevas.csv
```
