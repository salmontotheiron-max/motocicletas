import json
import tempfile
import unittest
from pathlib import Path
import procesar_matraba as p
import descargar_matraba as d
from datetime import date
from io import BytesIO
import zipfile

class ProcessorSchemaTests(unittest.TestCase):
    def test_schema_is_69_fields_and_714_chars(self):
        self.assertEqual(len(p.WIDTHS), 69)
        self.assertEqual(sum(p.WIDTHS), 714)

    def test_target_type_codes_are_exact(self):
        self.assertEqual(p.TARGET_TYPE_CODES, frozenset({"50", "51", "52", "53", "54", "90", "91", "92"}))

    def test_type_filter_excludes_other_vehicle_categories(self):
        for code in p.TARGET_TYPE_CODES:
            self.assertTrue(p.is_target_type(code))
        for code in ("00", "01", "40", "60", "SH", ""):
            self.assertFalse(p.is_target_type(code))

    def test_type_codes_remain_individual(self):
        self.assertNotEqual(p.TYPES["50"], p.TYPES["51"])
        self.assertNotEqual(p.TYPES["90"], p.TYPES["91"])

    def test_operation_codes(self):
        self.assertEqual(set(p.OPS), set("123456789AB"))

    def test_dates(self):
        self.assertEqual(p.parse_date("01092026").isoformat(), "2026-09-01")
        self.assertIsNone(p.parse_date("32132026"))

class DownloadValidationTests(unittest.TestCase):
    def make_record(self, process="01102026"):
        fields = [""] * 69
        fields[68] = process
        return "".join(value.ljust(width)[:width] for value, width in zip(fields, p.WIDTHS)).encode("cp1252")

    def test_valid_record_and_header(self):
        header = b"Veh\xedculos matriculados. Letras de la serie de la \xfaltima matr\xedcula asignada: NTN\n"
        ok, error, count = d.validate_txt(header + self.make_record(), date(2026, 10, 1))
        self.assertTrue(ok)
        self.assertIsNone(error)
        self.assertEqual(count, 1)

    def test_invalid_record_width(self):
        ok, error, _ = d.validate_txt(b"x" * 713, date(2026, 10, 1))
        self.assertFalse(ok)
        self.assertIn("longitudes_registro_invalidas", error)

    def test_process_date_mismatch(self):
        ok, error, _ = d.validate_txt(self.make_record("02102026"), date(2026, 10, 1))
        self.assertFalse(ok)
        self.assertIn("fec_proceso_no_coincide", error)

    def test_corrupt_zip(self):
        data, error, count = d.inspect_zip(b"not a zip", date(2026, 10, 1))
        self.assertIsNone(data)
        self.assertEqual(error, "zip_corrupto")
        self.assertEqual(count, 0)

    def test_zip_without_txt_is_invalid(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("readme.txt.bak", "x")
        data, error, _ = d.inspect_zip(buffer.getvalue(), date(2026, 10, 1))
        self.assertIsNone(data)
        self.assertEqual(error, "numero_txt_inesperado:0")

    def test_daily_inventory_covers_inclusive_range(self):
        self.assertEqual(list(d.iter_days(date(2026, 9, 1), date(2026, 9, 3))),
                         [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3)])

if __name__ == "__main__":
    unittest.main()
