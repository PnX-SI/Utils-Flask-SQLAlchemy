import datetime
import os
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from dateutil import parser
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import Boolean, Date, DateTime, Integer, Numeric, Text
from werkzeug.exceptions import BadRequest

from utils_flask_sqla.errors import UtilsSqlaError

# `utils_flask_sqla.generic` imports its `db` from `utils_flask_sqla.env`, which is
# resolved lazily from the FLASK_SQLALCHEMY_DB env var ("module.path.db_object") the
# first time it is imported. Point it at the SQLAlchemy instance defined below before
# importing the module under test, so GenericTable/GenericQuery operate on our test db.
db = SQLAlchemy()
os.environ["FLASK_SQLALCHEMY_DB"] = f"{__name__}.db"

# Aliased on import: their original names start with "test", which makes pytest's
# default collection try to gather them as test functions in this module.
from utils_flask_sqla.generic import (  # noqa: E402
    GenericQuery,
    GenericTable,
    serializeQuery,
    serializeQueryOneResult,
    serializeQueryTest,
    testDataType as check_data_type,
    test_type_and_generate_query as build_typed_filter_query,
)

# `item` is created via plain SQLAlchemy Core, on its own MetaData, rather than as a
# db.Model. GenericTable reflects tables into `db.metadata`: if a table of the same
# name were already declared there (e.g. as an ORM model), sa.Table(...) would just
# return that existing, non-reflected definition instead of actually reflecting the
# database, which would defeat the point of these tests.
item_metadata = sa.MetaData()
item_table = sa.Table(
    "item",
    item_metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.Text),
    sa.Column("price", sa.Numeric),
    sa.Column("created", sa.DateTime),
    sa.Column("active", sa.Boolean),
)


@pytest.fixture(scope="module")
def app():
    app = Flask("utils-flask-sqla-generic-test")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///"
    db.init_app(app)
    with app.app_context():
        item_metadata.create_all(db.engine)
        yield app


@pytest.fixture
def rows(app):
    db.session.execute(sa.delete(item_table))
    db.session.execute(
        item_table.insert(),
        [
            {
                "id": 1,
                "name": "foo",
                "price": 10.5,
                "created": datetime.datetime(2020, 1, 1),
                "active": True,
            },
            {
                "id": 2,
                "name": "bar",
                "price": 20.0,
                "created": datetime.datetime(2021, 6, 15),
                "active": False,
            },
            {
                "id": 3,
                "name": "foobar",
                "price": 5.25,
                "created": datetime.datetime(2022, 3, 10),
                "active": True,
            },
        ],
    )
    db.session.commit()
    yield
    db.session.execute(sa.delete(item_table))
    db.session.commit()


@pytest.fixture
def generic_table(app):
    return GenericTable("item", None, db.engine)


class TestTestDataType:
    def test_integer_valid(self):
        assert check_data_type("42", Integer, "age") is None

    def test_integer_valid_type_instance(self):
        assert check_data_type("42", Integer(), "age") is None

    def test_integer_invalid(self):
        assert check_data_type("abc", Integer, "age") == "age must be an integer"

    def test_numeric_valid(self):
        assert check_data_type("3.14", Numeric, "price") is None

    def test_numeric_invalid(self):
        assert (
            check_data_type("abc", Numeric, "price")
            == "price must be an float (decimal separator .)"
        )

    def test_datetime_valid(self):
        assert check_data_type("2020-01-01", DateTime, "created") is None

    def test_date_type_instance_valid(self):
        assert check_data_type("2020-01-01", Date(), "created") is None

    def test_datetime_invalid(self):
        assert (
            check_data_type("not-a-date", DateTime, "created")
            == "created must be an date (yyyy-mm-dd)"
        )

    def test_unhandled_type_returns_none(self):
        assert check_data_type("anything", Text, "name") is None


