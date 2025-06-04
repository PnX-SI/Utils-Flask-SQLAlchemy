from flask_sqlalchemy.pagination import SelectPagination


class AugmentedSelectedPagination(SelectPagination):

    def __init__(
        self, page=None, per_page=None, max_per_page=100, error_out=True, count=True, **kwargs
    ):
        self.scalars = kwargs.get("scalars", False)
        super().__init__(page, per_page, max_per_page, error_out, count, **kwargs)

    def _query_items(self):
        select = self._query_args["select"]
        select = select.limit(self.per_page).offset(self._query_offset)
        session = self._query_args["session"]
        if self.scalars:
            return list(session.execute(select).unique().scalars())
        return list(session.execute(select))
