import hashlib
import json
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

import descubrir_marcas_matraba as d
from procesar_matraba_mensual import WIDTHS


def make_record(brand="HONDA", vehicle_type="50", operation="1", new_used="N",
                matriculation="15072026", process="31072026"):
    values = [""] * len(WIDTHS)
    values[0] = matriculation
    values[3] = brand
    values[7] = vehicle_type
    values[21] = operation
    values[25] = new_used
    values[68] = process
    return "".join(value.ljust(width)[:width] for value, width in zip(values, WIDTHS)).encode("cp1252")


def make_archive(directory, records, month="202607"):
    payload = BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mat.txt", b"H" * 79 + b"\n" + b"\n".join(records))
    raw = payload.getvalue()
    digest = hashlib.sha256(raw).hexdigest()
    path = Path(directory) / f"export_mensual_mat_{month}_{digest}.zip"
    path.write_bytes(raw)
    return path


class BrandDiscoveryTests(unittest.TestCase):
    def test_normalization_is_accent_and_punctuation_insensitive(self):
        self.assertEqual(d.normalize_brand("  MÓTO-ÉX, S.A. "), "moto ex s a")

    def test_extracts_new_motorcycle_and_moped_brands(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_archive(tmp, [
                make_record("HONDA", "50"),
                make_record("VÉLCA", "90"),
                make_record("HONDA", "51"),
            ])
            _, counts, _, _, invalid = d.extract_archive(path, "2026-07")
            self.assertEqual(counts[("2026-07", "50", "honda")], 1)
            self.assertEqual(counts[("2026-07", "51", "honda")], 1)
            self.assertEqual(counts[("2026-07", "90", "velca")], 1)
            self.assertEqual(invalid, 0)

    def test_excludes_used_transfers_and_out_of_scope_vehicle_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_archive(tmp, [
                make_record("HONDA", "50", operation="2", new_used="U"),
                make_record("CAR BRAND", "53"),
                make_record("QUAD BRAND", "92"),
            ])
            _, counts, _, excluded, _ = d.extract_archive(path, "2026-07")
            self.assertEqual(sum(counts.values()), 0)
            self.assertEqual(excluded["53"], 1)
            self.assertEqual(excluded["92"], 1)

    def test_future_or_invalid_dates_are_not_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_archive(tmp, [
                make_record("HONDA", matriculation="01082026", process="31072026"),
                make_record("YAMAHA", matriculation="31132026", process="31072026"),
            ])
            _, counts, _, _, invalid = d.extract_archive(path, "2026-07")
            self.assertEqual(sum(counts.values()), 0)
            self.assertEqual(invalid, 2)

    def test_exact_normalized_inventory_match_and_unmatched_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = make_archive(root, [make_record("HÓNDA"), make_record("MOTO-EX")])
            inventory = root / "inventory.json"
            inventory.write_text(json.dumps({"ejecuciones": [{
                "fecha_captura_utc": "2026-11-12T00:00:00Z",
                "capturas": [{"archivo": str(archive), "estado": "descargado_validado"}],
            }]}), encoding="utf-8")
            registry = root / "registry.json"
            registry.write_text(json.dumps({"brands": [
                {"brand_id": "brand-honda", "canonical_name": "Honda", "market_status": "established"}
            ]}), encoding="utf-8")
            summary = d.build_outputs(root, root / "out", inventory, registry)
            payload = json.loads((root / "out" / "marcas_candidatas_revision.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["marcas_observadas"], 2)
            self.assertEqual(summary["marcas_ya_en_inventario"], 1)
            self.assertEqual(summary["nuevas_candidatas_revision"], 1)
            self.assertEqual(payload["candidatas_nuevas"][0]["marca_normalizada"], "moto ex")

    def test_duplicate_records_are_counted_not_silently_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_archive(tmp, [make_record("HONDA"), make_record("HONDA")])
            _, counts, _, _, _ = d.extract_archive(path, "2026-07")
            self.assertEqual(counts[("2026-07", "50", "honda")], 2)


if __name__ == "__main__":
    unittest.main()
