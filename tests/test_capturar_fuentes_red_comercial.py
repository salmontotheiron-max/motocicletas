import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from capturar_fuentes_red_comercial import (
    extract_visible_text, fetch_page, persist_capture, robots_allowed
)


class TestCapturaFuentesRedComercial(unittest.TestCase):
    def test_extrae_texto_y_omite_scripts_estilos(self):
        html = "<html><style>oculto</style><body><h1>Concesionarios</h1><script>token()</script><p>Madrid   Centro</p></body></html>"
        self.assertEqual(extract_visible_text(html), "Concesionarios\nMadrid Centro")

    def test_hash_sha256_y_snapshot_comprimido(self):
        body = b"<html><body><h1>Red oficial</h1></body></html>"
        source = {"source_id": "source-test", "source_role": "primary_monitoring", "url": "https://example.test"}
        result = {"capture_status": "captured", "http_status": 200, "final_url": source["url"],
                  "content_type": "text/html; charset=utf-8", "body": body}
        with tempfile.TemporaryDirectory() as tmp:
            import capturar_fuentes_red_comercial as module
            previous = module.EVIDENCE
            module.EVIDENCE = Path(tmp)
            try:
                record = persist_capture(source, result, "2026-11-12T00:00:00+00:00")
                self.assertEqual(record["sha256"], hashlib.sha256(body).hexdigest())
                path = Path(tmp) / "snapshots" / "source-test" / f'{record["sha256"]}.html.gz'
                self.assertTrue(record["snapshot_path"].endswith(f'{record["sha256"]}.html.gz'))
                self.assertTrue(path.exists())
                with gzip.open(path, "rb") as stream:
                    self.assertEqual(stream.read(), body)
            finally:
                module.EVIDENCE = previous

    def test_fetch_rechaza_redireccion_no_https(self):
        class Headers(dict):
            pass
        class Response:
            status = 200
            headers = Headers({"Content-Type": "text/html"})
            def geturl(self):
                return "http://downgrade.example/"
            def read(self, size=-1):
                return b"<html/>"
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        with patch("capturar_fuentes_red_comercial.urlopen", return_value=Response()):
            result = fetch_page("https://example.test")
        self.assertEqual(result["capture_status"], "redirect_rejected")


    def test_fetch_rechaza_redireccion_a_otro_dominio(self):
        class Response:
            status = 200
            headers = {"Content-Type": "text/html"}
            def geturl(self):
                return "https://external.example/"
            def read(self, size=-1):
                return b"<html/>"
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        with patch("capturar_fuentes_red_comercial.urlopen", return_value=Response()):
            result = fetch_page("https://example.test")
        self.assertEqual(result["capture_status"], "redirect_rejected")

    def test_robots_fail_closed_si_no_se_puede_consultar(self):
        from urllib.error import URLError
        with patch("capturar_fuentes_red_comercial.urlopen", side_effect=URLError("offline")):
            allowed, status = robots_allowed("https://example.test/dealers")
        self.assertFalse(allowed)
        self.assertIn("robots_unavailable", status)


if __name__ == "__main__":
    unittest.main()
