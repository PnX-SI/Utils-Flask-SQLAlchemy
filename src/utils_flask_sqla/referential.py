import csv
import os

from sqlalchemy import (
    inspect as sa_inspect,
    func,
    exists,
    select,
    table as sa_table,
    column as sa_column,
)

CSV_FIELDNAMES = [
    "ref_table",
    "table_name",
    "schema",
    "fk_column",
    "fk_value",
    "nb_affected_lines",
]


def get_referencing_tables(table_name, db, schema="", exclude_tables=[]):
    """Trouve toutes les tables qui ont des FK pointant vers table_name,
    en excluant les tables listées dans exclude_tables (même schéma)."""
    exclude_tables = set(exclude_tables or [])
    inspector = sa_inspect(db.engine)
    referencing_tables = []

    for other_schema in inspector.get_schema_names():
        if other_schema in ("pg_catalog", "information_schema", "pg_toast"):
            continue
        try:
            for other_table in inspector.get_table_names(schema=other_schema):
                if other_table != table_name and other_table in exclude_tables:
                    continue
                for fk in inspector.get_foreign_keys(other_table, schema=other_schema):
                    if fk["referred_table"] == f"{schema}.{table_name}":
                        referencing_tables.append(
                            {
                                "schema": other_schema,
                                "table": other_table,
                                "fk_column": fk["constrained_columns"][0],
                                "ref_column": fk["referred_columns"][0],
                            }
                        )
        except Exception as e:
            print(f"Impossible d'inspecter le schéma {other_schema}: {e}")

    return referencing_tables


def collect_orphan_rows(ref_table, new_ref_table, pk_col, db, schema="", exclude_tables=None):
    """
    Retourne la liste des lignes orphelines pour une table du référentiel :
    valeurs de pk_col présentes dans les tables référençantes mais absentes de new_ref_table.
    """
    referencing = get_referencing_tables(
        ref_table, db, schema=schema, exclude_tables=exclude_tables
    )
    rows = []
    for ref in referencing:
        fk_col = ref["fk_column"]
        src = sa_table(ref["table"], sa_column(fk_col), schema=ref["schema"])
        ref_t = sa_table(new_ref_table, sa_column(pk_col), schema=schema)
        subq = select(1).select_from(ref_t).where(ref_t.c[pk_col] == src.c[fk_col])
        stmt = (
            select(src.c[fk_col], func.count().label("nb_lines"))
            .where(src.c[fk_col].isnot(None))
            .where(~exists(subq))
            .group_by(src.c[fk_col])
            .order_by(src.c[fk_col])
        )
        for fk_value, nb_lines in db.session.execute(stmt).fetchall():
            rows.append(
                {
                    "ref_table": ref_table,
                    "table_name": ref["table"],
                    "schema": ref["schema"],
                    "fk_column": fk_col,
                    "fk_value": fk_value,
                    "nb_affected_lines": nb_lines,
                }
            )
    return rows


def export_orphans_to_csv(rows, output_path):
    """Écrit la liste de lignes orphelines dans un CSV."""
    if not rows:
        return 0
    dirname = os.path.dirname(output_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
