import unittest
import procesar_matraba as p

class ProcessorSchemaTests(unittest.TestCase):
    def test_schema_is_69_fields_and_714_chars(self):
        self.assertEqual(len(p.WIDTHS), 69)
        self.assertEqual(sum(p.WIDTHS), 714)

    def test_type_codes_are_individual(self):
        self.assertIn("50", p.TYPES)
        self.assertIn("51", p.TYPES)
        self.assertIn("90", p.TYPES)
        self.assertNotEqual(p.TYPES["50"], p.TYPES["51"])

    def test_operation_codes(self):
        self.assertEqual(set(p.OPS), set("123456789AB"))

    def test_dates(self):
        self.assertEqual(p.parse_date("01092026").isoformat(), "2026-09-01")
        self.assertIsNone(p.parse_date("32132026"))

if __name__ == "__main__":
    unittest.main()
