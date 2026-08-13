import importlib.util
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from utils_flask_sqla.revision import alter_table_with_dependent_views

# ---------------------------------------------------------------------------
# Integration tests against a real PostgreSQL database.
#
# These exercise the actual `pg_capture_dependent_views` / `pg_drop_dependent_views`
# / `pg_recreate_dependent_views` SQL functions (created by migration revision
# 1d09a9b67970) against a real dependency chain: a table, a materialized view
# built on that table, and a plain view built on that materialized view.
#
# They require a running PostgreSQL server. Point TEST_PG_DATABASE_URI at it,
# e.g.:
#   docker run --rm -p 5432:5432 -e POSTGRES_USER=geonatadmin \
#       -e POSTGRES_PASSWORD=geonatadmin -e POSTGRES_DB=geonature2db \
#       postgis/postgis:15-3.4
# Tests are skipped automatically if no server is reachable.
# ---------------------------------------------------------------------------

PG_URI = os.environ.get(
    "TEST_PG_DATABASE_URI",
    "postgresql+psycopg2://geonatadmin:geonatadmin@localhost:5432/geonature2db",
)

MIGRATION_FILE = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "1d09a9b67970_add_functions_to_fetch_dependent_view_.py"
)


def _load_migration_module():
    spec = importlib.util.spec_from_file_location(
        "utils_flask_sqla_test_dependent_views_migration", MIGRATION_FILE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def pg_engine():
    from alembic.operations import Operations
    from alembic.runtime.migration import MigrationContext

    engine = create_engine(PG_URI)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        engine.dispose()
        pytest.skip(f"PostgreSQL test database not reachable at {PG_URI}: {exc}")

    migration = _load_migration_module()
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()

    yield engine

    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
    engine.dispose()


@pytest.fixture
def pg_conn(pg_engine):
    """A connection wrapping the whole test in one rolled-back transaction.

    PostgreSQL DDL is transactional, so creating the schema/table/views inside
    this transaction and rolling it back at teardown leaves no trace, without
    needing per-test unique names.
    """
    with pg_engine.connect() as conn:
        trans = conn.begin()
        try:
            yield conn
        finally:
            trans.rollback()


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
