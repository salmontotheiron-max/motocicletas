# Observatorio del mercado de automoción en España

## Estado de la integración MATRABA

La integración está migrando de descargas diarias a snapshots mensuales de microdatos DGT. El desarrollo se realiza en la rama `integracion-matraba-inicial`; la rama `main` no se modifica.

### Ámbito del observatorio

El informe de motocicletas y ciclomotores mantiene separados los códigos `COD_TIPO`:

- `50`: Motocicleta de 2 ruedas sin sidecar.
- `51`: Motocicleta con sidecar.
- `52`: Motocarro.
- `53`: Automóvil de 3 ruedas.
- `54`: Cuadriciclo pesado.
- `90`: Ciclomotor de 2 ruedas.
- `91`: Ciclomotor de 3 ruedas.
- `92`: Cuadriciclo ligero.

Los códigos ajenos a este catálogo se excluyen de los dos informes. No se infieren categorías para códigos desconocidos.

### Modelo de captura mensual

El descargador `descargar_matraba_mensual.py` consulta el mes actual y el anterior, salvo que se indiquen meses concretos mediante `--month YYYY-MM` (opción repetible).

La URL mensual utiliza el mes sin cero inicial en la ruta y seis cifras en el nombre del ZIP. Se validan:

- Integridad del ZIP mediante CRC.
- Existencia de exactamente un TXT.
- Cabecera mensual de 79 bytes.
- Longitud de 714 bytes por registro.
- Validez de la fecha `FEC_PROCESO` de cada registro.

No se exige que `FEC_PROCESO` coincida con el mes del fichero. No se exige un volumen mínimo y no se eliminan registros duplicados automáticamente. Un HTTP 404 se registra como `no_disponible_en_barrido`; los errores de red, HTTP y estructura se mantienen diferenciados.

Cada ZIP se conserva con su SHA-256 en un nombre de archivo que identifica el periodo y la versión. El inventario `public/data/capturas_mensuales.json` mantiene el histórico de ejecuciones, fechas de captura, estados, tamaños, hashes y recuentos.

### Archivo de fuentes

Los ZIP originales se archivan como activos de **GitHub Releases** del repositorio. El repositorio es público, por lo que esos activos también son públicos. No se incorporan los ZIP al historial normal de Git.

Cada ejecución crea un Release de barrido. Un ZIP con el mismo nombre/hash que ya esté archivado no se vuelve a subir. Los ZIP históricos de Releases se recuperan antes de procesar, para que los agregados puedan reconstruirse con las fuentes conservadas.

### Procesamiento mensual

El procesador `procesar_matraba_mensual.py` selecciona una única versión por mes: la última captura válida registrada en el inventario. Las versiones anteriores se conservan como evidencia y no se suman entre sí.

Para vehículos nuevos se usa `FEC_MATRICULA`. Para usados se usa `FEC_TRAMITE`, porque el informe observa cambios de titularidad que no necesariamente modifican `FEC_MATRICULA`. En el agregado territorial de motocicletas, los nuevos se agrupan por provincia de matriculación (`COD_PROVINCIA_MAT`) y los usados por provincia de domicilio del vehículo (`COD_PROVINCIA_VEH`); son dimensiones distintas y no deben sumarse como una única distribución territorial. Las operaciones se fechan igualmente por `FEC_TRAMITE`. Si la fecha de referencia de un registro es posterior a `FEC_PROCESO`, se excluye el registro y se anota en la auditoría; no se sustituye por `FEC_PROCESO`. Los registros sin fecha de referencia válida tampoco se incorporan al recuento correspondiente. `FEC_PROCESO` se utiliza como control de coherencia y no para asignar el periodo.

Salidas:

