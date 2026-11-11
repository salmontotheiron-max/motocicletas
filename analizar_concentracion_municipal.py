#!/usr/bin/env python3
"""Cruza domicilios municipales MATRABA con población INE y parque DGT.

El municipio de MATRABA es el del domicilio registral. No representa necesariamente
residencia, punto de venta, entrega ni lugar de uso del vehículo.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


PERIOD = "2026-01/09"
SUPPRESSED = "SUPRIMIDO (<20)"

# Equivalencias editoriales exactas: categoría MATRABA -> nombre municipal DGT.
# Solo se incluyen equivalencias comprobadas contra el nomenclátor DGT 2025.
ALIASES = {
    "ALICANTE": "Alacant/Alicante",
    "LAS PALMAS G C": "Palmas de Gran Canaria, Las",
    "JEREZ DE LA FTRA": "Jerez de la Frontera",
    "L HOSPITALET DE LLOB": "Hospitalet de Llobregat, L'",
    "S C TENERIFE": "Santa Cruz de Tenerife",
    "ELCHE": "Elx/Elche",
    "DONOSTIA": "Donostia/San Sebastián",
    "LA LAGUNA": "San Cristóbal de La Laguna",
    "CHICLANA DE LA FTRA": "Chiclana de la Frontera",
    "CASTELLO PLANA": "Castelló de la Plana",
    "SANLUCAR BARRAMEDA": "Sanlúcar de Barrameda",
    "A CORUÑA": "Coruña, A",
    "EL PUERTO STA MARIA": "Puerto de Santa María, El",
    "S COLOMA GRAMENET": "Santa Coloma de Gramenet",
    "S BOI DE LLOB": "Sant Boi de Llobregat",
    "S CUGAT DEL VALLES": "Sant Cugat del Vallès",
    "LA LINEA CONCEPCION": "Línea de la Concepción, La",
    "CORNELLA DE LLOB": "Cornellà de Llobregat",
    "SAN SEBASTIAN REYES": "San Sebastián de los Reyes",
    "EL PRAT DE LLOBREGAT": "Prat de Llobregat, El",
    "RINCON DE VICTORIA": "Rincón de la Victoria",
    "LAS ROZAS DE MADRID": "Rozas de Madrid, Las",
    "STA EULALIA DEL RIO": "Santa Eulària des Riu",
    "S BARTOLOME TIRAJANA": "San Bartolomé de Tirajana",
    "S FELIU DE LLOB": "Sant Feliu de Llobregat",
    "CALPE": "Calp",
    "S JOAN DESPI": "Sant Joan Despí",
    "S PERE DE RIBES": "Sant Pere de Ribes",
    "LA OROTAVA": "Orotava, La",
    "ESPLUGUES DE LLOB": "Esplugues de Llobregat",
    "CIUTADELLA MENORCA": "Ciutadella de Menorca",
    "PUERTO CRUZ": "Puerto de la Cruz",
    "S ADRIA DE BESOS": "Sant Adrià de Besòs",
    "CONIL DE LA FTRA": "Conil de la Frontera",
    "SAN FERNANDO HENARES": "San Fernando de Henares",
    "ARCOS DE LA FTRA": "Arcos de la Frontera",
    "EL EJIDO": "Ejido, El",
    "EL VENDRELL": "Vendrell, El",
    "S PERPETUA DE MOGODA": "Santa Perpètua de Mogoda",
    "VILLAJOYOSA": "Vila Joiosa, la/Villajoyosa",
    "JAVEA": "Xàbia/Jávea",
    "SANTA LUCIA": "Santa Lucía de Tirajana",
    "LOS REALEJOS": "Realejos, Los",
    "LOS BARRIOS": "Barrios, Los",
    "PAMPLONA": "Pamplona/Iruña",
    "SAN VICENTE RASPEIG": "Sant Vicent del Raspeig/San Vicente del Raspeig",
    "CERDANYOLA VALLES": "Cerdanyola del Vallès",
    "GRANADILLA": "Granadilla de Abona",
    "SAGUNTO": "Sagunt/Sagunto",
    "RENTERIA": "Errenteria",
    "S JUST DESVERN": "Sant Just Desvern",
    "LAS GABIAS": "Gabias, Las",
    "EL MASNOU": "Masnou, El",
    "LA NUCIA": "Nucia, la",
    "ALCOY": "Alcoi/Alcoy",
    "S VICENC DELS HORTS": "Sant Vicenç dels Horts",
    "LA HIRUELA": "Hiruela, La",
    "ALFAZ DEL PI": "Alfàs del Pi, l'",
    "ALBORAYA": "Alboraia/Alboraya",
    "LA ZUBIA": "Zubia, La",
    "CAMPELLO": "Campello, el",
    "VILASECA": "Vila-seca",
    "LA RINCONADA": "Rinconada, La",
    "S ANDREU DE BARCA": "Sant Andreu de la Barca",
    "BURRIANA": "Borriana/Burriana",
    "BENICASIM": "Benicàssim/Benicasim",
    "S C LA PALMA": "Santa Cruz de la Palma",
    "ICOD": "Icod de los Vinos",
    "CORBERA DE LLOB": "Corbera de Llobregat",
    "LA POBLA DE VALLBONA": "Pobla de Vallbona, la",
    "LOS LLANOS A": "Llanos de Aridane, Los",
    "VILAFRANCA PENEDES": "Vilafranca del Penedès",
    "S QUIRZE DEL VALLES": "Sant Quirze del Vallès",
    "CASTELL PLATJA D ARO": "Castell d'Aro, Platja d'Aro i s'Agaró",
    "S ANDREU LLAVANERES": "Sant Andreu de Llavaneres",
    "VALL DE UXO": "Vall d'Uixó, la",
    "L ESCALA": "Escala, L'",
    "EL ROSARIO": "Rosario, El",
    "EL ASTILLERO": "Astillero, El",
    "S MARIA DE GUIA G C": "Santa María de Guía de Gran Canaria",
    "SAN ANDRES RABANEDO": "San Andrés del Rabanedo",
    "PARACUELLOS JARAMA": "Paracuellos de Jarama",
    "ALMAZORA": "Almassora",
}


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).upper()
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", text).split())


def parse_integer(value: object) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    digits = re.sub(r"[^0-9]", "", str(value))
    return int(digits) if digits else None


def read_ine(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            if row.get("Sexo") != "Total" or row.get("Periodo") != "2025":
                continue
            match = re.match(r"^(\d{5})\s", row.get("Municipios", ""))
            population = parse_integer(row.get("Total"))
            if match and population is not None:
                code = match.group(1)
                if code in result:
                    raise ValueError(f"Código INE duplicado: {code}")
                result[code] = population
    return result


def read_dgt(path: Path) -> dict[str, dict[str, object]]:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook["DatosMunicipalesGeneral_2025"]
        rows = sheet.iter_rows(values_only=True)
        headers = next(rows)
        indexes = {name: headers.index(name) for name in (
            "Código INE", "Municipio", "Provincia", "Parque Motocicletas"
        )}
        result = {}
        normalized_names: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            code = str(row[indexes["Código INE"]] or "").strip().zfill(5)
            if not re.fullmatch(r"\d{5}", code) or code.endswith("000"):
                continue
            if code in result:
                raise ValueError(f"Código INE DGT duplicado: {code}")
            name = str(row[indexes["Municipio"]] or "").strip()
            park_value = row[indexes["Parque Motocicletas"]]
            try:
                park = int(float(park_value)) if park_value is not None else None
            except (TypeError, ValueError):
                park = None
            result[code] = {
                "municipio": name,
                "provincia": str(row[indexes["Provincia"]] or "").strip(),
                "parque": park,
            }
            normalized_names[normalize(name)].append(code)
        # Solo coincidencias exactas con nombre único en el nomenclátor.
        name_to_code = {
            name: codes[0] for name, codes in normalized_names.items() if len(codes) == 1
        }
        for source_name, target_name in ALIASES.items():
            target = normalize(target_name)
            candidates = normalized_names.get(target, [])
            if len(candidates) != 1:
                raise ValueError(f"Alias no unívoco o inexistente: {source_name} -> {target_name}")
            name_to_code[normalize(source_name)] = candidates[0]
        return {"municipalities": result, "name_to_code": name_to_code}
    finally:
        workbook.close()


def read_matraba(path: Path, name_to_code: dict[str, str]) -> tuple[Counter, Counter, Counter, dict]:
    matched: Counter = Counter()
    unmatched: Counter = Counter()
    suppressed: Counter = Counter()
    provincial_totals: Counter = Counter()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("periodo") != PERIOD or row.get("dimension") != "municipio":
                continue
            province_code = row.get("COD_PROVINCIA_MAT", "")
            if province_code == "NACIONAL":
                continue
            count = parse_integer(row.get("recuento"))
            if count is None:
                continue
            category = row.get("categoria", "").strip()
            provincial_totals[province_code] += count
            if category == SUPPRESSED or category.startswith("SUPRIMIDO"):
                suppressed[province_code] += count
                continue
            code = name_to_code.get(normalize(category))
            if code:
                matched[code] += count
            else:
                unmatched[category] += count
    return matched, unmatched, suppressed, dict(provincial_totals)


def build(args: argparse.Namespace) -> dict:
    ine = read_ine(args.ine)
    dgt = read_dgt(args.dgt)
    matched, unmatched, suppressed, provincial_totals = read_matraba(args.matraba, dgt["name_to_code"])
    rows = []
    for code, item in sorted(dgt["municipalities"].items()):
        population = ine.get(code)
        park = item["parque"]
        units = matched.get(code, 0)
        if population is None:
            raise ValueError(f"Sin población INE 2025 para código DGT {code}")
        rate_population = units * 1000 / population if population > 0 else None
        rate_park = units * 1000 / park if park is not None and park > 0 else None
        rows.append({
            "codigo_ine": code,
            "municipio": item["municipio"],
            "provincia": item["provincia"],
            "matriculaciones_domicilio_registral_visibles": units,
            "poblacion_ine_2025": population,
            "parque_motocicletas_dgt_2025": park,
            "matriculaciones_por_1000_habitantes": rate_population,
            "matriculaciones_por_1000_motos_parque": rate_park,
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    total = sum(provincial_totals.values())
    matched_total = sum(matched.values())
    suppressed_total = sum(suppressed.values())
    unmatched_total = sum(unmatched.values())
    summary = {
        "periodo_matraba": PERIOD,
        "total_provincial_municipal": total,
        "domicilios_visibles_asignados": matched_total,
        "domicilios_suprimidos": suppressed_total,
        "domicilios_visibles_no_asignados": unmatched_total,
        "cobertura_sobre_visibles_pct": round(100 * matched_total / (total - suppressed_total), 2),
        "municipios_dgt_cruzados": len(rows),
        "municipios_sin_poblacion_ine": 0,
        "municipios_sin_parque_dgt": sum(1 for r in rows if r["parque_motocicletas_dgt_2025"] is None),
        "municipios_con_parque_cero": sum(1 for r in rows if r["parque_motocicletas_dgt_2025"] == 0),
        "top_categorias_no_asignadas": [
            {"categoria": name, "unidades": units}
            for name, units in unmatched.most_common(30)
        ],
    }
    if total != 219565 or (matched_total, suppressed_total, unmatched_total) != (170984, 41331, 7250):
        raise ValueError(
            "La conciliación cambió; revisar fuente o equivalencias: "
            f"total={total}, asignados={matched_total}, suprimidos={suppressed_total}, "
            f"no_asignados={unmatched_total}"
        )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matraba", type=Path, required=True, help="composicion_motocicletas_nuevas.csv")
    parser.add_argument("--ine", type=Path, required=True, help="CSV INE 29005")
    parser.add_argument("--dgt", type=Path, required=True, help="XLSX DGT municipal 2025")
    parser.add_argument("--output", type=Path, required=True, help="CSV municipal enriquecido")
    parser.add_argument("--summary", type=Path, required=True, help="JSON de cobertura y conciliación")
    args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
