import csv
import tempfile
import unittest
from pathlib import Path

import generar_informe_dispersion as report


class DispersionReportTests(unittest.TestCase):
    def write_csv(self, path, fields, rows):
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_builds_matrix_rankings_segovia_and_validates_totals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cross = root / "cross.csv"
            provincial = root / "provincial.csv"
            self.write_csv(cross, [
                "periodo", "COD_PROVINCIA_MAT", "provincia_matriculacion",
                "COD_PROVINCIA_VEH", "provincia_domicilio_vehiculo", "COD_TIPO", "recuento",
            ], [
                {"periodo":"2026-01","COD_PROVINCIA_MAT":"SG","provincia_matriculacion":"Segovia","COD_PROVINCIA_VEH":"M","provincia_domicilio_vehiculo":"Madrid","COD_TIPO":"50","recuento":"3"},
                {"periodo":"2026-01","COD_PROVINCIA_MAT":"SG","provincia_matriculacion":"Segovia","COD_PROVINCIA_VEH":"SG","provincia_domicilio_vehiculo":"Segovia","COD_TIPO":"50","recuento":"1"},
                {"periodo":"2026-01","COD_PROVINCIA_MAT":"NA","provincia_matriculacion":"Navarra","COD_PROVINCIA_VEH":"NA","provincia_domicilio_vehiculo":"Navarra","COD_TIPO":"51","recuento":"1"},
            ])
            self.write_csv(provincial, [
                "periodo", "ambito_provincial", "COD_PROVINCIA", "provincia", "COD_TIPO", "nuevo_usado", "recuento",
            ], [
                {"periodo":"2026-01","ambito_provincial":"matriculacion","COD_PROVINCIA":"SG","provincia":"Segovia","COD_TIPO":"50","nuevo_usado":"Nuevo","recuento":"4"},
                {"periodo":"2026-01","ambito_provincial":"matriculacion","COD_PROVINCIA":"NA","provincia":"Navarra","COD_TIPO":"51","nuevo_usado":"Nuevo","recuento":"1"},
            ])
            summary = report.build_report(cross, provincial, root / "out")
            self.assertEqual(summary["total_matriculaciones"], 5)
            self.assertEqual(summary["misma_provincia"], 2)
            self.assertEqual(summary["otra_provincia"], 3)
            self.assertEqual(summary["porcentaje_interprovincial_sobre_domicilios_conocidos"], 60.0)
            self.assertTrue(summary["validacion"]["agregado_provincial_coincide"])
            self.assertEqual(summary["matriz_filas"], 9)
            self.assertEqual(summary["segovia"]["domicilio_madrid"], 3)
            self.assertEqual(summary["segovia"]["domicilio_segovia"], 1)
            balance = {row["COD_PROVINCIA"]: row for row in summary["balance_interprovincial_por_provincia"]}
            self.assertEqual(balance["SG"]["salidas_interprovinciales"], 3)
            self.assertEqual(balance["SG"]["entradas_interprovinciales"], 0)
            self.assertEqual(balance["SG"]["saldo_neto_entradas_menos_salidas"], -3)
            self.assertEqual(balance["SG"]["saldo_neto_sobre_matriculaciones_pct"], -75.0)
            self.assertEqual(balance["M"]["entradas_interprovinciales"], 3)
            self.assertTrue((root / "out" / "dispersion_balance_provincial.csv").exists())
            self.assertTrue((root / "out" / "matriz_dispersion_provincias.csv").exists())
            self.assertTrue((root / "out" / "informe_dispersion_provincias.json").exists())

    def test_fails_when_cross_does_not_match_provincial_aggregate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cross = root / "cross.csv"
            provincial = root / "provincial.csv"
            self.write_csv(cross, [
                "periodo", "COD_PROVINCIA_MAT", "provincia_matriculacion",
                "COD_PROVINCIA_VEH", "provincia_domicilio_vehiculo", "COD_TIPO", "recuento",
            ], [
                {"periodo":"2026-01","COD_PROVINCIA_MAT":"NA","provincia_matriculacion":"Navarra","COD_PROVINCIA_VEH":"NA","provincia_domicilio_vehiculo":"Navarra","COD_TIPO":"50","recuento":"2"},
            ])
            self.write_csv(provincial, [
                "periodo", "ambito_provincial", "COD_PROVINCIA", "provincia", "COD_TIPO", "nuevo_usado", "recuento",
            ], [
                {"periodo":"2026-01","ambito_provincial":"matriculacion","COD_PROVINCIA":"NA","provincia":"Navarra","COD_TIPO":"50","nuevo_usado":"Nuevo","recuento":"3"},
            ])
            with self.assertRaisesRegex(ValueError, "no cuadra"):
                report.build_report(cross, provincial, root / "out")


if __name__ == "__main__":
    unittest.main()
