# Auditoría de composición de motocicletas nuevas

Este módulo complementa el informe territorial de dispersión. Trabaja exclusivamente
con motocicletas nuevas MATRABA (`COD_TIPO` 50/51), operación 1 y
`IND_NUEVO_USADO=N`. La fecha de referencia es `FEC_MATRICULA`,
con exclusión de fechas posteriores a `FEC_PROCESO`.

## Dimensiones agregadas

Clase de matrícula, marca, modelo, procedencia ITV, cilindrada, naturaleza
física/jurídica del titular, servicio, municipio del domicilio registral e
indicador de renting. La provincia de segmentación es la de matriculación.

Se publican el agregado nacional, Segovia y las provincias cuya proporción de
matriculaciones con domicilio registral en otra provincia supera el 20 %,
calculada sobre el CSV de cruce provincial. El umbral se aplica a los datos
acumulados por periodo y provincia: mínimo 10 unidades por categoría y 20 para
municipio. Las categorías por debajo del umbral se agrupan como suprimidas.

No se exportan bastidores, nombres, identificadores personales, códigos postales
ni domicilios individuales. El municipio se refiere al domicilio registral del
vehículo y no al lugar de compra, entrega o concesionario. Los códigos de servicio, renting y procedencia se
presentan como categorías descriptivas; por sí solos no acreditan uso comercial,
flota, concesionario ni causa de la discrepancia territorial.

## Ejecución

```bash
python auditar_composicion_motocicletas.py \\
  --input-dir datos/matraba_mensual \\
  --cross datos/matraba_mensual/resultados/matriculaciones_motocicletas_cruce_provincias_nuevas.csv \\
  --inventory-file public/data/capturas_mensuales.json \\
  --output datos/matraba_mensual/resultados/composicion_motocicletas_nuevas.csv
```

La salida es exploratoria y no sustituye una validación semántica de los códigos
frente al diseño oficial de registro DGT.
