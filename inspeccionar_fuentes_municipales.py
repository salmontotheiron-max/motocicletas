#!/usr/bin/env python3
"""Inspecciona las descargas municipales oficiales del INE y la DGT sin alterar los datos."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from openpyxl import load_workbook


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ine", required=True, type=Path)
    parser.add_argument("--dgt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    lines: list[str] = []
    lines.append("INSPECCIÓN DE FUENTES MUNICIPALES OFICIALES")
    lines.append(f"INE CSV: {args.ine.name} ({args.ine.stat().st_size} bytes)")
    lines.append(f"DGT XLSX: {args.dgt.name} ({args.dgt.stat().st_size} bytes)")
    lines.append("")

    # El CSV oficial del INE utiliza punto y coma y contiene metadatos iniciales.
    with args.ine.open(encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";\t,")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        rows = list(csv.reader(handle, dialect))
    lines.append("## INE: primeras 14 filas")
    for row in rows[:14]:
        lines.append(" | ".join(row[:12]))
    lines.append(f"Filas totales CSV (incluidos metadatos): {len(rows)}")
    lines.append("")

    workbook = load_workbook(args.dgt, read_only=True, data_only=True)
    lines.append("## DGT: hojas, dimensiones y muestra")
    for sheet in workbook.worksheets:
        lines.append(f"### Hoja: {sheet.title} | filas={sheet.max_row} | columnas={sheet.max_column}")
        emitted = 0
        for row in sheet.iter_rows(min_row=1, max_row=min(sheet.max_row, 15), values_only=True):
            values = ["" if value is None else str(value) for value in row[:18]]
            if any(values):
                lines.append(" | ".join(values))
                emitted += 1
        if emitted == 0:
            lines.append("(sin contenido en las primeras 15 filas)")
    workbook.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
