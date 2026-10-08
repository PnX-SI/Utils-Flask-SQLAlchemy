import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from utils_flask_sqla.fulltext import fts_document, fts_query, ts_rank


def compiled(expression):
    return str(
        expression.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


class TestFtsQuery:
    @pytest.mark.parametrize("search", [None, "", "   ", "-- ! ()", ":*&|"])
    def test_no_word(self, search):
        assert fts_query(search) is None

    def test_last_word_is_a_prefix(self):
        sql = compiled(fts_query("Anny Dupont"))
        assert "to_tsquery" in sql
        assert "unaccent('Anny & Dupont:*')" in sql

    def test_without_prefix(self):
        assert "unaccent('foo & bar')" in compiled(fts_query("foo bar", prefix=False))

    def test_punctuation_separates_words(self):
        sql = compiled(fts_query("CA-2020_foo"))
        assert "unaccent('CA & 2020 & foo:*')" in sql

    def test_tsquery_syntax_is_neutralized(self):
        sql = compiled(fts_query("foo'); drop table x; -- & !bar"))
        assert "unaccent('foo & drop & table & x & bar:*')" in sql

    def test_config(self):
        assert "'simple'" in compiled(fts_query("foo", config="simple"))
        assert "'french'" in compiled(fts_query("foo"))


class TestFtsDocument:
    def test_document(self):
        table = sa.table("t", sa.column("a"), sa.column("b"))
        sql = compiled(fts_document(table.c.a, table.c.b))
        assert "to_tsvector" in sql
        assert "unaccent(concat_ws(' ', t.a, t.b))" in sql
        assert "regexp_replace" in sql

    def test_rank(self):
        table = sa.table("t", sa.column("a"))
        sql = compiled(ts_rank(fts_document(table.c.a), fts_query("foo")))
        assert sql.startswith("ts_rank(")
