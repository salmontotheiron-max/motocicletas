"""Pruebas de integridad para la primera matriz territorial de concesionarios."""
import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "evidencias/red_comercial/establecimientos_prioridad_2026-11-12.json"
CSV_PATH = ROOT / "evidencias/red_comercial/establecimientos_prioridad_2026-11-12.csv"
PROVINCES = {"Barcelona", "Málaga", "Cádiz", "Alicante", "Murcia"}

class TestInventarioCoberturaPrioridad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        with CSV_PATH.open(encoding="utf-8-sig", newline="") as stream:
            cls.rows = list(csv.DictReader(stream))

    def test_json_csv_same_number_of_outlets(self):
        self.assertEqual(self.data["outlet_count"], len(self.rows))
        self.assertEqual(self.data["outlet_count"], len(self.data["outlets"]))

    def test_unique_outlet_ids_and_urls(self):
        ids = [row["outlet_id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(row["evidence_url"].startswith("https://") for row in self.rows))

    def test_all_rows_have_public_address_and_review_date(self):
        for row in self.rows:
            self.assertTrue(row["public_address"].strip(), row["outlet_id"])
            self.assertEqual(row["observed_at"], self.data["cutoff_date"])

    def test_scope_and_roles(self):
        self.assertEqual(set(row["province"] for row in self.rows), PROVINCES)
        self.assertTrue(all(row["outlet_role"] in {"sales", "service"} for row in self.rows))
        self.assertTrue(all(row["verification_status"] == "verified" for row in self.rows))

    def test_operator_groups_preserve_multi_site_operators(self):
        groups = {row["operator_group_id"] for row in self.rows}
        self.assertIn("motos-romero", groups)
        self.assertIn("servihonda", groups)
        self.assertIn("autoferro", groups)

    def test_service_entry_not_counted_as_sales(self):
        workshop = next(row for row in self.rows if row["outlet_id"] == "honda-lopera-workshop-malaga")
        self.assertEqual(workshop["outlet_role"], "service")
        self.assertFalse(any(row["outlet_id"] == workshop["outlet_id"] and row["outlet_role"] == "sales" for row in self.rows))

if __name__ == "__main__":
    unittest.main()
