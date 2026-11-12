"""Validación del registro de directorios oficiales de red comercial."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

REGISTRY_PATH = Path(__file__).resolve().parent / "fuentes_red_comercial.json"
ALLOWED_SOURCE_TYPES = {
    "official_directory", "company_page", "official_statement",
    "public_record", "press", "aggregator", "social", "other",
}
ALLOWED_RELIABILITY = {
    "primary_official", "primary_business", "secondary_reputable",
    "community", "unverified",
}
ALLOWED_CAPTURE_MODES = {"http_html", "manual", "browser_required", "api"}
ALLOWED_DISCOVERY = {
    "directory_content_visible", "locator_present_dynamic_content",
    "locator_present_no_entries_yet", "not_assessed",
}


def validate_registry(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version debe ser 1")
    if data.get("country_scope") != "ES":
        errors.append("country_scope debe ser ES")

    brands = data.get("brands")
    sources = data.get("sources")
    if not isinstance(brands, list) or not brands:
        return errors + ["brands debe ser una lista no vacía"]
    if not isinstance(sources, list) or not sources:
        return errors + ["sources debe ser una lista no vacía"]

    brand_ids = set()
    for index, brand in enumerate(brands):
        brand_id = brand.get("brand_id")
        if not brand_id or brand_id in brand_ids:
            errors.append(f"brands[{index}]: brand_id ausente o duplicado")
        brand_ids.add(brand_id)
        if not brand.get("canonical_name", "").strip():
            errors.append(f"brands[{index}]: canonical_name obligatorio")

    source_ids = set()
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        source_id = source.get("source_id")
        if not source_id or source_id in source_ids:
            errors.append(f"{prefix}: source_id ausente o duplicado")
        source_ids.add(source_id)
        if source.get("brand_id") not in brand_ids:
            errors.append(f"{prefix}: brand_id no registrado")
        parsed = urlparse(source.get("url", ""))
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{prefix}: URL HTTPS no válida")
        if source.get("source_type") not in ALLOWED_SOURCE_TYPES:
            errors.append(f"{prefix}: source_type no permitido")
        if source.get("reliability_class") not in ALLOWED_RELIABILITY:
            errors.append(f"{prefix}: reliability_class no permitida")
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
        if source.get("reliability_class") != "primary_official":
            errors.append(f"{prefix}: el registro primario solo admite fuentes oficiales")

    policy = data.get("policy", {})
    if policy.get("absence_is_not_closure") is not True:
        errors.append("La política debe declarar que ausencia no equivale a cierre")
    if policy.get("manual_review_required_before_history_update") is not True:
        errors.append("La actualización histórica debe exigir revisión manual")
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
    print("Registro de fuentes oficiales válido.")
