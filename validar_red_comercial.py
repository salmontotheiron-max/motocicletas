"""Inicialización y validación del esquema histórico de red comercial."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("esquema_red_comercial.sql")


def connect(database: str | Path = ":memory:") -> sqlite3.Connection:
    """Abre SQLite con claves foráneas activadas."""
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database: str | Path = ":memory:") -> sqlite3.Connection:
    """Crea las tablas e índices; es idempotente."""
    connection = connect(database)
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return connection


def validate_database(connection: sqlite3.Connection) -> list[str]:
    """Devuelve errores de integridad; lista vacía significa validación correcta."""
    errors: list[str] = []

    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        errors.append("foreign_keys debe estar activado")

    for row in connection.execute("PRAGMA foreign_key_check"):
        errors.append(
            f"clave foránea inválida en {row['table']}, fila {row['rowid']}"
        )

    for row in connection.execute("PRAGMA integrity_check"):
        if row[0] != "ok":
            errors.append(f"integrity_check: {row[0]}")

    temporal_tables = (
        "entity_alias",
        "brand_company_relation",
        "outlet_company_relation",
        "outlet_brand_relation",
        "claim",
    )
    for table in temporal_tables:
        invalid = connection.execute(
            f"""SELECT COUNT(*) FROM {table}
                WHERE valid_from IS NOT NULL
                  AND valid_to IS NOT NULL
                  AND valid_to <= valid_from"""
        ).fetchone()[0]
        if invalid:
            errors.append(f"{table}: {invalid} intervalos temporales inválidos")

    return errors


def validate_interval(valid_from: str | None, valid_to: str | None) -> None:
    """Valida un intervalo ISO YYYY-MM-DD semiabierto [inicio, fin)."""
    from datetime import date

    start = date.fromisoformat(valid_from) if valid_from else None
    end = date.fromisoformat(valid_to) if valid_to else None
    if start and end and end <= start:
        raise ValueError("valid_to debe ser posterior a valid_from")


if __name__ == "__main__":
    db = initialize_database()
    problems = validate_database(db)
    if problems:
        raise SystemExit("\n".join(problems))
    print("Esquema histórico válido.")
