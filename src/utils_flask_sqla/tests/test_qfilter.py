import pytest
from flask import Flask
from sqlalchemy import func, and_, select

from flask_sqlalchemy import SQLAlchemy

from utils_flask_sqla.models import qfilter


db = SQLAlchemy()


class FooModel(db.Model):
    pk = db.Column(db.Integer, primary_key=True)


class BarModel(db.Model):
    pk = db.Column(db.Integer, primary_key=True)

    @qfilter
    def where_pk(cls, pk, **kwargs):
        return BarModel.pk == pk

    @qfilter(query=True)
    def where_pk_query(cls, pk, **kwargs):
        query = kwargs["query"]
        return query.where(BarModel.pk == pk)

    @qfilter
    def where_pk_list(cls, pk, **kwargs):
        return BarModel.pk == pk


@pytest.fixture(scope="session")
def app():
    app = Flask("utils-flask-sqla")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///"
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


class TestQfilter:
    def test_qfilter(self, bar):
        assert db.session.scalars(BarModel.where_pk_query(bar.pk)).one_or_none() is bar
        assert (
            db.session.scalars(select(BarModel).where(BarModel.where_pk(bar.pk))).one_or_none()
            is bar
        )

        assert db.session.scalars(BarModel.where_pk_query(bar.pk + 1)).one_or_none() is not bar
        assert (
            db.session.scalars(select(BarModel).where(BarModel.where_pk(bar.pk + 1))).one_or_none()
            is not bar
        )

        assert (
            db.session.scalars(
                select(BarModel).where(BarModel.where_pk_list(bar.pk))
            ).one_or_none()
            is bar
        )
