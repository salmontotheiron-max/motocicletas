# Captura reproducible de fuentes de red comercial

## Objetivo y alcance

La etapa C implementa una primera captura reproducible sobre un inventario explícito y pequeño de fuentes públicas. No constituye un rastreador web general, un censo de concesionarios ni un verificador automático de vigencia comercial.

El inventario inicial (fuentes_red_comercial.json) contiene seis referencias relacionadas con tres casos piloto: cierre de Motos Copa, apertura de Zontes Centro Madrid y entrada de ZXMOTO/Desmotrón. Se incluyen fuentes periodísticas y páginas empresariales. Su selección sirve para probar el mecanismo, no para medir cobertura.

## Funcionamiento

Desde la raíz del repositorio:

```bash
python -c "from validar_red_comercial import initialize_database; db=initialize_database('red_comercial.sqlite'); db.close()"
python capturar_fuentes_red_comercial.py --db red_comercial.sqlite
python -m unittest tests.test_capturar_fuentes_red_comercial -v
```

El proceso:

1. Lee únicamente las URLs declaradas en el inventario.
2. Rechaza URLs que no sean HTTPS.
3. Ejecuta una petición GET por fuente, con timeout y límite de 2 MB.
4. No sigue enlaces ni descubre nuevas páginas.
5. Comprueba que una redirección permanezca en el mismo host HTTPS.
6. Calcula SHA-256 y conserva un extracto técnico limitado; no almacena el HTML completo.
7. Compara el hash con la última respuesta satisfactoria de esa fuente.
8. Registra el resultado de cada fuente en source_capture y crea una observation cuando hay primera captura o cambio de contenido.
9. Cierra la captura como completed, partial o failed.

La migración migraciones/002_capturas_fuentes.sql es aditiva e idempotente. Debe aplicarse después de esquema_red_comercial.sql; el script de captura la aplica automáticamente.

## Estados

| Resultado | Significado |
|---|---|
| success | Primera respuesta satisfactoria conocida |
| changed | Respuesta satisfactoria con hash distinto al anterior |
| unchanged | Respuesta satisfactoria con el mismo hash |
| not_found | HTTP 404 o 410; la URL no se ha encontrado |
| unavailable | Fallo transitorio, timeout, red, HTTP 429 o 5xx |
| error | Error HTTP no transitorio, redirección fuera del host o respuesta fuera de límites |

**Ninguno de estos estados significa que un concesionario haya cerrado o que una marca haya abandonado un establecimiento.** not_found se refiere exclusivamente a la URL consultada. Los cambios comerciales deben derivarse después de revisar el contenido y las evidencias.

## Límites y salvaguardas

- Inventario explícito; no hay rastreo recursivo ni enumeración de directorios.
- Sin autenticación, cookies, evasión de controles ni interacción con formularios.
- No se descargan ni conservan páginas completas.
- Timeout configurable entre 1 y 60 segundos; valor predeterminado 20.
- Límite de respuesta 2 MB.
- Un cambio de hash solo significa cambio de bytes. Puede deberse a banners, analítica, fechas dinámicas o contenido comercial; requiere revisión.
- La primera captura establece una línea base, no valida por sí sola una afirmación comercial.
- El inventario inicial incluye referencias históricas. La consulta actual puede devolver 404 o contenido actualizado; se registra el estado sin reescribir el piloto ni alterar eventos anteriores.
- La frecuencia de consulta se decidirá tras medir estabilidad y políticas de cada fuente. Esta etapa no programa aún una ejecución periódica.
- Antes de ampliar el inventario deben revisarse condiciones de uso, robots.txt, límites de frecuencia y permisos de cada dominio.

## Próxima validación

Antes de automatizar la periodicidad:
1. Ejecutar el piloto al menos dos veces y revisar los cambios de hash.
2. Comprobar que 404, errores de red y bloqueos no producen eventos de baja.
3. Revisar manualmente los extractos y fuentes originales.
4. Añadir fuentes oficiales de marcas/importadores con URL estable y alcance bien definido.
5. Definir un comparador semántico separado del comparador de hashes, con cola de revisión humana.

La base de datos guarda la evidencia técnica de la consulta. No convierte automáticamente el contenido web en entidades, relaciones ni eventos confirmados.
