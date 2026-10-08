"""
Helpers to build accent-insensitive PostgreSQL full text searches.

They rely on the PostgreSQL ``unaccent`` extension (``CREATE EXTENSION unaccent``).

Examples
--------
>>> query = fts_query("anny dup")
>>> if query is not None:
...     document = fts_document(User.nom_role, User.prenom_role)
...     stmt = (
...         select(User)
...         .where(document.op("@@")(query))
...         .order_by(ts_rank(document, query).desc())
...     )
"""

import re

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import REGCONFIG

__all__ = ["DEFAULT_FTS_CONFIG", "fts_document", "fts_query", "ts_rank"]

DEFAULT_FTS_CONFIG = "french"


def _regconfig(config):
    return sa.cast(sa.literal(config), REGCONFIG)


def fts_document(*columns, config=DEFAULT_FTS_CONFIG):
    """
    Build an accent-insensitive ``tsvector`` from text columns.

    Punctuation separates words.

    Parameters
    ----------
    *columns : sqlalchemy.sql.ColumnElement
        Columns (or text expressions) concatenated into one document. NULLs are ignored.
    config : str, default "french"
        Name of the PostgreSQL text search configuration.

    Returns
    -------
    sqlalchemy.sql.ColumnElement
        The ``tsvector`` expression.
    """
    # punctuation is replaced by spaces: the PostgreSQL parser would read "CA-2020" as the words
    # "ca" and "-2020" (a negative number), which a search for "2020" would not find
    text = func.regexp_replace(
        func.unaccent(func.concat_ws(" ", *columns)), r"[^[:alnum:]]+", " ", "g"
    )
    return func.to_tsvector(_regconfig(config), text)


def fts_query(search, *, prefix=True, config=DEFAULT_FTS_CONFIG):
    """
    Build an accent-insensitive ``tsquery`` matching all the words of a text.

    Only the words (letters and digits) of `search` are kept, so it is safe to give it as typed by
    a user. Punctuation, such as the dashes of "CA-2020" or of an UUID, separates words, like in
    `fts_document`.

    Parameters
    ----------
    search : str or None
        Text to search.
    prefix : bool, default True
        Match the last word as a prefix, so that results follow what is being typed: the other
        words are complete, otherwise "ca-1" would match any text with a word beginning with
        "ca" ("carte") and another one beginning with "1".
    config : str, default "french"
        Name of the PostgreSQL text search configuration.

    Returns
    -------
    sqlalchemy.sql.ColumnElement or None
        The ``tsquery`` expression, or None if `search` holds no word.
    """
    words = re.findall(r"[^\W_]+", search or "")
    if not words:
        return None
    if prefix:
        words[-1] += ":*"
    return func.to_tsquery(_regconfig(config), func.unaccent(" & ".join(words)))


def ts_rank(document, query):
    """
    Compute the relevance of a document for a query.

    Parameters
    ----------
    document : sqlalchemy.sql.ColumnElement
        The ``tsvector``, see `fts_document`.
    query : sqlalchemy.sql.ColumnElement
        The ``tsquery``, see `fts_query`.

    Returns
    -------
    sqlalchemy.sql.ColumnElement
        The rank expression, the higher the more relevant.
    """
    return func.ts_rank(document, query)
