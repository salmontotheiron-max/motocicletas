import unittest
import procesar_matraba as p

class ProcessorSchemaTests(unittest.TestCase):
    def test_schema_is_69_fields_and_714_chars(self):
        self.assertEqual(len(p.WIDTHS), 69)
        self.assertEqual(sum(p.WIDTHS), 714)

    def test_target_type_codes_are_exact(self):
        self.assertEqual(
            p.TARGET_TYPE_CODES,
            frozenset({"50", "51", "52", "53", "54", "90", "91", "92"})
        )

    def test_type_filter_excludes_other_vehicle_categories(self):
        for code in p.TARGET_TYPE_CODES:
            with self.subTest(code=code):
                self.assertTrue(p.is_target_type(code))
        for code in ("00", "01", "40", "60", "SH", ""):
            with self.subTest(code=code):
                self.assertFalse(p.is_target_type(code))

    def test_type_codes_remain_individual(self):
        self.assertNotEqual(p.TYPES["50"], p.TYPES["51"])
        self.assertNotEqual(p.TYPES["90"], p.TYPES["91"])

    def test_operation_codes(self):
        self.assertEqual(set(p.OPS), set("123456789AB"))

    def test_dates(self):
        self.assertEqual(p.parse_date("01092026").isoformat(), "2026-09-01")
        self.assertIsNone(p.parse_date("32132026"))

if __name__ == "__main__":
    unittest.main()
