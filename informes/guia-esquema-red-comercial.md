# Esquema SQLite del seguimiento histórico

Este esquema implementa la primera capa del diseño descrito en
`diseno-seguimiento-historico-red-comercial-2026-11-11.md`.

## Archivos

- `esquema_red_comercial.sql`: tablas, claves, vocabularios, índices y protección de observaciones.
- `validar_red_comercial.py`: inicialización y comprobaciones de integridad.
- `tests/test_validar_red_comercial.py`: pruebas unitarias del modelo y del piloto.
- `datos/piloto_red_comercial_2026-11-11.sql`: carga idempotente de casos documentados (Motos Copa/Suzuki, Zontes Centro Madrid y entrada de ZXMOTO/Desmotrón).
- `consultas_historicas_red_comercial.sql`: consultas de cronología por establecimiento, relaciones vigentes a una fecha, distribuidores por marca, eventos fechados/no fechados y trazabilidad de evidencias.

## Uso

Desde la raíz del repositorio, para cargar el piloto en una base inicializada:

```bash
python -c "from validar_red_comercial import initialize_database; db=initialize_database('red_comercial.sqlite'); db.executescript(open('datos/piloto_red_comercial_2026-11-11.sql', encoding='utf-8').read()); db.close()"
```

La carga usa `INSERT OR IGNORE` y puede repetirse. Para explorar el piloto, abrir `consultas_historicas_red_comercial.sql` y ejecutar cada consulta con los parámetros indicados en sus comentarios (por ejemplo, `:outlet_id` y `:as_of_date`). Las consultas temporales aplican intervalos semiabiertos `[valid_from, valid_to)`; las fechas efectivas desconocidas se muestran en una consulta separada para que no desaparezcan del seguimiento. No es un censo: los operadores societarios no identificados se dejan sin asignar, las fechas desconocidas permanecen nulas y los indicios se mantienen como candidatos.

Desde la raíz del repositorio:

```bash
python validar_red_comercial.py
python -m unittest discover -s tests -p 'test_*.py'
```

Para inicializar una base persistente:

```python
from validar_red_comercial import initialize_database, validate_database

db = initialize_database("red_comercial.sqlite")
errors = validate_database(db)
if errors:
    raise RuntimeError(errors)
db.close()
```

## Decisiones y límites

- SQLite con claves foráneas activadas por conexión.
- UUID generados por la aplicación; no se usa el nombre como clave.
- Intervalos de vigencia semiabiertos `[valid_from, valid_to)`; extremos desconocidos admitidos.
- Las observaciones son append-only. Las correcciones se incorporan como nuevas observaciones.
- Las relaciones pueden coexistir; no se impone unicidad de importador o concesionario por marca.
- La validación comprueba integridad SQLite, claves foráneas y coherencia de intervalos.
- La tabla `claim` conserva afirmaciones y contradicciones con su evidencia.
- Los eventos se vinculan a marcas, empresas y establecimientos mediante tablas de asociación tipadas (`change_event_brand`, `change_event_company`, `change_event_outlet`), con claves foráneas reales.
- No incluye rastreo web, deduplicación automática ni inferencia de bajas. Esas funciones quedan fuera de esta primera capa.

**Importante:** `valid_to = NULL` no demuestra vigencia actual. Una consulta de situación actual deberá aplicar reglas de recencia y estado de confirmación.
