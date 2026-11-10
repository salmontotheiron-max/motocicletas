import csv
import tempfile
import unittest
from pathlib import Path

import auditar_composicion_motocicletas as a


class CompositionAuditTests(unittest.TestCase):
    def test_dispersal_uses_registration_province_as_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cross.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["COD_PROVINCIA_MAT", "COD_PROVINCIA_VEH", "recuento"])
                writer.writerow(["SG", "SG", 10])
                writer.writerow(["SG", "M", 90])
                writer.writerow(["M", "M", 100])
            self.assertIn("SG", a.read_dispersal(path))
            self.assertNotIn("M", a.read_dispersal(path))

    def test_thresholds_are_more_restrictive_for_municipality(self):
        self.assertEqual(a.MINIMUMS["municipio"], 20)
        self.assertEqual(a.DIMENSIONS["marca"][1], 10)

    def test_cumulative_period_sums_months_without_losing_monthly_rows(self):
        from collections import Counter
        counts = Counter({
            ("SG", "2026-01", "marca", "HONDA"): 4,
            ("SG", "2026-02", "marca", "HONDA"): 7,
        })
        denominators = Counter({
            ("SG", "2026-01"): 10,
            ("SG", "2026-02"): 12,
        })
        a.add_cumulative_period(counts, denominators)
        self.assertEqual(counts[("SG", "2026-01/09", "marca", "HONDA")], 11)
        self.assertEqual(denominators[("SG", "2026-01/09")], 22)
        self.assertEqual(counts[("SG", "2026-01", "marca", "HONDA")], 4)

    def test_suppressed_totals_are_not_published_below_threshold(self):
        self.assertEqual(a.safe_published_count(9, "marca"), "")
        self.assertEqual(a.safe_published_count(10, "marca"), 10)
        self.assertEqual(a.safe_published_count(19, "municipio"), "")
        self.assertEqual(a.safe_published_count(20, "municipio"), 20)

    def test_only_expected_dimensions_are_exported(self):
        self.assertEqual(set(a.DIMENSIONS), {
            "clase_matricula", "marca", "modelo", "procedencia",
            "cilindrada_cc", "titular_fisico_juridico", "servicio",
            "municipio", "renting",
        })


if __name__ == "__main__":
    unittest.main()
