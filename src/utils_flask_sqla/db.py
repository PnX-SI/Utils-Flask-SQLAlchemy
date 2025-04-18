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


def ordered(select, model, *, order_by=None, join=False, arg_name="sort"):
    """
    User can order the select query through 'sort' query parameter.
    Several order criterias can be applied separating them with commas.
    Each criteria can be descending by prefixing it by '-'.
    Criteria can refer to a relationship using the dot notation.
    However, related model must be joined to the query, which can be done automatically
    with join=True. If join=False and referenced related model is not part of from clause
    of the query, a BadRequest is raised.
    The order_by argument allow to specify a default ordering if no order is requested
    in the query.
    """
    sort = request.args.get(arg_name)
    if sort:
        order_by = []
        sort = sort.split(",")
        for path in sort:
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
        return select.order_by(*order_by)
    elif order_by is not None:
        if isinstance(order_by, list) or isinstance(order_by, tuple):
            return select.order_by(*order_by)
        else:
            return select.order_by(order_by)
    return select
