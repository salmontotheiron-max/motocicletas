import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from capturar_fuentes_red_comercial import (
    capture_all, extract_visible_text, fetch_page, persist_capture, robots_allowed
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
        with patch("capturar_fuentes_red_comercial._open_without_redirects", return_value=Response()):
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
        with patch("capturar_fuentes_red_comercial._open_without_redirects", return_value=Response()):
            result = fetch_page("https://example.test")
        self.assertEqual(result["capture_status"], "redirect_rejected")

    def test_robots_fail_closed_si_no_se_puede_consultar(self):
        from urllib.error import URLError
        with patch("capturar_fuentes_red_comercial._open_without_redirects", side_effect=URLError("offline")):
            allowed, status = robots_allowed("https://example.test/dealers")
        self.assertFalse(allowed)
        self.assertIn("robots_unavailable", status)


    def test_redirect_se_rechaza_antes_de_solicitar_otro_dominio(self):
        from urllib.error import HTTPError
        from email.message import Message
        headers = Message()
        headers["Location"] = "https://external.example/dealers"
        redirect = HTTPError("https://example.test", 302, "Found", headers, None)
        with patch("capturar_fuentes_red_comercial._open_without_redirects", side_effect=redirect) as opener:
            result = fetch_page("https://example.test")
        self.assertEqual(result["capture_status"], "redirect_rejected")
        self.assertEqual(opener.call_count, 1)

    def test_redirect_a_subdominio_no_autorizado_se_rechaza(self):
        from urllib.error import HTTPError
        from email.message import Message
        headers = Message()
        headers["Location"] = "https://www.example.test/dealers"
        redirect = HTTPError("https://example.test", 301, "Moved", headers, None)
        with patch("capturar_fuentes_red_comercial._open_without_redirects", side_effect=redirect):
            result = fetch_page("https://example.test")
        self.assertEqual(result["capture_status"], "redirect_rejected")

    def test_redirect_https_mismo_host_revalida_robots(self):
        from urllib.error import HTTPError
        from email.message import Message
        headers = Message()
        headers["Location"] = "/directorio"
        redirect = HTTPError("https://example.test", 302, "Found", headers, None)
        class Response:
            status = 200
            headers = {"Content-Type": "text/html"}
            def geturl(self):
                return "https://example.test/directorio"
            def read(self, size=-1):
                return b"<html><body>Directorio</body></html>"
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        with patch("capturar_fuentes_red_comercial._open_without_redirects",
                   side_effect=[redirect, Response()]), \
             patch("capturar_fuentes_red_comercial.robots_allowed",
                   return_value=(True, "robots_txt")) as robots:
            result = fetch_page("https://example.test")
        self.assertEqual(result["capture_status"], "captured")
        robots.assert_called_once_with("https://example.test/directorio")

    def test_redirect_bloqueada_por_robots_no_se_sigue(self):
        from urllib.error import HTTPError
        from email.message import Message
        headers = Message()
        headers["Location"] = "/directorio"
        redirect = HTTPError("https://example.test", 302, "Found", headers, None)
        with patch("capturar_fuentes_red_comercial._open_without_redirects",
                   side_effect=redirect), \
             patch("capturar_fuentes_red_comercial.robots_allowed",
                   return_value=(False, "robots_disallowed")) as robots:
            result = fetch_page("https://example.test")
        self.assertEqual(result["capture_status"], "redirect_robots_disallowed")
        robots.assert_called_once()

    def test_host_alternativo_solo_se_acepta_si_se_autoriza_expresamente(self):
        from urllib.error import HTTPError
        from email.message import Message
        headers = Message()
        headers["Location"] = "https://www.example.test/dealers"
        redirect = HTTPError("https://example.test", 301, "Moved", headers, None)
        class Response:
            status = 200
            headers = {"Content-Type": "text/html"}
            def geturl(self):
                return "https://www.example.test/dealers"
            def read(self, size=-1):
                return b"<html><body>Dealers</body></html>"
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        with patch("capturar_fuentes_red_comercial._open_without_redirects",
                   side_effect=[redirect, Response()]), \
             patch("capturar_fuentes_red_comercial.robots_allowed",
                   return_value=(True, "robots_txt")) as robots:
            result = fetch_page("https://example.test", ["www.example.test"])
        self.assertEqual(result["capture_status"], "captured")
        robots.assert_called_once_with("https://www.example.test/dealers")


    def test_robots_no_sigue_redireccion_automaticamente(self):
        from urllib.error import HTTPError
        from email.message import Message
        headers = Message()
        headers["Location"] = "https://external.example/robots.txt"
        redirect = HTTPError("https://example.test/robots.txt", 302, "Found", headers, None)
        with patch("capturar_fuentes_red_comercial._open_without_redirects", side_effect=redirect) as opener:
            allowed, status = robots_allowed("https://example.test/dealers")
        self.assertFalse(allowed)
        self.assertIn("robots_http_302", status)
        self.assertEqual(opener.call_count, 1)

    def test_registra_fallos_aunque_ninguna_fuente_se_capture(self):
        source = {"source_id": "source-test", "source_role": "primary_monitoring",
                  "url": "https://example.test", "capture_mode": "http_html"}
        with tempfile.TemporaryDirectory() as tmp, \
             patch("capturar_fuentes_red_comercial.load_sources", return_value=[source]), \
             patch("capturar_fuentes_red_comercial.robots_allowed",
                   return_value=(False, "robots_unavailable")), \
             patch("capturar_fuentes_red_comercial.time.sleep"):
            records = capture_all(evidence_dir=Path(tmp))
        self.assertEqual(records[0]["capture_status"], "robots_disallowed")
        log = Path(tmp) / "capturas.jsonl"
        summary = Path(tmp) / "ultima_captura.json"
        self.assertTrue(log.exists())
        self.assertTrue(summary.exists())
        self.assertIn('"robots_disallowed"', log.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(summary.read_text(encoding="utf-8"))["failures"], 1)


if __name__ == "__main__":
    unittest.main()
