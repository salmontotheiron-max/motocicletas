import csv
import tempfile
import unittest
from pathlib import Path

import analizar_concentracion_municipal as m


class MunicipalCrosswalkTests(unittest.TestCase):
    def test_normalize_accents_and_punctuation(self):
        self.assertEqual(m.normalize("Sant Vicenç dels Horts"), "SANT VICENC DELS HORTS")
        self.assertEqual(m.normalize("L'Hospitalet de Llobregat"), "L HOSPITALET DE LLOBREGAT")

    def test_parse_ine_thousands_separator(self):
        self.assertEqual(m.parse_integer("1.731.649"), 1731649)
        self.assertEqual(m.parse_integer("  73 "), 73)
        self.assertIsNone(m.parse_integer(""))

    def test_read_ine_keeps_2025_total_by_string_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ine.csv"
            path.write_text(
                "Municipios;Sexo;Periodo;Total\n"
                "08019 Barcelona;Total;2025;1.731.649\n"
                "08019 Barcelona;Total;2024;1.636.732\n",
                encoding="utf-8",
            )
            self.assertEqual(m.read_ine(path), {"08019": 1731649})

    def test_matraba_preserves_na_province_code_and_separates_suppression(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "matraba.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "periodo", "COD_PROVINCIA_MAT", "dimension", "categoria", "recuento"
                ])
                writer.writeheader()
                writer.writerows([
                    {"periodo": m.PERIOD, "COD_PROVINCIA_MAT": "NA",
                     "dimension": "municipio", "categoria": "PAMPLONA", "recuento": "23"},
                    {"periodo": m.PERIOD, "COD_PROVINCIA_MAT": "NA",
                     "dimension": "municipio", "categoria": m.SUPPRESSED, "recuento": "10"},
                    {"periodo": m.PERIOD, "COD_PROVINCIA_MAT": "NACIONAL",
                     "dimension": "municipio", "categoria": "PAMPLONA", "recuento": "999"},
                ])
            matched, unmatched, suppressed, totals = m.read_matraba(
                path, {m.normalize("PAMPLONA"): "31201"}
            )
            self.assertEqual(matched["31201"], 23)
            self.assertEqual(sum(suppressed.values()), 10)
            self.assertEqual(sum(unmatched.values()), 0)
            self.assertEqual(totals, {"NA": 33})


if __name__ == "__main__":
    unittest.main()
