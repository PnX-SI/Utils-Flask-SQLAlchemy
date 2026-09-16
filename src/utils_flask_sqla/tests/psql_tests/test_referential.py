import pytest


from tempfile import NamedTemporaryFile

import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, Integer, Table, Unicode, insert
from utils_flask_sqla.referential import collect_orphan_rows, get_referencing_tables
from utils_flask_sqla.tests.psql_tests.conftest import PG_URI
from utils_flask_sqla.tests.utils import TestSession

db = SQLAlchemy()


table_1 = Table(
    "public.table1",
    db.metadata,
    db.Column("pk", Integer, primary_key=True),
    db.Column("name", Unicode),
)
table_2 = Table(
    "public.table2",
    db.metadata,
    db.Column("pk", Integer, primary_key=True),
    db.Column("fk", Integer, ForeignKey(table_1.c.pk)),
)
table_1_new = Table(
    "public.table1_new",
    db.metadata,
    db.Column("pk", Integer, primary_key=True),
)


@pytest.fixture(scope="session")
def _app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = PG_URI
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield


@pytest.fixture(scope="session")
def _session(_app):
    db.session.session_factory.class_ = TestSession
    db.session.remove()
    return db.session


@pytest.fixture(scope="session")
def app(_app, _session):
    pass


@pytest.fixture(scope="session")
def data(app):
    with db.session.begin_nested():
        db.session.execute(
            insert(table_1).values(
                [
                    {"pk": 1, "name": "ligne1"},
                    {"pk": 2, "name": "ligne2"},
                    {"pk": 3, "name": "ligne3"},
                ]
            )
        )
        db.session.execute(
            insert(table_2).values(
                [
                    {"pk": 1, "fk": 1},
                    {"pk": 2, "fk": 2},
                    {"pk": 3, "fk": 3},
                ]
            )
        )


@pytest.mark.usefixtures("app")
class TestReferential:

    def test_get_get_referencing_tables(data):
        referenced_tables = get_referencing_tables("table1", db, "public")
        assert any([table_def["table"] == "public.table2" for table_def in referenced_tables])

    def test_collect_orphan_rows_no_orphans(self, data):
        rows = collect_orphan_rows("table1", "public.table1", "pk", db, schema="public")
        assert rows == []

    def test_collect_orphan_rows_detects_missing_rows(self, data):
        db.session.execute(insert(table_1_new).values([{"pk": 1}, {"pk": 2}]))

        rows = collect_orphan_rows("table1", "public.table1_new", "pk", db, schema="public")

        assert rows == [
            {
                "ref_table": "table1",
                "table_name": "public.table2",
                "schema": "public",
                "fk_column": "fk",
                "fk_value": 3,
                "nb_affected_lines": 1,
            }
        ]

    def test_collect_orphan_rows_excludes_tables(self, data):
        rows = collect_orphan_rows(
            "table1", "public.table1", "pk", db, schema="public", exclude_tables=["table2"]
        )
        assert rows == []
