import sqlite3
import unittest
from pathlib import Path

from validar_red_comercial import (
    initialize_database,
    validate_database,
    validate_interval,
)


class TestEsquemaRedComercial(unittest.TestCase):
    def setUp(self):
        self.db = initialize_database()

    def tearDown(self):
        self.db.close()

    def test_esquema_inicial_integro(self):
        self.assertEqual(validate_database(self.db), [])

    def test_permite_dos_importadores_sucesivos(self):
        self.db.executescript("""
            INSERT INTO brand VALUES ('b1','Marca X','ES','2024-01-01',NULL);
            INSERT INTO company VALUES ('c1','Importador anterior','ES','2024-01-01');
            INSERT INTO company VALUES ('c2','Importador nuevo','ES','2025-01-01');
            INSERT INTO brand_company_relation VALUES
              ('r1','b1','c1','importer','ES','2024-01-01','2025-01-01',
               'historical_confirmed','2024-01-01',NULL);
            INSERT INTO brand_company_relation VALUES
              ('r2','b1','c2','importer','ES','2025-01-01',NULL,
               'active_confirmed','2025-01-01','r1');
        """)
        count = self.db.execute(
            "SELECT COUNT(*) FROM brand_company_relation WHERE brand_id='b1'"
        ).fetchone()[0]
        self.assertEqual(count, 2)

    def test_no_permite_intervalo_invertido(self):
        self.db.executescript("""
            INSERT INTO brand VALUES ('b1','Marca X','ES','2024-01-01',NULL);
            INSERT INTO company VALUES ('c1','Empresa','ES','2024-01-01');
        """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("""
                INSERT INTO brand_company_relation
                (relation_id,brand_id,company_id,role,territory,valid_from,valid_to,
                 status,created_at)
                VALUES ('r1','b1','c1','importer','ES','2025-02-01','2025-01-01',
                        'historical_confirmed','2025-01-01')
            """)

    def test_observaciones_son_inmutables(self):
        self.db.executescript("""
            INSERT INTO source VALUES
              ('s1','Fabricante','official_directory','https://example.test',
               'Directorio','primary_official',NULL);
            INSERT INTO observation
              (observation_id,source_id,observed_at)
              VALUES ('o1','s1','2026-11-11T10:00:00+01:00');
        """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE observation SET notes='corregido' WHERE observation_id='o1'"
            )


    def test_evento_se_vincula_a_entidades_con_integridad(self):
        self.db.executescript("""
            INSERT INTO brand VALUES ('b1','Suzuki','ES','2024-01-01',NULL);
            INSERT INTO outlet VALUES
              ('o1','Motos Copa','Valladolid',NULL,'47',NULL,NULL,'2024-01-01');
            INSERT INTO change_event
              VALUES ('e1','dealer_removed','2025-09-30','2026-11-11T10:00:00+01:00',
                      'confirmed','Cierre del establecimiento');
            INSERT INTO change_event_brand
              VALUES ('e1','b1','marca relacionada');
            INSERT INTO change_event_outlet
              VALUES ('e1','o1','establecimiento afectado');
        """)
        self.assertEqual(
            self.db.execute(
                "SELECT COUNT(*) FROM change_event_outlet WHERE outlet_id='o1'"
            ).fetchone()[0],
            1,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO change_event_outlet VALUES ('e1','outlet-inexistente','afectado')"
            )

    def test_vocabulario_admite_eventos_de_entrada_y_cierre(self):
        allowed = {
            row[0] for row in self.db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='change_event'"
            )
        }
        self.assertEqual(len(allowed), 1)
        schema_sql = next(iter(allowed))
        for event_type in ("outlet_closed", "brand_entered_market",
                           "brand_distributor_appointed"):
            self.assertIn(event_type, schema_sql)

    def test_evento_admite_varias_entidades_afectadas(self):
        self.db.executescript("""
            INSERT INTO brand VALUES ('b1','Suzuki','ES','2024-01-01',NULL);
            INSERT INTO brand VALUES ('b2','Zontes','ES','2024-01-01',NULL);
            INSERT INTO change_event
              VALUES ('e1','brand_added_to_outlet',NULL,'2026-11-11T10:00:00+01:00',
                      'candidate','Evento de prueba');
            INSERT INTO change_event_brand VALUES ('e1','b1','marca anterior');
            INSERT INTO change_event_brand VALUES ('e1','b2','marca nueva');
        """)
        self.assertEqual(
            self.db.execute(
                "SELECT COUNT(*) FROM change_event_brand WHERE event_id='e1'"
            ).fetchone()[0],
            2,
        )

    def test_carga_piloto_documental_y_conserva_integridad(self):
        fixture = Path(__file__).resolve().parents[1] / "datos" / "piloto_red_comercial_2026-11-11.sql"
        self.db.executescript(fixture.read_text(encoding="utf-8"))
        self.assertEqual(validate_database(self.db), [])
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM change_event").fetchone()[0],
            5,
        )
        self.assertEqual(
            self.db.execute(
                "SELECT event_status FROM change_event WHERE event_id='event-motos-copa-suzuki-ended'"
            ).fetchone()[0],
            "candidate",
        )
        self.assertEqual(
            self.db.execute(
                "SELECT COUNT(*) FROM change_event_outlet WHERE event_id='event-zontes-madrid-added'"
            ).fetchone()[0],
            2,
        )

    def test_intervalos_iso(self):
        validate_interval("2024-01-01", "2025-01-01")
        with self.assertRaises(ValueError):
            validate_interval("2025-01-01", "2024-01-01")
        with self.assertRaises(ValueError):
            validate_interval("2025-01-01", "2025-01-01")


if __name__ == "__main__":
    unittest.main()
