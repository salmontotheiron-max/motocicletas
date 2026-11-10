import csv
import json
import tempfile
import unittest
from pathlib import Path

import generar_informe_territorial_integrado as report


class IntegratedReportTests(unittest.TestCase):
    def write_csv(self, path, fields, data):
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(data)

    def fixture(self, root, total=4):
        d = root / "data"; d.mkdir()
        self.write_csv(d/"matriculaciones_motocicletas_por_provincia.csv",
            ["periodo","ambito_provincial","COD_PROVINCIA","provincia","COD_TIPO","nuevo_usado","recuento"],
            [{"periodo":"2026-01","ambito_provincial":"matriculacion","COD_PROVINCIA":"SG","provincia":"Segovia","COD_TIPO":"50","nuevo_usado":"Nuevo","recuento":"3"},
             {"periodo":"2026-01","ambito_provincial":"domicilio_vehiculo","COD_PROVINCIA":"M","provincia":"Madrid","COD_TIPO":"50","nuevo_usado":"Usado","recuento":"1"}])
        self.write_csv(d/"ranking_motocicletas_provincia.csv",
            ["ambito_provincial","COD_PROVINCIA","provincia","recuento","peso_porcentual","puesto"],
            [{"ambito_provincial":"matriculacion","COD_PROVINCIA":"SG","provincia":"Segovia","recuento":"3","peso_porcentual":"100","puesto":"1"}])
        self.write_csv(d/"indicadores_intensidad_territorial.csv",
            ["COD_PROVINCIA","provincia","matriculaciones_nuevas","matriculaciones_por_1000_habitantes","matriculaciones_sobre_parque_pct","umbral_revision_parque_pct","alerta_revision"],
            [{"COD_PROVINCIA":"SG","provincia":"Segovia","matriculaciones_nuevas":"3","matriculaciones_por_1000_habitantes":"20","matriculaciones_sobre_parque_pct":"30","umbral_revision_parque_pct":"25","alerta_revision":"REVISAR"}])
        self.write_csv(d/"dispersion_balance_provincial.csv",
            ["COD_PROVINCIA","provincia","salidas_interprovinciales","entradas_interprovinciales","saldo_neto_entradas_menos_salidas"],
            [{"COD_PROVINCIA":"SG","provincia":"Segovia","salidas_interprovinciales":"2","entradas_interprovinciales":"0","saldo_neto_entradas_menos_salidas":"-2"}])
        self.write_csv(d/"dispersion_provincias_flujos.csv",
            ["provincia_matriculacion","provincia_domicilio_vehiculo","recuento"],
            [{"provincia_matriculacion":"Segovia","provincia_domicilio_vehiculo":"Madrid","recuento":"2"}])
        self.write_csv(d/"matriculaciones_nuevos_usados_por_tipo.csv",
            ["periodo","COD_TIPO","nuevo_usado","recuento"],
            [{"periodo":"2026-01","COD_TIPO":"50","nuevo_usado":"Nuevo","recuento":str(total-1)},
             {"periodo":"2026-01","COD_TIPO":"50","nuevo_usado":"Usado","recuento":"1"}])
        dispersion = {"total_matriculaciones":3,"misma_provincia":1,"otra_provincia":2,
            "domicilio_no_informado":0,"porcentaje_misma_provincia":33.3333,
            "porcentaje_interprovincial_sobre_domicilios_conocidos":66.6667,"matriz_filas":4,
            "validacion":{"agregado_provincial_coincide":True,"diferencias":0,"total_cruce":3,"total_agregado_provincial":3},
            "ranking_provincial":[{"provincia_matriculacion":"Segovia","matriculaciones":3,"domicilio_otra_provincia":2,"porcentaje_domicilio_externo_sobre_conocidos":66.6667}],
            "balance_interprovincial_por_provincia":[],
            "segovia":{"matriculaciones":3,"domicilio_segovia":1,"domicilio_madrid":2,"porcentaje_domicilio_externo_sobre_conocidos":66.6667,"porcentaje_domicilio_madrid_sobre_total":66.6667,
                "evolucion_mensual":[{"periodo":"2026-01","matriculaciones":3,"domicilio_segovia":1,"domicilio_madrid":2,"domicilio_otras_provincias":0}]}}
        (d/"informe_dispersion_provincias.json").write_text(json.dumps(dispersion),encoding="utf-8")
        return d

    def test_generates_dynamic_report_and_flags_segovia(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); data=self.fixture(root); output=root/"informe.md"
            result=report.build_report(data,output)
            body=output.read_text(encoding="utf-8")
            self.assertEqual(result["nuevas"],3)
            self.assertEqual(result["alertas"],["Segovia"])
            self.assertIn("2026-01",body)
            self.assertIn("REVISAR",body)
            self.assertIn("Domicilio Madrid",body)

    def test_generates_report_from_published_snapshot(self):
        data = Path(__file__).resolve().parents[1] / "public" / "data"
        required = ["matriculaciones_motocicletas_por_provincia.csv",
                    "ranking_motocicletas_provincia.csv",
                    "indicadores_intensidad_territorial.csv",
                    "dispersion_balance_provincial.csv",
                    "dispersion_provincias_flujos.csv",
                    "matriculaciones_nuevos_usados_por_tipo.csv",
                    "informe_dispersion_provincias.json"]
        if not all((data / name).exists() for name in required):
            self.skipTest("No hay snapshot MATRABA publicado en este checkout")
        with tempfile.TemporaryDirectory() as tmp:
            result = report.build_report(data, Path(tmp) / "informe.md")
            self.assertEqual(result["nuevas"], 219565)
            self.assertEqual(result["usadas"], 3078)
            self.assertEqual(result["alertas"], ["Segovia"])

    def test_rejects_inconsistent_totals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); data=self.fixture(root,total=5)
            with self.assertRaisesRegex(ValueError,"No concilian"):
                report.build_report(data,root/"informe.md")


if __name__ == "__main__":
    unittest.main()
