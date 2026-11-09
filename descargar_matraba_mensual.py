#!/usr/bin/env python3
"""Descarga y valida snapshots mensuales MATRABA sin alterar los ZIP originales."""
import argparse
import hashlib
import json
import re
import time
import zipfile
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WIDTH = 714
MONTHLY_HEADER_WIDTH = 79
BASE_URL = (
    "https://www.dgt.es/microdatos/salida/{year}/{month}/vehiculos/"
    "matriculaciones/export_mensual_mat_{stamp}.zip"
)


def month_pair(today=None):
    """Devuelve mes actual y anterior en calendario local del runner."""
    today = today or datetime.now(ZoneInfo("Europe/Madrid")).date()
    first = today.replace(day=1)
    previous_last = first.fromordinal(first.toordinal() - 1)
    return [previous_last.strftime("%Y-%m"), first.strftime("%Y-%m")]


def validate_month(value):
    # Acepta YYYY-MM y YYYYMM para evitar errores de formato al introducir
    # meses desde el formulario de GitHub Actions.
    if re.fullmatch(r"\d{6}", value):
        value = value[:4] + "-" + value[4:]
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("El mes debe tener formato YYYY-MM o YYYYMM") from exc
    if parsed.strftime("%Y-%m") != value:
        raise argparse.ArgumentTypeError("El mes debe tener formato YYYY-MM o YYYYMM")
    return value


def monthly_url(month):
    year, mm = month.split("-")
    return BASE_URL.format(year=year, month=str(int(mm)), stamp=year + mm)


def inspect_zip(payload):
    """Valida ZIP, un TXT, cabecera mensual de 79 bytes y registros de 714."""
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                return None, "zip_crc_invalido:" + bad_member, 0
            txt_names = [
                name for name in archive.namelist()
                if name.lower().endswith(".txt") and not name.endswith("/")
            ]
            if len(txt_names) != 1:
                return None, f"numero_txt_inesperado:{len(txt_names)}", 0
            data = archive.read(txt_names[0])
    except (zipfile.BadZipFile, OSError, RuntimeError, EOFError):
        return None, "zip_corrupto", 0

    normalized = data.replace(b"\r\n", b"\n")
    lines = normalized.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    if not lines:
        return None, "txt_vacio", 0
    if len(lines[0]) != MONTHLY_HEADER_WIDTH:
        return None, f"cabecera_mensual_ancho_invalido:{len(lines[0])}", 0

    records = lines[1:]
    invalid = sorted({len(line) for line in records if len(line) != WIDTH})
    if invalid:
        return None, f"longitudes_registro_invalidas:{invalid[:10]}", len(records)

    for number, record in enumerate(records, 1):
        try:
            raw_date = record[706:714].decode("ascii").strip()
            datetime.strptime(raw_date, "%d%m%Y")
        except (UnicodeDecodeError, ValueError):
            return None, f"fec_proceso_invalida_registro:{number}", len(records)

    return data, None, len(records)


def download_month(month, output_dir, opener=urlopen, retries=2, pause=1):
    url = monthly_url(month)
    target_dir = Path(output_dir) / month
    target_dir.mkdir(parents=True, exist_ok=True)
    last_error = None

    for attempt in range(retries + 1):
        try:
            request = Request(url, headers={"User-Agent": "observatorio-matraba/2.0"})
            with opener(request, timeout=60) as response:
                status = getattr(response, "status", 200)
                payload = response.read()
            if status == 404:
                return {"periodo": month, "estado": "no_disponible_en_barrido", "url": url}
            if status != 200:
                return {"periodo": month, "estado": "error_http", "http_status": status, "url": url}
            txt, error, records = inspect_zip(payload)
            if error:
                return {
                    "periodo": month, "estado": "fichero_invalido",
                    "detalle": error, "registros": records, "url": url,
                }

            digest = hashlib.sha256(payload).hexdigest()
            archive_name = f"export_mensual_mat_{month.replace('-', '')}_{digest}.zip"
            archive_path = target_dir / archive_name
            if not archive_path.exists():
                archive_path.write_bytes(payload)
            return {
                "periodo": month, "estado": "descargado_validado",
                "archivo": str(archive_path), "nombre_txt": None,
                "sha256": digest, "bytes_zip": len(payload),
                "bytes_txt": len(txt), "registros": records, "url": url,
            }
        except HTTPError as exc:
            if exc.code == 404:
                return {"periodo": month, "estado": "no_disponible_en_barrido", "http_status": 404, "url": url}
            last_error = f"HTTP {exc.code}"
        except (URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < retries:
            time.sleep(pause * (attempt + 1))

    return {"periodo": month, "estado": "error_red", "detalle": last_error, "url": url}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", action="append", type=validate_month,
                        help="Mes YYYY-MM; puede repetirse. Por defecto, mes actual y anterior.")
    parser.add_argument("--output-dir", default="datos/matraba_mensual")
    parser.add_argument("--inventory-file", default="public/data/capturas_mensuales.json")
    args = parser.parse_args()

    months = args.month or month_pair()
    results = [download_month(month, args.output_dir) for month in months]
    inventory_path = Path(args.inventory_file)
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    captured_at = datetime.now(timezone.utc).isoformat()
    previous = {"ejecuciones": []}
    if inventory_path.exists():
        try:
            previous = json.loads(inventory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise SystemExit("El inventario existente no es JSON válido; no se sobrescribe.")
    executions = previous.get("ejecuciones", [])
    executions.append({
        "fecha_captura_utc": captured_at,
        "periodos_consultados": months,
        "capturas": results,
    })
    inventory = {
        "esquema": 1,
        "ultima_captura_utc": captured_at,
        "ejecuciones": executions,
    }
    inventory_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for result in results:
        print(json.dumps(result, ensure_ascii=False))
    if any(item["estado"] in {"error_red", "error_http", "fichero_invalido"} for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
