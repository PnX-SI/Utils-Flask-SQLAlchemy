from itertools import chain
from warnings import warn

from dateutil import parser
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import Boolean, Date, DateTime, Integer, Numeric
from werkzeug.exceptions import BadRequest

from .errors import UtilsSqlaError


def testDataType(value, sqlType, paramName):
    """
    Test the type of a filter
    #TODO: antipatern: should raise something which can be exect by the function which use it
    # and not return the error
    """
    if sqlType == Integer or isinstance(sqlType, (Integer)):
        try:
            int(value)
        except Exception as e:
            return "{0} must be an integer".format(paramName)
    if sqlType == Numeric or isinstance(sqlType, (Numeric)):
        try:
            float(value)
        except Exception as e:
            return "{0} must be an float (decimal separator .)".format(paramName)
    elif sqlType == DateTime or isinstance(sqlType, (Date, DateTime)):
        try:
            dt = parser.parse(value)
        except Exception as e:
            return "{0} must be an date (yyyy-mm-dd)".format(paramName)
    return None


def test_type_and_generate_query(param_name, value, model, q):
    """
    Generate a query with the filter given, checking the params is the good type of the columns, and formmatting it
    Params:
        - param_name (str): the name of the column
        - value (any): the value of the filter
        - model (SQLA model)
        - q (SQLA Query)
    """
    # check the attribut exist in the model
    try:
        col = getattr(model, param_name)
    except AttributeError as error:
        raise UtilsSqlaError(str(error))
    sql_type = col.type
    if sql_type == Integer or isinstance(sql_type, (Integer)):
        try:
            return q.where(col == int(value))
        except Exception as e:
            raise UtilsSqlaError("{0} must be an integer".format(param_name))
    if sql_type == Numeric or isinstance(sql_type, (Numeric)):
        try:
            return q.where(col == float(value))
        except Exception as e:
            raise UtilsSqlaError("{0} must be an float (decimal separator .)".format(param_name))
    if sql_type == DateTime or isinstance(sql_type, (Date, DateTime)):
        try:
            return q.where(col == parser.parse(value))
        except Exception as e:
            raise UtilsSqlaError("{0} must be an date (yyyy-mm-dd)".format(param_name))

    if sql_type == Boolean or isinstance(sql_type, Boolean):
        try:
            return q.where(col.is_(bool(value)))
        except Exception:
            raise UtilsSqlaError("{0} must be a boolean".format(param_name))


"""
    Liste des types de données sql qui
    nécessite une sérialisation particulière en
    @TODO MANQUE FLOAT
"""
SERIALIZERS = {
    "date": lambda x: str(x) if x else None,
    "datetime": lambda x: str(x) if x else None,
    "time": lambda x: str(x) if x else None,
    "timestamp": lambda x: str(x) if x else None,
    "uuid": lambda x: str(x) if x else None,
    "numeric": lambda x: str(x) if x else None,
}


class GenericTable:
    """
    Classe permettant de créer à la volée un mapping
        d'une vue avec la base de données par rétroingénierie
    """

    def __init__(self, tableName, schemaName, engine):
        """
        params:
            - tableName
            - schemaName
            - engine : sqlalchemy instance engine
                for exemple : DB.engine if DB = Sqlalchemy()
        """
        meta = MetaData(schema=schemaName)
        meta.reflect(views=True, bind=engine)

        try:
            self.tableDef = meta.tables["{}.{}".format(schemaName, tableName)]
        except KeyError:
            raise KeyError("table {}.{} doesn't exists".format(schemaName, tableName))

        # Mise en place d'un mapping des colonnes en vue d'une sérialisation
        self.serialize_columns, self.db_cols = self.get_serialized_columns()

    def get_serialized_columns(self, serializers=SERIALIZERS):
        """
        Return a tuple of serialize_columns, and db_cols
        from the generic table
        """
        regular_serialize = []
        db_cols = []
        for name, db_col in self.tableDef.columns.items():
            if not db_col.type.__class__.__name__ == "Geometry":
                serialize_attr = (
                    name,
                    serializers.get(db_col.type.__class__.__name__.lower(), lambda x: x),
                )
                regular_serialize.append(serialize_attr)

            db_cols.append(db_col)
        return regular_serialize, db_cols

    def as_dict(self, data, columns=[], fields=[]):
        fields = list(chain(fields, columns))
        if columns:
            warn(
                "'columns' argument is deprecated. Please add columns to serialize "
                "directly in 'fields' argument.",
                DeprecationWarning,
            )
        if fields:
            fprops = list(filter(lambda d: d[0] in fields, self.serialize_columns))
        else:
            fprops = self.serialize_columns

        return {item: _serializer(getattr(data, item)) for item, _serializer in fprops}


