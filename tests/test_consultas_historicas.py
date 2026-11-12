"""Pruebas de ejecución y semántica de las consultas históricas SQL."""

import sqlite3
import unittest
from pathlib import Path

from validar_red_comercial import initialize_database, validate_database

ROOT = Path(__file__).resolve().parents[1]
QUERY_FILE = ROOT / "consultas_historicas_red_comercial.sql"
PILOT_FILE = ROOT / "datos" / "piloto_red_comercial_2026-11-11.sql"


def load_selects(connection):
    """Extrae y ejecuta como sentencias separadas los SELECT del fichero SQL."""
    statements = []
    buffer = ""
    for line in QUERY_FILE.read_text(encoding="utf-8").splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            if "SELECT" in buffer.upper():
                statements.append(buffer)
            buffer = ""
    if buffer.strip():
        raise AssertionError("Quedó una sentencia SQL incompleta")
    params = {
        "outlet_id": "outlet-zontes-centro-madrid",
        "brand_id": "brand-zxmoto-es",
        "as_of_date": "2026-07-01",
        "date_from": "2026-01-01",
        "date_to": "2027-01-01",
        "event_id": "event-zxmoto-distributor",
    }
    results = []
    for statement in statements:
        results.append(connection.execute(statement, params).fetchall())
    return results


class TestConsultasHistoricas(unittest.TestCase):
    def setUp(self):
        self.db = initialize_database()
        self.db.executescript(PILOT_FILE.read_text(encoding="utf-8"))

    def tearDown(self):
        self.db.close()

    def test_todas_las_consultas_se_ejecutan_con_el_piloto(self):
        results = load_selects(self.db)
        self.assertEqual(len(results), 8)

    def test_no_infiere_vigencia_si_falta_un_extremo(self):
        results = load_selects(self.db)
        # Consulta 2: Zontes tiene inicio conocido, pero no fecha fin; no se
        # presenta como relación demostrada en la fecha consultada.
        self.assertEqual(results[1], [])
        # Consulta 7: la misma relación aparece como temporalmente indeterminada.
        self.assertEqual(len(results[6]), 1)
        self.assertEqual(results[6][0][6], "fin_desconocido")

    def test_no_infiere_distribuidor_vigente_con_fechas_desconocidas(self):
        results = load_selects(self.db)
        # Consulta 3 no atribuye a Desmotrón vigencia en una fecha arbitraria.
        self.assertEqual(results[2], [])
        # Consulta 8 conserva el vínculo anunciado, pero marca ambos extremos.
        self.assertEqual(len(results[7]), 1)
        self.assertEqual(results[7][0][7], "ambos_extremos_desconocidos")

    def test_devuelve_relaciones_confirmadas_con_intervalo_acotado(self):
        self.db.executescript("""
            INSERT INTO brand VALUES
              ('brand-honda-test','Honda','ES','2026-01-01',NULL);
            INSERT INTO outlet_brand_relation
              (relation_id,outlet_id,brand_id,activity,valid_from,valid_to,status,created_at)
            VALUES
              ('rel-honda-test','outlet-zontes-centro-madrid','brand-honda-test',
               'new_sales','2026-01-01','2027-01-01','historical_confirmed','2026-01-01');
            INSERT INTO company
              (company_id,legal_name,country,created_at)
            VALUES ('company-zxmoto-test','Distribuidor de prueba','ES','2026-01-01');
            INSERT INTO brand_company_relation
              (relation_id,brand_id,company_id,role,territory,valid_from,valid_to,status,created_at)
            VALUES ('rel-zxmoto-test','brand-zxmoto-es','company-zxmoto-test',
                    'national_distributor','ES','2026-01-01','2027-01-01',
                    'historical_confirmed','2026-01-01');
        """)
        results = load_selects(self.db)
        self.assertEqual([row[1] for row in results[1]], ["Honda"])
        self.assertEqual([row[1] for row in results[2]], ["Distribuidor de prueba"])

    def test_piloto_y_consultas_no_rompen_integridad(self):
        self.assertEqual(validate_database(self.db), [])


if __name__ == "__main__":
    unittest.main()
