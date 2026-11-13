"""Validación del registro abierto de fuentes del mercado motociclista."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

REGISTRY_PATH = Path(__file__).resolve().parent / "fuentes_red_comercial.json"
ALLOWED_SOURCE_TYPES = {
    "official_directory", "company_page", "product_catalog", "secondary_directory", "official_statement",
    "public_record", "press", "aggregator", "social", "other",
}
ALLOWED_RELIABILITY = {
    "primary_official", "primary_business", "secondary_reputable", "secondary_aggregator",
    "community", "unverified",
}
ALLOWED_CAPTURE_MODES = {"http_html", "manual", "browser_required", "api", "dynamic_unextractable"}
ALLOWED_DISCOVERY = {
    "directory_content_visible", "dynamic_unextractable", "locator_present_dynamic_content",
    "locator_present_no_entries_yet", "not_assessed",
}
ALLOWED_SOURCE_ROLES = {"primary_monitoring", "market_discovery"}
ALLOWED_MARKET_STATUSES = {
    "announced", "recent_entry", "established", "under_review",
    "ceased_confirmed", "inactive_unverified", "unknown",
}


def validate_registry(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 2:
        errors.append("schema_version debe ser 2")
    if data.get("country_scope") != "ES":
        errors.append("country_scope debe ser ES")

    market_scope = data.get("market_scope", {})
    if market_scope.get("coverage") != "open_market":
        errors.append("market_scope debe declarar cobertura open_market")
    for flag in ("discovery_is_continuous", "unknown_brands_allowed",
                 "unknown_manufacturers_allowed"):
        if market_scope.get(flag) is not True:
            errors.append(f"market_scope.{flag} debe ser true")

    manufacturers = data.get("manufacturers")
    brands = data.get("brands")
    sources = data.get("sources")
    if not isinstance(manufacturers, list):
        errors.append("manufacturers debe ser una lista")
        manufacturers = []
    if not isinstance(brands, list) or not brands:
        return errors + ["brands debe ser una lista no vacía"]
    if not isinstance(sources, list) or not sources:
        return errors + ["sources debe ser una lista no vacía"]

    manufacturer_ids = set()
    for index, manufacturer in enumerate(manufacturers):
        manufacturer_id = manufacturer.get("manufacturer_id")
        if not manufacturer_id or manufacturer_id in manufacturer_ids:
            errors.append(f"manufacturers[{index}]: manufacturer_id ausente o duplicado")
        manufacturer_ids.add(manufacturer_id)
        if not manufacturer.get("canonical_name", "").strip():
            errors.append(f"manufacturers[{index}]: canonical_name obligatorio")

    brand_ids = set()
    for index, brand in enumerate(brands):
        brand_id = brand.get("brand_id")
        if not brand_id or brand_id in brand_ids:
            errors.append(f"brands[{index}]: brand_id ausente o duplicado")
        brand_ids.add(brand_id)
        if not brand.get("canonical_name", "").strip():
            errors.append(f"brands[{index}]: canonical_name obligatorio")
        if brand.get("market_status") not in ALLOWED_MARKET_STATUSES:
            errors.append(f"brands[{index}]: market_status no permitido")
        manufacturer_id = brand.get("manufacturer_id")
        if manufacturer_id is not None and manufacturer_id not in manufacturer_ids:
            errors.append(f"brands[{index}]: manufacturer_id no registrado")

    source_ids = set()
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        source_id = source.get("source_id")
        if not source_id or source_id in source_ids:
            errors.append(f"{prefix}: source_id ausente o duplicado")
        source_ids.add(source_id)
        role = source.get("source_role")
        if role not in ALLOWED_SOURCE_ROLES:
            errors.append(f"{prefix}: source_role no permitido")
        brand_id = source.get("brand_id")
        if role == "primary_monitoring" and brand_id not in brand_ids:
            errors.append(f"{prefix}: una fuente primaria debe referir una marca registrada")
        if role == "market_discovery" and brand_id is not None:
            errors.append(f"{prefix}: una fuente de descubrimiento de mercado no debe exigir marca")
        parsed = urlparse(source.get("url", ""))
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{prefix}: URL HTTPS no válida")
        if source.get("source_type") not in ALLOWED_SOURCE_TYPES:
            errors.append(f"{prefix}: source_type no permitido")
        reliability = source.get("reliability_class")
        if reliability not in ALLOWED_RELIABILITY:
            errors.append(f"{prefix}: reliability_class no permitida")
        if role == "primary_monitoring" and reliability != "primary_official":
            errors.append(f"{prefix}: el seguimiento primario solo admite fuentes oficiales")
        if role == "market_discovery" and reliability == "unverified":
            errors.append(f"{prefix}: una fuente de descubrimiento no puede ser unverified")
        if source.get("capture_mode") not in ALLOWED_CAPTURE_MODES:
            errors.append(f"{prefix}: capture_mode no permitido")
        if source.get("discovery_status") not in ALLOWED_DISCOVERY:
            errors.append(f"{prefix}: discovery_status no permitido")
        if not source.get("publisher", "").strip():
            errors.append(f"{prefix}: publisher obligatorio")
        if not source.get("title", "").strip():
            errors.append(f"{prefix}: title obligatorio")
        interval = source.get("capture_interval_days")
        if not isinstance(interval, int) or interval < 1:
            errors.append(f"{prefix}: capture_interval_days debe ser entero positivo")

    policy = data.get("policy", {})
    if policy.get("absence_is_not_closure") is not True:
        errors.append("La política debe declarar que ausencia no equivale a cierre")
    if policy.get("announcement_is_not_operation") is not True:
        errors.append("Un anuncio no debe equivaler a actividad efectiva")
    if policy.get("manual_review_required_before_history_update") is not True:
        errors.append("La actualización histórica debe exigir revisión manual")
    if policy.get("discovery_sources_may_be_secondary") is not True:
        errors.append("Debe permitirse evidencia secundaria para descubrimiento")
    return errors


def load_and_validate(path: Path = REGISTRY_PATH) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"No se pudo leer el registro: {exc}"]
    if not isinstance(data, dict):
        return ["La raíz del registro debe ser un objeto JSON"]
    return validate_registry(data)


if __name__ == "__main__":
    issues = load_and_validate()
    if issues:
        raise SystemExit("\n".join(issues))
    print("Registro abierto de fuentes del mercado válido.")