class TestTestTypeAndGenerateQuery:
    # Plain sa.Column objects (not bound to any table) are enough to build the
    # comparison expressions this function produces, without needing a real model.
    class Model:
        id = sa.Column("id", Integer())
        amount = sa.Column("amount", Numeric())
        created = sa.Column("created", DateTime())
        active = sa.Column("active", Boolean())

    def test_unknown_column_raises(self):
        with pytest.raises(UtilsSqlaError):
            build_typed_filter_query("missing", "1", self.Model, sa.select(1))

    def test_integer_column(self):
        q = build_typed_filter_query("id", "5", self.Model, sa.select(1))
        assert q.whereclause.right.value == 5

    def test_integer_column_invalid_value_raises(self):
        with pytest.raises(UtilsSqlaError):
            build_typed_filter_query("id", "abc", self.Model, sa.select(1))

    def test_numeric_column(self):
        q = build_typed_filter_query("amount", "3.5", self.Model, sa.select(1))
        assert q.whereclause.right.value == 3.5

    def test_numeric_column_invalid_value_raises(self):
        with pytest.raises(UtilsSqlaError):
            build_typed_filter_query("amount", "abc", self.Model, sa.select(1))

    def test_datetime_column(self):
        q = build_typed_filter_query("created", "2020-01-01", self.Model, sa.select(1))
        assert q.whereclause.right.value == parser.parse("2020-01-01")

    def test_datetime_column_invalid_value_raises(self):
        with pytest.raises(UtilsSqlaError):
            build_typed_filter_query("created", "not-a-date", self.Model, sa.select(1))

    def test_boolean_column(self):
        q = build_typed_filter_query("active", "true", self.Model, sa.select(1))
        assert "active IS true" in str(q)


class TestGenericTable:
    def test_reflects_columns_from_the_database(self, generic_table):
        assert set(generic_table.tableDef.columns.keys()) == {
            "id",
            "name",
            "price",
            "created",
            "active",
        }
        assert [c.name for c in generic_table.db_cols] == [
            "id",
            "name",
            "price",
            "created",
            "active",
        ]

    def test_missing_table_raises(self, app):
        # GenericTable.__init__ catches KeyError around the reflection call, but
        # sa.Table(..., autoload_with=...) actually raises NoSuchTableError for a
        # missing table, which is not a KeyError subclass: the except clause never
        # triggers, and the SQLAlchemy exception propagates as-is.
        with pytest.raises(sa.exc.NoSuchTableError):
            GenericTable("does_not_exist_table", None, db.engine)

    def test_get_serialized_columns_excludes_geometry_columns(self):
        class Geometry:
            pass

        fake_table_def = SimpleNamespace(
            columns=SimpleNamespace(
                items=lambda: [
                    ("id", SimpleNamespace(type=Integer())),
                    ("geom", SimpleNamespace(type=Geometry())),
                    ("created", SimpleNamespace(type=DateTime())),
                ]
            )
        )
        table = GenericTable.__new__(GenericTable)
        table.tableDef = fake_table_def

        serialize_columns, db_cols = table.get_serialized_columns()

        assert [name for name, _ in serialize_columns] == ["id", "created"]
        assert len(db_cols) == 3

    def test_get_serialized_columns_uses_type_specific_serializers(self):
        table = GenericTable.__new__(GenericTable)
        table.tableDef = SimpleNamespace(
            columns=SimpleNamespace(
                items=lambda: [
                    ("created", SimpleNamespace(type=DateTime())),
                    ("name", SimpleNamespace(type=Text())),
                ]
            )
        )
        serialize_columns, _ = table.get_serialized_columns()
        serializers = dict(serialize_columns)

        assert serializers["created"](None) is None
        assert serializers["created"](datetime.datetime(2020, 1, 1)) == "2020-01-01 00:00:00"
        # Text has no dedicated serializer registered, so it passes through unchanged.
        assert serializers["name"]("foo") == "foo"

    def test_as_dict_all_fields(self, generic_table, rows):
        row = db.session.execute(
            sa.select(generic_table.tableDef).where(generic_table.tableDef.c.id == 1)
        ).first()

        assert generic_table.as_dict(row) == {
            "id": 1,
            "name": "foo",
            "price": "10.5000000000",
            "created": "2020-01-01 00:00:00",
            "active": True,
        }

    def test_as_dict_fields_restricts_output(self, generic_table, rows):
        row = db.session.execute(
            sa.select(generic_table.tableDef).where(generic_table.tableDef.c.id == 1)
        ).first()

        assert generic_table.as_dict(row, fields=["id", "name"]) == {"id": 1, "name": "foo"}

    def test_as_dict_columns_argument_is_deprecated_but_still_works(self, generic_table, rows):
        row = db.session.execute(
            sa.select(generic_table.tableDef).where(generic_table.tableDef.c.id == 1)
        ).first()

        with pytest.deprecated_call():
            result = generic_table.as_dict(row, columns=["id", "name"])

        assert result == {"id": 1, "name": "foo"}


