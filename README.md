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

Para vehículos nuevos se usa `FEC_MATRICULA`. Para usados se usa `FEC_TRAMITE`, porque el informe observa cambios de titularidad que no necesariamente modifican `FEC_MATRICULA`. Las operaciones se fechan igualmente por `FEC_TRAMITE`. Si la fecha de referencia de un registro es posterior a `FEC_PROCESO`, se excluye el registro y se anota en la auditoría; no se sustituye por `FEC_PROCESO`. Los registros sin fecha de referencia válida tampoco se incorporan al recuento correspondiente. `FEC_PROCESO` se utiliza como control de coherencia y no para asignar el periodo.

Salidas:

- `public/data/matriculaciones_nuevos_usados_por_tipo.csv`: matriculaciones por periodo, código de tipo y nuevo/usado.
- `public/data/tipo_operacion.csv`: operaciones por periodo y clave de trámite.
- `public/data/manifest.json`: fuente seleccionada por periodo, SHA-256, tamaño, registros y rango de fechas de proceso.
- `public/data/periodos.json`: periodos con fuente mensual procesada.
- `public/data/resumen.json`: totales, exclusiones y criterios de procesamiento.
- `public/data/capturas_mensuales.json`: inventario acumulado de barridos y descargas.

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
