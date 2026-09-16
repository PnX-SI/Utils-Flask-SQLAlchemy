from flask_sqlalchemy import SQLAlchemy
from utils_flask_sqla.pagination import AugmentedSelectedPagination


class AugmentedSQLAlchemy(SQLAlchemy):

    def paginate(
        self,
        select,
        *,
        page=None,
        per_page=None,
        max_per_page=None,
        error_out=True,
        count=True,
        scalars=False,
        unique=False,
    ):
        return AugmentedSelectedPagination(
            select=select,
            session=self.session(),
            page=page,
            per_page=per_page,
            max_per_page=max_per_page,
            error_out=error_out,
            count=count,
            scalars=scalars,
            unique=unique,
        )
