"""Comparador conservador de capturas de fuentes de red comercial.

Genera candidatos técnicos de revisión; no identifica entidades ni modifica el
histórico. Solo compara capturas HTML válidas con texto suficiente.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidencias" / "red_comercial"
CAPTURES = EVIDENCE / "capturas.jsonl"
CANDIDATES = EVIDENCE / "candidatos_cambio.jsonl"
SUMMARY = EVIDENCE / "resumen_comparacion.json"
MIN_TEXT_CHARS = 80
MAX_EXCERPT_CHARS = 500

# Solo se descartan avisos de cookies inequívocos; no se eliminan fechas,
# nombres, direcciones ni otros contenidos potencialmente comerciales.
COOKIE_PATTERNS = (
    re.compile(r"^(aceptar|rechazar|configurar|gestionar)\s+(todas\s+)?las?\s+cookies\b", re.I),
    re.compile(r"^(utilizamos|usamos)\s+cookies\b", re.I),
    re.compile(r"^pol[ií]tica de cookies$", re.I),
)


def display_lines(value: str) -> list[str]:
    """Normaliza espacios y Unicode conservando mayúsculas para la evidencia."""
    value = unicodedata.normalize("NFKC", value or "")
    lines = []
    for raw in value.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or any(pattern.search(line) for pattern in COOKIE_PATTERNS):
            continue
        lines.append(line)
    return lines


def normalize_text(value: str) -> str:
    """Representación comparable, insensible a mayúsculas."""
    return "\n".join(line.casefold() for line in display_lines(value))


def load_capture_log(path: Path = CAPTURES) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido en {path}:{number}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Registro no objeto en {path}:{number}")
        records.append(record)
    return records


def is_comparable(record: dict) -> bool:
    return (
        record.get("capture_status") == "captured"
        and isinstance(record.get("source_id"), str)
        and isinstance(record.get("captured_at"), str)
        and isinstance(record.get("extracted_text"), str)
        and bool(record.get("sha256"))
        and bool(record.get("snapshot_path"))
    )


def _candidate_id(source_id: str, previous_hash: str, current_hash: str) -> str:
    raw = "\0".join((source_id, previous_hash, current_hash)).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compare_records(records: list[dict]) -> dict:
    """Compara capturas válidas consecutivas por fuente, en orden temporal."""
    grouped: dict[str, list[dict]] = {}
    ignored = 0
    for record in records:
        if not is_comparable(record):
            ignored += 1
            continue
        grouped.setdefault(record["source_id"], []).append(record)

    candidates = []
    baselines = 0
    insufficient = 0
    unchanged = 0
    for source_id, rows in sorted(grouped.items()):
        rows.sort(key=lambda row: (row["captured_at"], row.get("sha256", "")))
        previous = None
        for current in rows:
            current_text = normalize_text(current["extracted_text"])
            if len(current_text) < MIN_TEXT_CHARS:
                insufficient += 1
                # Una captura tipo carcasa JS no reemplaza el último baseline
                # válido: no debe ocultar cambios entre dos páginas completas.
                continue
            if previous is None:
                previous = (current, current_text)
                baselines += 1
                continue

            old_record, old_text = previous
            old_hash = old_record.get("text_sha256") or hashlib.sha256(
                old_text.encode("utf-8")
            ).hexdigest()
            new_hash = current.get("text_sha256") or hashlib.sha256(
                current_text.encode("utf-8")
            ).hexdigest()
            if old_hash == new_hash or old_text == current_text:
                unchanged += 1
                previous = (current, current_text)
                continue

            old_display = display_lines(old_record["extracted_text"])
            new_display = display_lines(current["extracted_text"])
            old_lines = {line.casefold() for line in old_display}
            new_lines = {line.casefold() for line in new_display}
            added = [line for line in new_display if line.casefold() not in old_lines]
            removed = [line for line in old_display if line.casefold() not in new_lines]
            candidate = {
                "candidate_id": _candidate_id(source_id, old_record["sha256"], current["sha256"]),
                "candidate_type": "source_content_changed",
                "review_status": "pending_manual_review",
                "source_id": source_id,
                "previous_captured_at": old_record["captured_at"],
                "current_captured_at": current["captured_at"],
                "previous_sha256": old_record["sha256"],
                "current_sha256": current["sha256"],
                "previous_text_sha256": old_hash,
                "current_text_sha256": new_hash,
                "previous_snapshot_path": old_record["snapshot_path"],
                "current_snapshot_path": current["snapshot_path"],
                "added_lines": added[:20],
                "removed_lines": removed[:20],
                "added_excerpt": "\n".join(added)[:MAX_EXCERPT_CHARS],
                "removed_excerpt": "\n".join(removed)[:MAX_EXCERPT_CHARS],
                "interpretation": (
                    "Cambio textual observado en la fuente. No implica por sí mismo "
                    "alta, baja, cierre, cambio de operador ni actividad comercial."
                ),
            }
            candidates.append(candidate)
            previous = (current, current_text)

    candidates.sort(key=lambda item: (
        item["current_captured_at"], item["source_id"], item["candidate_id"]
    ))
    return {
        "total_records": len(records),
        "comparable_sources": len(grouped),
        "baseline_captures": baselines,
        "unchanged_comparisons": unchanged,
        "insufficient_content_captures": insufficient,
        "ignored_records": ignored,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def run_comparison(capture_path: Path = CAPTURES,
                   candidate_path: Path = CANDIDATES,
                   summary_path: Path = SUMMARY) -> dict:
    result = compare_records(load_capture_log(capture_path))
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    with candidate_path.open("w", encoding="utf-8") as stream:
        for candidate in result["candidates"]:
            stream.write(json.dumps(candidate, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {key: value for key, value in result.items() if key != "candidates"}
    summary["candidate_file"] = candidate_path.as_posix()
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    outcome = run_comparison()
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
