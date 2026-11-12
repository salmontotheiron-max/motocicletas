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

    def source(self, discovery="directory_content_visible"):
        return {
            "source_id": "source-x",
            "source_role": "primary_monitoring",
            "brand_id": "brand-x",
            "url": "https://example.com/dealers",
            "discovery_status": discovery,
        }

    def capture(self, status="captured", text="Directorio oficial de establecimientos " * 4):
        return {
            "source_id": "source-x",
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
        result = classify_brand(self.brand, [self.source()], {"source-x": self.capture("http_error")})
        self.assertEqual(result["coverage_status"], "pending")

    def test_visible_directory_is_partial_until_outlets_are_audited(self):
        result = classify_brand(self.brand, [self.source()], {"source-x": self.capture()})
        self.assertEqual(result["coverage_status"], "partial")
        self.assertIn("not_individually_audited", result["coverage_basis"])

    def test_dynamic_locator_is_not_claimed_as_absent(self):
        result = classify_brand(
            self.brand, [self.source("locator_present_dynamic_content")],
            {"source-x": self.capture()},
        )
        self.assertEqual(result["coverage_status"], "dynamic_unextractable")

    def test_empty_locator_is_partial_not_not_found(self):
        result = classify_brand(
            self.brand, [self.source("locator_present_no_entries_yet")],
            {"source-x": self.capture()},
        )
        self.assertEqual(result["coverage_status"], "partial")

    def test_audit_keeps_all_brands_and_explicit_null_count(self):
        registry = {
            "brands": [self.brand, {
                "brand_id": "brand-y", "canonical_name": "Marca Y",
                "market_status": "established",
            }],
            "sources": [self.source()],
        }
        capture_data = {"captured_at": "2026-11-12T10:00:00+00:00",
                        "records": [self.capture()]}
        result = build_audit(registry, capture_data)
        self.assertEqual(result["brand_count"], 2)
        self.assertIsNone(result["verified_outlets_count"])
        self.assertEqual(result["status_counts"]["partial"], 1)
        self.assertEqual(result["status_counts"]["pending"], 1)


if __name__ == "__main__":
    unittest.main()
