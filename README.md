# Observatorio del mercado de automoción en España

## Estado de la integración MATRABA

Se ha añadido un procesador de microdatos diarios MATRABA y un workflow de GitHub Actions en la rama `integracion-matraba-inicial`. Esta fase todavía no sustituye el dashboard ANESDOR ni debe considerarse validada para publicación hasta comprobar la cobertura de fuentes y los resultados.

### Ámbito del observatorio

El informe se limita a motocicletas y ciclomotores, manteniendo cada código `COD_TIPO` por separado:

- `50`: Motocicleta de 2 ruedas sin sidecar.
- `51`: Motocicleta con sidecar.
- `52`: Motocarro.
- `53`: Automóvil de 3 ruedas.
- `54`: Cuadriciclo pesado.
- `90`: Ciclomotor de 2 ruedas.
- `91`: Ciclomotor de 3 ruedas.
- `92`: Cuadriciclo ligero.

Los códigos ajenos a este catálogo se excluyen de ambos informes. El código `60`, por ejemplo, corresponde a coche de inválido y no forma parte del ámbito.

### Procesador

Ejecutar localmente:

```bash
python procesar_matraba.py --input-dir datos/matraba --output-dir public/data
```

El directorio de entrada acepta archivos `export_mat_YYYYMMDD.txt` desde el 1 de septiembre de 2026. El procesador valida registros de ancho fijo (69 campos/714 caracteres) y que `FEC_PROCESO` coincida con la fecha del nombre del archivo. Los agregados se reconstruyen desde los archivos presentes; al reemplazar un archivo diario y volver a ejecutar, sus recuentos sustituyen los de esa fecha en lugar de sumarse a una ejecución anterior.

### Salidas

- `public/data/matriculaciones_nuevos_usados_por_tipo.csv`: trámites `CLAVE_TRAMITE=1`, por periodo, código de tipo y nuevo/usado, limitados al catálogo anterior.
- `public/data/tipo_operacion.csv`: operaciones con claves 1–9, A y B, limitadas al mismo catálogo de tipos.
- `public/data/manifest.json`: SHA-256 y cantidad de registros de cada fuente, filtro aplicado e inventario diario/mensual.
- `public/data/cobertura_diaria.json`: un registro por cada día consultado, con estado de descarga, HTTP, validación y número de registros.
- `public/data/periodos.json`: periodos con matriculaciones procesadas y estado de cobertura mensual.
- `public/data/resumen.json`: resumen de ejecución, filtro aplicado, exclusiones por código de tipo y nota para los recuentos marcados con asterisco.

Para vehículos nuevos se usa el mes de `FEC_MATRICULA`. Para usados se usa `FEC_TRAMITACION`; si falta o es posterior a `FEC_PROCESO`, se usa la fecha de proceso y se marca con asterisco. La etiqueta `CLAVE_TRAMITE=1` significa matriculación ordinaria y de ciclomotores; no implica por sí sola que todos los vehículos sean nuevos.

Si no hay archivos para un periodo, la interfaz debe mostrar literalmente **Dato no disponible en DGT**, no un cero. Un cero solo debe mostrarse si se ha procesado la fuente pertinente y no hay registros de esa categoría. No se deduplican automáticamente filas idénticas.

### Actualización programada

El workflow `.github/workflows/actualizar-matraba.yml` puede ejecutarse manualmente desde **GitHub → Actions → Actualizar datos MATRABA → Run workflow** y tiene una programación diaria. El descargador `descargar_matraba.py` consulta todos los días desde el 1 de septiembre de 2026 y clasifica cada resultado como `descargado_validado`, `no_encontrado_dgt`, `error_http`, `error_red` o `fichero_invalido`. Valida ZIP, TXT, ancho de 714 bytes y `FEC_PROCESO`. Un día con HTTP 404 no se convierte en cero matriculaciones. Los meses solo se consideran completos si todos sus días inventariados tienen un fichero validado; en otro caso se etiquetan como incompletos. Los ficheros con pocos registros no se descartan por volumen.

### Validación pendiente antes de publicación

1. Ejecutar manualmente el workflow en la rama de trabajo.
2. Comprobar los registros descargados y los SHA-256 del manifiesto contra los archivos oficiales.
3. Revisar los CSV y confirmar que los meses incompletos se etiqueten como provisionales.
4. Revisar `cobertura_diaria.json`: un HTTP 404 se registra como no encontrado en DGT; los fallos de red/HTTP y los ficheros inválidos quedan diferenciados. Ninguno se interpreta como un día con cero matriculaciones.
5. Mantener fuera de la web los microdatos originales y los campos identificativos o sensibles.

## Prototipo anterior ANESDOR

El `index.html` existente sigue siendo el prototipo estático ANESDOR de 2025. La incorporación del procesador no ha conectado todavía sus CSV al dashboard ni ha cambiado el contenido publicado.