- `public/data/matriculaciones_nuevos_usados_por_tipo.csv`: matriculaciones por periodo, código de tipo y nuevo/usado.
- `public/data/matriculaciones_motocicletas_por_provincia.csv`: motocicletas (códigos 50 y 51) por periodo y provincia. En nuevos se utiliza `COD_PROVINCIA_MAT`; en usados, `COD_PROVINCIA_VEH`. Los códigos no catalogados se conservan y se etiquetan, no se descartan.
- `matriculaciones_motocicletas_cruce_provincias_nuevas.csv`: cruce exploratorio por periodo entre provincia de matriculación (`COD_PROVINCIA_MAT`) y provincia del domicilio registrado del vehículo (`COD_PROVINCIA_VEH`) para motocicletas nuevas. No identifica necesariamente la residencia efectiva del comprador.
- `public/data/tipo_operacion.csv`: operaciones por periodo y clave de trámite.
- `public/data/manifest.json`: fuente seleccionada por periodo, SHA-256, tamaño, registros y rango de fechas de proceso.
- `public/data/periodos.json`: periodos con fuente mensual procesada.
- `public/data/resumen.json`: totales, exclusiones y criterios de procesamiento.
- `public/data/capturas_mensuales.json`: inventario acumulado de barridos y descargas.
- `public/data/ranking_motocicletas_provincia.csv`: ranking acumulado por provincia, con recuento, peso porcentual, puesto y número de periodos con datos. Mantiene separados nuevos (provincia de matriculación) y usados (provincia de domicilio del vehículo).
- `public/data/evolucion_motocicletas_provincia.csv`: evolución mensual provincial, con recuentos y peso porcentual dentro de cada ámbito y mes.
- `public/data/resumen_territorial.json`: totales, número de provincias, concentración de las cinco y diez primeras, periodos disponibles y trazabilidad de códigos provinciales vacíos.
- `public/data/informe_dispersion_provincias.json`: resumen nacional de coincidencia y dispersión, evolución mensual, ranking provincial, principales flujos, seguimiento de Segovia y validación de totales.
- `public/data/dispersion_provincias_mensual.csv`: evolución mensual de matriculaciones en la misma provincia, en otra provincia y con domicilio no informado.
- `public/data/dispersion_provincias_ranking.csv`: ranking por provincia de matriculación, con volúmenes y porcentaje de domicilios externos sobre domicilios conocidos.
- `public/data/dispersion_provincias_flujos.csv`: flujos interprovinciales ordenados por volumen.
- `public/data/dispersion_balance_provincial.csv`: salidas, entradas y saldo neto interprovincial por provincia, con indicadores relativos sobre el volumen de matriculaciones.
- `public/data/dispersion_corredores_estabilidad.csv`: estabilidad y simetría de cada corredor dirigido, con meses activos, persistencia, peso sobre salidas del origen, pesos mensuales, flujo inverso, simetría y evolución mensual.
- `public/data/matriz_dispersion_provincias.csv`: matriz completa de combinaciones entre provincias de matriculación y domicilio, incluidos los pares con cero registros.

El script `generar_informe_provincial.py` produce estas tres salidas a partir del CSV provincial. La generación se ejecuta en el workflow mensual y queda cubierta por pruebas automatizadas. Los códigos provinciales vacíos se identifican expresamente; no se asigna una provincia por inferencia. El código `NA` se conserva como Navarra. El script `generar_informe_dispersion.py` cruza el CSV de matriculación y domicilio de vehículos nuevos con el agregado provincial, exige coincidencia exacta de los totales y genera el resumen, evolución, ranking, flujos, matriz de dispersión y balance interprovincial por provincia. El balance incorpora las salidas (matriculadas en la provincia y domiciliadas fuera), las entradas (domiciliadas en la provincia y matriculadas fuera) y el saldo neto (entradas menos salidas), tanto en número de registros como en porcentaje del volumen de matriculaciones de la provincia. Los flujos solo se calculan cuando ambos códigos provinciales están informados y son distintos; los porcentajes relativos usan como denominador las matriculaciones de la provincia. La matriz se presenta en formato largo y contiene todas las combinaciones de las provincias presentes en ambas dimensiones, también las que tienen recuento cero. El informe se regenera en cada ejecución mensual y sus salidas quedan incluidas en los artefactos piloto y en la publicación de agregados.

Los rankings absolutos no se interpretan como tasas de penetración ni como intensidad de mercado por habitante. Si en una fase posterior se incorpora una fuente oficial y comparable de población o parque de motocicletas, podrán añadirse indicadores relativos sin sustituir los recuentos originales.

Las cifras elevadas de una provincia, incluida Segovia, no se corrigen ni se descartan por su magnitud. Se conservan cuando proceden de los microdatos DGT y superan las validaciones de integridad. Su interpretación contextual se separa de la validación del dato.

Si no existe una fuente válida para un periodo, la interfaz debe mostrar **Dato no disponible en DGT**, no un cero. Un cero solo puede mostrarse cuando se ha procesado la fuente correspondiente y no contiene registros de esa categoría. No se exportan campos personales ni identificadores sensibles.

### Ejecución y estado de la automatización

El workflow `.github/workflows/actualizar-matraba.yml` se ejecuta manualmente desde GitHub Actions y ofrece dos modos:

- `piloto` (predeterminado): descarga, archiva y procesa las fuentes; adjunta los resultados al Release, pero no sustituye los agregados publicados.
- `actualizar`: además publica los CSV y JSON generados en `public/data`.

