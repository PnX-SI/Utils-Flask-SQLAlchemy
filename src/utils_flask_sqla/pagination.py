from flask_sqlalchemy.pagination import SelectPagination


class AugmentedSelectedPagination(SelectPagination):

    def _query_items(self):
        select = self._query_args["select"]
        select = select.limit(self.per_page).offset(self._query_offset)
        session = self._query_args["session"]
        if len(select.column_descriptions) < 2:
            return list(session.execute(select).unique().scalars())
        return list(session.execute(select))
