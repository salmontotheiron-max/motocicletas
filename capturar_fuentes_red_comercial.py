"""Captura conservadora de fuentes públicas de red comercial.

Guarda observaciones técnicas, texto extraído y snapshots HTML comprimidos cuando
cambia el contenido. No extrae entidades comerciales ni modifica el histórico.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "fuentes_red_comercial.json"
EVIDENCE = ROOT / "evidencias" / "red_comercial"
USER_AGENT = "ObservatorioRedComercial/1.0 (+https://github.com/salmontotheiron-max/motocicletas)"
TIMEOUT_SECONDS = 25
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_TEXT_CHARS = 250_000


class VisibleTextParser(HTMLParser):
    """Extrae texto visible básico sin ejecutar JavaScript ni CSS."""

    HIDDEN = {"script", "style", "noscript", "svg", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in self.HIDDEN:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.HIDDEN and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value)


def extract_visible_text(html: str) -> str:
    parser = VisibleTextParser()
    parser.feed(html)
    return "\n".join(parser.parts)[:MAX_TEXT_CHARS]


def load_sources(registry_path: Path = REGISTRY) -> list[dict]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    sources = []
    for source in data["sources"]:
        if source.get("capture_mode") != "http_html":
            continue
        if source.get("source_role") not in {"primary_monitoring", "market_discovery"}:
            continue
        parsed = urlparse(source["url"])
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"URL no permitida para {source.get('source_id')}")
        sources.append(source)
    return sources


def robots_allowed(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        request = Request(robots_url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(512_000).decode("utf-8", errors="replace")
        parser.parse(body.splitlines())
        return parser.can_fetch(USER_AGENT, url), "robots_txt"
    except HTTPError as exc:
        if exc.code in (401, 403):
            return False, f"robots_http_{exc.code}"
        # 404/410 or a transient robots error does not authorize bypassing
        # explicit restrictions; on other errors, fail closed.
        return (exc.code in (404, 410), f"robots_http_{exc.code}")
    except (URLError, TimeoutError, OSError) as exc:
        return False, f"robots_unavailable:{type(exc).__name__}"


def fetch_page(url: str) -> dict:
    request = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
    })
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            parsed_final = urlparse(final_url)
            if parsed_final.scheme != "https":
                return {"capture_status": "redirect_rejected", "http_status": response.status,
                        "final_url": final_url, "error": "redirect_not_https"}
            content_type = response.headers.get("Content-Type", "")
            body = response.read(MAX_RESPONSE_BYTES + 1)
            status = response.status
    except HTTPError as exc:
        body = exc.read(MAX_RESPONSE_BYTES + 1)
        return {
            "capture_status": "http_error", "http_status": exc.code,
            "final_url": exc.geturl(), "content_type": exc.headers.get("Content-Type", ""),
            "body": body[:MAX_RESPONSE_BYTES], "error": f"HTTP {exc.code}",
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {"capture_status": "network_error", "http_status": None,
                "final_url": None, "content_type": None, "error": str(exc)}

    if len(body) > MAX_RESPONSE_BYTES:
        return {"capture_status": "response_too_large", "http_status": status,
                "final_url": final_url, "content_type": content_type,
                "error": f"response_exceeds_{MAX_RESPONSE_BYTES}_bytes"}
    if status < 200 or status >= 300:
        return {"capture_status": "http_error", "http_status": status,
                "final_url": final_url, "content_type": content_type,
                "body": body, "error": f"HTTP {status}"}
    if "html" not in content_type.lower():
        return {"capture_status": "unexpected_content_type", "http_status": status,
                "final_url": final_url, "content_type": content_type,
                "error": "expected_html"}
    return {"capture_status": "captured", "http_status": status,
            "final_url": final_url, "content_type": content_type, "body": body}


def persist_capture(source: dict, result: dict, captured_at: str) -> dict:
    record = {
        "captured_at": captured_at,
        "source_id": source["source_id"],
        "source_role": source["source_role"],
        "requested_url": source["url"],
        "final_url": result.get("final_url"),
        "http_status": result.get("http_status"),
        "content_type": result.get("content_type"),
        "capture_status": result["capture_status"],
        "robots_status": result.get("robots_status"),
        "error": result.get("error"),
        "sha256": None,
        "snapshot_path": None,
        "extracted_text": None,
    }
    body = result.get("body")
    if body is not None and result["capture_status"] == "captured":
        digest = hashlib.sha256(body).hexdigest()
        record["sha256"] = digest
        encoding = result.get("content_type", "").lower()
        html = body.decode("utf-8-sig", errors="replace")
        text = extract_visible_text(html)
        record["extracted_text"] = text
        record["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        record["content_bytes"] = len(body)
        snapshot = EVIDENCE / "snapshots" / source["source_id"] / f"{digest}.html.gz"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if not snapshot.exists():
            with snapshot.open("wb") as raw:
                with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
                    compressed.write(body)
        record["snapshot_path"] = str(snapshot.relative_to(ROOT))
    return record


def capture_all(registry_path: Path = REGISTRY, evidence_dir: Path = EVIDENCE) -> list[dict]:
    global EVIDENCE
    EVIDENCE = evidence_dir
    records = []
    captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for source in load_sources(registry_path):
        allowed, robots_status = robots_allowed(source["url"])
        if not allowed:
            result = {"capture_status": "robots_disallowed", "error": robots_status,
                      "robots_status": robots_status}
        else:
            result = fetch_page(source["url"])
            result["robots_status"] = robots_status
        records.append(persist_capture(source, result, captured_at))
        time.sleep(1.0)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    log_path = evidence_dir / "capturas.jsonl"
    with log_path.open("a", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {
        "captured_at": captured_at,
        "total_sources": len(records),
        "captured": sum(r["capture_status"] == "captured" for r in records),
        "failures": sum(r["capture_status"] != "captured" for r in records),
        "records": records,
    }
    (evidence_dir / "ultima_captura.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return records


if __name__ == "__main__":
    try:
        rows = capture_all()
    except Exception as exc:
        print(f"Error de captura: {exc}", file=sys.stderr)
        raise SystemExit(1)
    for row in rows:
        print(f'{row["source_id"]}: {row["capture_status"]} '
              f'HTTP={row["http_status"]} SHA256={row["sha256"]}')
    if not rows or all(row["capture_status"] != "captured" for row in rows):
        raise SystemExit("No se capturó correctamente ninguna fuente.")
