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

    def test_period_and_province_filters_are_multivalued(self):
        self.assertIn('id="period" multiple', self.html)
        self.assertIn('id="province" multiple', self.html)
        self.assertIn("function periodOK(row,f)", self.html)
        self.assertIn("function provinceOK(row,f", self.html)

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
        self.assertIn('const source=f.province.length?state.provincial:state.monthly;', chart)
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
        self.assertIn('provinceOK(r,f)', export)
        self.assertIn('"nivel_agregacion","periodo","tipo_registro"', export)
        self.assertIn('"marca","modelo","recuento"', export)
        self.assertIn('["marca_modelo",period,r.tipo_registro', export)
        self.assertIn('"matriculacion_nueva":"Matriculación nueva"', export)

    def test_brand_selectors_use_active_volume_order_and_partial_universe_totals(self):
        self.assertIn("function activeModelRows(operation,segment,f)", self.html)
        self.assertIn("function rankedBrands(rows)", self.html)
        self.assertIn("unidades del universo filtrado", self.html)
        self.assertIn("SUMA DE UNIDADES · RESULTADO ACTUAL", self.html)

    def test_dashboard_filter_accessor_does_not_collide_with_selected_locals(self):
        self.assertIn("function getDashboardFilters()", self.html)
        self.assertNotIn("function selected()", self.html)
        self.assertNotIn("selected()", self.html)

    def test_brand_search_and_multiselect_remain_mutually_exclusive(self):
        self.assertIn("function syncBrandControls()", self.html)
        self.assertIn('el("brandMulti").disabled=hasSearch', self.html)
        self.assertIn('el("brandSearch").disabled=hasSelection', self.html)

    def test_map_loader_is_async_and_has_fallback_sources(self):
        self.assertIn("async function loadProvinceMap()", self.html)
        self.assertIn("https://unpkg.com/d3@7/dist/d3.min.js", self.html)
        self.assertIn("https://unpkg.com/es-atlas@0.6.0/es/provinces.json", self.html)

    def test_used_registration_is_not_exported_as_a_transfer(self):
        self.assertIn('"matriculacion_usada":"Matriculación de vehículo usado"', self.html)
        self.assertNotIn('"Usada · cambio de titularidad"', self.html)


if __name__ == "__main__":
    unittest.main()
