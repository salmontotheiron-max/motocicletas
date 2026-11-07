#!/usr/bin/env python3
"""Procesa la última captura mensual válida de cada periodo MATRABA."""
import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

from descargar_matraba_mensual import inspect_zip

START = "2026-01"
WIDTHS = [8,1,8,30,22,1,21,2,1,5,6,6,6,3,2,2,2,2,24,2,2,1,8,5,8,1,1,9,3,5,30,7,3,5,1,1,1,1,1,1,11,25,25,35,70,6,6,4,4,3,8,4,4,4,6,30,50,35,25,35,4,4,4,1,25,1,4,25,8]
assert len(WIDTHS) == 69 and sum(WIDTHS) == 714

TYPES = {
    "50": "Motocicleta de 2 ruedas sin sidecar",
    "51": "Motocicleta con sidecar",
    "52": "Motocarro",
    "53": "Automóvil de 3 ruedas",
    "54": "Cuadriciclo pesado",
    "90": "Ciclomotor de 2 ruedas",
    "91": "Ciclomotor de 3 ruedas",
    "92": "Cuadriciclo ligero",
}
TARGET_TYPE_CODES = frozenset(TYPES)
OPS = {
    "1": "Matriculación ordinaria y de ciclomotores",
    "2": "Transferencia", "3": "Baja definitiva",
    "4": "Baja definitiva por Plan Renove", "5": "Rematriculación",
    "6": "Baja temporal",
    "7": "Baja definitiva por exportación y tránsito comunitario",
    "8": "Matriculación de vehículo especial",
    "9": "Matriculación temporal", "A": "Prórroga de matrícula temporal",
    "B": "Paso de matrícula temporal a definitiva",
}


def parse_date(value):
    try:
        return datetime.strptime(value, "%d%m%Y").date()
    except (ValueError, TypeError):
        return None


def load_capture_times(inventory_path):
    if not inventory_path or not Path(inventory_path).exists():
        return {}
    data = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    times = {}
    for execution in data.get("ejecuciones", []):
        captured = execution.get("fecha_captura_utc", "")
        for item in execution.get("capturas", []):
            name = Path(item.get("archivo", "")).name
            if name and item.get("estado") == "descargado_validado":
                times[name] = captured
    return times


def period_from_name(path):
    match = re.fullmatch(r"export_mensual_mat_(\d{4})(\d{2})_([0-9a-f]{64})\.zip", path.name)
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}"


def select_latest_archives(input_dir, inventory_path=None):
    capture_times = load_capture_times(inventory_path)
    candidates = {}
    for path in Path(input_dir).rglob("*.zip"):
        period = period_from_name(path)
        if not period or period < START:
            continue
        captured = capture_times.get(path.name, "")
        current = candidates.get(period)
        rank = (captured, path.name)
        if current is None or rank > current[0]:
            candidates[period] = (rank, path)
    return {period: pair[1] for period, pair in sorted(candidates.items())}


