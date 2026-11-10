#!/usr/bin/env python3
"""Genera el informe reproducible de dispersión entre matriculación y domicilio del vehículo."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

MOTORCYCLE_CODES = {"50", "51"}
SEGOVIA_CODE = "SG"
MADRID_CODE = "M"


def read_csv(path, required):
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: faltan columnas {sorted(missing)}")
        return list(reader)


def integer(value, path, line):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{path}: recuento no entero en línea {line}") from None
    if number < 0:
        raise ValueError(f"{path}: recuento negativo en línea {line}")
    return number


def build_report(cross_path, provincial_path, output_dir):
    cross_rows = read_csv(cross_path, {
        "periodo", "COD_PROVINCIA_MAT", "provincia_matriculacion",
        "COD_PROVINCIA_VEH", "provincia_domicilio_vehiculo", "COD_TIPO", "recuento",
    })
    provincial_rows = read_csv(provincial_path, {
        "periodo", "ambito_provincial", "COD_PROVINCIA", "provincia",
        "COD_TIPO", "nuevo_usado", "recuento",
    })

    cross = Counter()
    names_mat = {}
    names_veh = {}
    periods = set()
    for line, row in enumerate(cross_rows, 2):
        vehicle_type = row["COD_TIPO"].strip()
        if vehicle_type not in MOTORCYCLE_CODES:
            raise ValueError(f"{cross_path}: COD_TIPO no permitido en línea {line}: {vehicle_type!r}")
        period = row["periodo"].strip()
        mat_code = row["COD_PROVINCIA_MAT"].strip() or "(vacío)"
        veh_code = row["COD_PROVINCIA_VEH"].strip() or "(vacío)"
        mat_name = row["provincia_matriculacion"].strip() or "Código vacío"
        veh_name = row["provincia_domicilio_vehiculo"].strip() or "Código vacío"
        for mapping, code, name, label in (
            (names_mat, mat_code, mat_name, "matriculación"),
            (names_veh, veh_code, veh_name, "domicilio"),
        ):
            if code in mapping and mapping[code] != name:
                raise ValueError(f"{cross_path}: nombres incompatibles para {label} {code}: {mapping[code]!r} / {name!r}")
            mapping[code] = name
        count = integer(row["recuento"], cross_path, line)
        cross[(period, mat_code, veh_code)] += count
        periods.add(period)

    provincial = Counter()
    for line, row in enumerate(provincial_rows, 2):
        if row["ambito_provincial"].strip() != "matriculacion" or row["nuevo_usado"].strip() != "Nuevo":
            continue
        if row["COD_TIPO"].strip() not in MOTORCYCLE_CODES:
            continue
        code = row["COD_PROVINCIA"].strip() or "(vacío)"
        provincial[(row["periodo"].strip(), code)] += integer(row["recuento"], provincial_path, line)

    cross_margins = Counter()
    for (period, mat_code, _), count in cross.items():
        cross_margins[(period, mat_code)] += count
    keys = set(cross_margins) | set(provincial)
    differences = {
        key: (provincial.get(key, 0), cross_margins.get(key, 0))
        for key in keys if provincial.get(key, 0) != cross_margins.get(key, 0)
    }
    if differences:
        sample = list(sorted(differences.items()))[:10]
        raise ValueError("El cruce no cuadra con el agregado provincial; diferencias (provincial, cruce): " + repr(sample))

    total = sum(cross.values())
    same = different = unknown = 0
    monthly = defaultdict(Counter)
    by_registration = defaultdict(Counter)
    flows = Counter()
    outgoing = Counter()
    incoming = Counter()
    matrix = Counter()
    destinations_segovia = Counter()
    segovia_monthly = defaultdict(Counter)

    for (period, mat_code, veh_code), count in cross.items():
        matrix[(mat_code, veh_code)] += count
        month = monthly[period]
        month["total"] += count
        registration = by_registration[mat_code]
        registration["total"] += count
        if mat_code == "(vacío)" or veh_code == "(vacío)":
            unknown += count
            month["domicilio_no_informado"] += count
            registration["domicilio_no_informado"] += count
        elif mat_code == veh_code:
            same += count
            month["misma_provincia"] += count
            registration["misma_provincia"] += count
        else:
            different += count
            month["otra_provincia"] += count
            registration["otra_provincia"] += count
            flows[(mat_code, veh_code)] += count
            outgoing[mat_code] += count
            incoming[veh_code] += count
        if mat_code == SEGOVIA_CODE:
            destinations_segovia[veh_code] += count
            sm = segovia_monthly[period]
            sm["total"] += count
            if veh_code == "(vacío)":
                sm["domicilio_no_informado"] += count
            elif veh_code == SEGOVIA_CODE:
                sm["Segovia"] += count
            elif veh_code == MADRID_CODE:
                sm["Madrid"] += count
            else:
                sm["otras_provincias"] += count

    known_total = same + different
    monthly_rows = []
    for period in sorted(periods):
        item = monthly[period]
        known = item["misma_provincia"] + item["otra_provincia"]
        monthly_rows.append({
            "periodo": period,
            "total": item["total"],
            "misma_provincia": item["misma_provincia"],
            "otra_provincia": item["otra_provincia"],
            "domicilio_no_informado": item["domicilio_no_informado"],
            "porcentaje_interprovincial_sobre_domicilios_conocidos": round(100 * item["otra_provincia"] / known, 4) if known else None,
        })

    ranking_rows = []
    for code, item in by_registration.items():
        known = item["misma_provincia"] + item["otra_provincia"]
        ranking_rows.append({
            "COD_PROVINCIA_MAT": code,
            "provincia_matriculacion": names_mat.get(code, "Código no catalogado"),
            "matriculaciones": item["total"],
            "misma_provincia": item["misma_provincia"],
            "domicilio_otra_provincia": item["otra_provincia"],
            "domicilio_no_informado": item["domicilio_no_informado"],
            "porcentaje_domicilio_externo_sobre_conocidos": round(100 * item["otra_provincia"] / known, 4) if known else None,
        })
    ranking_rows.sort(key=lambda row: (
        -(row["porcentaje_domicilio_externo_sobre_conocidos"] or 0),
        -row["domicilio_otra_provincia"], row["provincia_matriculacion"],
    ))

    # Balance por provincia: entradas menos salidas. Las entradas y salidas
    # solo incluyen pares con ambas provincias conocidas y distintas.
    balance_rows = []
    all_province_codes = sorted((set(names_mat) | set(names_veh)) - {"(vacío)"})
    for code in all_province_codes:
        registrations = by_registration.get(code, Counter())["total"]
        exits = outgoing[code]
        entries = incoming[code]
        net = entries - exits
        balance_rows.append({
            "COD_PROVINCIA": code,
            "provincia": names_mat.get(code, names_veh.get(code, "Código no catalogado")),
            "matriculaciones": registrations,
            "salidas_interprovinciales": exits,
            "entradas_interprovinciales": entries,
            "saldo_neto_entradas_menos_salidas": net,
            "salidas_sobre_matriculaciones_pct": round(100 * exits / registrations, 4) if registrations else None,
            "entradas_sobre_matriculaciones_pct": round(100 * entries / registrations, 4) if registrations else None,
            "saldo_neto_sobre_matriculaciones_pct": round(100 * net / registrations, 4) if registrations else None,
        })
    balance_rows.sort(key=lambda row: (row["saldo_neto_entradas_menos_salidas"], row["provincia"]))

    flow_rows = [{
        "COD_PROVINCIA_MAT": mat_code,
        "provincia_matriculacion": names_mat.get(mat_code, "Código no catalogado"),
        "COD_PROVINCIA_VEH": veh_code,
        "provincia_domicilio_vehiculo": names_veh.get(veh_code, "Código no catalogado"),
        "recuento": count,
    } for (mat_code, veh_code), count in sorted(
        flows.items(), key=lambda item: (-item[1], names_mat.get(item[0][0], item[0][0]), names_veh.get(item[0][1], item[0][1]))
    )]

    for code in set(names_mat) & set(names_veh):
        if names_mat[code] != names_veh[code]:
            raise ValueError(f"Nombres provinciales incompatibles entre dimensiones para {code}: {names_mat[code]!r} / {names_veh[code]!r}")

    # Matriz cuadrada completa: unión de códigos de ambas dimensiones,
    # incluyendo combinaciones sin registros y provincias sin flujo observado
    # en una de las dos dimensiones.
    all_codes = sorted((set(names_mat) | set(names_veh)) - {"(vacío)"})
    province_names = {**names_veh, **names_mat}
    matrix_rows = []
    for mat_code in all_codes:
        for veh_code in all_codes:
            matrix_rows.append({
                "COD_PROVINCIA_MAT": mat_code,
                "provincia_matriculacion": province_names[mat_code],
                "COD_PROVINCIA_VEH": veh_code,
                "provincia_domicilio_vehiculo": province_names[veh_code],
                "recuento": matrix[(mat_code, veh_code)],
            })

    segovia_total = by_registration.get(SEGOVIA_CODE, Counter())
    segovia_known = segovia_total["misma_provincia"] + segovia_total["otra_provincia"]
    segovia = {
        "matriculaciones": segovia_total["total"],
        "domicilio_segovia": segovia_total["misma_provincia"],
        "domicilio_otra_provincia": segovia_total["otra_provincia"],
        "domicilio_madrid": destinations_segovia[MADRID_CODE],
        "porcentaje_domicilio_externo_sobre_conocidos": round(100 * segovia_total["otra_provincia"] / segovia_known, 4) if segovia_known else None,
        "porcentaje_domicilio_madrid_sobre_total": round(100 * destinations_segovia[MADRID_CODE] / segovia_total["total"], 4) if segovia_total["total"] else None,
        "destinos": [
            {"COD_PROVINCIA_VEH": code, "provincia": names_veh.get(code, "Código no catalogado"), "recuento": count}
            for code, count in destinations_segovia.most_common(20)
        ],
        "evolucion_mensual": [
            {
                "periodo": period,
                "matriculaciones": segovia_monthly[period]["total"],
                "domicilio_segovia": segovia_monthly[period]["Segovia"],
                "domicilio_madrid": segovia_monthly[period]["Madrid"],
                "domicilio_otras_provincias": segovia_monthly[period]["otras_provincias"],
                "domicilio_no_informado": segovia_monthly[period]["domicilio_no_informado"],
                "porcentaje_madrid": round(100 * segovia_monthly[period]["Madrid"] / segovia_monthly[period]["total"], 4) if segovia_monthly[period]["total"] else None,
            } for period in sorted(periods) if segovia_monthly[period]["total"]
        ],
    }

    summary = {
        "periodos": sorted(periods),
        "ambito": "Matriculaciones nuevas de motocicletas, COD_TIPO 50 y 51, operación 1 y FEC_MATRICULA válida",
        "total_matriculaciones": total,
        "misma_provincia": same,
        "otra_provincia": different,
        "domicilio_no_informado": unknown,
        "porcentaje_misma_provincia": round(100 * same / total, 4) if total else None,
        "porcentaje_interprovincial_sobre_domicilios_conocidos": round(100 * different / known_total, 4) if known_total else None,
        "provincias_matriculacion": sum(code != "(vacío)" for code in names_mat),
        "provincias_domicilio": sum(code != "(vacío)" for code in names_veh),
        "matriz_filas": len(matrix_rows),
        "validacion": {
            "agregado_provincial_coincide": True,
            "diferencias": 0,
            "total_cruce": total,
            "total_agregado_provincial": sum(provincial.values()),
        },
        "evolucion_mensual": monthly_rows,
        "ranking_provincial": ranking_rows,
        "principales_flujos_interprovinciales": flow_rows[:30],
        "balance_interprovincial_por_provincia": balance_rows,
        "provincias_mayor_saldo_positivo": sorted(balance_rows, key=lambda row: (-row["saldo_neto_entradas_menos_salidas"], row["provincia"]))[:10],
        "provincias_mayor_saldo_negativo": balance_rows[:10],
        "segovia": segovia,
        "nota_metodologica": (
            "COD_PROVINCIA_MAT identifica la provincia de matriculación. "
            "COD_PROVINCIA_VEH identifica la provincia donde figura domiciliado el vehículo; "
            "no acredita residencia efectiva del comprador, lugar de compra o entrega, ni causa "
            "administrativa o comercial. Los porcentajes interprovinciales se calculan sobre "
            "registros con ambos códigos provinciales conocidos."
        ),
    }

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    def write_csv(filename, rows):
        if not rows:
            return
        with (output / filename).open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    write_csv("dispersion_provincias_mensual.csv", monthly_rows)
    write_csv("dispersion_provincias_ranking.csv", ranking_rows)
    write_csv("dispersion_provincias_flujos.csv", flow_rows)
    write_csv("dispersion_balance_provincial.csv", balance_rows)
    write_csv("matriz_dispersion_provincias.csv", matrix_rows)
    (output / "informe_dispersion_provincias.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cross", required=True, help="CSV del cruce de provincias de nuevas")
    parser.add_argument("--provincial", required=True, help="CSV provincial para validar totales")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary = build_report(args.cross, args.provincial, args.output_dir)
    print(json.dumps({
        "periodos": summary["periodos"],
        "total_matriculaciones": summary["total_matriculaciones"],
        "porcentaje_interprovincial": summary["porcentaje_interprovincial_sobre_domicilios_conocidos"],
        "matriz_filas": summary["matriz_filas"],
        "validacion": summary["validacion"],
        "segovia": summary["segovia"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
