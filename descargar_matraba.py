#!/usr/bin/env python3
"""Descarga MATRABA y genera una auditoría diaria de cobertura."""
import argparse
import json
import re
import time
import zipfile
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WIDTH = 714
HEADER = b"Veh\xedculos matriculados. Letras de la serie de la \xfaltima matr\xedcula asignada:"
BASE = "https://www.dgt.es/microdatos/salida/{year}/{month}/vehiculos/matriculaciones/export_mat_{stamp}.zip"


def iter_days(start, end):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def validate_txt(data, expected_day):
    normalized = data.replace(b"\r\n", b"\n")
    lines = [line for line in normalized.split(b"\n") if line.strip()]
    if lines and lines[0].startswith(HEADER):
        lines = lines[1:]
    bad = sorted({len(line) for line in lines if len(line) != WIDTH})
    if bad:
        return False, f"longitudes_registro_invalidas:{bad[:10]}", 0
    for index, line in enumerate(lines, 1):
        try:
            field = line[-8:].decode("cp1252").strip()
            process_date = datetime.strptime(field, "%d%m%Y").date()
        except (UnicodeDecodeError, ValueError):
            return False, f"fec_proceso_invalida_registro:{index}", len(lines)
        if process_date != expected_day:
            return False, f"fec_proceso_no_coincide_registro:{index}", len(lines)
    return True, None, len(lines)


def inspect_zip(payload, expected_day):
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            if archive.testzip() is not None:
                return None, "zip_corrupto", 0
            txt_names = [n for n in archive.namelist() if n.lower().endswith(".txt") and not n.endswith("/")]
            if len(txt_names) != 1:
                return None, f"numero_txt_inesperado:{len(txt_names)}", 0
            data = archive.read(txt_names[0])
    except (zipfile.BadZipFile, OSError, RuntimeError):
        return None, "zip_corrupto", 0
    valid, error, count = validate_txt(data, expected_day)
    if not valid:
        return None, error, count
    return data, None, count


def download_day(day, output_dir, opener=urlopen, retries=2, pause=1):
    stamp = day.strftime("%Y%m%d")
    url = BASE.format(year=day.strftime("%Y"), month=day.strftime("%m"), stamp=stamp)
    last_error = None
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers={"User-Agent": "observatorio-matraba/1.0"})
            with opener(request, timeout=30) as response:
                status = getattr(response, "status", 200)
                payload = response.read()
            if status == 404:
                return {"fecha": day.isoformat(), "estado": "no_encontrado_dgt", "http_status": 404}
            if status != 200:
                return {"fecha": day.isoformat(), "estado": "error_http", "http_status": status}
            data, error, count = inspect_zip(payload, day)
            if error:
                return {"fecha": day.isoformat(), "estado": "fichero_invalido", "detalle": error, "registros": count, "http_status": 200}
            path = output_dir / f"export_mat_{stamp}.txt"
            path.write_bytes(data)
            return {"fecha": day.isoformat(), "estado": "descargado_validado", "archivo": path.name, "registros": count, "http_status": 200}
        except HTTPError as exc:
            if exc.code == 404:
                return {"fecha": day.isoformat(), "estado": "no_encontrado_dgt", "http_status": 404}
            last_error = f"HTTP {exc.code}"
        except (URLError, TimeoutError, OSError) as exc:
            last_error = type(exc).__name__ + ": " + str(exc)
        if attempt < retries:
            time.sleep(pause * (attempt + 1))
    return {"fecha": day.isoformat(), "estado": "error_red", "detalle": last_error}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2026-09-01")
    parser.add_argument("--end", required=True)
    parser.add_argument("--output-dir", default="datos/matraba")
    parser.add_argument("--coverage-file", default="public/data/cobertura_diaria.json")
    args = parser.parse_args()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    if end < start:
        parser.error("--end no puede ser anterior a --start")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    coverage = [download_day(day, output_dir) for day in iter_days(start, end)]
    out = Path(args.coverage_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "desde": start.isoformat(), "hasta": end.isoformat(),
        "dias_inventariados": len(coverage), "dias": coverage
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = [d for d in coverage if d["estado"] in ("error_http", "error_red", "fichero_invalido")]
    if failures:
        raise SystemExit(f"Auditoría completada con {len(failures)} incidencias técnicas; revisar cobertura_diaria.json")


if __name__ == "__main__":
    main()
