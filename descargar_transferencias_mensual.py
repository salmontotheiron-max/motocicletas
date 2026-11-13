#!/usr/bin/env python3
"""Descarga y valida snapshots mensuales de transferencias MATRABA."""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from descargar_matraba_mensual import inspect_zip, month_pair, validate_month

BASE_URL = (
    "https://www.dgt.es/microdatos/salida/{year}/{month}/vehiculos/"
    "transferencias/export_mensual_trf_{stamp}.zip"
)


def transfer_url(month):
    year, mm = month.split("-")
    return BASE_URL.format(year=year, month=str(int(mm)), stamp=year + mm)


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
            txt, error, records = inspect_zip(payload)
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
    months = args.month or month_pair()
    results = [download_month(month, args.output_dir) for month in months]
    inventory_path = Path(args.inventory_file)
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
