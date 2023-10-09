import pytest
import os.path
from tempfile import NamedTemporaryFile
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class MyModel(db.Model):
    pk = db.Column(db.Integer, primary_key=True)


@pytest.fixture(scope="session")
def _app():
    app = Flask(__name__)
    sqlite = NamedTemporaryFile()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite.name}"
    db.init_app(app)
    app.push_context()
    db.create_all()
    return app


@pytest.fixture(scope="session")
def _session(_app):
    return db.session


@pytest.fixture(scope="session", autouse=True)
def app(_app, _session, temporary_session_transaction):
    return _app


@pytest.fixture(scope="session")
def fixture_session():
    o = MyModel(pk=1)
    db.session.add(o)
    db.session.commit()


@pytest.fixture(scope="class")
def fixture_class():
    o = MyModel(pk=2)
    db.session.add(o)
    db.session.commit()


@pytest.fixture(scope="function")
def fixture_function():
    o = MyModel(pk=3)
    db.session.add(o)
    db.session.commit()


class TestClassOne:
    def test_c1_f1(self, fixture_session, fixture_class, fixture_function):
        pass

    def test_c1_f2(self, fixture_session, fixture_class, fixture_function):
        pass


class TestClassTwo:
    def test_c2_f1(self, fixture_session, fixture_class, fixture_function):
        pass

    def test_c2_f2(self, fixture_session, fixture_class, fixture_function):
        pass