class TestGenericQuery:
    def test_direct_equality_filter(self, app, rows):
        gq = GenericQuery(db, "item", None, filters={"name": "bar"})
        data, total, total_filtered = gq.query()

        assert [d.id for d in data] == [2]
        assert total == 3
        assert total_filtered == 1

    def test_ilike_filter(self, app, rows):
        gq = GenericQuery(db, "item", None, filters={"ilike_name": "foo"})
        data, total, total_filtered = gq.query()

        assert sorted(d.id for d in data) == [1, 3]
        assert total == 3
        assert total_filtered == 2

    def test_filter_d_up_lo_eq_on_matching_column_type(self, app, rows):
        # filter_d_* only ends up applied when the reflected column type name is
        # one of "Date", "DateTime", "TIMESTAMP" or "INTEGER" (see build_query_filter).
        # A reflected sqlite INTEGER column matches, so it is used here.
        up = GenericQuery(db, "item", None, filters={"filter_d_up_id": "2"})
        data_up, *_ = up.query()
        assert sorted(d.id for d in data_up) == [2, 3]

        lo = GenericQuery(db, "item", None, filters={"filter_d_lo_id": "2"})
        data_lo, *_ = lo.query()
        assert sorted(d.id for d in data_lo) == [1, 2]

        eq = GenericQuery(db, "item", None, filters={"filter_d_eq_id": "2"})
        data_eq, *_ = eq.query()
        assert sorted(d.id for d in data_eq) == [2]

    def test_filter_d_on_datetime_column_is_not_applied(self, app, rows):
        # Characterizes existing behavior: a reflected sqlite DateTime column has
        # class name "DATETIME", which is not in the ("Date", "DateTime",
        # "TIMESTAMP", "INTEGER") list checked by build_query_filter, so the filter
        # is silently ignored and every row is returned.
        gq = GenericQuery(db, "item", None, filters={"filter_d_up_created": "2021-01-01"})
        data, *_ = gq.query()
        assert sorted(d.id for d in data) == [1, 2, 3]

    def test_filter_d_invalid_value_raises(self, app, rows):
        gq = GenericQuery(db, "item", None, filters={"filter_d_up_id": "not-a-date-or-int"})
        with pytest.raises(UtilsSqlaError):
            gq.query()

    def test_filter_n_up_lo(self, app, rows):
        up = GenericQuery(db, "item", None, filters={"filter_n_up_price": "10"})
        data_up, *_ = up.query()
        assert sorted(d.id for d in data_up) == [1, 2]

        lo = GenericQuery(db, "item", None, filters={"filter_n_lo_price": "10"})
        data_lo, *_ = lo.query()
        assert sorted(d.id for d in data_lo) == [3]

    def test_filter_n_invalid_value_raises(self, app, rows):
        gq = GenericQuery(db, "item", None, filters={"filter_n_up_price": "abc"})
        with pytest.raises(UtilsSqlaError):
            gq.query()

    def test_orderby_asc_and_desc(self, app, rows):
        asc = GenericQuery(db, "item", None, filters={"orderby": "price:asc"})
        data_asc, *_ = asc.query()
        assert [d.id for d in data_asc] == [3, 1, 2]

        desc = GenericQuery(db, "item", None, filters={"orderby": "price:desc"})
        data_desc, *_ = desc.query()
        assert [d.id for d in data_desc] == [2, 1, 3]

    def test_orderby_defaults_to_asc(self, app, rows):
        gq = GenericQuery(db, "item", None, filters={"orderby": "price"})
        data, *_ = gq.query()
        assert [d.id for d in data] == [3, 1, 2]

    def test_orderby_unknown_column_raises_bad_request(self, app, rows):
        gq = GenericQuery(db, "item", None, filters={"orderby": "nope"})
        with pytest.raises(BadRequest):
            gq.query()

    def test_limit_must_be_positive(self, app):
        with pytest.raises(AssertionError):
            GenericQuery(db, "item", None, limit=-1)

    def test_limit_and_offset_use_page_semantics(self, app, rows):
        # offset is a page index: set_limit() computes offset * limit, not a raw
        # row offset.
        gq = GenericQuery(db, "item", None, limit=1, offset=1)
        data, total, total_filtered = gq.query()

        assert [d.id for d in data] == [2]
        assert total == 3
        assert total_filtered == 3

    def test_raw_query_without_filters_ignores_process_filter_flag(self, app, rows):
        gq = GenericQuery(db, "item", None, filters={"name": "bar"})

        unfiltered = gq.raw_query(process_filter=False)
        assert unfiltered.count() == 3

        filtered = gq.raw_query(process_filter=True)
        assert filtered.count() == 1

    def test_return_query_shape(self, app, rows):
        gq = GenericQuery(db, "item", None, filters={"name": "bar"})
        result = gq.return_query()

        assert result["total"] == 3
        assert result["total_filtered"] == 1
        assert result["page"] == 0
        assert result["limit"] is None
        assert result["items"] == [
            {
                "id": 2,
                "name": "bar",
                "price": "20.0000000000",
                "created": "2021-06-15 00:00:00",
                "active": False,
            }
        ]

    def test_as_dict_is_an_alias_of_return_query(self, app, rows):
        gq = GenericQuery(db, "item", None)
        assert gq.as_dict() == gq.return_query()


