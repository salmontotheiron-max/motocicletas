# Captura reproducible de fuentes de red comercial

## Objetivo y alcance

La captura técnica consulta el inventario explícito vigente \`fuentes_red_comercial.json\` (esquema 2). En la revisión de 12-11-2026 contiene 15 fuentes de distinta naturaleza: directorios oficiales, páginas de operadores, registros públicos y fuentes secundarias de descubrimiento. No constituye un censo ni un listado exhaustivo de concesionarios.

El proceso registra respuestas HTTP y hashes; no determina por sí solo la vigencia de una red, la actividad de un establecimiento ni un cambio comercial confirmado.

## Ejecución

Desde la raíz del repositorio:

\`\`\`bash
python -c "from validar_red_comercial import initialize_database; db=initialize_database('red_comercial.sqlite'); db.close()"
python capturar_fuentes_red_comercial.py --db red_comercial.sqlite
python -m unittest discover -s tests -p 'test_capturar_fuentes_red_comercial.py' -v
\`\`\`

Opciones:
- \`--db\`: base SQLite de destino (por defecto \`red_comercial.sqlite\`).
- \`--sources\`: inventario JSON alternativo; admite esquema 2 actual y esquema 1 del piloto anterior.
- \`--timeout\`: timeout por petición entre 1 y 60 segundos (por defecto 20).

El capturador:
1. Lee exclusivamente las URLs declaradas en el inventario.
2. Exige HTTPS y valida los campos y categorías del catálogo.
3. Ejecuta GET con timeout y límite máximo de 2 MB.
4. No rastrea enlaces, no usa autenticación, cookies ni formularios.
5. Solo sigue redirecciones que conservan esquema, host y puerto HTTPS.
6. Calcula SHA-256 y conserva un extracto técnico limitado a 600 bytes; no almacena el HTML completo.
7. Compara el hash con la última respuesta satisfactoria de esa fuente.
8. Registra el resultado en \`source_capture\` y crea una observación técnica en la primera captura y cuando cambia el hash.
9. Cierra la captura como \`completed\`, \`partial\` o \`failed\`.

La migración \`migraciones/002_capturas_fuentes.sql\` es aditiva e idempotente. El script la aplica automáticamente después de inicializar el esquema principal. Si un \`source_id\` ya existe con metadatos distintos, la captura se detiene para evitar sobrescribir silenciosamente el catálogo.

## Estados de cada fuente

| Resultado | Significado |
|---|---|
| \`success\` | Primera respuesta satisfactoria conocida |
| \`changed\` | Respuesta satisfactoria con hash distinto al anterior |
| \`unchanged\` | Respuesta satisfactoria con el mismo hash |
| \`not_found\` | HTTP 404 o 410; la URL consultada no se ha encontrado |
| \`unavailable\` | Fallo transitorio, timeout, red, HTTP 429 o 5xx |
| \`error\` | Error HTTP no transitorio, redirección fuera del origen o respuesta fuera de límites |

**Ningún estado equivale al cierre de un concesionario, la baja de un operador o la salida de una marca.** \`not_found\` se refiere exclusivamente a la URL consultada. Los cambios de hash indican diferencias de bytes, que pueden deberse a banners, analítica, fechas dinámicas o contenido comercial; requieren revisión humana.

## Salvaguardas y límites

- Inventario explícito; no hay rastreo recursivo ni descubrimiento automático de establecimientos.
- No se eluden robots.txt, controles de acceso, límites del sitio ni autenticación.
- No se descargan ni conservan páginas completas.
- El límite de 2 MB se aplica a la respuesta leída; el extracto almacenado se limita a 600 bytes.
- La primera captura establece una línea base técnica, no valida una afirmación comercial.
- Las fuentes dinámicas pueden devolver HTML sin establecimientos; se registra la respuesta, no se interpreta como red vacía.
- La captura no se programa periódicamente en esta fase. Antes de automatizarla deben revisarse condiciones de uso, estabilidad, frecuencia y resultados de cada dominio.
- El inventario puede contener fuentes secundarias de descubrimiento; su hash nunca las convierte en fuentes primarias ni prueba por sí solo un hecho.

## Validación previa a automatización

1. Ejecutar el piloto en fechas distintas y revisar cambios de hash.
2. Confirmar que 404, errores de red y bloqueos no generan eventos de baja.
3. Revisar manualmente extractos y páginas originales.
4. Evaluar estabilidad y límites de cada fuente individualmente.
5. Diseñar un comparador semántico separado del comparador de hashes, con cola de revisión humana.

La base de datos conserva evidencia técnica de consultas. No convierte automáticamente el contenido web en entidades, relaciones ni eventos confirmados.
