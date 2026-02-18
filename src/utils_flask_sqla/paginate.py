from flask_sqlalchemy.pagination import Pagination, QueryPagination
from sqlalchemy.orm.query import Query
from sqlalchemy.orm import lazyload
from sqlalchemy import Column, select, func, Table
import typing as t


def paginate(session, query, **flask_sqla_args):
    """
    Paginate a SQLAlchemy query or select statement.

    This function determines whether the given object is a `Query` or a
    `select` statement and returns the appropriate pagination object.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
        The current SQLAlchemy session
    query : sqlalchemy.orm.query.Query or sqlalchemy.sql.Select
        The query or select object to paginate.
    **flask_sqla_args : dict
        Additional keyword arguments passed to the pagination object, such as
        `page`, `per_page`, and `session`.

    Returns
    -------
    flask_sqlalchemy.pagination.QueryPagination or SelectPagination
        The pagination object for the given query.
    """
    using_query_api = isinstance(query, Query)
    flask_sqla_args["session"] = session
    if using_query_api:
        flask_sqla_args["query"] = query
        return QueryPagination(**flask_sqla_args)
    flask_sqla_args["select"] = query
    return SelectPagination(**flask_sqla_args)


def is_entity_select(stmt):
    """
    Check whether a given SQLAlchemy statement selects an entity.

    Parameters
    ----------
    stmt : sqlalchemy.sql.Select
        The select statement to inspect.

    Returns
    -------
    bool
        True if the select statement targets an entity (not just columns),
        False otherwise.
    """
    raw_cols = stmt._raw_columns
    if len(raw_cols) == 1:
        target = raw_cols[0]
        if not isinstance(target, Column) and not isinstance(target, Table):
            return True
    return False


class SelectPagination(Pagination):
    """
    Pagination class for SQLAlchemy `select` statements.

    This class extends Flask-SQLAlchemy's `Pagination` to support
    SQLAlchemy 1.4/2.0 `select` objects instead of only ORM queries.
    """

    def _query_items(self) -> list[t.Any]:
        """
        Retrieve the items for the current page.

        Applies `limit` and `offset` to the select statement, executes it,
        and returns the paginated results.

        Returns
        -------
        list of Any
            The items retrieved for the current page.
        """
        select = self._query_args["select"]
        select = select.limit(self.per_page).offset(self._query_offset)
        session = self._query_args["session"]
        if is_entity_select(select):
            return list(session.execute(select).unique().scalars())
        return list(session.execute(select).all())

    def _query_count(self) -> int:
        """
        Count the total number of rows for the select statement.

        Builds a subquery from the select statement, removes ordering,
        and counts the total rows using `COUNT(*)`.

        Returns
        -------
        int
            The total number of rows in the query.
        """
        select_q = self._query_args["select"]
        sub = select_q.options(lazyload("*")).order_by(None).subquery()
        session = self._query_args["session"]
        out = session.execute(select(func.count()).select_from(sub)).scalar()
        return out
