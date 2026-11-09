import unittest
from datetime import date
from io import BytesIO
import zipfile

import descargar_matraba_mensual as d


def record(process_date="01072026"):
    row = bytearray(b" " * d.WIDTH)
    row[706:714] = process_date.encode("ascii")
    return bytes(row)


def zip_payload(txt):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("export_mensual.txt", txt)
    return buffer.getvalue()


class MonthlyDownloaderTests(unittest.TestCase):
    def test_month_url_uses_unpadded_route_month(self):
        self.assertIn("/2026/7/", d.monthly_url("2026-07"))
        self.assertTrue(d.monthly_url("2026-07").endswith("export_mensual_mat_202607.zip"))

    def test_month_pair_crosses_year_boundary(self):
        self.assertEqual(d.month_pair(date(2027, 1, 4)), ["2026-12", "2027-01"])

    def test_validate_month_accepts_compact_and_hyphenated_formats(self):
        self.assertEqual(d.validate_month("202609"), "2026-09")
        self.assertEqual(d.validate_month("2026-09"), "2026-09")

    def test_monthly_header_and_records(self):
        payload = zip_payload(b"H" * 79 + b"\n" + record() + b"\n")
        data, error, count = d.inspect_zip(payload)
        self.assertIsNotNone(data)
        self.assertIsNone(error)
        self.assertEqual(count, 1)

    def test_process_date_is_valid_but_need_not_match_month_end_or_capture_date(self):
        payload = zip_payload(b"H" * 79 + b"\n" + record("31102026"))
        _, error, count = d.inspect_zip(payload)
        self.assertIsNone(error)
        self.assertEqual(count, 1)

    def test_invalid_record_width(self):
        payload = zip_payload(b"H" * 79 + b"\n" + b"x" * 713)
        _, error, _ = d.inspect_zip(payload)
        self.assertIn("longitudes_registro_invalidas", error)

    def test_invalid_process_date(self):
        payload = zip_payload(b"H" * 79 + b"\n" + record("32132026"))
        _, error, _ = d.inspect_zip(payload)
        self.assertIn("fec_proceso_invalida", error)

    def test_zip_without_txt(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("readme.md", "not a data file")
        _, error, count = d.inspect_zip(buffer.getvalue())
        self.assertEqual(error, "numero_txt_inesperado:0")
        self.assertEqual(count, 0)

    def test_corrupt_zip(self):
        _, error, count = d.inspect_zip(b"not a zip")
        self.assertEqual(error, "zip_corrupto")
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
