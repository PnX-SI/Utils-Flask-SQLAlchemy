from sqlalchemy import MetaData
from flask_sqlalchemy import SQLAlchemy
DB = SQLAlchemy()

def testDataType(value, sqlType, paramName):
    """
        Test the type of a filter
        #TODO: antipatern: should raise something which can be exect by the function which use it
        # and not return the error
    """
    if sqlType == DB.Integer or isinstance(sqlType, (DB.Integer)):
        try:
            int(value)
        except Exception as e:
            return "{0} must be an integer".format(paramName)
    if sqlType == DB.Numeric or isinstance(sqlType, (DB.Numeric)):
        try:
            float(value)
        except Exception as e:
            return "{0} must be an float (decimal separator .)".format(paramName)
    elif sqlType == DB.DateTime or isinstance(sqlType, (DB.Date, DB.DateTime)):
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
        raise GeonatureApiError(str(error))
    sql_type = col.type
    if sql_type == DB.Integer or isinstance(sql_type, (DB.Integer)):
        try:
            return q.filter(col == int(value))
        except Exception as e:
            raise GeonatureApiError("{0} must be an integer".format(param_name))
    if sql_type == DB.Numeric or isinstance(sql_type, (DB.Numeric)):
        try:
            return q.filter(col == float(value))
        except Exception as e:
            raise GeonatureApiError(
                "{0} must be an float (decimal separator .)".format(param_name)
            )
    if sql_type == DB.DateTime or isinstance(sql_type, (DB.Date, DB.DateTime)):
        try:
            return q.filter(col == parser.parse(value))
        except Exception as e:
            raise GeonatureApiError(
                "{0} must be an date (yyyy-mm-dd)".format(param_name)
            )

    if sql_type == DB.Boolean or isinstance(sql_type, DB.Boolean):
        try:
            return q.filter(col.is_(bool(value)))
        except Exception:
            raise GeonatureApiError("{0} must be a boolean".format(param_name))


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

    def __init__(self, tableName, schemaName):
        meta = MetaData(schema=schemaName, bind=DB.engine)
        meta.reflect(views=True)

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
                    serializers.get(
                        db_col.type.__class__.__name__.lower(), lambda x: x
                    ),
                )
                regular_serialize.append(serialize_attr)

            db_cols.append(db_col)
        return regular_serialize, db_cols

    def as_dict(self, data, columns=None):
        if columns:
            fprops = list(filter(lambda d: d[0] in columns, self.serialize_columns))
        else:
            fprops = self.serialize_columns

        return {item: _serializer(getattr(data, item)) for item, _serializer in fprops}


class GenericQuery:
    """
        Classe permettant de manipuler des objets GenericTable
    """

    def __init__(
        self,
        db_session,
        tableName,
        schemaName,
        filters,
        limit=100,
        offset=0,
    ):
        self.db_session = db_session
        self.tableName = tableName
        self.schemaName = schemaName
        self.filters = filters
        self.limit = limit
        self.offset = offset
        self.view = GenericTable(tableName, schemaName)

    def build_query_filters(self, query, parameters):
        """
            Construction des filtres
        """
        for f in parameters:
            query = self.build_query_filter(query, f, parameters.get(f))

        return query

    def build_query_filter(self, query, param_name, param_value):
        if param_name in self.view.tableDef.columns.keys():
            query = query.filter(self.view.tableDef.columns[param_name] == param_value)

        if param_name.startswith("ilike_"):
            col = self.view.tableDef.columns[param_name[6:]]
            if col.type.__class__.__name__ == "TEXT":
                query = query.filter(col.ilike("%{}%".format(param_value)))

        if param_name.startswith("filter_d_"):
            col = self.view.tableDef.columns[param_name[12:]]
            col_type = col.type.__class__.__name__
            test_type = testDataType(param_value, DB.DateTime, col)
            if test_type:
                raise GeonatureApiError(message=test_type)
            if col_type in ("Date", "DateTime", "TIMESTAMP"):
                if param_name.startswith("filter_d_up_"):
                    query = query.filter(col >= param_value)
                if param_name.startswith("filter_d_lo_"):
                    query = query.filter(col <= param_value)
                if param_name.startswith("filter_d_eq_"):
                    query = query.filter(col == param_value)

        if param_name.startswith("filter_n_"):
            col = self.view.tableDef.columns[param_name[12:]]
            col_type = col.type.__class__.__name__
            test_type = testDataType(param_value, DB.Numeric, col)
            if test_type:
                raise GeonatureApiError(message=test_type)
            if param_name.startswith("filter_n_up_"):
                query = query.filter(col >= param_value)
            if param_name.startswith("filter_n_lo_"):
                query = query.filter(col <= param_value)
        return query

    def build_query_order(self, query, parameters):
        # Ordonnancement
        if "orderby" in parameters:
            if parameters.get("orderby") in self.view.columns:
                ordel_col = getattr(self.view.tableDef.columns, parameters["orderby"])
        else:
            return query

        if "order" in parameters:
            if parameters["order"] == "desc":
                ordel_col = ordel_col.desc()
                return query.order_by(ordel_col)
        else:
            return query

        return query

    def query(self):
        """
            Lance la requete et retourne l'objet sqlalchemy
        """
        q = self.db_session.query(self.view.tableDef)
        nb_result_without_filter = q.count()

        if self.filters:
            q = self.build_query_filters(q, self.filters)
            q = self.build_query_order(q, self.filters)

        # Si la limite spécifiée est égale à -1
        # les paramètres limit et offset ne sont pas pris en compte
        if self.limit == -1:
            data = q.all()
        else:
            data = q.limit(self.limit).offset(self.offset * self.limit).all()
        nb_results = q.count()

        return data, nb_result_without_filter, nb_results

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
                if isinstance(c["type"], (DB.Date, DB.DateTime, UUID)):
                    inter[c["name"]] = str(getattr(row, c["name"]))
                elif isinstance(c["type"], DB.Numeric):
                    inter[c["name"]] = float(getattr(row, c["name"]))
                elif not isinstance(c["type"], Geometry):
                    inter[c["name"]] = getattr(row, c["name"])
        rows.append(inter)
    return rows
