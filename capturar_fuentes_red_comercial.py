"""Captura reproducible de un inventario explícito de fuentes públicas.

No rastrea enlaces ni extrae concesionarios. Consulta exclusivamente las URLs
HTTPS declaradas en fuentes_red_comercial.json y registra resultado/hash en
SQLite. Los cambios técnicos nunca se convierten automáticamente en eventos.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from validar_red_comercial import initialize_database

ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCES = ROOT / "fuentes_red_comercial.json"
DEFAULT_MIGRATION = ROOT / "migraciones" / "002_capturas_fuentes.sql"
USER_AGENT = "ObservatorioRedComercial/1.0"
MAX_BYTES = 2_000_000
EXCERPT_BYTES = 600
ALLOWED_SOURCE_TYPES = {
    "official_directory", "company_page", "product_catalog", "secondary_directory", "official_statement",
    "public_record", "press", "aggregator", "social", "other",
}
ALLOWED_RELIABILITY = {
    "primary_official", "primary_business", "secondary_reputable", "secondary_aggregator",
    "community", "unverified",
}


class UnsafeRedirectError(Exception):
    """Redirección que cambia el origen HTTPS declarado."""


class SameOriginRedirectHandler(HTTPRedirectHandler):
    """Sigue solo redirecciones HTTPS que conservan esquema, host y puerto."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlparse(urljoin(req.full_url, newurl))
        original = urlparse(req.full_url)
        origin = (original.scheme.lower(), original.hostname, original.port)
        destination = (target.scheme.lower(), target.hostname, target.port)
        if destination != origin or target.scheme.lower() != "https":
            raise UnsafeRedirectError("Redirección fuera del origen HTTPS original")
        return super().redirect_request(req, fp, code, msg, headers, target.geturl())


