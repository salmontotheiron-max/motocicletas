from pathlib import Path
import unittest


class DashboardMotorcycleFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (Path(__file__).resolve().parents[1] / "index.html").read_text(
            encoding="utf-8"
        )

    def test_default_filter_is_motorcycles_50_and_51(self):
        self.assertIn(
            '<option value="motos" selected>Motocicletas (50 + 51)</option>',
            self.html,
        )

    def test_all_observed_types_is_an_explicit_separate_option(self):
        self.assertIn(
            '<option value="all">Todos los tipos observados</option>',
            self.html,
        )

    def test_type_predicate_keeps_motorcycles_separate(self):
        self.assertIn(
            'if(k==="motos")return ["50","51"].includes(String(r.COD_TIPO));',
            self.html,
        )
        self.assertIn('if(k==="all")return true;', self.html)

    def test_shared_predicate_is_used_across_dashboard_views(self):
        self.assertGreaterEqual(self.html.count("typeOK(r,f.kind)"), 5)

    def test_precomputed_motorcycle_ranking_is_not_used_for_all_types(self):
        self.assertIn('f.kind==="motos"', self.html)
        self.assertNotIn('f.kind==="all"){\n    rows=state.ranking', self.html)

    def test_composition_chart_uses_the_selected_type_filter_and_scope(self):
        start = self.html.index("function renderTypes(f){")
        end = self.html.index("\nfunction renderRanking(f){", start)
        chart = self.html[start:end]
        self.assertIn('const source=f.province==="all"?state.monthly:state.provincial;', chart)
        self.assertIn("typeOK(r,f.kind)", chart)
        self.assertIn('r.ambito_provincial==="matriculacion"', chart)
        self.assertIn('"90":"Ciclomotor de dos ruedas"', chart)
        self.assertIn('"92":"Cuadriciclo ligero"', chart)
        self.assertIn('el("typeNote").textContent=', chart)

    def test_csv_export_includes_all_filtered_operation_families(self):
        start = self.html.index("function exportCSV(){")
        end = self.html.index('\n["period","province","kind"]', start)
        export = self.html[start:end]
        self.assertIn('r.tipo_registro', export)
        self.assertIn('"venta":"Transferencia · venta declarada DGT"', export)
        self.assertIn('"subasta":"Transferencia · subasta"', export)
        self.assertIn('"transferencia_sin_clasificar":"Transferencia · sin clasificar"', export)
        self.assertIn('typeOK(r,f.kind)', export)
        self.assertIn('f.province===r.provincia', export)
        self.assertIn('"nivel_agregacion","periodo","tipo_registro"', export)
        self.assertIn('"marca","modelo","recuento"', export)
        self.assertIn('["marca_modelo",period,r.tipo_registro', export)
        self.assertIn('"matriculacion_nueva":"Matriculación nueva"', export)

    def test_used_registration_is_not_exported_as_a_transfer(self):
        self.assertIn('"matriculacion_usada":"Matriculación de vehículo usado"', self.html)
        self.assertNotIn('"Usada · cambio de titularidad"', self.html)


if __name__ == "__main__":
    unittest.main()
