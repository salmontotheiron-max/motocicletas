"""Genera una matriz conservadora del estado de captura de fuentes de red comercial.

No cuenta establecimientos ni infiere cierres. La clasificación describe el estado
técnico de captura de una fuente primaria, no la cobertura ni el tamaño de la red.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "fuentes_red_comercial.json"
LATEST_CAPTURE = ROOT / "evidencias" / "red_comercial" / "ultima_captura.json"
OUTPUT_CSV = ROOT / "evidencias" / "red_comercial" / "auditoria_cobertura.csv"
OUTPUT_JSON = ROOT / "evidencias" / "red_comercial" / "auditoria_cobertura.json"

STATUSES = {"verified", "partial", "dynamic_unextractable", "not_found", "pending"}
MIN_VISIBLE_TEXT_CHARS = 80


def _latest_records(capture_data: dict) -> dict[str, dict]:
    records = capture_data.get("records")
    if not isinstance(records, list):
        raise ValueError("El archivo de captura debe contener records como lista")
    latest: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict) or not record.get("source_id"):
            continue
        source_id = record["source_id"]
        previous = latest.get(source_id)
        if previous is None or str(record.get("captured_at", "")) >= str(previous.get("captured_at", "")):
            latest[source_id] = record
    return latest


def _source_priority(source: dict) -> tuple:
    """Prioriza directorios oficiales y localizadores frente a notas de prensa."""
    source_id = source.get("source_id", "").casefold()
    is_directory = source.get("source_type") == "official_directory"
    is_locator = any(token in source_id for token in ("locator", "dealers", "dealer-finder"))
    return (0 if is_directory else 1, 0 if is_directory and is_locator else 1, source_id)


def classify_brand(brand: dict, primary_sources: list[dict],
                   captures: dict[str, dict]) -> dict:
    """Clasifica captura técnica sin equipararla a cobertura comercial completa."""
    sources = sorted(primary_sources, key=_source_priority)
    directories = [source for source in sources if source.get("source_type") == "official_directory"]
    if not sources:
        return {
            "coverage_status": "pending",
            "coverage_basis": "no_brand_specific_primary_source_registered",
            "primary_source_id": "",
            "source_url": "",
            "source_type": "",
            "primary_source_count": 0,
            "official_directory_source_count": 0,
            "captured_at": "",
            "capture_status": "not_captured",
            "http_status": "",
            "visible_text_chars": "",
            "notes": "No hay fuente primaria específica de la marca en el registro; no equivale a ausencia de red.",
        }

    # Si existe localizador/directorio oficial, nunca se sustituye por una nota
    # de prensa o una página corporativa al evaluar la cobertura de red.
    source = directories[0] if directories else sources[0]
    record = captures.get(source["source_id"])
    common = {
        "primary_source_id": source["source_id"],
        "source_url": source.get("url", ""),
        "source_type": source.get("source_type", ""),
        "primary_source_count": len(sources),
        "official_directory_source_count": len(directories),
        "captured_at": (record or {}).get("captured_at", ""),
        "capture_status": (record or {}).get("capture_status", "not_captured"),
        "http_status": (record or {}).get("http_status", ""),
        "visible_text_chars": len((record or {}).get("extracted_text") or ""),
    }

    if not directories:
        return {
            **common,
            "coverage_status": "pending",
            "coverage_basis": "no_official_dealer_directory_registered",
            "notes": "Hay evidencia primaria, pero no consta un directorio oficial de establecimientos; la red no se considera ausente.",
        }

    if record is None or record.get("capture_status") != "captured":
        return {
            **common,
            "coverage_status": "pending",
            "coverage_basis": "official_source_not_successfully_captured",
            "notes": "Fallo o ausencia de captura técnica del directorio; no permite concluir si existe o no red.",
        }

    discovery = source.get("discovery_status")
    text_chars = common["visible_text_chars"]
    if discovery in {"locator_present_dynamic_content", "dynamic_unextractable"}:
        status = "dynamic_unextractable"
        basis = "official_locator_declared_dynamic"
        notes = "El localizador requiere contenido dinámico; la captura HTML no permite auditar sus establecimientos."
    elif discovery == "locator_present_no_entries_yet":
        status = "partial"
        basis = "official_locator_present_without_entries_in_capture"
        notes = "Hay localizador oficial, pero la captura no muestra entradas; no se interpreta como ausencia de concesionarios."
    elif discovery == "directory_content_visible" and text_chars >= MIN_VISIBLE_TEXT_CHARS:
        status = "partial"
        basis = "official_directory_content_captured_not_individually_audited"
        notes = "Contenido de directorio visible; los establecimientos aún no se han deduplicado ni verificado individualmente."
    else:
        status = "pending"
        basis = "official_source_captured_without_assessable_directory"
        notes = "La captura no acredita un directorio de establecimientos evaluable."
    return {
        **common,
        "coverage_status": status,
        "coverage_basis": basis,
        "notes": notes,
    }


def build_audit(registry: dict, capture_data: dict) -> dict:
    brands = registry.get("brands")
    sources = registry.get("sources")
    if not isinstance(brands, list) or not isinstance(sources, list):
        raise ValueError("El registro debe contener brands y sources como listas")
    captures = _latest_records(capture_data)
    primary_by_brand: dict[str, list[dict]] = {}
    primary_sources = [source for source in sources
                       if source.get("source_role") == "primary_monitoring" and source.get("brand_id")]
    for source in primary_sources:
        primary_by_brand.setdefault(source["brand_id"], []).append(source)

    rows = []
    for brand in sorted(brands, key=lambda item: item.get("canonical_name", "").casefold()):
        assessment = classify_brand(
            brand, primary_by_brand.get(brand.get("brand_id"), []), captures
        )
        rows.append({
            "brand_id": brand["brand_id"],
            "brand": brand["canonical_name"],
            "market_status": brand.get("market_status", ""),
            **assessment,
            "verified_outlets_count": "",
        })

    counts = Counter(row["coverage_status"] for row in rows)
    market_counts = Counter(row["market_status"] for row in rows)
    primary_ids = {source["source_id"] for source in primary_sources}
    primary_in_capture = [record for record in captures.values()
                          if record.get("source_id") in primary_ids]
    capture_modes = Counter(source.get("capture_mode", "unspecified") for source in primary_sources)
    return {
        # Legacy field retained for compatibility; this is the latest capture
        # dataset timestamp, not the wall-clock generation time.
        "generated_at": capture_data.get("captured_at", ""),
        "registry_reviewed_at": registry.get("registry_reviewed_at", ""),
        "capture_snapshot_at": capture_data.get("captured_at", ""),
        "method": "primary_source_capture_status_not_outlet_census",
        "coverage_status_scope": "La clasificación mide la captura técnica de un directorio oficial representativo por marca. No mide si la marca tiene red ni si los establecimientos individuales están verificados.",
        "brand_count": len(rows),
        "market_status_counts": dict(sorted(market_counts.items())),
        "primary_source_count": len(primary_sources),
        "primary_sources_in_latest_capture_count": len(primary_in_capture),
        "primary_sources_captured_count": sum(
            record.get("capture_status") == "captured" for record in primary_in_capture
        ),
        "primary_source_capture_modes": dict(sorted(capture_modes.items())),
        "latest_capture_record_count": len(captures),
        "status_counts": {status: counts.get(status, 0) for status in sorted(STATUSES)},
        "verified_outlets_count": None,
        "limitations": [
            "La clasificación describe la captura técnica de fuentes oficiales, no la cobertura exhaustiva de la red comercial.",
            "Una marca puede tener establecimientos auditados manualmente aunque su localizador oficial no esté capturado por el proceso automático.",
            "pending significa que la captura del directorio no está disponible o no es evaluable; nunca significa ausencia de red.",
            "partial significa que hay contenido de directorio o localizador, pero no que todos los establecimientos estén deduplicados y verificados.",
            "verified y not_found requieren revisión humana documentada; nunca se asignan por ausencia de captura.",
            "No se cuentan establecimientos automáticamente ni se deduplican nombres comerciales.",
            "Una variación textual de una web no demuestra una apertura, cierre o cambio de operador.",
        ],
        "brands": rows,
    }


def write_outputs(result: dict, csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "brand_id", "brand", "market_status", "coverage_status", "coverage_basis",
        "primary_source_id", "source_url", "source_type", "primary_source_count",
        "official_directory_source_count", "captured_at", "capture_status",
        "http_status", "visible_text_chars", "verified_outlets_count", "notes",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["brands"])
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--capture", type=Path, default=LATEST_CAPTURE)
    parser.add_argument("--csv", type=Path, default=OUTPUT_CSV)
    parser.add_argument("--json", type=Path, default=OUTPUT_JSON)
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    capture_data = json.loads(args.capture.read_text(encoding="utf-8"))
    result = build_audit(registry, capture_data)
    write_outputs(result, args.csv, args.json)
    print(json.dumps({
        "brand_count": result["brand_count"],
        "market_status_counts": result["market_status_counts"],
        "primary_source_count": result["primary_source_count"],
        "primary_sources_in_latest_capture_count": result["primary_sources_in_latest_capture_count"],
        "primary_sources_captured_count": result["primary_sources_captured_count"],
        "status_counts": result["status_counts"],
        "csv": str(args.csv),
        "json": str(args.json),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
