from .sqlalchemy import CustomSelect
from flask_sqlalchemy.model import Model


class SelectModelMixin(Model):
    __abstract__ = True

    @classmethod
    @property
    def select(cls):
        if hasattr(cls, "__select_class__"):
            select_cls = cls.__select_class__
        else:
            select_cls = CustomSelect
        return select_cls._create_future_select(cls)  # SQLA 2.0: _create_future_select → _create