import csv
import tempfile
import unittest
from pathlib import Path

from generar_indicadores_intensidad import build_report, read_reference

ROOT = Path(__file__).resolve().parents[1]
POPULATION = ROOT / "public/data/poblacion_provincial_2025.csv"
PARK = ROOT / "public/data/parque_motocicletas_provincia_2025.csv"


class IndicadoresIntensidadTests(unittest.TestCase):
    def test_referencias_cubren_52_territorios_y_total_parque(self):
        population = read_reference(POPULATION, "poblacion", "2025-01-01")
        park = read_reference(PARK, "parque_motocicletas", "2025-12-31")
        self.assertEqual(len(population), 52)
        self.assertEqual(set(population), set(park))
        self.assertEqual(sum(x["parque_motocicletas"] for x in park.values()), 4510222)
        self.assertEqual(population["NA"]["provincia"], "Navarra")
        self.assertEqual(park["SG"]["parque_motocicletas"], 11497)

    def test_calcula_indicadores_y_alerta_sin_excluir_seg o_via(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            provincial = temp / "provincial.csv"
            with provincial.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow([
                    "periodo", "ambito_provincial", "COD_PROVINCIA",
                    "provincia", "COD_TIPO", "nuevo_usado", "recuento",
                ])
                writer.writerow(["2026-01", "matriculacion", "SG", "Segovia", "50", "Nuevo", 8908])
                writer.writerow(["2026-01", "matriculacion", "NA", "Navarra", "50", "Nuevo", 1729])
                writer.writerow(["2026-01", "domicilio_vehiculo", "SG", "Segovia", "50", "Usado", 3])
            rows, metadata = build_report(
                provincial, POPULATION, PARK, temp / "out"
            )
            self.assertEqual(len(rows), 52)
            segovia = next(row for row in rows if row["COD_PROVINCIA"] == "SG")
            navarra = next(row for row in rows if row["COD_PROVINCIA"] == "NA")
            self.assertAlmostEqual(segovia["matriculaciones_por_1000_habitantes"], 56.2125, places=4)
            self.assertAlmostEqual(segovia["matriculaciones_sobre_parque_pct"], 77.4811, places=4)
            self.assertEqual(segovia["alerta_revision"], "REVISAR")
            self.assertEqual(segovia["matriculaciones_nuevas"], 8908)
            self.assertAlmostEqual(navarra["matriculaciones_por_1000_habitantes"], 2.5296, places=4)
            self.assertEqual(navarra["alerta_revision"], "")
            self.assertEqual(metadata["periodos_matriculaciones"], ["2026-01"])
            self.assertTrue((temp / "out/indicadores_intensidad_territorial.csv").exists())
            self.assertTrue((temp / "out/metodologia_indicadores_territoriales.json").exists())


if __name__ == "__main__":
    unittest.main()
