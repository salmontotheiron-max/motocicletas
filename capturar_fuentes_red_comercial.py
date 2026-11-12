"""Captura reproducible de un inventario explícito de fuentes públicas.

No rastrea enlaces, no extrae automáticamente concesionarios y no convierte
ausencias de página en bajas comerciales. Solo realiza GET sobre URLs HTTPS
declaradas en el inventario JSON y registra resultado/hash en SQLite.
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
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from validar_red_comercial import initialize_database

ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCES = ROOT / "fuentes_red_comercial.json"
DEFAULT_MIGRATION = ROOT / "migraciones" / "002_capturas_fuentes.sql"
USER_AGENT = "ObservatorioMotocicletas/1.0 (+captura de fuentes públicas; contacto: repositorio)"
MAX_BYTES = 2_000_000
EXCERPT_BYTES = 600


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_sources(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("sources"), list):
        raise ValueError("Inventario de fuentes no reconocido")
    seen: set[str] = set()
    for source in data["sources"]:
        required = ("source_id", "publisher", "source_type", "reliability_class", "title", "url")
        if any(not source.get(key) for key in required):
            raise ValueError("Cada fuente debe incluir todos los campos obligatorios")
        if source["source_id"] in seen:
            raise ValueError(f"source_id duplicado: {source['source_id']}")
        seen.add(source["source_id"])
        parsed = urlparse(source["url"])
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"Solo se admiten URLs HTTPS: {source['source_id']}")
    return data["sources"]


def fetch_page(url: str, timeout: int = 20, opener=urlopen) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.8,*/*;q=0.1"})
    try:
        with opener(request, timeout=timeout) as response:
            final_url = response.geturl()
            if urlparse(final_url).scheme != "https" or urlparse(final_url).hostname != urlparse(url).hostname:
                return {"result": "error", "error_category": "redirect", "error_message": "Redirección fuera del host HTTPS original"}
            status = response.getcode()
            content_type = response.headers.get("Content-Type", "")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                return {"result": "error", "http_status": status, "final_url": final_url,
                        "content_type": content_type, "error_category": "size_limit",
                        "error_message": f"Respuesta superior al límite de {MAX_BYTES} bytes"}
            if status < 200 or status >= 300:
                return classify_http(status)
            digest = hashlib.sha256(body).hexdigest()
            excerpt = body[:EXCERPT_BYTES].decode("utf-8", errors="replace")
            return {"result": "success", "http_status": status, "final_url": final_url,
                    "content_type": content_type, "content_length": len(body),
                    "content_hash": digest, "excerpt": excerpt}
    except HTTPError as exc:
        return classify_http(exc.code)
    except (URLError, TimeoutError, OSError) as exc:
        return {"result": "unavailable", "error_category": type(exc).__name__,
                "error_message": str(exc)[:300]}


def classify_http(status: int) -> dict:
    if status == 404 or status == 410:
        return {"result": "not_found", "http_status": status,
                "error_category": "http_not_found", "error_message": f"HTTP {status}"}
    if status in (408, 425, 429) or status >= 500:
        return {"result": "unavailable", "http_status": status,
                "error_category": "http_transient", "error_message": f"HTTP {status}"}
    return {"result": "error", "http_status": status,
            "error_category": "http_error", "error_message": f"HTTP {status}"}


def apply_migration(connection: sqlite3.Connection, migration_path: Path = DEFAULT_MIGRATION) -> None:
    connection.executescript(migration_path.read_text(encoding="utf-8"))


def ensure_sources(connection: sqlite3.Connection, sources: list[dict]) -> None:
    for item in sources:
        connection.execute(
            """INSERT OR IGNORE INTO source
               (source_id,publisher,source_type,url,title,reliability_class,notes)
               VALUES (?,?,?,?,?,?,?)""",
            (item["source_id"], item["publisher"], item["source_type"], item["url"],
             item["title"], item["reliability_class"], item.get("notes"))
        )


def previous_hash(connection: sqlite3.Connection, source_id: str) -> str | None:
    row = connection.execute(
        """SELECT content_hash FROM source_capture
           WHERE source_id=? AND result IN ('success','changed','unchanged')
           ORDER BY observed_at DESC LIMIT 1""", (source_id,)
    ).fetchone()
    return row[0] if row else None


def run_capture(database: str | Path, sources_path: str | Path = DEFAULT_SOURCES,
                timeout: int = 20, opener=urlopen) -> tuple[str, dict[str, int]]:
    sources = load_sources(Path(sources_path))
    connection = initialize_database(database)
    try:
        apply_migration(connection)
        ensure_sources(connection, sources)
        capture_id = str(uuid.uuid4())
        started = utc_now()
        connection.execute(
            "INSERT INTO capture(capture_id,started_at,status,notes) VALUES (?,?,?,?)",
            (capture_id, started, "running", "Captura explícita de inventario; sin rastreo de enlaces")
        )
        counts: dict[str, int] = {}
        for item in sources:
            observed = utc_now()
            result = fetch_page(item["url"], timeout=timeout, opener=opener)
            outcome = result["result"]
            if outcome == "success":
                old_hash = previous_hash(connection, item["source_id"])
                if old_hash is None:
                    outcome = "success"
                elif old_hash == result["content_hash"]:
                    outcome = "unchanged"
                else:
                    outcome = "changed"
            connection.execute(
                """INSERT INTO source_capture
                   (source_capture_id,capture_id,source_id,observed_at,result,http_status,
                    final_url,content_type,content_length,content_hash,excerpt,error_category,error_message)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()), capture_id, item["source_id"], observed, outcome,
                 result.get("http_status"), result.get("final_url"), result.get("content_type"),
                 result.get("content_length"), result.get("content_hash"), result.get("excerpt"),
                 result.get("error_category"), result.get("error_message"))
            )
            if outcome in ("success", "changed"):
                connection.execute(
                    """INSERT INTO observation
                       (observation_id,source_id,capture_id,observed_at,content_hash,
                        evidence_excerpt,evidence_location,notes)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (str(uuid.uuid4()), item["source_id"], capture_id, observed,
                     result["content_hash"], result.get("excerpt"), result.get("final_url"),
                     "Hash SHA-256 de respuesta HTTP; extracto limitado a 600 bytes")
                )
            counts[outcome] = counts.get(outcome, 0) + 1
        finished = utc_now()
        failures = counts.get("error", 0) + counts.get("unavailable", 0)
        status = "failed" if failures == len(sources) else ("partial" if failures else "completed")
        connection.execute("UPDATE capture SET finished_at=?,status=? WHERE capture_id=?",
                           (finished, status, capture_id))
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
    print(json.dumps({"capture_id": capture_id, "results": counts}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
