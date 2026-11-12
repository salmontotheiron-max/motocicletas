#!/usr/bin/env python3
"""Detecta marcas observadas en nuevas matriculaciones DGT sin exportar datos personales."""
import argparse
import csv
import hashlib
import json
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from descargar_matraba_mensual import inspect_zip
from procesar_matraba_mensual import START, WIDTHS, parse_date, select_latest_archives

# Motocicletas (50/51) y ciclomotores (90/91). Motocarros, triciclos
# automóviles y cuadriciclos quedan fuera del universo principal.
DISCOVERY_TYPE_CODES = frozenset({"50", "51", "90", "91"})
TYPE_LABELS = {
    "50": "Motocicleta de 2 ruedas sin sidecar",
    "51": "Motocicleta con sidecar",
    "90": "Ciclomotor de 2 ruedas",
    "91": "Ciclomotor de 3 ruedas",
}
BRAND_START = sum(WIDTHS[:3])
BRAND_END = BRAND_START + WIDTHS[3]
TYPE_START = sum(WIDTHS[:7])
TYPE_END = TYPE_START + WIDTHS[7]
OP_START = sum(WIDTHS[:21])
OP_END = OP_START + WIDTHS[21]
NEW_USED_START = sum(WIDTHS[:25])
NEW_USED_END = NEW_USED_START + WIDTHS[25]
MATRICULATION_START = 0
MATRICULATION_END = WIDTHS[0]
PROCESS_START = sum(WIDTHS[:68])
PROCESS_END = PROCESS_START + WIDTHS[68]


