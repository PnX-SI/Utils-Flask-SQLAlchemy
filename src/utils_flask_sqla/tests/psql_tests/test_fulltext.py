import pytest
import sqlalchemy as sa

from utils_flask_sqla.fulltext import fts_document, fts_query, ts_rank

NAMES = [
    "DUPONT Anny",
    "Aménagement du territoire",
    "Forêts de montagne",
    None,
]


@pytest.fixture
def pg_conn_unaccent(pg_conn):
    pg_conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS unaccent"))
    pg_conn.execute(sa.text("CREATE TEMPORARY TABLE fts_test (id serial, name text, descr text)"))
    for i, name in enumerate(NAMES):
        pg_conn.execute(
            sa.text("INSERT INTO fts_test (name, descr) VALUES (:name, :descr)"),
            {"name": name, "descr": f"description {i}"},
        )
    return pg_conn


def search(conn, text, *columns):
    table = sa.table("fts_test", sa.column("id"), sa.column("name"), sa.column("descr"))
    query = fts_query(text)
    document = fts_document(*[table.c[c] for c in columns or ("name",)])
    stmt = (
        sa.select(table.c.name)
        .where(document.op("@@")(query))
        .order_by(ts_rank(document, query).desc())
    )
    return [row.name for row in conn.execute(stmt)]


@pytest.mark.postgresql
class TestFulltextPostgreSQL:
    def test_accent_and_case_insensitive(self, pg_conn_unaccent):
        assert search(pg_conn_unaccent, "anny dupont") == ["DUPONT Anny"]
        assert search(pg_conn_unaccent, "ANNY") == ["DUPONT Anny"]

    def test_word_order_does_not_matter(self, pg_conn_unaccent):
        assert search(pg_conn_unaccent, "Anny Dupont") == ["DUPONT Anny"]
        assert search(pg_conn_unaccent, "dupont anny") == ["DUPONT Anny"]

    def test_prefix(self, pg_conn_unaccent):
        assert search(pg_conn_unaccent, "amén") == ["Aménagement du territoire"]
        assert search(pg_conn_unaccent, "dup an") == ["DUPONT Anny"]

    def test_stemming(self, pg_conn_unaccent):
        assert search(pg_conn_unaccent, "forêt") == ["Forêts de montagne"]

    def test_no_match(self, pg_conn_unaccent):
        assert search(pg_conn_unaccent, "inexistant") == []

    def test_null_columns_are_ignored(self, pg_conn_unaccent):
        # the row with a NULL name is still searchable on its other columns
        assert search(pg_conn_unaccent, "description 3", "name", "descr") == [None]

    def test_syntax_injection_is_harmless(self, pg_conn_unaccent):
        assert search(pg_conn_unaccent, "anny'); drop table fts_test; --") == []
