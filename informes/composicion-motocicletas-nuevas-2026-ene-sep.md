# Composición de las matriculaciones de motocicletas nuevas (enero-septiembre 2026)

## Alcance

Auditoría sobre 219.565 motocicletas nuevas MATRABA de tipos 50/51, matriculadas
entre enero y septiembre de 2026. Se comparan Segovia (8.908 unidades), el
agregado nacional y las otras 24 provincias cuyo porcentaje de matriculaciones
con domicilio registral en otra provincia supera el 20 %.

La selección de las 25 provincias procede del cruce provincial. El agregado
«otras 24» es ponderado: se suman recuentos y denominadores provinciales, no
se promedian porcentajes.

## Hallazgos principales

### Marcas

| Marca | Segovia | Nacional | Otras 24 provincias |
|---|---:|---:|---:|
| Yamaha | 25,19 % | 13,54 % | 9,83 % |
| Zontes | 20,23 % | 12,58 % | 12,29 % |
| Honda | 13,11 % | 18,84 % | 16,27 % |
| QJMotor | 6,49 % | 2,79 % | 2,26 % |
| Voge | 3,79 % | 7,80 % | 8,55 % |

Yamaha, Zontes y Honda reúnen el 58,53 % de las matriculaciones de Segovia,
frente al 44,97 % nacional y el 38,39 % de las otras 24 provincias.

### Cilindrada

| Cilindrada | Segovia | Nacional | Otras 24 provincias |
|---|---:|---:|---:|
| 125 cc | 50,62 % | 42,92 % | 36,46 % |
| 124 cc | 4,79 % | 6,94 % | 7,83 % |
| 368 cc | 7,04 % | 4,54 % | 4,18 % |

Las categorías 124 y 125 cc suman el 55,41 % en Segovia, el 49,86 % nacional
y el 44,29 % en las otras 24 provincias. El código de cilindrada «0» se
mantiene como valor no informado/no interpretable; no se atribuye a propulsión
eléctrica.

### Propulsión

| Propulsión | Segovia | Nacional | Otras 24 provincias |
|---|---:|---:|---:|
| Gasolina | 95,72 % | 97,53 % | 97,93 % |
| Eléctrica | 4,28 % | 2,47 % | 2,04 % |

La proporción eléctrica de Segovia es superior a los dos grupos de comparación.
Es una diferencia descriptiva; no demuestra que la propulsión explique la
dispersión registral.

### Titularidad y renting

| Indicador | Segovia | Nacional | Otras 24 provincias |
|---|---:|---:|---:|
| Persona física | 93,22 % | 90,14 % | 89,20 % |
| Persona jurídica | 6,78 % | 9,86 % | 10,80 % |
| Renting | 0,00 % | 0,33 % | 0,78 % |

### Procedencia registrada

En Segovia constan 5.662 unidades (63,58 %) como importación no comunitaria,
3.224 (36,19 %) como importación UE y 21 (0,24 %) con código no informado.
La procedencia es el descriptor administrativo MATRABA: no identifica el país
concreto de fabricación ni permite inferir la cadena comercial.

### Modelos más frecuentes en Segovia

| Modelo | Unidades | Porcentaje |
|---|---:|---:|
| GPD125D-A | 529 | 5,94 % |
| 368G | 481 | 5,40 % |
| GPD125-A | 442 | 4,96 % |
| 125X | 327 | 3,67 % |
| WW125A | 199 | 2,23 % |
| 125V | 158 | 1,77 % |

Se agrupan 1.051 registros de modelo en la categoría de supresión, al aplicar
el umbral mínimo de 10 unidades después de acumular los nueve meses.

### Municipio del domicilio registral

Madrid capital representa 3.893 registros (43,70 %), seguido por Getafe (175),
Barcelona (155), Leganés (142), San Sebastián de los Reyes (141), Móstoles
(141), Fuenlabrada (140), Alcorcón (126) y Alcobendas (120). Se agrupan
2.332 registros en la categoría de supresión municipal, con umbral 20.

El municipio es el del domicilio registral del vehículo. No equivale al
concesionario, lugar de compra, entrega, uso o residencia efectiva. Madrid
capital tampoco equivale a la provincia de Madrid: el cruce provincial atribuye
6.727 registros segovianos (75,52 %) a domicilios de la provincia de Madrid.

## Lectura

Segovia presenta una composición singular: mayor peso de Yamaha y Zontes,
más motocicletas de 124/125 cc y una proporción eléctrica más alta que el
agregado nacional y las otras provincias de alta dispersión. La distribución
de titulares físicos/jurídicos también difiere, aunque en menor medida.

Estos contrastes caracterizan el conjunto matriculado, pero no identifican
causas ni prueban irregularidades. La discrepancia entre provincia de
matriculación y domicilio registral no acredita por sí misma el lugar de venta,
entrega o circulación.

## Controles de calidad y privacidad

- 9 de 9 ZIP históricos descargados y verificados mediante SHA-256.
- Universo: tipos 50/51, operación 1, nuevo/usado = N, fechas de matrícula y
  trámite no posteriores a la fecha de proceso.
- 219.565 registros nacionales y 8.908 de Segovia.
- Detalle mensual y acumulado enero-septiembre.
- Conciliación interna exacta por provincia, periodo y dimensión antes de
  exportar.
- Umbral mínimo 10 por categoría y 20 para municipio; categorías pequeñas
  suprimidas después de acumular el periodo.
- Sin bastidores, nombres, domicilios individuales, códigos postales ni
  identificadores personales.

La validación completa se ejecuta en GitHub Actions y sus resultados se
publican como artefacto temporal del PR, no en `main`.
