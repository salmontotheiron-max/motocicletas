import csv
import tempfile
import unittest
from pathlib import Path

from generar_informe_provincial import build_reports, load_rows


class ProvincialReportTests(unittest.TestCase):
    def write_input(self, root, rows):
        path = root / "provincial.csv"
        fields = [
            "periodo", "ambito_provincial", "COD_PROVINCIA", "provincia",
            "COD_TIPO", "nuevo_usado", "recuento",
        ]
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_navarra_code_is_preserved_and_empty_codes_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.write_input(root, [
                {
                    "periodo": "2026-01", "ambito_provincial": "matriculacion",
                    "COD_PROVINCIA": "NA", "provincia": "Navarra",
                    "COD_TIPO": "50", "nuevo_usado": "Nuevo", "recuento": "10",
                },
                {
                    "periodo": "2026-01", "ambito_provincial": "domicilio_vehiculo",
                    "COD_PROVINCIA": "NA", "provincia": "Navarra",
                    "COD_TIPO": "50", "nuevo_usado": "Usado", "recuento": "2",
                },
            ])
            summary = build_reports(load_rows(source), root / "out")
            self.assertEqual(summary["totales_y_concentracion"]["matriculacion"]["total"], 10)
            self.assertEqual(summary["totales_y_concentracion"]["domicilio_vehiculo"]["total"], 2)
            self.assertEqual(summary["codigos_provinciales_vacios"], [])
            with (root / "out" / "ranking_motocicletas_provincia.csv").open(
                encoding="utf-8-sig"
            ) as handle:
                rankings = list(csv.DictReader(handle))
            self.assertTrue(any(row["COD_PROVINCIA"] == "NA" and row["provincia"] == "Navarra"
                                for row in rankings))

    def test_blank_province_code_is_explicitly_reported_not_silently_assigned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.write_input(root, [{
                "periodo": "2026-01", "ambito_provincial": "matriculacion",
                "COD_PROVINCIA": "", "provincia": "Código no catalogado",
                "COD_TIPO": "50", "nuevo_usado": "Nuevo", "recuento": "3",
            }])
            summary = build_reports(load_rows(source), root / "out")
            self.assertEqual(summary["codigos_provinciales_vacios"][0]["recuento"], 3)

    def test_new_and_used_must_use_their_defined_geographical_scopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.write_input(root, [{
                "periodo": "2026-01", "ambito_provincial": "matriculacion",
                "COD_PROVINCIA": "NA", "provincia": "Navarra",
                "COD_TIPO": "50", "nuevo_usado": "Usado", "recuento": "3",
            }])
            with self.assertRaises(ValueError):
                load_rows(source)

    def test_monthly_share_and_rankings_are_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.write_input(root, [
                {
                    "periodo": "2026-01", "ambito_provincial": "matriculacion",
                    "COD_PROVINCIA": "B", "provincia": "Barcelona",
                    "COD_TIPO": "50", "nuevo_usado": "Nuevo", "recuento": "60",
                },
                {
                    "periodo": "2026-01", "ambito_provincial": "matriculacion",
                    "COD_PROVINCIA": "M", "provincia": "Madrid",
                    "COD_TIPO": "50", "nuevo_usado": "Nuevo", "recuento": "40",
                },
            ])
            build_reports(load_rows(source), root / "out")
            with (root / "out" / "ranking_motocicletas_provincia.csv").open(
                encoding="utf-8-sig"
            ) as handle:
                ranking = list(csv.DictReader(handle))
            self.assertEqual(ranking[0]["provincia"], "Barcelona")
            self.assertEqual(ranking[0]["peso_porcentual"], "60.0")
            with (root / "out" / "evolucion_motocicletas_provincia.csv").open(
                encoding="utf-8-sig"
            ) as handle:
                monthly = list(csv.DictReader(handle))
            self.assertEqual(sum(float(row["peso_porcentual"]) for row in monthly), 100.0)


if __name__ == "__main__":
    unittest.main()
