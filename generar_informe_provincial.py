#!/usr/bin/env python3
"""Genera rankings y series territoriales a partir del agregado provincial MATRABA."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_SCOPE = {
    ("matriculacion", "Nuevo"),
    ("domicilio_vehiculo", "Usado"),
}


def load_rows(path):
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {
            "periodo", "ambito_provincial", "COD_PROVINCIA",
            "provincia", "COD_TIPO", "nuevo_usado", "recuento",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Faltan columnas: " + ", ".join(sorted(missing)))
        rows = []
        for line_number, row in enumerate(reader, 2):
            scope = row["ambito_provincial"].strip()
            new_used = row["nuevo_usado"].strip()
            if (scope, new_used) not in EXPECTED_SCOPE:
                raise ValueError(
                    f"Fila {line_number}: ámbito y condición incompatibles "
                    f"({scope!r}, {new_used!r})"
                )
            code = row["COD_PROVINCIA"].strip()
            province = row["provincia"].strip()
            if not province:
                province = "Código provincial vacío" if not code else "Nombre no catalogado"
            try:
                count = int(row["recuento"])
            except (TypeError, ValueError):
                raise ValueError(f"Fila {line_number}: recuento no entero") from None
            if count < 0:
                raise ValueError(f"Fila {line_number}: recuento negativo")
            rows.append({
                "periodo": row["periodo"].strip(),
                "ambito_provincial": scope,
                "COD_PROVINCIA": code or "(vacío)",
                "provincia": province,
                "COD_TIPO": row["COD_TIPO"].strip(),
                "nuevo_usado": new_used,
                "recuento": count,
            })
    return rows


def build_reports(rows, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    totals = Counter()
    months = defaultdict(set)
    monthly = Counter()
    names_by_code = defaultdict(set)
    blank_codes = Counter()

    for row in rows:
        scope = row["ambito_provincial"]
        code = row["COD_PROVINCIA"]
        name = row["provincia"]
        key = (scope, code, name)
        totals[key] += row["recuento"]
        months[key].add(row["periodo"])
        monthly[(row["periodo"], scope, code, name)] += row["recuento"]
        names_by_code[(scope, code)].add(name)
        if code == "(vacío)":
            blank_codes[(scope, name)] += row["recuento"]

    for (scope, code), names in names_by_code.items():
        if len(names) > 1:
            raise ValueError(
                f"El código {code!r} del ámbito {scope!r} tiene varios nombres: "
                + ", ".join(sorted(names))
            )

    rankings = []
    concentration = {}
    for scope in ("matriculacion", "domicilio_vehiculo"):
        group = [
            (code, name, count)
            for (row_scope, code, name), count in totals.items()
            if row_scope == scope
        ]
        group.sort(key=lambda item: (-item[2], item[1], item[0]))
        denominator = sum(item[2] for item in group)
        previous_count = None
        current_rank = 0
        for index, (code, name, count) in enumerate(group, 1):
            if count != previous_count:
                current_rank = index
            previous_count = count
            rankings.append({
                "ambito_provincial": scope,
                "COD_PROVINCIA": code,
                "provincia": name,
                "recuento": count,
                "peso_porcentual": round(100 * count / denominator, 4) if denominator else 0,
                "puesto": current_rank,
                "periodos_con_datos": len(months[(scope, code, name)]),
            })
        concentration[scope] = {
            "total": denominator,
            "provincias": len(group),
            "top_5_recuento": sum(item[2] for item in group[:5]),
            "top_5_porcentaje": round(
                100 * sum(item[2] for item in group[:5]) / denominator, 4
            ) if denominator else 0,
            "top_10_recuento": sum(item[2] for item in group[:10]),
            "top_10_porcentaje": round(
                100 * sum(item[2] for item in group[:10]) / denominator, 4
            ) if denominator else 0,
        }

    with (output / "ranking_motocicletas_provincia.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        fields = [
            "ambito_provincial", "COD_PROVINCIA", "provincia", "recuento",
            "peso_porcentual", "puesto", "periodos_con_datos",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rankings)

    monthly_rows = []
    monthly_totals = Counter()
    for (period, scope, code, name), count in monthly.items():
        monthly_totals[(period, scope)] += count
        monthly_rows.append({
            "periodo": period,
            "ambito_provincial": scope,
            "COD_PROVINCIA": code,
            "provincia": name,
            "recuento": count,
        })
    monthly_rows.sort(key=lambda row: (
        row["periodo"], row["ambito_provincial"], row["provincia"], row["COD_PROVINCIA"]
    ))
    for row in monthly_rows:
        denominator = monthly_totals[(row["periodo"], row["ambito_provincial"])]
        row["peso_porcentual"] = round(
            100 * row["recuento"] / denominator, 4
        ) if denominator else 0

    with (output / "evolucion_motocicletas_provincia.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        fields = [
            "periodo", "ambito_provincial", "COD_PROVINCIA",
            "provincia", "recuento", "peso_porcentual",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(monthly_rows)

    summary = {
        "periodos": sorted({row["periodo"] for row in rows}),
        "criterio_geografico": {
            "matriculacion": "Provincia de matriculación del vehículo nuevo (COD_PROVINCIA_MAT).",
            "domicilio_vehiculo": "Provincia de domicilio del vehículo usado (COD_PROVINCIA_VEH).",
        },
        "totales_y_concentracion": concentration,
        "codigos_provinciales_vacios": [
            {
                "ambito_provincial": scope,
                "provincia": name,
                "recuento": count,
            }
            for (scope, name), count in sorted(blank_codes.items())
        ],
        "nota_interpretacion": (
            "Los recuentos de nuevos y usados usan ámbitos geográficos distintos. "
            "Los usados representan cambios de titularidad y no todas las compraventas."
        ),
    }
    (output / "resumen_territorial.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV provincial generado por MATRABA")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary = build_reports(load_rows(args.input), args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
