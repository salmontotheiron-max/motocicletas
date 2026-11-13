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
MOTORCYCLE_CODES = frozenset({"50", "51"})
PROVINCES = {
    "A": "Alicante/Alacant", "AB": "Albacete", "AL": "Almería",
    "AV": "Ávila", "B": "Barcelona", "BA": "Badajoz",
    "BI": "Bizkaia", "BU": "Burgos", "C": "A Coruña",
    "CA": "Cádiz", "CC": "Cáceres", "CE": "Ceuta",
    "CO": "Córdoba", "CR": "Ciudad Real", "CS": "Castellón/Castelló",
    "CU": "Cuenca", "DS": "Desconocido", "EX": "Extranjero",
    "GC": "Las Palmas", "GI": "Girona", "GR": "Granada",
    "GU": "Guadalajara", "H": "Huelva", "HU": "Huesca",
    "IB": "Illes Balears", "J": "Jaén", "L": "Lleida",
    "LE": "León", "LO": "La Rioja", "LU": "Lugo",
    "M": "Madrid", "MA": "Málaga", "ML": "Melilla",
    "MU": "Murcia", "NA": "Navarra", "O": "Asturias",
    "OU": "Ourense", "P": "Palencia", "PO": "Pontevedra",
    "S": "Cantabria", "SA": "Salamanca", "SC": "Servicios Centrales",
    "SE": "Sevilla", "SG": "Segovia", "SO": "Soria",
    "SS": "Gipuzkoa", "T": "Tarragona", "TE": "Teruel",
    "TF": "Santa Cruz de Tenerife", "TO": "Toledo",
    "V": "Valencia/València", "VA": "Valladolid",
    "VI": "Araba/Álava", "Z": "Zaragoza", "ZA": "Zamora",
}
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
    provincial_counts = Counter()
    provincial_cross_counts = Counter()
    model_counts = Counter()
    opcounts = Counter()
    excluded = Counter()
    process_dates = []
    audit_rows = []
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
        # FEC_TRAMITE está en el campo 22 (offsets [157:165]).
        transaction_date = parse_date(values[22])
        operation = values[21]
        new_used = values[25]
        vehicle_type = values[7]
        province_vehicle = values[19]
        province_registration = values[20]
        brand_itv = values[3] or "(sin marca)"
        model_itv = values[4] or "(sin modelo)"

        if vehicle_type not in TARGET_TYPE_CODES:
            excluded[vehicle_type or "(vacío)"] += 1
            continue

        # Para nuevos, la referencia de matriculación es FEC_MATRICULA.
        # Para usados, se observa el cambio de titular mediante FEC_TRAMITE.
        # Una fecha de referencia posterior a FEC_PROCESO es incoherente:
        # se audita y se excluye el registro, sin sustituirla por otra fecha.
        future_matriculation = (
            new_used == "N" and matriculation_date is not None
            and matriculation_date > process_date
        )
        future_transaction = (
            transaction_date is not None and transaction_date > process_date
        )
        reference_date = (
            matriculation_date if new_used == "N"
            else transaction_date if new_used == "U"
            else None
        )
        invalid_future = future_matriculation or future_transaction

        if future_matriculation:
            audit_rows.append([
                path.name, number + 1, "FEC_MATRICULA_POSTERIOR_A_FEC_PROCESO",
                vehicle_type, operation, new_used,
                matriculation_date.isoformat(),
                transaction_date.isoformat() if transaction_date else "",
                process_date.isoformat(),
            ])
        if future_transaction:
            audit_rows.append([
                path.name, number + 1, "FEC_TRAMITE_POSTERIOR_A_FEC_PROCESO",
                vehicle_type, operation, new_used,
                matriculation_date.isoformat() if matriculation_date else "",
                transaction_date.isoformat(),
                process_date.isoformat(),
            ])
        if operation not in OPS:
            audit_rows.append([
                path.name, number + 1, "CLAVE_TRAMITE_NO_CATALOGADA",
                vehicle_type, operation, new_used,
                matriculation_date.isoformat() if matriculation_date else "",
                transaction_date.isoformat() if transaction_date else "",
                process_date.isoformat(),
            ])
        if new_used in ("N", "U") and reference_date is None:
            audit_rows.append([
                path.name, number + 1, "FECHA_REFERENCIA_NO_DISPONIBLE",
                vehicle_type, operation, new_used,
                matriculation_date.isoformat() if matriculation_date else "",
                transaction_date.isoformat() if transaction_date else "",
                process_date.isoformat(),
            ])

        if invalid_future:
            continue

        if operation == "1" and reference_date and reference_date.strftime("%Y-%m") >= START and new_used in ("N", "U"):
            reference_period = reference_date.strftime("%Y-%m")
            counts[(reference_period, vehicle_type, new_used, False)] += 1
            if vehicle_type in MOTORCYCLE_CODES:
                # En nuevos se clasifica por provincia de matriculación.
                # En usados se clasifica por provincia de domicilio del vehículo.
                province_scope, province_code = (
                    ("matriculacion", province_registration) if new_used == "N"
                    else ("domicilio_vehiculo", province_vehicle)
                )
                provincial_counts[(
                    reference_period, province_scope, province_code or "(vacío)",
                    vehicle_type, new_used
                )] += 1
                if new_used == "N":
                    # Contraste exploratorio: provincia de matriculación frente
                    # a provincia del domicilio registrado del vehículo.
                    provincial_cross_counts[(
                        reference_period, province_registration or "(vacío)",
                        province_vehicle or "(vacío)", vehicle_type
                    )] += 1
                province_scope, province_code = (
                    ("matriculacion", province_registration) if new_used == "N"
                    else ("domicilio_vehiculo", province_vehicle)
                )
                model_counts[(
                    reference_period, brand_itv, model_itv, vehicle_type,
                    new_used, "matriculacion_nueva" if new_used == "N" else "matriculacion_usada",
                    province_scope, province_code or "(vacío)"
                )] += 1
        if operation in OPS and transaction_date and transaction_date.strftime("%Y-%m") >= START:
            opcounts[(transaction_date.strftime("%Y-%m"), operation, False)] += 1
            if operation == "2":
                # COD_PROVINCIA_VEH es el domicilio registral, no la provincia de venta.
                model_counts[(
                    transaction_date.strftime("%Y-%m"), brand_itv, model_itv,
                    vehicle_type, new_used or "(vacío)", "transferencia",
                    "domicilio_vehiculo", province_vehicle or "(vacío)"
                )] += 1

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
    }, counts, provincial_counts, provincial_cross_counts, model_counts, opcounts, excluded, audit_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--inventory-file")
    parser.add_argument("--previous-dir")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    selected = select_latest_archives(args.input_dir, args.inventory_file)
    counts = Counter()
    provincial_counts = Counter()
    provincial_cross_counts = Counter()
    model_counts = Counter()
    opcounts = Counter()
    excluded = Counter()
    manifest = []
    audit_rows = []
    for period, archive in selected.items():
        info, month_counts, month_provincial, month_cross, month_models, month_ops, month_excluded, month_audit = process_archive(archive, period)
        manifest.append(info)
        counts.update(month_counts)
        provincial_counts.update(month_provincial)
        provincial_cross_counts.update(month_cross)
        model_counts.update(month_models)
        opcounts.update(month_ops)
        excluded.update(month_excluded)
        audit_rows.extend(month_audit)

    with (output / "matriculaciones_nuevos_usados_por_tipo.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["periodo", "COD_TIPO", "descripcion_tipo", "nuevo_usado", "recuento", "fecha_sustitutiva_con_asterisco"])
        for key, value in sorted(counts.items()):
            writer.writerow([key[0], key[1], TYPES[key[1]], "Nuevo" if key[2] == "N" else "Usado", value, "*" if key[3] else ""])

    with (output / "matriculaciones_motocicletas_por_provincia.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["periodo", "ambito_provincial", "COD_PROVINCIA", "provincia",
                         "COD_TIPO", "nuevo_usado", "recuento"])
        for key, value in sorted(provincial_counts.items()):
            period, scope, province_code, vehicle_type, new_used = key
            writer.writerow([
                period, scope, province_code,
                PROVINCES.get(province_code, "Código no catalogado"),
                vehicle_type, "Nuevo" if new_used == "N" else "Usado", value,
            ])

    with (output / "matriculaciones_motocicletas_cruce_provincias_nuevas.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["periodo", "COD_PROVINCIA_MAT", "provincia_matriculacion",
                         "COD_PROVINCIA_VEH", "provincia_domicilio_vehiculo",
                         "COD_TIPO", "recuento"])
        for key, value in sorted(provincial_cross_counts.items()):
            period, registration_code, vehicle_code, vehicle_type = key
            writer.writerow([
                period, registration_code,
                PROVINCES.get(registration_code, "Código no catalogado") if registration_code != "(vacío)" else "Código vacío",
                vehicle_code,
                PROVINCES.get(vehicle_code, "Código no catalogado") if vehicle_code != "(vacío)" else "Código vacío",
                vehicle_type, value,
            ])

    with (output / "matriculaciones_marca_modelo_segmento.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "periodo", "marca", "modelo", "COD_TIPO", "nuevo_usado",
            "tipo_registro", "ambito_provincial", "COD_PROVINCIA", "provincia",
            "recuento",
        ])
        for key, value in sorted(model_counts.items()):
            period, brand, model, vehicle_type, new_used, record_type, scope, province_code = key
            writer.writerow([
                period, brand, model, vehicle_type, new_used, record_type,
                scope, province_code,
                PROVINCES.get(province_code, "Código no catalogado") if province_code != "(vacío)" else "Código vacío",
                value,
            ])

    with (output / "tipo_operacion.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["periodo", "CLAVE_TRAMITE", "descripcion_operacion", "recuento", "fecha_sustitutiva_con_asterisco"])
        for key, value in sorted(opcounts.items()):
            writer.writerow([key[0], key[1], OPS[key[1]], value, "*" if key[2] else ""])

    with (output / "auditoria_registros.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["archivo", "linea_txt", "incidencia", "COD_TIPO", "CLAVE_TRAMITE",
                         "NUEVO_USADO", "FEC_MATRICULA", "FEC_TRAMITE", "FEC_PROCESO"])
        writer.writerows(audit_rows)

    def write_comparison(previous_name, current_name, output_name, key_columns):
        if not args.previous_dir:
            return
        previous_path = Path(args.previous_dir) / previous_name
        current_path = output / current_name
        if not previous_path.exists() or not current_path.exists():
            return
        def read_counts(file_path):
            result = Counter()
            with file_path.open("r", newline="", encoding="utf-8-sig") as source:
                for row in csv.DictReader(source):
                    key = tuple(row.get(column, "") for column in key_columns)
                    result[key] += int(row.get("recuento", "0") or 0)
            return result
        old_counts = read_counts(previous_path)
        new_counts = read_counts(current_path)
        with (output / output_name).open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(key_columns + ["recuento_anterior", "recuento_corregido", "diferencia"])
            for key in sorted(set(old_counts) | set(new_counts)):
                old_value, new_value = old_counts[key], new_counts[key]
                writer.writerow(list(key) + [old_value, new_value, new_value - old_value])

    write_comparison(
        "matriculaciones_nuevos_usados_por_tipo.csv",
        "matriculaciones_nuevos_usados_por_tipo.csv",
        "comparacion_matriculaciones.csv",
        ["periodo", "COD_TIPO", "descripcion_tipo", "nuevo_usado", "fecha_sustitutiva_con_asterisco"],
    )
    write_comparison(
        "tipo_operacion.csv", "tipo_operacion.csv", "comparacion_operaciones.csv",
        ["periodo", "CLAVE_TRAMITE", "descripcion_operacion", "fecha_sustitutiva_con_asterisco"],
    )

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
        "registros_desglose_marca_modelo": sum(model_counts.values()),
        "modelos_observados": len({(key[1], key[2]) for key in model_counts}),
        "filtro_cod_tipo": sorted(TARGET_TYPE_CODES),
        "registros_excluidos_por_cod_tipo": sum(excluded.values()),
        "exclusiones_por_codigo": dict(sorted(excluded.items())),
        "registros_auditados_con_incidencias": len(audit_rows),
        "incidencias_por_tipo": dict(sorted(Counter(row[2] for row in audit_rows).items())),
        "nota_fecha": "En nuevos se utiliza FEC_MATRICULA. En usados se utiliza FEC_TRAMITE para observar los cambios de titular. Si FEC_MATRICULA (nuevos) o FEC_TRAMITE (cualquier operación) es posterior a FEC_PROCESO, se excluye el registro y se anota en auditoría. No se sustituyen fechas futuras por FEC_PROCESO.",
        "privacidad": "No exportar campos personales ni identificadores sensibles.",
        "duplicados": "No se eliminan filas idénticas automáticamente.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
