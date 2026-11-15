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


if __name__ == "__main__":
    unittest.main()