def safe_urlopen(request: Request, timeout: int = 20):
    """Abre una URL sin permitir que urllib siga redirecciones a otro origen."""
    return build_opener(SameOriginRedirectHandler()).open(request, timeout=timeout)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_sources(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    version_ok = data.get("schema_version") == 2 or data.get("version") == 1
    sources = data.get("sources")
    if not version_ok or not isinstance(sources, list) or not sources:
        raise ValueError("Inventario de fuentes no reconocido o vacío")
    seen: set[str] = set()
    for source in sources:
        required = ("source_id", "publisher", "source_type", "reliability_class", "title", "url")
        if any(not isinstance(source.get(key), str) or not source[key].strip() for key in required):
            raise ValueError("Cada fuente debe incluir los campos obligatorios no vacíos")
        if source["source_id"] in seen:
            raise ValueError(f"source_id duplicado: {source['source_id']}")
        seen.add(source["source_id"])
        if source["source_type"] not in ALLOWED_SOURCE_TYPES:
            raise ValueError(f"source_type no admitido: {source['source_type']}")
        if source["reliability_class"] not in ALLOWED_RELIABILITY:
            raise ValueError(f"reliability_class no admitida: {source['reliability_class']}")
        parsed = urlparse(source["url"])
        if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError(f"Solo se admiten URLs HTTPS válidas: {source['source_id']}")
    return sources


def classify_http(status: int) -> dict:
    if status in (404, 410):
        return {"result": "not_found", "http_status": status,
                "error_category": "http_not_found", "error_message": f"HTTP {status}"}
    if status in (408, 425, 429) or status >= 500:
        return {"result": "unavailable", "http_status": status,
                "error_category": "http_transient", "error_message": f"HTTP {status}"}
    return {"result": "error", "http_status": status,
            "error_category": "http_error", "error_message": f"HTTP {status}"}


def fetch_page(url: str, timeout: int = 20, opener=safe_urlopen) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.8,*/*;q=0.1",
        },
    )
    try:
        with opener(request, timeout=timeout) as response:
            final_url = response.geturl()
            original = urlparse(url)
            final = urlparse(final_url)
            if (final.scheme.lower(), final.hostname, final.port) != (
                original.scheme.lower(), original.hostname, original.port
            ):
                return {"result": "error", "error_category": "redirect",
                        "error_message": "Redirección fuera del origen HTTPS original"}
            status = response.getcode()
            content_type = response.headers.get("Content-Type", "")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                return {"result": "error", "http_status": status, "final_url": final_url,
                        "content_type": content_type, "error_category": "size_limit",
                        "error_message": f"Respuesta superior al límite de {MAX_BYTES} bytes"}
            if status < 200 or status >= 300:
                return classify_http(status)
            return {
                "result": "success", "http_status": status, "final_url": final_url,
                "content_type": content_type, "content_length": len(body),
                "content_hash": hashlib.sha256(body).hexdigest(),
                "excerpt": body[:EXCERPT_BYTES].decode("utf-8", errors="replace"),
            }
    except UnsafeRedirectError as exc:
        return {"result": "error", "error_category": "redirect", "error_message": str(exc)}
    except HTTPError as exc:
        return classify_http(exc.code)
    except (URLError, TimeoutError, OSError) as exc:
        return {"result": "unavailable", "error_category": type(exc).__name__,
                "error_message": str(exc)[:300]}


def apply_migration(connection: sqlite3.Connection, migration_path: Path = DEFAULT_MIGRATION) -> None:
    connection.executescript(migration_path.read_text(encoding="utf-8"))


def ensure_sources(connection: sqlite3.Connection, sources: list[dict]) -> None:
    fields = ("publisher", "source_type", "url", "title", "reliability_class")
    for item in sources:
        existing = connection.execute(
            "SELECT publisher,source_type,url,title,reliability_class FROM source WHERE source_id=?",
            (item["source_id"],),
        ).fetchone()
        values = tuple(item[key] for key in fields)
        if existing is not None:
            if tuple(existing) != values:
                raise ValueError(
                    f"El source_id {item['source_id']} ya existe con metadatos distintos; "
                    "revisar el catálogo antes de capturar"
                )
            continue
        connection.execute(
            """INSERT INTO source
               (source_id,publisher,source_type,url,title,reliability_class,notes)
               VALUES (?,?,?,?,?,?,?)""",
            (item["source_id"], *values, item.get("notes")),
        )


def previous_hash(connection: sqlite3.Connection, source_id: str) -> str | None:
    row = connection.execute(
        """SELECT content_hash FROM source_capture
           WHERE source_id=? AND result IN ('success','changed','unchanged')
           ORDER BY observed_at DESC LIMIT 1""",
        (source_id,),
    ).fetchone()
    return row[0] if row else None


def run_capture(
    database: str | Path,
    sources_path: str | Path = DEFAULT_SOURCES,
    timeout: int = 20,
    opener=safe_urlopen,
) -> tuple[str, dict[str, int]]:
    if not 1 <= timeout <= 60:
        raise ValueError("timeout debe estar entre 1 y 60 segundos")
    sources = load_sources(Path(sources_path))
    connection = initialize_database(database)
    try:
        apply_migration(connection)
        ensure_sources(connection, sources)
        capture_id = str(uuid.uuid4())
        connection.execute(
            "INSERT INTO capture(capture_id,started_at,status,notes) VALUES (?,?,?,?)",
            (capture_id, utc_now(), "running",
             "Captura explícita de inventario; sin rastreo de enlaces ni inferencia de eventos"),
        )
        counts: dict[str, int] = {}
        for item in sources:
            observed = utc_now()
            result = fetch_page(item["url"], timeout=timeout, opener=opener)
            outcome = result["result"]
            if outcome == "success":
                old_hash = previous_hash(connection, item["source_id"])
                outcome = (
                    "success" if old_hash is None else
                    "unchanged" if old_hash == result["content_hash"] else "changed"
                )
            connection.execute(
                """INSERT INTO source_capture
                   (source_capture_id,capture_id,source_id,observed_at,result,http_status,
                    final_url,content_type,content_length,content_hash,excerpt,error_category,error_message)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()), capture_id, item["source_id"], observed, outcome,
                    result.get("http_status"), result.get("final_url"), result.get("content_type"),
                    result.get("content_length"), result.get("content_hash"), result.get("excerpt"),
                    result.get("error_category"), result.get("error_message"),
                ),
            )
            if outcome in ("success", "changed"):
                connection.execute(
                    """INSERT INTO observation
                       (observation_id,source_id,capture_id,observed_at,content_hash,
                        evidence_excerpt,evidence_location,notes)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        str(uuid.uuid4()), item["source_id"], capture_id, observed,
                        result["content_hash"], result.get("excerpt"), result.get("final_url"),
                        "Hash SHA-256 de respuesta HTTP; extracto limitado a 600 bytes",
                    ),
                )
            counts[outcome] = counts.get(outcome, 0) + 1
        failures = counts.get("error", 0) + counts.get("unavailable", 0)
        status = "failed" if failures == len(sources) else ("partial" if failures else "completed")
        connection.execute(
            "UPDATE capture SET finished_at=?,status=? WHERE capture_id=?",
            (utc_now(), status, capture_id),
        )
        connection.commit()
        return capture_id, counts
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="red_comercial.sqlite")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES))
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 60:
        parser.error("--timeout debe estar entre 1 y 60 segundos")
    capture_id, counts = run_capture(args.db, args.sources, args.timeout)
    print(json.dumps(
        {"capture_id": capture_id, "results": counts},
        ensure_ascii=False, sort_keys=True,
    ))


if __name__ == "__main__":
    main()