class TestSerializeQuery:
    def test_serialize_query_drops_none_values(self):
        rows = [
            SimpleNamespace(id=1, name="foo", price=None),
            SimpleNamespace(id=2, name=None, price=9.5),
        ]
        column_def = [{"name": "id"}, {"name": "name"}, {"name": "price"}]

        assert serializeQuery(rows, column_def) == [
            {"id": 1, "name": "foo"},
            {"id": 2, "price": 9.5},
        ]

    def test_serialize_query_one_result(self):
        row = SimpleNamespace(id=1, name="foo", price=None)
        column_def = [{"name": "id"}, {"name": "name"}, {"name": "price"}]

        assert serializeQueryOneResult(row, column_def) == {"id": 1, "name": "foo"}

    def test_serialize_query_test_only_serializes_typed_columns(self):
        # Characterizes existing behavior: serializeQueryTest only ever populates
        # the output dict for Date/DateTime/UUID/Numeric columns; every other
        # column type (here, "id" and "name") is silently dropped.
        row = SimpleNamespace(
            id=1, name="foo", price=9.5, created=datetime.date(2020, 1, 1), uid="not-checked"
        )
        column_def = [
            {"name": "id", "type": Integer()},
            {"name": "name", "type": Text()},
            {"name": "price", "type": Numeric()},
            {"name": "created", "type": Date()},
        ]

        assert serializeQueryTest([row], column_def) == [{"price": 9.5, "created": "2020-01-01"}]

    def test_serialize_query_test_handles_uuid_type(self):
        row = SimpleNamespace(uid="123e4567-e89b-12d3-a456-426614174000")
        column_def = [{"name": "uid", "type": UUID()}]

        assert serializeQueryTest([row], column_def) == [
            {"uid": "123e4567-e89b-12d3-a456-426614174000"}
        ]
