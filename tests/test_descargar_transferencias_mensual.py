import unittest
from io import BytesIO
import zipfile

from descargar_transferencias_mensual import inspect_transfer_zip, transfer_url
from descargar_matraba_mensual import WIDTH


def transfer_record(process_date="31102026"):
    row = bytearray(b" " * WIDTH)
    row[706:714] = process_date.encode("ascii")
    return bytes(row)


def zip_payload(txt):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("export_mensual_trf.txt", txt)
    return buffer.getvalue()


class TransferDownloaderTests(unittest.TestCase):
    def test_url_uses_official_monthly_export_pattern(self):
        self.assertEqual(
            transfer_url("2026-01"),
            "https://www.dgt.es/microdatos/salida/2026/1/vehiculos/transferencias/export_mensual_trf_202601.zip",
        )

    def test_first_record_is_data_not_header_and_is_counted(self):
        payload = zip_payload(transfer_record() + b"\n" + transfer_record("01112026"))
        data, error, count = inspect_transfer_zip(payload)
        self.assertIsNotNone(data)
        self.assertIsNone(error)
        self.assertEqual(count, 2)

    def test_rejects_wrong_record_width(self):
        _, error, count = inspect_transfer_zip(zip_payload(b"x" * 713))
        self.assertIn("longitudes_registro_invalidas", error)
        self.assertEqual(count, 1)

    def test_rejects_invalid_process_date(self):
        _, error, count = inspect_transfer_zip(zip_payload(transfer_record("32132026")))
        self.assertIn("fec_proceso_invalida_registro:1", error)
        self.assertEqual(count, 1)

    def test_rejects_corrupt_zip(self):
        _, error, count = inspect_transfer_zip(b"not a zip")
        self.assertEqual(error, "zip_corrupto")
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
