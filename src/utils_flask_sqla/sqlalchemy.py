from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.expression import Select


class CustomSelect(Select):
    inherit_cache = True

    def where_if(self, condition_to_execute_where, whereclause):
        if condition_to_execute_where:
            return self.where(whereclause)
        else:
            return self


class CustomSQLAlchemy(SQLAlchemy):
    @staticmethod
    def select(*entities):
        return CustomSelect._create_future_select(*entities)
