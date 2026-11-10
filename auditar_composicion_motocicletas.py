#!/usr/bin/env python3
"""Auditoría agregada de composición de motocicletas nuevas MATRABA (50/51)."""
import argparse
import csv
import hashlib
import zipfile
from collections import Counter
from pathlib import Path

from descargar_matraba_mensual import inspect_zip
from procesar_matraba_mensual import (
    MOTORCYCLE_CODES, PROVINCES, START, WIDTHS, parse_date,
    period_from_name, select_latest_archives,
)

# Índices de campos según el diseño MATRABA (base cero).
DIMENSIONS = {
    "clase_matricula": (1, 1, "clase de matrícula"),
    "marca": (3, 10, "marca ITV"),
    "modelo": (4, 10, "modelo ITV"),
    "procedencia": (5, 10, "procedencia ITV"),
    "cilindrada_cc": (9, 10, "cilindrada en cm³"),
    "titular_fisico_juridico": (26, 10, "naturaleza del titular"),
    "servicio": (28, 10, "servicio del vehículo"),
    "municipio": (30, 20, "municipio del domicilio registral"),
    "renting": (34, 10, "indicador de renting"),
}
MINIMUMS = {"municipio": 20}
CLASS_LABELS = {
    "0": "Ordinaria", "1": "Turística", "2": "Remolque",
    "3": "Diplomática", "4": "Reservada", "5": "Vehículo especial",
    "6": "Ciclomotor", "7": "Transporte temporal", "8": "Histórica",
}
ORIGIN_LABELS = {
    "0": "Fabricación nacional", "1": "Importación no comunitaria",
    "2": "Subasta", "3": "Importación UE",
}
SERVICE_LABELS = {
    "A00": "Público: sin especificar",
    "A01": "Público: alquiler sin conductor",
    "A02": "Público: alquiler con conductor",
    "A03": "Público: aprendizaje de conducción",
    "A04": "Público: taxi",
    "A05": "Público: auxilio en carretera",
    "A07": "Público: ambulancia",
    "A08": "Público: funerario",
    "A09": "Particular: obras",
    "A10": "Público: mercancías peligrosas",
    "A11": "Público: basurero",
    "A12": "Público: transporte escolar",
    "A13": "Público: policía",
    "A14": "Público: bomberos",
    "A15": "Público: protección civil y salvamento",
    "A16": "Público: defensa",
    "A18": "Público: actividad económica",
    "A20": "Público: mercancías perecederas",
    "B00": "Particular: sin especificar",
    "B06": "Particular: agrícola",
    "B07": "Particular: código B07",
    "B09": "Particular: obras",
    "B17": "Particular: vivienda",
    "B18": "Particular: actividad económica",
    "B19": "Particular: recreativo",
    "B21": "Particular: vehículo para ferias",
}


def safe_published_count(count, dimension):
    """No publica ni siquiera el total agregado si sigue bajo el umbral."""
    threshold = MINIMUMS.get(dimension, 10)
    return count if count >= threshold else ""


def read_dispersal(path):
    totals, external = Counter(), Counter()
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            province = row.get("COD_PROVINCIA_MAT", "")
            if not province or province == "(vacío)":
                continue
            count = int(row.get("recuento", "0") or 0)
            totals[province] += count
            if row.get("COD_PROVINCIA_MAT") != row.get("COD_PROVINCIA_VEH"):
                external[province] += count
    return {
        code for code, total in totals.items()
        if total and external[code] / total > 0.20
    }


