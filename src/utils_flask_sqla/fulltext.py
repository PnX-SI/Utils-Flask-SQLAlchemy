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
    return func.to_tsvector(_regconfig(config), func.unaccent(func.concat_ws(" ", *columns)))


def fts_query(search, *, prefix=True, config=DEFAULT_FTS_CONFIG):
    """
    Build an accent-insensitive ``tsquery`` matching all the words of a text.

    Only the words of `search` are kept, so it is safe to give it as typed by a user.

    Parameters
    ----------
    search : str or None
        Text to search.
    prefix : bool, default True
        Match each word as a prefix, so that results follow what is being typed.
    config : str, default "french"
        Name of the PostgreSQL text search configuration.

    Returns
    -------
    sqlalchemy.sql.ColumnElement or None
        The ``tsquery`` expression, or None if `search` holds no word.
    """
    words = re.findall(r"\w+", search or "")
    if not words:
        return None
    suffix = ":*" if prefix else ""
    return func.to_tsquery(
        _regconfig(config), func.unaccent(" & ".join(f"{word}{suffix}" for word in words))
    )


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
