import unittest
from io import BytesIO
import zipfile

import descargar_transferencias_mensual as d
from descargar_matraba_mensual import WIDTH


def record(process_date="01072026"):
    row = bytearray(b" " * WIDTH)
    row[706:714] = process_date.encode("ascii")
    return bytes(row)


def zip_payload(txt):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("export_mensual.txt", txt)
    return buffer.getvalue()


class TransferDownloaderValidationTests(unittest.TestCase):
    def test_transfer_file_has_no_header_and_first_row_is_counted(self):
        payload = zip_payload(record() + b"\n" + record("02072026"))
        data, error, count = d.inspect_transfer_zip(payload)
        self.assertIsNotNone(data)
        self.assertIsNone(error)
        self.assertEqual(count, 2)

    def test_rejects_invalid_record_width(self):
        _, error, count = d.inspect_transfer_zip(zip_payload(b"x" * (WIDTH - 1)))
        self.assertIn("longitudes_registro_invalidas", error)
        self.assertEqual(count, 1)

    def test_rejects_invalid_process_date(self):
        _, error, _ = d.inspect_transfer_zip(zip_payload(record("32132026")))
        self.assertIn("fec_proceso_invalida", error)

    def test_rejects_zip_without_txt(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("readme.md", "not data")
        _, error, count = d.inspect_transfer_zip(buffer.getvalue())
        self.assertEqual(error, "numero_txt_inesperado:0")
        self.assertEqual(count, 0)

    def test_rejects_corrupt_zip(self):
        _, error, count = d.inspect_transfer_zip(b"not a zip")
        self.assertEqual(error, "zip_corrupto")
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
