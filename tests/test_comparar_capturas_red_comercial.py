import json
import tempfile
import unittest
from pathlib import Path

from comparar_capturas_red_comercial import (
    compare_records, normalize_text, run_comparison
)


def row(source, date, digest, text, status="captured"):
    return {
        "source_id": source, "captured_at": date, "capture_status": status,
        "sha256": digest, "text_sha256": digest + "-text",
        "snapshot_path": f"snapshots/{source}/{digest}.html.gz",
        "extracted_text": text,
    }


class TestCompararCapturasRedComercial(unittest.TestCase):
    def test_normaliza_unicode_espacios_y_cookie_banner(self):
        value = "  RED   OFICIAL \n Aceptar todas las cookies \nPuntos de venta"
        self.assertEqual(normalize_text(value), "red oficial\npuntos de venta")

    def test_primera_captura_solo_establece_baseline(self):
        result = compare_records([row("a", "2026-11-01", "h1", "Directorio oficial " * 10)])
        self.assertEqual(result["baseline_captures"], 1)
        self.assertEqual(result["candidate_count"], 0)

    def test_cambio_textual_genera_candidato_pendiente(self):
        old = "Directorio oficial de concesionarios. " * 5
        new = old + "\nNuevo punto de venta en Murcia."
        result = compare_records([
            row("a", "2026-11-01T00:00:00Z", "h1", old),
            row("a", "2026-11-08T00:00:00Z", "h2", new),
        ])
        self.assertEqual(result["candidate_count"], 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["review_status"], "pending_manual_review")
        self.assertIn("Nuevo punto de venta", candidate["added_excerpt"])
        self.assertIn("No implica por sí mismo", candidate["interpretation"])

    def test_error_http_no_se_interpreta_como_baja(self):
        old = "Directorio oficial de concesionarios. " * 5
        result = compare_records([
            row("a", "2026-11-01T00:00:00Z", "h1", old),
            row("a", "2026-11-08T00:00:00Z", "h2", "", status="http_error"),
        ])
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["ignored_records"], 1)

    def test_carcasa_dinamica_no_sustituye_baseline(self):
        old = "Directorio oficial de concesionarios. " * 5
        new = old + "\nNuevo establecimiento confirmado en Murcia."
        shell = "Cargando..."
        result = compare_records([
            row("a", "2026-11-01T00:00:00Z", "h1", old),
            row("a", "2026-11-05T00:00:00Z", "shell", shell),
            row("a", "2026-11-08T00:00:00Z", "h2", new),
        ])
        self.assertEqual(result["insufficient_content_captures"], 1)
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["previous_sha256"], "h1")

    def test_igual_contenido_no_genera_candidato(self):
        text = "Directorio oficial de concesionarios. " * 5
        result = compare_records([
            row("a", "2026-11-01T00:00:00Z", "h1", text),
            row("a", "2026-11-08T00:00:00Z", "h2", text),
        ])
        self.assertEqual(result["unchanged_comparisons"], 1)
        self.assertEqual(result["candidate_count"], 0)

    def test_ignora_cambios_solo_de_mayusculas_y_cookies(self):
        old = "DIRECTORIO OFICIAL DE CONCESIONARIOS. " * 4
        new = "Directorio oficial de concesionarios. " * 4 + "\nAceptar todas las cookies"
        result = compare_records([
            row("a", "2026-11-01T00:00:00Z", "h1", old),
            row("a", "2026-11-08T00:00:00Z", "h2", new),
        ])
        self.assertEqual(result["unchanged_comparisons"], 1)
        self.assertEqual(result["candidate_count"], 0)

    def test_cambios_en_multiplicidad_aparecen_en_extractos(self):
        repeated = "Horario de atención de lunes a viernes."
        old = "Directorio oficial de concesionarios. " * 3 + "\\n" + repeated + "\\n" + repeated
        new = "Directorio oficial de concesionarios. " * 3 + "\\n" + repeated
        result = compare_records([
            row("a", "2026-11-01T00:00:00Z", "h1", old),
            row("a", "2026-11-08T00:00:00Z", "h2", new),
        ])
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["removed_lines"], [repeated])

    def test_formato_registro_real_primera_captura(self):
        # Fixture compacto con el esquema de capturas.jsonl de PR #21:
        # siete fuentes HTTP 200 y una fuente bloqueada por robots.
        records = []
        for index in range(7):
            records.append({
                "capture_status": "captured",
                "captured_at": "2026-11-12T09:25:53+00:00",
                "http_status": 200,
                "source_id": f"source-{index}",
                "sha256": f"digest-{index}",
                "snapshot_path": f"evidencias/red_comercial/snapshots/{index}.html.gz",
                "extracted_text": "Directorio oficial de concesionarios y puntos de venta. " * 3,
            })
        records.append({
            "capture_status": "robots_disallowed",
            "captured_at": "2026-11-12T09:25:53+00:00",
            "http_status": 403,
            "source_id": "source-blocked",
            "sha256": None,
            "snapshot_path": None,
            "extracted_text": "",
        })
        result = compare_records(records)
        self.assertEqual(result["total_records"], 8)
        self.assertEqual(result["comparable_sources"], 7)
        self.assertEqual(result["baseline_captures"], 7)
        self.assertEqual(result["ignored_records"], 1)
        self.assertEqual(result["candidate_count"], 0)

    def test_run_escribe_jsonl_y_resumen(self):
        text = "Directorio oficial de concesionarios. " * 5
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "capturas.jsonl"
            log.write_text(json.dumps(row("a", "2026-11-01", "h1", text)) + "\n" +
                           json.dumps(row("a", "2026-11-08", "h2", text + "Nuevo punto.")) + "\n",
                           encoding="utf-8")
            candidates = root / "candidatos.jsonl"
            summary = root / "resumen.json"
            outcome = run_comparison(log, candidates, summary)
            self.assertEqual(outcome["candidate_count"], 1)
            self.assertTrue(candidates.exists())
            self.assertEqual(len(candidates.read_text(encoding="utf-8").splitlines()), 1)
            self.assertEqual(json.loads(summary.read_text(encoding="utf-8"))["candidate_count"], 1)


if __name__ == "__main__":
    unittest.main()
