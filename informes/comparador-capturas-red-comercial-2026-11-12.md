# Comparación conservadora de capturas de red comercial

**Estado:** implementación inicial propuesta en PR independiente; requiere capturas reales para calibrar.

## Qué hace

`comparar_capturas_red_comercial.py` lee `evidencias/red_comercial/capturas.jsonl`, agrupa por fuente y compara capturas HTML válidas con texto extraído suficiente. Usa la captura válida anterior como baseline; los registros fallidos se ignoran y una página demasiado corta (posible carcasa JavaScript) no reemplaza el baseline.

Genera:
- `evidencias/red_comercial/candidatos_cambio.jsonl`: un candidato por transición textual distinta.
- `evidencias/red_comercial/resumen_comparacion.json`: contadores del barrido.

Cada candidato conserva fechas, hashes, rutas de snapshots, líneas añadidas/retiradas y extractos acotados. Su estado es `pending_manual_review` y su tipo es técnico (`source_content_changed`), no un evento comercial.

## Límites probatorios

- Una variación textual no demuestra alta, baja, cierre, traslado, cambio de operador ni actividad.
- Errores HTTP, bloqueos robots, redirecciones rechazadas y fallos de red no generan candidatos de desaparición.
- Un contenido muy corto no se considera comparable ni sustituye el último baseline suficiente.
- Solo se eliminan avisos inequívocos de cookies; no se borran nombres, fechas, direcciones ni texto comercial.
- El comparador no crea entidades, claims ni change_event y no actualiza el histórico SQLite.
- Los extractos son pistas para revisión; la validación exige abrir los snapshots y contrastar fuentes.

## Validación pendiente

La primera ejecución real permitirá medir ruido por cambios de diseño, banners y páginas dinámicas. Los umbrales y reglas deberán ajustarse con ejemplos observados, sin convertir automáticamente cambios de contenido en hechos de mercado.