Admite una lista opcional de meses separados por comas; por ejemplo, `2026-07,2026-08,2026-09`. Si se deja vacío, consulta el mes actual y el anterior.

El workflow incorpora un calendario para los días 1, 8, 15, 22 y 28 de cada mes a las 05:25 UTC. GitHub Actions solo ejecutará ese calendario cuando esta versión esté integrada en la rama predeterminada `main`. Las ejecuciones programadas publicarán automáticamente los agregados en la rama desde la que se ejecuten. La hora corresponde a UTC: 06:25 en horario peninsular de invierno y 07:25 en horario de verano.

### Validación pendiente

1. Ejecutar la batería completa de pruebas en GitHub Actions.
2. Descargar julio de 2026 y comparar el TXT contenido en el ZIP con el fichero mensual ya validado.
3. Confirmar que el ZIP original se archiva en Releases y que el hash coincide.
4. Cargar los meses disponibles de 2026 sin sumar capturas distintas del mismo mes.
5. Revisar agregados y manifiestos antes de activar el cron.

## Prototipo anterior ANESDOR

El `index.html` existente sigue siendo el prototipo estático ANESDOR de 2025. La migración MATRABA todavía no conecta sus CSV al dashboard ni sustituye el contenido del prototipo.


### Indicadores relativos de intensidad territorial

Se incorporan dos referencias oficiales provinciales:

- `public/data/poblacion_provincial_2025.csv`: cifras oficiales de población a 1 de enero de 2025 (INE, declaradas por el Real Decreto 1117/2025).
- `public/data/parque_motocicletas_provincia_2025.csv`: parque de motocicletas a 31 de diciembre de 2025 (DGT, Anuario Estadístico General 2025, tabla 75).
- `public/data/fuentes_referencias_territoriales.json`: fuentes, fechas de referencia y descarga, cobertura y total nacional de control.

El script `generar_indicadores_intensidad.py` genera:

- `indicadores_intensidad_territorial.csv`: matriculaciones nuevas acumuladas por 1.000 habitantes y como porcentaje del parque provincial de referencia.
- `metodologia_indicadores_territoriales.json`: periodos, fórmulas, fuentes y limitaciones.

La cobertura de los dos denominadores debe ser exactamente de 52 territorios (50 provincias y las ciudades autónomas), sin códigos duplicados, nombres incompatibles ni fechas de referencia distintas de las declaradas. El total del parque de motocicletas debe coincidir con 4.510.222 unidades de la tabla 75 de la DGT.

Los indicadores se calculan únicamente para motocicletas nuevas (códigos 50 y 51), por provincia de matriculación. No se calculan ratios para usados: estos son cambios de titularidad por provincia de domicilio del vehículo y no todas las compraventas. Los flujos acumulados de 2026 se comparan con población de 1-1-2025 y parque de 31-12-2025; por tanto, son indicadores descriptivos de intensidad, no tasas de renovación ni cuotas de mercado.

Se marca `REVISAR` cuando las matriculaciones acumuladas alcanzan el 25% del parque de referencia. El umbral es una señal operativa de revisión, no una anomalía confirmada. No excluye ni corrige registros. En particular, los valores elevados de Segovia se conservan íntegramente.

La generación se ejecuta en el workflow mensual después del agregado provincial, por lo que los dos archivos de salida se publican junto con el resto de datos cuando el workflow actualiza `public/data`.


### Informe territorial integrado recurrente

El script `generar_informe_territorial_integrado.py` construye `informes/informe-territorial-integrado.md` a partir de los CSV y JSON generados en cada ejecución MATRABA. El diagnóstico de dispersión incorpora todas las provincias con más del 20% de domicilios externos, su persistencia mensual, concentración de destinos (principal destino, tres primeros, HHI y número efectivo de destinos) y una advertencia para muestras inferiores a 300 domicilios conocidos. Incluye la serie mensual, concentración provincial, intensidad respecto a población y parque, dispersión entre provincia de matriculación y domicilio del vehículo, balance de entradas/salidas, flujos origen-destino, persistencia y variabilidad mensual de corredores, comparación del flujo inverso y seguimiento de Segovia. El generador verifica que el total de motocicletas nuevas por códigos 50/51 coincide con el cruce provincial y que este ha superado la conciliación con el agregado independiente.

En los barridos programados y en el modo manual `actualizar`, el informe se incorpora al commit junto con `public/data`. En modo `piloto`, se adjunta al artefacto y al GitHub Release, sin actualizar el informe publicado en la rama. La generación está cubierta por pruebas unitarias. Los umbrales se muestran como alertas de revisión, nunca como anomalías confirmadas.
