import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from io import BytesIO
import zipfile

import procesar_matraba_mensual as p
import descargar_matraba_mensual as d
import descargar_transferencias_mensual as dt


def make_record(**fields):
    values = [""] * 69
    indexes = {"FEC_MATRICULA": 0, "FEC_TRAMITACION": 22, "MARCA_ITV": 3, "MODELO_ITV": 4, "COD_TIPO": 7,
               "CLAVE_TRAMITE": 21, "NUEVO_USADO": 25, "COD_POSESION": 36, "COD_PROVINCIA_VEH": 19, "COD_PROVINCIA_MAT": 20, "FEC_PROCESO": 68}
    for name, value in fields.items():
        values[indexes[name]] = value
    return "".join(value.ljust(width)[:width] for value, width in zip(values, p.WIDTHS)).encode("cp1252")


def make_zip(record):
    data = BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mat.txt", b"H" * 79 + b"\n" + record)
    return data.getvalue()


class MonthlyProcessorTests(unittest.TestCase):
    def test_transfer_snapshot_filename_is_recognized(self):
        from pathlib import Path
        self.assertEqual(
            p.transfer_period_from_name(Path("export_mensual_trf_202609_" + "a" * 64 + ".zip")),
            "2026-09",
        )

    def test_transfer_url_uses_the_official_monthly_export_pattern(self):
        self.assertEqual(
            dt.transfer_url("2026-09"),
            "https://www.dgt.es/microdatos/salida/2026/9/vehiculos/transferencias/export_mensual_trf_202609.zip",
        )

    def test_transfer_backfill_starts_in_january_2026(self):
        from datetime import date
        months = dt.initial_months(today=date(2026, 3, 13))
        self.assertEqual(months, ["2026-01", "2026-02", "2026-03"])

    def test_selects_latest_capture_for_each_month(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            older = root / ("export_mensual_mat_202607_" + "a" * 64 + ".zip")
            newer = root / ("export_mensual_mat_202607_" + "b" * 64 + ".zip")
            older.write_bytes(b"x")
            newer.write_bytes(b"x")
            inventory = root / "inventory.json"
            inventory.write_text(json.dumps({"ejecuciones": [
                {"fecha_captura_utc": "2026-11-01T00:00:00Z", "capturas": [
                    {"archivo": str(older), "estado": "descargado_validado"}]},
                {"fecha_captura_utc": "2026-11-08T00:00:00Z", "capturas": [
                    {"archivo": str(newer), "estado": "descargado_validado"}]},
            ]}), encoding="utf-8")
            selected = p.select_latest_archives(root, inventory)
            self.assertEqual(selected["2026-07"].name, newer.name)

    def test_processes_monthly_zip_without_matching_process_month(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = make_record(FEC_MATRICULA="15072026", FEC_TRAMITACION="15072026",
                              COD_TIPO="50", CLAVE_TRAMITE="1",
                              NUEVO_USADO="N", FEC_PROCESO="31102026")
            payload = make_zip(row)
            archive = Path(tmp) / ("export_mensual_mat_202607_" + hashlib.sha256(payload).hexdigest() + ".zip")
            archive.write_bytes(payload)
            info, counts, provincial, cross, models, ops, excluded, audit = p.process_archive(archive, "2026-07")
            self.assertEqual(info["registros"], 1)
            self.assertEqual(sum(counts.values()), 1)
            self.assertEqual(sum(ops.values()), 1)
            self.assertEqual(sum(excluded.values()), 0)


    def test_uses_certified_fec_tramite_field_for_used_vehicles(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = make_record(FEC_MATRICULA="15082026", FEC_TRAMITACION="15082026",
                              COD_TIPO="50", CLAVE_TRAMITE="1",
                              NUEVO_USADO="U", FEC_PROCESO="01092026")
            payload = make_zip(row)
            archive = Path(tmp) / ("export_mensual_mat_202609_" + hashlib.sha256(payload).hexdigest() + ".zip")
            archive.write_bytes(payload)
            _, counts, _, _, _, _, _, audit = p.process_archive(archive, "2026-09")
            self.assertEqual(counts[("2026-08", "50", "U", False)], 1)

    def test_future_matriculation_date_uses_process_month_and_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = make_record(FEC_MATRICULA="08102026", FEC_TRAMITACION="01092026",
                              COD_TIPO="53", CLAVE_TRAMITE="1",
                              NUEVO_USADO="N", FEC_PROCESO="01092026")
            payload = make_zip(row)
            archive = Path(tmp) / ("export_mensual_mat_202609_" + hashlib.sha256(payload).hexdigest() + ".zip")
            archive.write_bytes(payload)
            _, counts, _, _, _, _, _, audit = p.process_archive(archive, "2026-09")
            self.assertEqual(sum(counts.values()), 0)
            self.assertNotIn(("2026-10", "53", "N", False), counts)
            self.assertEqual(len(audit), 1)
            self.assertEqual(audit[0][2], "FEC_MATRICULA_POSTERIOR_A_FEC_PROCESO")

    def test_future_transaction_date_excludes_used_vehicle_and_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = make_record(FEC_MATRICULA="15082026", FEC_TRAMITACION="10092026",
                              COD_TIPO="50", CLAVE_TRAMITE="1",
                              NUEVO_USADO="U", FEC_PROCESO="01092026")
            payload = make_zip(row)
            archive = Path(tmp) / ("export_mensual_mat_202609_" + hashlib.sha256(payload).hexdigest() + ".zip")
            archive.write_bytes(payload)
            _, counts, _, _, _, ops, _, audit = p.process_archive(archive, "2026-09")
            self.assertEqual(sum(counts.values()), 0)
            self.assertEqual(sum(ops.values()), 0)
            self.assertEqual(audit[0][2], "FEC_TRAMITE_POSTERIOR_A_FEC_PROCESO")

    def test_future_transaction_date_excludes_operation_even_for_new_vehicle(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = make_record(FEC_MATRICULA="15082026", FEC_TRAMITACION="10092026",
                              COD_TIPO="50", CLAVE_TRAMITE="1",
                              NUEVO_USADO="N", FEC_PROCESO="01092026")
            payload = make_zip(row)
            archive = Path(tmp) / ("export_mensual_mat_202609_" + hashlib.sha256(payload).hexdigest() + ".zip")
            archive.write_bytes(payload)
            _, counts, _, _, _, ops, _, audit = p.process_archive(archive, "2026-09")
            self.assertEqual(sum(counts.values()), 0)
            self.assertEqual(sum(ops.values()), 0)
            self.assertEqual(len(audit), 1)
            self.assertEqual(audit[0][2], "FEC_TRAMITE_POSTERIOR_A_FEC_PROCESO")

    def test_used_vehicle_without_valid_transaction_date_is_excluded(self):
        for transaction_date in ("", "31132026"):
            with self.subTest(transaction_date=transaction_date):
                with tempfile.TemporaryDirectory() as tmp:
                    row = make_record(FEC_MATRICULA="15082026", FEC_TRAMITACION=transaction_date,
                                      COD_TIPO="50", CLAVE_TRAMITE="1",
                                      NUEVO_USADO="U", FEC_PROCESO="01092026")
                    payload = make_zip(row)
                    archive = Path(tmp) / ("export_mensual_mat_202609_" + hashlib.sha256(payload).hexdigest() + ".zip")
                    archive.write_bytes(payload)
                    _, counts, _, _, _, ops, _, audit = p.process_archive(archive, "2026-09")
                    self.assertEqual(sum(counts.values()), 0)
                    self.assertEqual(sum(ops.values()), 0)
                    self.assertEqual(len(audit), 1)
                    self.assertEqual(audit[0][2], "FECHA_REFERENCIA_NO_DISPONIBLE")

    def test_provincial_scope_uses_registration_for_new_and_vehicle_domicile_for_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            new_row = make_record(
                FEC_MATRICULA="15072026", FEC_TRAMITACION="15072026",
                COD_TIPO="50", CLAVE_TRAMITE="1", NUEVO_USADO="N",
                COD_PROVINCIA_VEH="MU", COD_PROVINCIA_MAT="A",
                FEC_PROCESO="31072026",
            )
            used_row = make_record(
                FEC_MATRICULA="15072026", FEC_TRAMITACION="15082026",
                COD_TIPO="50", CLAVE_TRAMITE="1", NUEVO_USADO="U",
                COD_POSESION="V", COD_PROVINCIA_VEH="MU", COD_PROVINCIA_MAT="A",
                FEC_PROCESO="31082026",
            )
            payload = make_zip(new_row + b"\n" + used_row)
            archive = Path(tmp) / ("export_mensual_mat_202608_" + hashlib.sha256(payload).hexdigest() + ".zip")
            archive.write_bytes(payload)
            _, _, provincial, cross, _, _, _, _ = p.process_archive(archive, "2026-08")
            self.assertEqual(provincial[("2026-07", "matriculacion", "A", "50", "N")], 1)
            self.assertEqual(provincial[("2026-08", "domicilio_vehiculo", "MU", "50", "U")], 1)
            self.assertEqual(cross[("2026-07", "A", "MU", "50")], 1)
            self.assertEqual(sum(cross.values()), 1)

    def test_extracts_brand_model_segment_and_province_without_vehicle_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = make_record(
                FEC_MATRICULA="15072026", FEC_TRAMITACION="15072026",
                MARCA_ITV="HONDA", MODELO_ITV="CB 500 X",
                COD_TIPO="50", CLAVE_TRAMITE="1", NUEVO_USADO="N",
                COD_PROVINCIA_VEH="MU", COD_PROVINCIA_MAT="A",
                FEC_PROCESO="31072026",
            )
            payload = make_zip(row)
            archive = Path(tmp) / ("export_mensual_mat_202607_" + hashlib.sha256(payload).hexdigest() + ".zip")
            archive.write_bytes(payload)
            _, _, _, _, models, _, _, _ = p.process_archive(archive, "2026-07")
            key = ("2026-07", "HONDA", "CB 500 X", "50", "N",
                   "matriculacion_nueva", "matriculacion", "A")
            self.assertEqual(models[key], 1)

    def test_transfer_model_uses_vehicle_domicile_not_a_sale_province(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = make_record(
                FEC_MATRICULA="15072020", FEC_TRAMITACION="15082026",
                MARCA_ITV="YAMAHA", MODELO_ITV="MT-07",
                COD_TIPO="50", CLAVE_TRAMITE="2", NUEVO_USADO="U",
                COD_PROVINCIA_VEH="MU", COD_PROVINCIA_MAT="A",
                FEC_PROCESO="31082026",
            )
            payload = make_zip(row)
            archive = Path(tmp) / ("export_mensual_mat_202608_" + hashlib.sha256(payload).hexdigest() + ".zip")
            archive.write_bytes(payload)
            _, _, _, _, models, _, _, _ = p.process_archive(archive, "2026-08", include_transfers=True)
            key = ("2026-08", "YAMAHA", "MT-07", "50", "U",
                   "venta", "domicilio_vehiculo", "MU")
            self.assertEqual(models[key], 1)

    def test_duplicate_rows_are_not_silently_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = make_record(FEC_MATRICULA="15072026", FEC_TRAMITACION="15072026",
                              COD_TIPO="50", CLAVE_TRAMITE="1",
                              NUEVO_USADO="N", FEC_PROCESO="31072026")
            payload = make_zip(row + b"\n" + row)
            archive = Path(tmp) / ("export_mensual_mat_202607_" + hashlib.sha256(payload).hexdigest() + ".zip")
            archive.write_bytes(payload)
            _, counts, _, _, _, _, _, audit = p.process_archive(archive, "2026-07")
            self.assertEqual(sum(counts.values()), 2)


if __name__ == "__main__":
    unittest.main()
