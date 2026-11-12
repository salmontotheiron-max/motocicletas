import json
import unittest

from validar_fuentes_red_comercial import REGISTRY_PATH, load_and_validate, validate_registry


class TestRegistroFuentesRedComercial(unittest.TestCase):
    def test_registro_abierto_inicial_valido(self):
        self.assertEqual(load_and_validate(), [])

    def test_fuente_primaria_no_puede_referir_marca_inexistente(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        data["sources"][0]["brand_id"] = "brand-inexistente"
        self.assertTrue(any("marca registrada" in e for e in validate_registry(data)))

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

    def test_anuncio_no_equivale_a_operacion(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        data["policy"]["announcement_is_not_operation"] = False
        self.assertTrue(any("anuncio no debe equivaler" in e for e in validate_registry(data)))

    def test_descubrimiento_admite_marca_desconocida(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        source = dict(data["sources"][0])
        source.update({
            "source_id": "source-market-discovery-example",
            "source_role": "market_discovery",
            "brand_id": None,
            "reliability_class": "secondary_reputable",
            "source_type": "press",
        })
        data["sources"].append(source)
        self.assertEqual(validate_registry(data), [])

    def test_fuente_de_descubrimiento_no_exige_marca(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        source = dict(data["sources"][0])
        source.update({
            "source_id": "source-market-discovery-example",
            "source_role": "market_discovery",
            "brand_id": None,
            "reliability_class": "secondary_reputable",
            "source_type": "press",
        })
        data["sources"].append(source)
        source["brand_id"] = "brand-suzuki"
        self.assertTrue(any("no debe exigir marca" in e for e in validate_registry(data)))

    def test_no_acepta_marca_con_fabricante_desconocido_no_registrado(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        data["brands"][0]["manufacturer_id"] = "manufacturer-missing"
        self.assertTrue(any("manufacturer_id no registrado" in e for e in validate_registry(data)))


if __name__ == "__main__":
    unittest.main()