def process_archive(path, period):
    payload = path.read_bytes()
    txt, error, record_count = inspect_zip(payload)
    if error:
        raise ValueError(f"{path.name}: {error}")
    lines = txt.replace(b"\r\n", b"\n").split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    rows = [line.decode("cp1252") for line in lines[1:]]
    counts = Counter()
    opcounts = Counter()
    excluded = Counter()
    process_dates = []
    for number, row in enumerate(rows, 1):
        values = []
        offset = 0
        for width in WIDTHS:
            values.append(row[offset:offset + width].strip())
            offset += width
        process_date = parse_date(values[68])
        if process_date is None:
            raise ValueError(f"{path.name}:{number}: FEC_PROCESO inválida")
        process_dates.append(process_date.isoformat())
        matriculation_date = parse_date(values[0])
        transaction_date = parse_date(values[2])
        operation = values[21]
        new_used = values[25]
        vehicle_type = values[7]

        if vehicle_type not in TARGET_TYPE_CODES:
            excluded[vehicle_type or "(vacío)"] += 1
            continue

        reference_date = (
            matriculation_date if new_used == "N"
            else transaction_date if transaction_date and transaction_date <= process_date
            else process_date if new_used == "U"
            else None
        )
        substitute = new_used == "U" and (
            not transaction_date or transaction_date > process_date
        )

        if operation == "1" and reference_date and reference_date.strftime("%Y-%m") >= START and new_used in ("N", "U"):
            counts[(reference_date.strftime("%Y-%m"), vehicle_type, new_used, substitute)] += 1
        if operation in OPS and reference_date and reference_date.strftime("%Y-%m") >= START:
            opcounts[(reference_date.strftime("%Y-%m"), operation, substitute)] += 1

    digest = hashlib.sha256(payload).hexdigest()
    expected_digest = path.stem.rsplit("_", 1)[-1]
    if digest != expected_digest:
        raise ValueError(f"{path.name}: SHA-256 no coincide con el nombre del snapshot")
    return {
        "archivo": path.name,
        "periodo_fuente": period,
        "sha256": digest,
        "bytes_zip": len(payload),
        "registros": record_count,
        "fec_proceso_min": min(process_dates) if process_dates else None,
        "fec_proceso_max": max(process_dates) if process_dates else None,
    }, counts, opcounts, excluded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--inventory-file")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    selected = select_latest_archives(args.input_dir, args.inventory_file)
    counts = Counter()
    opcounts = Counter()
    excluded = Counter()
    manifest = []
    for period, archive in selected.items():
        info, month_counts, month_ops, month_excluded = process_archive(archive, period)
        manifest.append(info)
        counts.update(month_counts)
        opcounts.update(month_ops)
        excluded.update(month_excluded)

    with (output / "matriculaciones_nuevos_usados_por_tipo.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["periodo", "COD_TIPO", "descripcion_tipo", "nuevo_usado", "recuento", "fecha_sustitutiva_con_asterisco"])
        for key, value in sorted(counts.items()):
            writer.writerow([key[0], key[1], TYPES[key[1]], "Nuevo" if key[2] == "N" else "Usado", value, "*" if key[3] else ""])

    with (output / "tipo_operacion.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["periodo", "CLAVE_TRAMITE", "descripcion_operacion", "recuento", "fecha_sustitutiva_con_asterisco"])
        for key, value in sorted(opcounts.items()):
            writer.writerow([key[0], key[1], OPS[key[1]], value, "*" if key[2] else ""])

    available = sorted(selected.keys())
    (output / "manifest.json").write_text(json.dumps({
        "modelo": "mensual",
        "criterio_inicio": START,
        "criterio_version": "última captura válida por periodo según fecha de captura; si falta, nombre de archivo",
        "filtro_cod_tipo": sorted(TARGET_TYPE_CODES),
        "archivos": manifest,
        "capturas_validas_procesadas": len(manifest),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "periodos.json").write_text(json.dumps({
        "periodos_disponibles": available,
        "mensaje_sin_datos": "Dato no disponible en DGT",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "resumen.json").write_text(json.dumps({
        "archivos_procesados": len(manifest),
        "periodos_procesados": len(selected),
        "registros_matriculaciones": sum(counts.values()),
        "registros_operaciones": sum(opcounts.values()),
        "filtro_cod_tipo": sorted(TARGET_TYPE_CODES),
        "registros_excluidos_por_cod_tipo": sum(excluded.values()),
        "exclusiones_por_codigo": dict(sorted(excluded.items())),
        "nota_fecha": "* En usados se utiliza FEC_TRAMITACION cuando es válida y no posterior a FEC_PROCESO; en caso contrario se usa FEC_PROCESO y se marca con asterisco.",
        "privacidad": "No exportar campos personales ni identificadores sensibles.",
        "duplicados": "No se eliminan filas idénticas automáticamente.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
