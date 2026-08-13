import pytest

"""
We open a nested transaction at each scope, and this nested transaction is rollback at teardown,
removing all db changes introduced by fixtures at this level.

Changes made by fixtures should be commited to be visible by testing function, but a commit will
close the nested transaction created for rollback. DO NOT USE db.session.commit() INSIDE FIXTURES!
Instead, in your fixtures, create a dedicated nested transaction:
    with db.session.begin_nested():
        # do changes to database
    # there, changes are visible, and the parent transation remain open

TestSession (see utils.py) is what makes commit()/rollback() in tested code safe: commit() only
flushes instead of ending the current savepoint, and rollback() rolls back to the nearest savepoint
and immediately reopens one, so the outer transaction stays open until the end of the test. Because
of this, this fixture opens an extra, disposable savepoint on top of the one it owns for teardown,
so tested code's commit()/rollback() calls never touch the fixture's own transaction directly. This
protection is only meaningful at function scope, where tested code actually runs, so, as stated
before, do not use commit() in your fixtures (including function scoped fixtures in order to avoid
mistakes, although it may work theoretically).

The temporary transaction fixtures must be called before regular fixtures to be able to rollback
database changes. Decorator @pytest.usefixtures() add fixtures at the end of required fixtures
list, which does not comply with our needs. Instead, temporary transaction fixtures are marked for
autouse, ensuring to be executed before other regular fixtures as stated in pytest doc.

As these fixtures are marked for autouse, they are called even in tests which does not interact
with the database, and worse, in test in which the database is not available. For this reason,
these fixture check that the "_session" fixture is part of the test requested fixtures. It is
therefore necessary that any test interacting with the db requires the "_session" fixture.
"""


@pytest.fixture(scope="session", autouse=True)
def temporary_session_transaction(request):
    try:
        _session = request.getfixturevalue("_session")
    except pytest.FixtureLookupError:
        yield
        return

    transaction = _session.begin_nested()
    yield transaction
    transaction.rollback()


@pytest.fixture(scope="package", autouse=True)
def temporary_package_transaction(request):
    try:
        _session = request.getfixturevalue("_session")
    except pytest.FixtureLookupError:
        yield
        return

    transaction = _session.begin_nested()
    yield transaction
    transaction.rollback()


@pytest.fixture(scope="module", autouse=True)
def temporary_module_transaction(request):
    try:
        _session = request.getfixturevalue("_session")
    except pytest.FixtureLookupError:
        yield
        return

    transaction = _session.begin_nested()
    yield transaction
    transaction.rollback()


@pytest.fixture(scope="class", autouse=True)
def temporary_class_transaction(request):
    try:
        _session = request.getfixturevalue("_session")
    except pytest.FixtureLookupError:
        yield
        return

    transaction = _session.begin_nested()
    yield transaction
    transaction.rollback()


@pytest.fixture(scope="function", autouse=True)
def temporary_function_transaction(request):
    try:
        _session = request.getfixturevalue("_session")
    except pytest.FixtureLookupError:
        yield
        return

    # Ensure an empty session cache before each test
    # This is particularly important to test raiseload loading strategy.
    _session.expire_all()

    outer_transaction = _session.begin_nested()
    _session.begin_nested()  # disposable savepoint consumed by tested code's commit()/rollback()

    yield outer_transaction

    _session().get_nested_transaction().rollback()  # whatever TestSession left active
    outer_transaction.rollback()  # rollback all changes made during this test


# retro-compatibility, should be deleted
@pytest.fixture
def temporary_transaction():
    yield
