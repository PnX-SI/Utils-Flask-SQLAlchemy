from tempfile import NamedTemporaryFile

import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class MyModel(db.Model):
    pk = db.Column(db.Integer, primary_key=True)
    instance = db.Column(db.Integer)


@pytest.fixture(scope="session")
def _app():
    app = Flask(__name__)
    sqlite = NamedTemporaryFile()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite.name}"
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield


@pytest.fixture(scope="session")
def _session(_app):
    return db.session


@pytest.fixture(scope="session")
def app(_app, _session):
    pass


@pytest.fixture(
    scope="session",
)
def fixture_session(app):
    o = MyModel(pk=1)
    with db.session.begin_nested():
        db.session.add(o)


@pytest.fixture(scope="class")
def fixture_class1(app):
    o = MyModel(pk=2, instance=1)
    with db.session.begin_nested():
        db.session.add(o)


@pytest.fixture(scope="class")
def fixture_class2(app):
    # should not conflict with fixture_class1 if correctly rollback
    o = MyModel(pk=2, instance=2)
    with db.session.begin_nested():
        db.session.add(o)


@pytest.fixture(scope="function")
def fixture_function1(app):
    o = MyModel(pk=3)
    db.session.add(o)
    db.session.commit()


@pytest.fixture(scope="function")
def fixture_function2(app):
    # should not conflict with fixture_function1 if correctly rollback
    o = MyModel(pk=3)
    db.session.add(o)
    db.session.commit()


class TestTemporaryTransaction:
    def test_temporary_transactions(
        self,
        app,
        temporary_session_transaction,
        temporary_package_transaction,
        temporary_module_transaction,
        temporary_class_transaction,
        temporary_function_transaction,
    ):
        transaction = db.session.begin_nested()
        transaction = transaction.parent  # inner function-scoped transaction
        transaction = transaction.parent  # outer function-scoped transaction
        assert transaction == temporary_function_transaction
        transaction = transaction.parent  # class-scoped transaction
        assert transaction == temporary_class_transaction
        transaction = transaction.parent  # module-scoped transaction
        assert transaction == temporary_module_transaction
        # Here, _session is defined in this module, which guarentees that module-scoped
        # temporary transaction will be created. But package-scoped and session-scoped
        # transaction fixtures may be initialized from another module, where _session
        # does not exists. If so, these fixtures will be null. But you are not likely
        # to use package-scoped fixture using the database if the session is defined
        # at module level…
        # transaction = transaction.parent  # package-scoped transaction
        # assert transaction == temporary_package_transaction
        # transaction = transaction.parent  # session-scoped transaction
        # assert transaction == temporary_session_transaction


@pytest.mark.usefixtures("temporary_transaction")  # to test retro-compat
class TestClassOne:
    def test_c1_f1(self, app, fixture_session, fixture_class1, fixture_function1):
        pass

    def test_c1_f2(self, app, fixture_session, fixture_class1, fixture_function2):
        pass


class TestClassTwo:
    def test_c2_f1(self, app, fixture_session, fixture_class2, fixture_function1):
        pass

    def test_c2_f2(self, app, fixture_session, fixture_class2, fixture_function2):
        pass