def extract_rows(archive_path):
    payload = archive_path.read_bytes()
    text, error, _ = inspect_zip(payload)
    expected_digest = archive_path.stem.rsplit("_", 1)[-1]
    if hashlib.sha256(payload).hexdigest() != expected_digest:
        raise ValueError(f"{archive_path.name}: SHA-256 no coincide con el nombre del snapshot")
    if error:
        raise ValueError(f"{archive_path.name}: {error}")
    lines = text.replace(b"\r\n", b"\n").split(b"\n")
    if lines and not lines[-1]:
        lines.pop()
    for line_number, raw in enumerate(lines[1:], 2):
        row = raw.decode("cp1252")
        values, offset = [], 0
        for width in WIDTHS:
            values.append(row[offset:offset + width].strip())
            offset += width
        date = parse_date(values[0])
        process_date = parse_date(values[68])
        transaction_date = parse_date(values[22])
        # Mismo universo del informe territorial: operación 1, nuevo N,
        # tipos 50/51 y FEC_MATRICULA no posterior a FEC_PROCESO.
        if (values[7] not in MOTORCYCLE_CODES or values[21] != "1"
                or values[25] != "N" or date is None or process_date is None
                or date > process_date
                or (transaction_date is not None and transaction_date > process_date)
                or date.strftime("%Y-%m") < START):
            continue
        province = values[20] or "(vacío)"
        yield date.strftime("%Y-%m"), province, values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--cross", required=True,
                        help="CSV de cruce provincia de matriculación/domicilio")
    parser.add_argument("--output", required=True)
    parser.add_argument("--inventory-file")
    args = parser.parse_args()

    dispersal = read_dispersal(args.cross)
    selected = select_latest_archives(args.input_dir, args.inventory_file)
    counts = Counter()
    denominators = Counter()
    for period, archive in selected.items():
        for month, province, values in extract_rows(archive):
            if month != period:
                # El archivo mensual contiene trámites retrospectivos; se asigna
                # el periodo por FEC_MATRICULA, no por mes del ZIP.
                pass
            denominators[("NACIONAL", month)] += 1
            denominators[(province, month)] += 1
            for dimension, (index, threshold, _) in DIMENSIONS.items():
                category = values[index] or "(no informado)"
                if dimension == "clase_matricula":
                    category = CLASS_LABELS.get(category, f"Código {category}")
                elif dimension == "procedencia":
                    category = ORIGIN_LABELS.get(category, f"Código {category}")
                elif dimension == "servicio":
                    category = SERVICE_LABELS.get(category, category)
                elif dimension == "titular_fisico_juridico":
                    category = {"D": "Persona física", "X": "Persona jurídica"}.get(category, category)
                elif dimension == "renting":
                    category = {"S": "Renting", "N": "No renting"}.get(category, category)
                counts[("NACIONAL", month, dimension, category)] += 1
                counts[(province, month, dimension, category)] += 1

    # Añade una vista acumulada enero-septiembre. La supresión se aplica
    # después de acumular, evitando ocultar marcas/modelos por umbrales mensuales.
    cumulative_counts = Counter()
    cumulative_denominators = Counter()
    for (province, month, dimension, category), count in counts.items():
        cumulative_counts[(province, "2026-01/09", dimension, category)] += count
    for (province, month), count in denominators.items():
        cumulative_denominators[(province, "2026-01/09")] += count
    counts.update(cumulative_counts)
    denominators.update(cumulative_denominators)

    target_provinces = set(dispersal) | {"SG"}
    rows = []
    for key, count in sorted(counts.items()):
        province, period, dimension, category = key
        if province != "NACIONAL" and province not in target_provinces:
            continue
        threshold = MINIMUMS.get(dimension, 10)
        if count >= threshold:
            published_category = category
            published_count = count
        else:
            published_category = f"SUPRIMIDO (<{threshold})"
            published_count = count
        rows.append((period, province,
                     "Nacional" if province == "NACIONAL" else PROVINCES.get(province, province),
                     dimension, DIMENSIONS[dimension][2],
                     published_category, published_count,
                     denominators[(province, period)]))

    # Agrupa las categorías de baja frecuencia en una sola celda suprimida.
    merged = Counter()
    for period, code, name, dimension, label, category, count, total in rows:
        merged[(period, code, name, dimension, label, category, total)] += count
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["periodo", "COD_PROVINCIA_MAT", "provincia",
                         "dimension", "descripcion_dimension", "categoria",
                         "recuento", "total_motocicletas_nuevas"])
        for key, count in sorted(merged.items()):
            published_count = safe_published_count(count, key[3])
            writer.writerow(list(key[:-1]) + [published_count, key[-1]])


if __name__ == "__main__":
    main()
