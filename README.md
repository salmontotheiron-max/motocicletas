# Observatorio del mercado de automoción en España

## Estado de la integración MATRABA

Se ha añadido un primer procesador de microdatos diarios MATRABA y un workflow de GitHub Actions en la rama `integracion-matraba-inicial`. Esta fase todavía no sustituye el dashboard ANESDOR ni debe considerarse validada para publicación hasta ejecutar el workflow y revisar los resultados.

### Procesador

Ejecutar localmente:

```bash
python procesar_matraba.py --input-dir datos/matraba --output-dir public/data
```

El directorio de entrada acepta archivos `export_mat_YYYYMMDD.txt` desde el 1 de septiembre de 2026. El procesador valida registros de ancho fijo (69 campos/714 caracteres) y que `FEC_PROCESO` coincida con la fecha del nombre del archivo. Los agregados se reconstruyen desde los archivos presentes; al reemplazar un archivo diario y volver a ejecutar, sus recuentos sustituyen los de esa fecha en lugar de sumarse a una ejecución anterior.

### Salidas

- `public/data/matriculaciones_nuevos_usados_por_tipo.csv`: trámites `CLAVE_TRAMITE=1`, por periodo, código de tipo y nuevo/usado.
- `public/data/tipo_operacion.csv`: trámites de códigos 1–9, A y B.
- `public/data/manifest.json`: SHA-256 y cantidad de registros de cada fuente.
- `public/data/periodos.json`: periodos con datos procesados.
- `public/data/resumen.json`: resumen de ejecución y nota para los recuentos marcados con asterisco.

Para vehículos nuevos se usa el mes de `FEC_MATRICULA`. Para usados se usa `FEC_TRAMITACION`; si falta o es posterior a `FEC_PROCESO`, se usa la fecha de proceso y se marca con asterisco. La etiqueta `CLAVE_TRAMITE=1` significa matriculación ordinaria y de ciclomotores; no implica por sí sola que todos los vehículos sean nuevos.

Si no hay archivos para un periodo, la interfaz debe mostrar literalmente **Dato no disponible en DGT**, no un cero. Un cero solo debe mostrarse si se ha procesado la fuente pertinente y no hay registros de esa categoría. No se deduplican automáticamente filas idénticas.

### Actualización programada

El workflow `.github/workflows/actualizar-matraba.yml` puede ejecutarse manualmente desde **GitHub → Actions → Actualizar datos MATRABA → Run workflow** y tiene una programación diaria. Descarga los ZIP diarios que estén disponibles desde el 1 de septiembre de 2026, procesa el conjunto y guarda los agregados en `public/data`.

### Validación pendiente antes de publicación

1. Ejecutar manualmente el workflow en la rama de trabajo.
2. Comprobar los registros descargados y los SHA-256 del manifiesto contra los archivos oficiales.
3. Revisar los CSV y confirmar que los meses incompletos se etiqueten como provisionales.
4. Revisar el resultado de la descarga DGT: un fallo de red o un archivo no disponible no debe interpretarse como un día con cero matriculaciones.
5. Mantener fuera de la web los microdatos originales y los campos identificativos o sensibles.

## Prototipo anterior ANESDOR

El `index.html` existente sigue siendo el prototipo estático ANESDOR de 2025. La incorporación del procesador no ha conectado todavía sus CSV al dashboard ni ha cambiado el contenido publicado.