def normalize_brand(value):
    """Normalización conservadora para comparar cadenas, no para fusionar marcas."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def inventory_brand_index(registry_path):
    data = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    index = {}
    for brand in data.get("brands", []):
        canonical = brand.get("canonical_name", "")
        normalized = normalize_brand(canonical)
        if normalized:
            index.setdefault(normalized, []).append({
                "brand_id": brand.get("brand_id"),
                "canonical_name": canonical,
                "market_status": brand.get("market_status", "unknown"),
            })
    return index


def extract_archive(path, period):
    payload = path.read_bytes()
    txt, error, record_count = inspect_zip(payload)
    if error:
        raise ValueError(f"{path.name}: {error}")
    lines = txt.replace(b"\r\n", b"\n").split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()

    counts = Counter()
    variants = defaultdict(Counter)
    excluded = Counter()
    invalid_dates = 0
    for line_number, raw in enumerate(lines[1:], 2):
        row = raw.decode("cp1252")
        vehicle_type = row[TYPE_START:TYPE_END].strip()
        if vehicle_type not in DISCOVERY_TYPE_CODES:
            excluded[vehicle_type or "(vacío)"] += 1
            continue

        operation = row[OP_START:OP_END].strip()
        new_used = row[NEW_USED_START:NEW_USED_END].strip()
        # Para detectar presencia comercial se usan solo matriculaciones
        # ordinarias de vehículos nuevos. Transferencias y usados no prueban
        # una comercialización nueva en el periodo.
        if operation != "1" or new_used != "N":
            continue

        matriculation_date = parse_date(row[MATRICULATION_START:MATRICULATION_END].strip())
        process_date = parse_date(row[PROCESS_START:PROCESS_END].strip())
        if matriculation_date is None or process_date is None or matriculation_date > process_date:
            invalid_dates += 1
            continue
        if matriculation_date.strftime("%Y-%m") < START:
            continue

        raw_brand = row[BRAND_START:BRAND_END].strip()
        normalized = normalize_brand(raw_brand)
        if not normalized:
            excluded["marca_vacía"] += 1
            continue

        observed_period = matriculation_date.strftime("%Y-%m")
        counts[(observed_period, vehicle_type, normalized)] += 1
        variants[(observed_period, vehicle_type, normalized)][raw_brand] += 1

    digest = hashlib.sha256(payload).hexdigest()
    expected = path.stem.rsplit("_", 1)[-1]
    if digest != expected:
        raise ValueError(f"{path.name}: SHA-256 no coincide con el nombre del snapshot")
    info = {
        "periodo_archivo": period,
        "archivo": path.name,
        "sha256": digest,
        "registros_leidos": record_count,
    }
    return info, counts, variants, excluded, invalid_dates


def build_outputs(input_dir, output_dir, inventory_file, registry_file):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    selected = select_latest_archives(input_dir, inventory_file)
    known = inventory_brand_index(registry_file)

    counts = Counter()
    variants = defaultdict(Counter)
    excluded = Counter()
    invalid_dates = 0
    manifest = []
    for period, archive in selected.items():
        info, month_counts, month_variants, month_excluded, month_invalid = extract_archive(archive, period)
        manifest.append(info)
        counts.update(month_counts)
        for key, value in month_variants.items():
            variants[key].update(value)
        excluded.update(month_excluded)
        invalid_dates += month_invalid

    brand_totals = Counter()
    brand_periods = defaultdict(set)
    brand_types = defaultdict(Counter)
    brand_variants = defaultdict(Counter)
    for (period, vehicle_type, normalized), count in counts.items():
        brand_totals[normalized] += count
        brand_periods[normalized].add(period)
        brand_types[normalized][vehicle_type] += count
        brand_variants[normalized].update(variants[(period, vehicle_type, normalized)])

    observations = []
    candidates = []
    for normalized in sorted(brand_totals):
        matches = known.get(normalized, [])
        raw_variants = [
            {"valor_observado": value, "recuento": count}
            for value, count in brand_variants[normalized].most_common()
        ]
        record = {
            "marca_normalizada": normalized,
            "variantes_observadas": raw_variants,
            "recuento_nuevas_matriculaciones": brand_totals[normalized],
            "periodos_observados": sorted(brand_periods[normalized]),
            "tipos_vehiculo": dict(sorted(brand_types[normalized].items())),
            "coincidencias_inventario": matches,
            "estado_revision": "ya_en_inventario" if matches else "nueva_candidata",
            "fuente": "DGT MATRABA microdatos mensuales",
            "criterio": "CLAVE_TRAMITE=1; NUEVO_USADO=N; COD_TIPO en 50,51,90,91",
            "nota": "Una observación de matriculación no acredita por sí sola comercialización vigente, importador actual ni red de venta o posventa.",
        }
        observations.append(record)
        if not matches:
            candidates.append(record)

    with (output / "marcas_motocicletas_observadas.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "marca_normalizada", "variantes_observadas", "recuento_nuevas_matriculaciones",
            "periodos_observados", "COD_TIPO_y_recuentos", "estado_revision",
        ])
        for item in observations:
            writer.writerow([
                item["marca_normalizada"],
                " | ".join(f'{v["valor_observado"]} ({v["recuento"]})' for v in item["variantes_observadas"]),
                item["recuento_nuevas_matriculaciones"],
                ", ".join(item["periodos_observados"]),
                json.dumps(item["tipos_vehiculo"], ensure_ascii=False, sort_keys=True),
                item["estado_revision"],
            ])

    payload = {
        "esquema": 1,
        "fuente": "DGT MATRABA microdatos mensuales",
        "inventario_consultado": str(registry_file),
        "criterio_inicio": START,
        "criterio_descubrimiento": {
            "CLAVE_TRAMITE": "1",
            "NUEVO_USADO": "N",
            "COD_TIPO": sorted(DISCOVERY_TYPE_CODES),
            "campo_marca": "MARCA_ITV (campo de ancho fijo 30 caracteres)",
        },
        "politica": "Coincidencia exacta tras normalización textual conservadora. No se aplican alias automáticos ni se fusionan marcas similares.",
        "observaciones": observations,
        "candidatas_nuevas": candidates,
        "nota": "Las candidatas requieren revisión manual y contraste con ANESDOR, fuentes sectoriales y fuentes oficiales de fabricante/importador. Los datos DGT no acreditan red comercial.",
    }
    (output / "marcas_candidatas_revision.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "archivos_procesados": len(manifest),
        "periodos_procesados": sorted(selected),
        "marcas_observadas": len(observations),
        "marcas_ya_en_inventario": sum(1 for item in observations if item["estado_revision"] == "ya_en_inventario"),
        "nuevas_candidatas_revision": len(candidates),
        "nuevas_matriculaciones_contabilizadas": sum(brand_totals.values()),
        "registros_excluidos_por_tipo": dict(sorted(excluded.items())),
        "registros_con_fecha_invalida_o_incoherente": invalid_dates,
        "archivos": manifest,
        "privacidad": "Solo agregados por marca, periodo y tipo de vehículo. No se exportan datos personales, domicilios, matrículas ni identificadores de vehículo.",
    }
    (output / "resumen_marcas_dgt.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--inventory-file", required=True)
    parser.add_argument("--registry-file", default="fuentes_red_comercial.json")
    args = parser.parse_args()
    summary = build_outputs(args.input_dir, args.output_dir, args.inventory_file, args.registry_file)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
