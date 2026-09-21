import importlib.util
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from utils_flask_sqla.revision import alter_table_with_dependent_views

SCHEMA = "test_revision"


@pytest.fixture
def dependent_view_chain(pg_conn):
    """table -> materialized view -> view, so alter_table_with_dependent_views
    has to recursively capture/drop/recreate two levels of dependents."""
    pg_conn.execute(text(f"CREATE SCHEMA {SCHEMA}"))
    pg_conn.execute(text(f"""
            CREATE TABLE {SCHEMA}.base_table (
                id integer PRIMARY KEY,
                name text,
                legacy_column text
            )
            """))
    pg_conn.execute(
        text(
            f"INSERT INTO {SCHEMA}.base_table (id, name, legacy_column) "
            "VALUES (1, 'foo', 'to-be-dropped')"
        )
    )
    pg_conn.execute(text(f"""
            CREATE MATERIALIZED VIEW {SCHEMA}.base_matview AS
            SELECT id, name FROM {SCHEMA}.base_table
            """))
    pg_conn.execute(text(f"""
            CREATE VIEW {SCHEMA}.dependent_view AS
            SELECT id, name FROM {SCHEMA}.base_matview
            """))
    return SCHEMA, "base_table"


@pytest.mark.postgresql
class TestAlterTableWithDependentViewsPostgres:
    def test_alter_table_preserves_view_chain(self, pg_conn, dependent_view_chain):
        schema, table_name = dependent_view_chain

        with alter_table_with_dependent_views(pg_conn, schema, table_name):
            pg_conn.execute(text(f"ALTER TABLE {schema}.{table_name} DROP COLUMN legacy_column"))

        columns = (
            pg_conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = :s AND table_name = :t"
                ),
                {"s": schema, "t": table_name},
            )
            .scalars()
            .all()
        )
        assert "legacy_column" not in columns
        assert set(columns) == {"id", "name"}

        assert pg_conn.execute(
            text(f"SELECT id, name FROM {schema}.base_matview ORDER BY id")
        ).all() == [(1, "foo")]

        assert pg_conn.execute(
            text(f"SELECT id, name FROM {schema}.dependent_view ORDER BY id")
        ).all() == [(1, "foo")]

    def test_recreated_views_reflect_altered_table_data(self, pg_conn, dependent_view_chain):
        schema, table_name = dependent_view_chain

        with alter_table_with_dependent_views(pg_conn, schema, table_name):
            pg_conn.execute(text(f"ALTER TABLE {schema}.{table_name} DROP COLUMN legacy_column"))
            pg_conn.execute(
                text(f"INSERT INTO {schema}.{table_name} (id, name) VALUES (2, 'bar')")
            )

        # the materialized view is only refreshed as part of the recreate step,
        # so it must pick up rows inserted during the body too
        assert pg_conn.execute(
            text(f"SELECT id, name FROM {schema}.base_matview ORDER BY id")
        ).all() == [(1, "foo"), (2, "bar")]

        assert pg_conn.execute(
            text(f"SELECT id, name FROM {schema}.dependent_view ORDER BY id")
        ).all() == [(1, "foo"), (2, "bar")]

    def test_views_dropped_during_body(self, pg_conn, dependent_view_chain):
        schema, table_name = dependent_view_chain

        def view_exists(name):
            return (
                pg_conn.execute(
                    text(
                        "SELECT 1 FROM pg_matviews WHERE schemaname = :s AND matviewname = :n "
                        "UNION ALL "
                        "SELECT 1 FROM pg_views WHERE schemaname = :s AND viewname = :n"
                    ),
                    {"s": schema, "n": name},
                ).first()
                is not None
            )

        with alter_table_with_dependent_views(pg_conn, schema, table_name):
            assert not view_exists("base_matview")
            assert not view_exists("dependent_view")

        assert view_exists("base_matview")
        assert view_exists("dependent_view")

    def test_views_recreated_even_if_body_raises(self, pg_conn, dependent_view_chain):
        schema, table_name = dependent_view_chain

        with pytest.raises(RuntimeError):
            with alter_table_with_dependent_views(pg_conn, schema, table_name):
                raise RuntimeError("failure mid-alter")

        assert pg_conn.execute(
            text(f"SELECT id, name FROM {schema}.base_matview ORDER BY id")
        ).all() == [(1, "foo")]
        assert pg_conn.execute(
            text(f"SELECT id, name FROM {schema}.dependent_view ORDER BY id")
        ).all() == [(1, "foo")]
