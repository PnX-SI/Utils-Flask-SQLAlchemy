from sqlalchemy.sql.expression import BooleanClauseList, BinaryExpression
from flask_sqlalchemy.model import DefaultMeta
from sqlalchemy.sql import select, Select


def qfilter(*args_dec, **kwargs_dec):
    """
    This decorator allows you to constrain a SQLAlchemy model method to return a whereclause (by default) or a query. If
    its `query` is set to True and no query is given in a `query` parameter, it will create one with a simple select: `select(model)`. The latter
    is accessible through `kwargs.get("query")` in the decorated method.

    The decorated query requires the following minimum parameters (cls,**kwargs).

    >>> from utils_flask_sqla.models import qfilter
    >>> from sqlalchemy.sql import select
    >>> class Station(NomenclaturesMixin, db.Model):
            __tablename__ = "t_stations"
            __table_args__ = {"schema": "pr_occhab"}
            # If you wish the method to return a whereclause
            @qfilter
            def filter_by_params(cls,**kwargs):
                filters = []
                if "id_station" in kwargs:
                    filters.append(Station.id_station == kwargs["id_station"])
                return query.whereclause
            # If you wish the method to return a query
            @qfilter(query=True)
            def filter_by_paramsQ(cls,**kwargs):
                query = kwargs("query") #  select(Station)
                if "id_station" in kwargs:
                    query = query.filter_by(id_station=kwargs["id_station"])
                return query

    >>> query = Station.filter_by_paramsQ(id_station=1)
    >>> query2 = select(Station).where(Station.filter_by_params(id_station=1))

    Parameters
    ----------
    query : bool
        decorated function must (or not) return a query (Select)

    Returns
    -------
    function
        decorated method

    Raises
    ------
    ValueError
        Method's class is not DefaultMeta class
    ValueError
        if query is True and return value of the decorated method is not Select
    ValueError
        if query is False and return value of the decorated method is not a : `bool` or sqlalchemy.sql.expression.BooleanClauseList` or `sqlalchemy.sql.expression.BinaryExpression`

    """
    if len(args_dec) == 1 and len(kwargs_dec) == 0 and callable(args_dec[0]):
        return _qfilter()(args_dec[0])
    else:
        return _qfilter(*args_dec, **kwargs_dec)


def _qfilter(*args_dec, **kwargs_dec):
    is_query = kwargs_dec.get("query", False)

    def _qfilter_decorator(method):
        def _(*args, **kwargs):
            # verify if class of the method is ORM model
            sqla_class = args[0]
            if not isinstance(sqla_class, DefaultMeta):
                raise ValueError(
                    "The decorated method's class must inherit from flask_sqlalchemy.model.DefaultMeta"
                )

            query = kwargs.get("query", None)

            # if no query given
            if query == None:
                query = select(sqla_class)
                kwargs["query"] = query
            result = method(*args, **kwargs)

            if is_query and not isinstance(result, Select):
                raise ValueError("Your method must return a SQLAlchemy Select object ")

            authorise_whereclause_type = [bool, BooleanClauseList, BinaryExpression]
            if not is_query and not any(
                [isinstance(result, type_) for type_ in authorise_whereclause_type]
            ):
                raise ValueError(
                    "Your method must return an object in the following types: {} ".format(
                        ", ".join(map(lambda cls: cls.__name__, authorise_whereclause_type))
                    )
                )
            # if filter is wanted as where clause
            return result

        return classmethod(_)

    return _qfilter_decorator
