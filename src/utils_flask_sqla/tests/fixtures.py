import pytest
from sqlalchemy.event import listen, remove


"""
We open a nested transaction at each scope, and this nested transaction is rollback at teardown,
removing all db changes introduced by fixtures at this level.

Changes made by fixtures should be commited to be visible by testing function, but a commit will
close the nested transaction created for rollback. DO NOT USE db.session.commit() INSIDE FIXTURES!
Instead, in your fixtures, create a dedicated nested transaction:
    with db.session.begin_nested():
        # do changes to database
    # there, changes are visible, and the parent transation remain open

At function scope level, and only at function scope level, we have a mechanism to detect calls to
commit() and automatically restart a nested transaction, allowing to keep an outer transaction
always open until the end of the test, where then all changes are rollback.
This mechanism is in place at function scope level in order to handle commit() in tested code. But
it is not available at other scopes, so, as stated before, do not use commit() in your fixtures
(including function scoped fixtures in order to avoid mistakes, although it may work
theoretically).

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

    # Ensure an empty session cache before each test
    # This is particularly important to test raiseload loading strategy.
    _session.expire_all()

    outer_transaction = _session.begin_nested()
    inner_transaction = _session.begin_nested()

    def restart_savepoint(session, transaction):
        nonlocal inner_transaction
        if transaction == inner_transaction:
            session.expire_all()
            inner_transaction = session.begin_nested()

    listen(_session, "after_transaction_end", restart_savepoint)

    yield outer_transaction

    remove(_session, "after_transaction_end", restart_savepoint)

    inner_transaction.rollback()  # probably rollback not so much
    outer_transaction.rollback()  # rollback all changes made during this test


# retro-compatibility, should be deleted
@pytest.fixture
def temporary_transaction():
    yield
