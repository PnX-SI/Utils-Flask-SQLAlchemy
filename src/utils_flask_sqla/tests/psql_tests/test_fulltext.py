import pytest
import sqlalchemy as sa

from utils_flask_sqla.fulltext import fts_document, fts_query, ts_rank

NAMES = [
    "DUPONT Anny",
    "Aménagement du territoire",
    "Forêts de montagne",
    "CA-2020-inventaire",
    "9409111b-4783-426f-9c57-1083718292a5",
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
        assert search(pg_conn_unaccent, "dupont an") == ["DUPONT Anny"]

    def test_dashes_do_not_break_words(self, pg_conn_unaccent):
        # "-2020" would be read as a negative number without replacing punctuation by spaces
        for text in ("CA", "ca-", "CA-2020", "ca-2020-inv", "2020", "inventaire ca"):
            assert search(pg_conn_unaccent, text) == ["CA-2020-inventaire"], text

    def test_uuid_by_beginning_or_fragment(self, pg_conn_unaccent):
        uuid = "9409111b-4783-426f-9c57-1083718292a5"
        for text in ("9409", "9409111B-47", uuid[:13], uuid, "4783", "1083718292a5"):
            assert search(pg_conn_unaccent, text) == [uuid], text

    def test_only_the_last_word_is_a_prefix(self, pg_conn_unaccent):
        # "ca" must not match "carte": the other words are complete
        assert search(pg_conn_unaccent, "ca-2") == ["CA-2020-inventaire"]
        assert search(pg_conn_unaccent, "dup anny") == []

    def test_stemming(self, pg_conn_unaccent):
        assert search(pg_conn_unaccent, "forêt") == ["Forêts de montagne"]

    def test_no_match(self, pg_conn_unaccent):
        assert search(pg_conn_unaccent, "inexistant") == []

    def test_null_columns_are_ignored(self, pg_conn_unaccent):
        # the row with a NULL name is still searchable on its other columns
        assert search(pg_conn_unaccent, "description 5", "name", "descr") == [None]

    def test_syntax_injection_is_harmless(self, pg_conn_unaccent):
        assert search(pg_conn_unaccent, "anny'); drop table fts_test; --") == []
