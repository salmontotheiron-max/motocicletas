import json
import sqlite3
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request

from capturar_fuentes_red_comercial import (
    SameOriginRedirectHandler,
    apply_migration,
    classify_http,
    fetch_page,
    load_sources,
    run_capture,
)


class FakeHeaders(dict):
    pass


class FakeResponse:
    def __init__(self, body=b"<html>directorio</html>", status=200,
                 url="https://example.org/listado"):
        self.body = body
        self.status = status
        self.url = url
        self.headers = FakeHeaders({"Content-Type": "text/html; charset=utf-8"})

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status

    def read(self, limit=-1):
        return self.body[:limit]


class CaptureTests(unittest.TestCase):
    def test_current_main_inventory_schema_v2_is_supported(self):
        sources = load_sources(Path(__file__).resolve().parents[1] / "fuentes_red_comercial.json")
        self.assertGreaterEqual(len(sources), 15)
        self.assertIn("source-honda-es-moto-dealers", {item["source_id"] for item in sources})

    def test_classify_http_keeps_url_absence_separate_from_closure(self):
        self.assertEqual(classify_http(404)["result"], "not_found")
        self.assertEqual(classify_http(410)["result"], "not_found")
        self.assertEqual(classify_http(503)["result"], "unavailable")
        self.assertEqual(classify_http(403)["result"], "error")

    def test_fetch_page_hashes_successful_response(self):
        result = fetch_page(
            "https://example.org/listado",
            opener=lambda *a, **k: FakeResponse(),
        )
        self.assertEqual(result["result"], "success")
        self.assertEqual(len(result["content_hash"]), 64)
        self.assertGreater(result["content_length"], 0)

    def test_fetch_page_rejects_cross_origin_final_url(self):
        result = fetch_page(
            "https://example.org/listado",
            opener=lambda *a, **k: FakeResponse(url="https://other.example/listado"),
        )
        self.assertEqual(result["result"], "error")
        self.assertEqual(result["error_category"], "redirect")

    def test_redirect_handler_blocks_cross_host_before_following(self):
        handler = SameOriginRedirectHandler()
        request = Request("https://example.org/listado")
        with self.assertRaisesRegex(Exception, "fuera del origen"):
            handler.redirect_request(
                request, BytesIO(b""), 302, "Found", {}, "https://other.example/listado"
            )

    def test_redirect_handler_allows_same_origin_https(self):
        handler = SameOriginRedirectHandler()
        request = Request("https://example.org/listado")
        redirected = handler.redirect_request(
            request, BytesIO(b""), 302, "Found", {}, "/directorio"
        )
        self.assertEqual(redirected.full_url, "https://example.org/directorio")

    def test_fetch_page_classifies_network_error(self):
        def fail(*args, **kwargs):
            raise URLError("offline")
        result = fetch_page("https://example.org/listado", opener=fail)
        self.assertEqual(result["result"], "unavailable")

    def test_fetch_page_enforces_response_size(self):
        from capturar_fuentes_red_comercial import MAX_BYTES
        result = fetch_page(
            "https://example.org/listado",
            opener=lambda *a, **k: FakeResponse(b"x" * (MAX_BYTES + 1)),
        )
        self.assertEqual(result["result"], "error")
        self.assertEqual(result["error_category"], "size_limit")

    def test_capture_marks_unchanged_and_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = root / "sources.json"
            inventory.write_text(json.dumps({
                "schema_version": 2,
                "sources": [{
                    "source_id": "test-source",
                    "publisher": "Test",
                    "source_type": "company_page",
                    "reliability_class": "primary_business",
                    "title": "Test page",
                    "url": "https://example.org/listado",
                }],
            }), encoding="utf-8")
            database = root / "test.sqlite"
            first = run_capture(database, inventory, opener=lambda *a, **k: FakeResponse(b"version-1"))
            second = run_capture(database, inventory, opener=lambda *a, **k: FakeResponse(b"version-1"))
            third = run_capture(database, inventory, opener=lambda *a, **k: FakeResponse(b"version-2"))
            connection = sqlite3.connect(database)
            rows = connection.execute(
                "SELECT result FROM source_capture ORDER BY rowid"
            ).fetchall()
            observations = connection.execute(
                "SELECT COUNT(*) FROM observation"
            ).fetchone()[0]
            connection.close()
            self.assertEqual(rows, [("success",), ("unchanged",), ("changed",)])
            self.assertEqual(observations, 2)
            self.assertNotEqual(first[0], second[0])
            self.assertNotEqual(second[0], third[0])

    def test_migration_is_idempotent(self):
        from validar_red_comercial import initialize_database
        with tempfile.TemporaryDirectory() as directory:
            connection = initialize_database(Path(directory) / "schema.sqlite")
            apply_migration(connection)
            apply_migration(connection)
            names = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            self.assertIn("source_capture", names)
            connection.close()

    def test_inventory_rejects_non_https_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "bad.json"
            inventory.write_text(json.dumps({
                "schema_version": 2,
                "sources": [{
                    "source_id": "bad",
                    "publisher": "Test",
                    "source_type": "company_page",
                    "reliability_class": "primary_business",
                    "title": "Bad",
                    "url": "http://example.org",
                }],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                load_sources(inventory)


if __name__ == "__main__":
    unittest.main()
