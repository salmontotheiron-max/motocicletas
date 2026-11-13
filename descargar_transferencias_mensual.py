#!/usr/bin/env python3
"""Descarga y valida snapshots mensuales de transferencias MATRABA."""
import argparse
import hashlib
import json
import time
import zipfile
from datetime import date, datetime, timezone
from io import BytesIO
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from descargar_matraba_mensual import WIDTH, month_pair, validate_month

BASE_URL = (
    "https://www.dgt.es/microdatos/salida/{year}/{month}/vehiculos/"
    "transferencias/export_mensual_trf_{stamp}.zip"
)


def transfer_url(month):
    year, mm = month.split("-")
    return BASE_URL.format(year=year, month=str(int(mm)), stamp=year + mm)


def initial_months(today=None):
    today = today or datetime.now(ZoneInfo("Europe/Madrid")).date()
    current = date(2026, 1, 1)
    months = []
    while current <= today.replace(day=1):
        months.append(current.strftime("%Y-%m"))
        current = date(current.year + (current.month == 12), 1 if current.month == 12 else current.month + 1, 1)
    return months


def months_to_check(inventory_path, today=None):
    today = today or datetime.now(ZoneInfo("Europe/Madrid")).date()
    if not Path(inventory_path).exists():
        return initial_months(today)
    data = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    validated = {
        item.get("periodo")
        for execution in data.get("ejecuciones", [])
        for item in execution.get("capturas", [])
        if item.get("estado") == "descargado_validado"
    }
    pending = [month for month in initial_months(today) if month not in validated]
    return sorted(set(pending + month_pair(today)))


def inspect_transfer_zip(payload):
    """Valida ZIP de transferencias: registros de ancho fijo, sin cabecera."""
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

    # A diferencia del fichero de matriculaciones, el mensual de transferencias
    # comienza directamente por el primer registro MATRABA de 714 posiciones.
    # Admite una cabecera histórica de 79 bytes, pero los ZIP de transferencias
    # actuales empiezan directamente con el primer registro de 714 bytes.
    records = lines[1:] if len(lines[0]) == 79 else lines
    if not records:
        return None, "txt_sin_registros", 0
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
    url = transfer_url(month)
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
            txt, error, records = inspect_transfer_zip(payload)
            if error:
                return {
                    "periodo": month, "estado": "fichero_invalido",
                    "detalle": error, "registros": records, "url": url,
                }
            digest = hashlib.sha256(payload).hexdigest()
            name = f"export_mensual_trf_{month.replace('-', '')}_{digest}.zip"
            path = target_dir / name
            if not path.exists():
                path.write_bytes(payload)
            return {
                "periodo": month, "estado": "descargado_validado",
                "archivo": str(path), "sha256": digest, "bytes_zip": len(payload),
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
    parser.add_argument("--month", action="append", type=validate_month)
    parser.add_argument("--output-dir", default="datos/matraba_mensual/transferencias")
    parser.add_argument("--inventory-file", default="public/data/capturas_transferencias_mensuales.json")
    args = parser.parse_args()
    inventory_path = Path(args.inventory_file)
    months = args.month or months_to_check(inventory_path)
    results = [download_month(month, args.output_dir) for month in months]
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    captured_at = datetime.now(timezone.utc).isoformat()
    previous = {"ejecuciones": []}
    if inventory_path.exists():
        previous = json.loads(inventory_path.read_text(encoding="utf-8"))
    executions = previous.get("ejecuciones", [])
    executions.append({
        "fecha_captura_utc": captured_at,
        "periodos_consultados": months,
        "capturas": results,
    })
    inventory_path.write_text(
        json.dumps({
            "esquema": 1, "ultima_captura_utc": captured_at,
            "ejecuciones": executions,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for result in results:
        print(json.dumps(result, ensure_ascii=False))
    if any(item["estado"] in {"error_red", "error_http", "fichero_invalido"} for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