class GenericQuery:
    """
    Classe permettant de manipuler des objets GenericTable

    params:
        - DB: sqlalchemy instantce (DB if DB = Sqlalchemy())
        - tableName
        - schemaName
        - filters: array of filter of the query
        - engine : sqlalchemy instance engine
            for exemple : DB.engine if DB = Sqlalchemy()
        - limit
        - offset
    """

    def __init__(
        self,
        DB,
        tableName: str,
        schemaName: str,
        filters: list = [],
        limit: int = None,
        offset: int = 0,
    ):
        self.DB = DB
        self.tableName = tableName
        self.schemaName = schemaName
        self.filters = filters
        if limit:
            assert limit > 0
        self.limit = limit
        self.offset = offset
        self.view = GenericTable(tableName, schemaName, DB.engine)

    def build_query_filters(self, query, parameters):
        """
        Construction des filtres
        """
        for f in parameters:
            query = self.build_query_filter(query, f, parameters.get(f))
        return query

    def build_query_filter(self, query, param_name, param_value):
        if param_name in self.view.tableDef.columns.keys():
            query = query.where(self.view.tableDef.columns[param_name] == param_value)

        if param_name.startswith("ilike_"):
            col = self.view.tableDef.columns[param_name[6:]]
            if col.type.__class__.__name__ == "TEXT":
                query = query.where(col.ilike("%{}%".format(param_value)))

        if param_name.startswith("filter_d_"):
            col = self.view.tableDef.columns[param_name[12:]]
            col_type = col.type.__class__.__name__
            test_type = testDataType(param_value, DateTime, col) and testDataType(
                param_value, Integer, col
            )
            if test_type:
                raise UtilsSqlaError(message=test_type)
            if col_type in ("Date", "DateTime", "TIMESTAMP", "INTEGER"):
                if param_name.startswith("filter_d_up_"):
                    query = query.where(col >= param_value)
                if param_name.startswith("filter_d_lo_"):
                    query = query.where(col <= param_value)
                if param_name.startswith("filter_d_eq_"):
                    query = query.where(col == param_value)

        if param_name.startswith("filter_n_"):
            col = self.view.tableDef.columns[param_name[12:]]
            col_type = col.type.__class__.__name__
            test_type = testDataType(param_value, Numeric, col)
            if test_type:
                raise UtilsSqlaError(message=test_type)
            if param_name.startswith("filter_n_up_"):
                query = query.where(col >= param_value)
            if param_name.startswith("filter_n_lo_"):
                query = query.where(col <= param_value)
        return query

    def build_query_order(self, query, parameters):
        # Ordonnancement
        # L'ordonnancement se base actuellement sur une seule colonne
        #   et prend la forme suivante : nom_colonne[:ASC|DESC]
        if parameters.get("orderby", "").replace(" ", ""):
            order_by = parameters.get("orderby")
            col, *sort = order_by.split(":")
            if col in self.view.tableDef.columns.keys():
                ordel_col = getattr(self.view.tableDef.columns, col)
                if (sort[0:1] or ["ASC"])[0].lower() == "desc":
                    ordel_col = ordel_col.desc()
                return query.order_by(ordel_col)
            else:
                raise BadRequest(f"No column name {col} to sort with")
        return query

    def set_limit(self, q):
        return q.limit(self.limit).offset(self.offset * self.limit)

    def raw_query(self, process_filter=True):
        """
        Renvoie la requete 'brute' (sans .all)
        - process_filter: application des filtres (et du sort)
        """

        q = self.DB.session.query(self.view.tableDef)

        if not process_filter:
            return q
        if self.filters:
            unordered_q = self.build_query_filters(q, self.filters)
            q = self.build_query_order(unordered_q, self.filters)

        if self.limit:
            q = self.set_limit(q)

        return q

    def query(self):
        """
        Lance la requete et retourne l'objet sqlalchemy
        """
        q = self.DB.session.query(self.view.tableDef)
        nb_result_without_filter = q.count()

        q = self.raw_query(process_filter=True)
        total_filtered = q.count() if self.filters else nb_result_without_filter

        data = q.all()

        return data, nb_result_without_filter, total_filtered

    def return_query(self):
        """
        Lance la requete (execute self.query())
            et retourne les résutats dans un format standard

        """

        data, nb_result_without_filter, nb_results = self.query()

        results = [self.view.as_dict(d) for d in data]

        return {
            "total": nb_result_without_filter,
            "total_filtered": nb_results,
            "page": self.offset,
            "limit": self.limit,
            "items": results,
        }

    as_dict = return_query


def serializeQuery(data, columnDef):
    rows = [
        {
            c["name"]: getattr(row, c["name"])
            for c in columnDef
            if getattr(row, c["name"]) is not None
        }
        for row in data
    ]
    return rows


def serializeQueryOneResult(row, column_def):
    row = {
        c["name"]: getattr(row, c["name"])
        for c in column_def
        if getattr(row, c["name"]) is not None
    }
    return row


def serializeQueryTest(data, column_def):
    rows = list()
    for row in data:
        inter = {}
        for c in column_def:
            if getattr(row, c["name"]) is not None:
                if isinstance(c["type"], (Date, DateTime, UUID)):
                    inter[c["name"]] = str(getattr(row, c["name"]))
                elif isinstance(c["type"], Numeric):
                    inter[c["name"]] = float(getattr(row, c["name"]))
                # elif not isinstance(c["type"], Geometry):
                # inter[c["name"]] = getattr(row, c["name"])
        rows.append(inter)
    return rows
