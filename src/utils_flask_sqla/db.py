from flask import request
from werkzeug.exceptions import BadRequest


__all__ = ["ordered"]


def get_column_from_path(select, model, path, *, join=False):
    """
    Return a tuple (select, column), with column retrieved from the model following the given path.
    If join is True, each time a relationship is traversed, the related model is automatically
    joined to the select statement.
    """
    field, _, path = path.partition(".")
    if path:
        try:
            rel = model.__mapper__.relationships[field]
        except KeyError:
            raise BadRequest("{} does not have a relationship '{}'".format(model, field))
        if join:
            select = select.join(getattr(model, field))
        model = rel.mapper.class_
        return get_column_from_path(select, model, path, join=join)
    else:
        try:
            col = model.__mapper__.columns[field]
        except KeyError:
            raise BadRequest("{} does not have a field '{}'".format(model, field))
        return select, col


def ordered(select, model, *, order_by=None, join=False, arg_name="sort", reset=False):
    """
    This method applies an order_by on query based on column(s) found either in the
    query parameters or directly in the function parameter `order_by`.

    Usage
    =====

    Using query parameters
    ----------------------

    To fetch column using the query, indicate the query parameter name in the
    `arg_name` function parameter.

    Example 1: Fetch column by query parameter

    >>> ## URL of the query : http://localhost/api/route?sort=name
    >>> ordered(select,User,arg_name=sort)

    Example 2: Fetch multiple columns by query parameter

    >>> ## URL of the query : http://localhost/api/route?sort=name,address
    >>> ordered(select,User,arg_name=sort)

    Example 3: Change ordering direction by prefixing each field name with a
    `-`

    >>> ## URL of the query : http://localhost/api/route?sort=-name,address
    >>> ordered(select,User,arg_name=sort)

    Using `order_by` function parameter
    -----------------------------------

    Simply, indicate the column object in the `order_by` parameter

    Example 1: Order by a single column

    >>>  ordered(select,User,order_by=User.name)

    Example 2: Order by multiple columns with different directions

    >>>  ordered(select,User,order_by=[User.name.desc(), User.address])

    Cancel previous ordering
    ========================

    Set the `reset` parameter to True to deactivate previous order_by on the
    existing query.

    Example: Reset previous ordering

    >>>  ordered(select,User,reset=True)

    `join` parameter
    ================

    Criteria can refer to a relationship using the dot notation.
    However, related model must be joined to the query, which can be done automatically
    with join=True. If join=False and referenced related model is not part of from clause
    of the query, a BadRequest is raised.

    Parameters
    ==========
    select : Union[Select, Selectable]
        A SQLAlchemy select statement
    model : Model
        The model class for which the ordering should be performed.
    order_by : Optional[Union[str, List[str], Tuple[str]]]
        A string or a list/tuple of strings representing the columns to order
    by. If `None`, the default ordering will be used.
    join : bool, optional
        Whether to perform a join with the `model` table before applying the
    ordering. Defaults to `False`.
    arg_name : str, optional
        The name of the query parameter that contains the sorting information.
    Defaults to `"sort"`.
    reset : bool, optional
        Whether to reset the existing ordering before applying the new ordering.
    Defaults to `False`.

    Returns
    =======
    Union[Select, Selectable]
        A SQLAlchemy select statement or an object that can be passed to
    `sqlalchemy.orm.class_mapper` with the applied ordering.
    """

    sort_fields = request.args.get(arg_name)
    if sort_fields:
        order_by = []
        sort_fields = sort_fields.split(",")
        for path in sort_fields:
            direction = None
            if path.startswith("-"):
                path = path[1:]
                direction = "desc"

            select, col = get_column_from_path(select, model, path, join=join)
            if not join and not any(
                [col in from_clause.columns.values() for from_clause in select.get_final_froms()]
            ):
                raise BadRequest("{} is not part of from clauses".format(path))

            if direction == "desc":
                col = col.desc()
            else:
                col = col.asc()

            order_by.append(col)
        if reset:
            select = select.order_by(None)
        return select.order_by(*order_by)

    elif order_by is not None:
        if reset:
            select = select.order_by(None)
        if isinstance(order_by, list) or isinstance(order_by, tuple):
            return select.order_by(*order_by)
        else:
            return select.order_by(order_by)

    return select
