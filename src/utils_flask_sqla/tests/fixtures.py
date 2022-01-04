import pytest
from sqlalchemy.event import listen, remove


@pytest.fixture(scope="function")
def temporary_transaction(_session):
    """
    We start two nested transaction (SAVEPOINT):
        - The outer one will be used to rollback all changes made by the current test function.
        - The inner one will be used to catch all commit() / rollback() made in tested code.
          After starting the inner transaction, we install a listener on transaction end events,
          and each time the inner transaction is closed, we restart a new transaction to catch
          potential new commit() / rollback().
    Note: When we rollback the inner transaction at the end of the test, we actually rollback
    only the last inner transaction but previous inner transaction may have been committed by the
    tested code! This is why we need an outer transaction to rollback all changes made by the test.
    """
    outer_transaction = _session.begin_nested()
    inner_transaction = _session.begin_nested()

    def restart_savepoint(session, transaction):
        nonlocal inner_transaction
        if transaction == inner_transaction:
            session.expire_all()
            inner_transaction = session.begin_nested()

    listen(_session, "after_transaction_end", restart_savepoint)

    yield

    remove(_session, "after_transaction_end", restart_savepoint)

    inner_transaction.rollback()  # probably rollback not so much
    outer_transaction.rollback()  # rollback all changes made during this test
