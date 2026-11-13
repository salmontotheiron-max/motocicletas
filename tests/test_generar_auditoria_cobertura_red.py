"""Pruebas de la auditoría de cobertura de red comercial."""
import unittest

from generar_auditoria_cobertura_red import build_audit, classify_brand


class CoverageAuditTests(unittest.TestCase):
    def setUp(self):
        self.brand = {
            "brand_id": "brand-x",
            "canonical_name": "Marca X",
            "market_status": "under_review",
        }

    def source(self, discovery="directory_content_visible", source_id="source-x",
               source_type="official_directory"):
        return {
            "source_id": source_id,
            "source_role": "primary_monitoring",
            "brand_id": "brand-x",
            "source_type": source_type,
            "url": "https://example.com/dealers",
            "discovery_status": discovery,
        }

    def capture(self, status="captured",
                text="Directorio oficial de establecimientos " * 4,
                source_id="source-x"):
        return {
            "source_id": source_id,
            "captured_at": "2026-11-12T10:00:00+00:00",
            "capture_status": status,
            "http_status": 200 if status == "captured" else 503,
            "extracted_text": text if status == "captured" else None,
        }

    def test_no_source_is_pending_not_not_found(self):
        result = classify_brand(self.brand, [], {})
        self.assertEqual(result["coverage_status"], "pending")
        self.assertNotEqual(result["coverage_status"], "not_found")

    def test_failed_capture_is_pending(self):
        result = classify_brand(
            self.brand, [self.source()],
            {"source-x": self.capture("http_error")},
        )
        self.assertEqual(result["coverage_status"], "pending")

    def test_visible_directory_is_partial_until_outlets_are_audited(self):
        result = classify_brand(
            self.brand, [self.source()], {"source-x": self.capture()}
        )
        self.assertEqual(result["coverage_status"], "partial")
        self.assertIn("not_individually_audited", result["coverage_basis"])

    def test_dynamic_locator_is_not_claimed_as_absent(self):
        result = classify_brand(
            self.brand, [self.source("locator_present_dynamic_content")],
            {"source-x": self.capture()},
        )
        self.assertEqual(result["coverage_status"], "dynamic_unextractable")

    def test_dynamic_unextractable_discovery_state_is_recognized(self):
        result = classify_brand(
            self.brand, [self.source("dynamic_unextractable")],
            {"source-x": self.capture()},
        )
        self.assertEqual(result["coverage_status"], "dynamic_unextractable")

    def test_empty_locator_is_partial_not_not_found(self):
        result = classify_brand(
            self.brand, [self.source("locator_present_no_entries_yet")],
            {"source-x": self.capture()},
        )
        self.assertEqual(result["coverage_status"], "partial")

    def test_official_directory_is_preferred_over_official_statement(self):
        news = self.source(
            "directory_content_visible", "source-a-news", "official_statement"
        )
        directory = self.source(
            "directory_content_visible", "source-z-dealers", "official_directory"
        )
        result = classify_brand(
            self.brand, [news, directory],
            {"source-z-dealers": self.capture(source_id="source-z-dealers")},
        )
        self.assertEqual(result["primary_source_id"], "source-z-dealers")
        self.assertEqual(result["source_type"], "official_directory")
        self.assertEqual(result["coverage_status"], "partial")

    def test_no_official_directory_is_pending_even_with_statement_capture(self):
        statement = self.source(
            "directory_content_visible", "source-statement", "official_statement"
        )
        result = classify_brand(
            self.brand, [statement],
            {"source-statement": self.capture(source_id="source-statement")},
        )
        self.assertEqual(result["coverage_status"], "pending")
        self.assertEqual(
            result["coverage_basis"], "no_official_dealer_directory_registered"
        )

    def test_audit_keeps_all_brands_and_explicit_null_outlet_count(self):
        registry = {
            "registry_reviewed_at": "2026-11-13",
            "brands": [self.brand, {
                "brand_id": "brand-y", "canonical_name": "Marca Y",
                "market_status": "established",
            }],
            "sources": [self.source()],
        }
        capture_data = {
            "captured_at": "2026-11-12T10:00:00+00:00",
            "records": [self.capture()],
        }
        result = build_audit(registry, capture_data)
        self.assertEqual(result["brand_count"], 2)
        self.assertEqual(result["registry_reviewed_at"], "2026-11-13")
        self.assertIsNone(result["verified_outlets_count"])
        self.assertEqual(result["status_counts"]["partial"], 1)
        self.assertEqual(result["status_counts"]["pending"], 1)
        self.assertEqual(result["primary_source_count"], 1)
        self.assertEqual(result["primary_sources_captured_count"], 1)


if __name__ == "__main__":
    unittest.main()
