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
#   docker run --rm -d -p 5432:5432 -e POSTGRES_USER=geonatadmin \
#       -e POSTGRES_PASSWORD=geonatadmin -e POSTGRES_DB=geonature2db \
#       postgis/postgis:15-3.4
# Tests are skipped automatically if no server is reachable.
# ---------------------------------------------------------------------------

PG_URI = os.environ.get(
    "TEST_PG_DATABASE_URI",
    "postgresql+psycopg2://geonatadmin:geonatadmin@localhost:5432/geonature2db",
)

MIGRATION_FILE = (
    Path(__file__).resolve().parent.parent.parent
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
