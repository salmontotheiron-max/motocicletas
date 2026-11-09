#!/usr/bin/env python3
"""Calcula indicadores relativos de matriculación territorial de motocicletas."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ALERTA_PARQUE_PCT = 25.0
EXPECTED_CODES = 52


def read_reference(path, value_field, expected_date):
    rows = {}
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {
            "COD_PROVINCIA", "provincia", value_field, "fecha_referencia",
            "fecha_descarga",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: faltan columnas {sorted(missing)}")
        for line, row in enumerate(reader, 2):
            code = row["COD_PROVINCIA"].strip()
            name = row["provincia"].strip()
            if not code or not name:
                raise ValueError(f"{path}: código o provincia vacío en línea {line}")
            if code in rows:
                raise ValueError(f"{path}: código duplicado {code!r}")
            if row["fecha_referencia"].strip() != expected_date:
                raise ValueError(
                    f"{path}: fecha de referencia incorrecta para {code}: "
                    f"{row['fecha_referencia']!r}"
                )
            if not row["fecha_descarga"].strip():
                raise ValueError(f"{path}: falta fecha de descarga para {code}")
            try:
                value = int(row[value_field])
            except (TypeError, ValueError):
                raise ValueError(f"{path}: valor no entero para {code}") from None
            if value <= 0:
                raise ValueError(f"{path}: valor no positivo para {code}")
            rows[code] = {
                "provincia": name,
                value_field: value,
                "fecha_descarga": row["fecha_descarga"].strip(),
                "fecha_referencia": expected_date,
            }
    if len(rows) != EXPECTED_CODES:
        raise ValueError(
            f"{path}: cobertura incompleta; se esperaban {EXPECTED_CODES} códigos "
            f"y hay {len(rows)}"
        )
    return rows


def read_new_counts(path):
    counts = Counter()
    periods = set()
    names = {}
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {
            "periodo", "ambito_provincial", "COD_PROVINCIA",
            "provincia", "COD_TIPO", "nuevo_usado", "recuento",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: faltan columnas {sorted(missing)}")
        for line, row in enumerate(reader, 2):
            if row["ambito_provincial"].strip() != "matriculacion":
                continue
            if row["nuevo_usado"].strip() != "Nuevo":
                raise ValueError(f"{path}: condición inesperada en línea {line}")
            code = row["COD_PROVINCIA"].strip()
            if not code:
                raise ValueError(f"{path}: código provincial vacío en línea {line}")
            name = row["provincia"].strip()
            if code in names and names[code] != name:
                raise ValueError(f"{path}: nombres incompatibles para {code}")
            names[code] = name
            try:
                value = int(row["recuento"])
            except (TypeError, ValueError):
                raise ValueError(f"{path}: recuento no entero en línea {line}") from None
            if value < 0:
                raise ValueError(f"{path}: recuento negativo en línea {line}")
            counts[code] += value
            periods.add(row["periodo"].strip())
    if not periods:
        raise ValueError(f"{path}: no hay periodos de matriculación")
    return counts, sorted(periods), names


def build_report(provincial_path, population_path, park_path, output_dir):
    population = read_reference(population_path, "poblacion", "2025-01-01")
    park = read_reference(park_path, "parque_motocicletas", "2025-12-31")
    if set(population) != set(park):
        raise ValueError("La cobertura de población y parque no coincide")
    counts, periods, names = read_new_counts(provincial_path)

    unknown = set(counts) - set(population)
    if unknown:
        raise ValueError("Códigos MATRABA sin denominador oficial: " + ", ".join(sorted(unknown)))
    for code, name in names.items():
        if population[code]["provincia"] != name:
            raise ValueError(
                f"Nombre provincial incompatible para {code}: "
                f"{name!r} != {population[code]['provincia']!r}"
            )

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for code in sorted(population, key=lambda item: population[item]["provincia"]):
        name = population[code]["provincia"]
        new_count = counts.get(code, 0)
        people = population[code]["poblacion"]
        motorcycles = park[code]["parque_motocicletas"]
        rate_population = 1000 * new_count / people
        rate_park = 100 * new_count / motorcycles
        rows.append({
            "COD_PROVINCIA": code,
            "provincia": name,
            "matriculaciones_nuevas": new_count,
            "poblacion": people,
            "matriculaciones_por_1000_habitantes": round(rate_population, 4),
            "parque_motocicletas": motorcycles,
            "matriculaciones_sobre_parque_pct": round(rate_park, 4),
            "umbral_revision_parque_pct": ALERTA_PARQUE_PCT,
            "alerta_revision": "REVISAR" if rate_park >= ALERTA_PARQUE_PCT else "",
            "periodos": "|".join(periods),
        })

    with (output / "indicadores_intensidad_territorial.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "periodos_matriculaciones": periods,
        "ambito": "Motocicletas nuevas (COD_TIPO 50 y 51), provincia de matriculación",
        "poblacion": {
            "fecha_referencia": "2025-01-01",
            "fuente": "INE / BOE-A-2025-25362",
            "url": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-25362",
        },
        "parque_motocicletas": {
            "fecha_referencia": "2025-12-31",
            "fuente": "DGT, Anuario Estadístico General 2025, tabla 75",
            "url": "https://www.dgt.es/export/sites/web-DGT/.galleries/downloads/dgt-en-cifras/publicaciones/Anuario_Estadistico_General/Anuario-General-2025.pdf",
            "total_nacional": sum(row["parque_motocicletas"] for row in park.values()),
        },
        "indicadores": {
            "matriculaciones_por_1000_habitantes": "matriculaciones nuevas acumuladas / población provincial * 1000",
            "matriculaciones_sobre_parque_pct": "matriculaciones nuevas acumuladas / parque de motocicletas * 100",
        },
        "alerta": {
            "umbral_pct": ALERTA_PARQUE_PCT,
            "criterio": "Marca REVISAR cuando las matriculaciones acumuladas igualan o superan el 25% del parque de referencia. Es un umbral operativo de revisión, no una anomalía confirmada ni una tasa de renovación.",
        },
        "limitaciones": [
            "Los nuevos se asignan por provincia de matriculación; el parque se asigna por provincia del parque registrado por la DGT.",
            "Los indicadores describen un flujo acumulado frente a denominadores de referencia, no cuotas de mercado ni tasas de renovación.",
            "No se calculan indicadores relativos para usados: son cambios de titularidad por provincia de domicilio del vehículo y no todas las compraventas.",
            "Las cifras elevadas se conservan; la alerta no excluye ni corrige registros.",
        ],
    }
    (output / "metodologia_indicadores_territoriales.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return rows, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provincial", required=True)
    parser.add_argument("--population", required=True)
    parser.add_argument("--park", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    rows, metadata = build_report(
        args.provincial, args.population, args.park, args.output_dir
    )
    print(json.dumps({
        "filas": len(rows),
        "periodos": metadata["periodos_matriculaciones"],
        "alertas": [row["provincia"] for row in rows if row["alerta_revision"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
