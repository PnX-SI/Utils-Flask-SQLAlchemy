import pytest
from flask import Flask
from sqlalchemy import func

from utils_flask_sqla.sqlalchemy import CustomSQLAlchemy, CustomSelect
from utils_flask_sqla.models import SelectModel


db = CustomSQLAlchemy(model_class=SelectModel)


class FooModel(db.Model):
    pk = db.Column(db.Integer, primary_key=True)


class BarSelect(CustomSelect):
    inherit_cache = True

    def where_pk(self, pk):
        return self.where(BarModel.pk == pk)


class BarModel(db.Model):
    __select_class__ = BarSelect

    pk = db.Column(db.Integer, primary_key=True)


@pytest.fixture(scope="session")
def app():
    app = Flask("utils-flask-sqla")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///"
    app.config["SQLALCHEMY_ECHO"] = True
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture(scope="session")
def foo(app):
    foo = FooModel()
    db.session.add(foo)
    db.session.commit()
    return foo


@pytest.fixture(scope="session")
def bar(app):
    bar = BarModel()
    db.session.add(bar)
    db.session.commit()
    return bar


class TestCustomSelect:
    def test_select_where_if(self, foo):
        # Filter does not apply, we get foo
        assert (
            foo
            in db.session.scalars(db.select(FooModel).where_if(False, FooModel.pk != foo.pk)).all()
        )
        # Filter apply, we does not get foo
        assert (
            foo
            not in db.session.scalars(
                db.select(FooModel).where_if(True, FooModel.pk != foo.pk)
            ).all()
        )

    def test_model_where_if(self, foo):
        # Filter does not apply, we get foo
        assert (
            foo in db.session.scalars(FooModel.select.where_if(False, FooModel.pk != foo.pk)).all()
        )
        # Filter apply, we does not get foo
        assert (
            foo
            not in db.session.scalars(FooModel.select.where_if(True, FooModel.pk != foo.pk)).all()
        )

    def test_model_select_class(self, bar):
        assert db.session.scalars(BarModel.select.where_pk(bar.pk)).one_or_none() is bar
        assert db.session.scalars(BarModel.select.where_pk(bar.pk + 1)).one_or_none() is not bar

    def test_chain_custom_where(self, bar):
        assert (
            db.session.scalars(BarModel.select.where_pk(bar.pk).where_pk(bar.pk)).one_or_none()
            is bar
        )
