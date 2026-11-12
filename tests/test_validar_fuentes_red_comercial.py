import json
import unittest

from validar_fuentes_red_comercial import REGISTRY_PATH, load_and_validate, validate_registry


class TestRegistroFuentesRedComercial(unittest.TestCase):
    def test_registro_oficial_inicial_valido(self):
        self.assertEqual(load_and_validate(), [])

    def test_fuente_no_puede_referir_marca_inexistente(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        data["sources"][0]["brand_id"] = "brand-inexistente"
        self.assertTrue(any("brand_id no registrado" in e for e in validate_registry(data)))

    def test_no_acepta_http_ni_url_sin_host(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        data["sources"][0]["url"] = "http://example.com/directorio"
        self.assertTrue(any("URL HTTPS no válida" in e for e in validate_registry(data)))

    def test_no_acepta_identificadores_duplicados(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        data["sources"].append(dict(data["sources"][0]))
        self.assertTrue(any("source_id ausente o duplicado" in e for e in validate_registry(data)))

    def test_no_permite_convertir_ausencia_en_cierre(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        data["policy"]["absence_is_not_closure"] = False
        self.assertTrue(any("ausencia no equivale a cierre" in e for e in validate_registry(data)))

    def test_no_permite_fuente_primaria_no_oficial(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        data["sources"][0]["reliability_class"] = "community"
        self.assertTrue(any("solo admite fuentes oficiales" in e for e in validate_registry(data)))


if __name__ == "__main__":
    unittest.main()
