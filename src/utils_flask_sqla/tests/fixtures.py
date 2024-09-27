import pytest
from sqlalchemy.event import listen, remove


def _temporary_transaction(request):
    if "_session" not in request.fixturenames:
        yield
        return

    _session = request.getfixturevalue("_session")

    outer_transaction = _session.begin_nested()
    inner_transaction = _session.begin_nested()

    def restart_savepoint(session, transaction):
        nonlocal inner_transaction
        if (
            transaction == inner_transaction
            and request.fixturename != "temporary_session_transaction"
        ):
            session.expire_all()
            inner_transaction = session.begin_nested()

    listen(_session, "after_transaction_end", restart_savepoint)

    yield

    remove(_session, "after_transaction_end", restart_savepoint)

    inner_transaction.rollback()  # probably rollback not so much
    outer_transaction.rollback()  # rollback all changes made during this scope


@pytest.fixture(scope="session", autouse=True)
def temporary_session_transaction(request):
    yield from _temporary_transaction(request)


@pytest.fixture(scope="package", autouse=True)
def temporary_package_transaction(request):
    yield from _temporary_transaction(request)


@pytest.fixture(scope="module", autouse=True)
def temporary_module_transaction(request):
    yield from _temporary_transaction(request)


@pytest.fixture(scope="class", autouse=True)
def temporary_class_transaction(request):
    yield from _temporary_transaction(request)


@pytest.fixture(scope="function", autouse=True)
def temporary_function_transaction(request):
    yield from _temporary_transaction(request)


# Retro-compatibility
@pytest.fixture(scope="function")
def temporary_transaction(temporary_function_transaction):
    pass
