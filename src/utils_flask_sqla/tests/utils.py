import json
from flask import testing
from werkzeug.datastructures import Headers
from flask_sqlalchemy.session import Session


class TestSession(Session):
    __test__ = False
    join_transaction_mode = "create_savepoint"
    expire_on_commit = False

    def commit(self):
        if self.in_nested_transaction():
            self.flush()
        else:
            super().commit()

    def rollback(self):
        # Session.rollback() always rolls back to the topmost transaction,
        # discarding every savepoint in progress (see SQLAlchemy docs). That
        # would wipe out data committed by session/package/module/class-scoped
        # fixtures for real. Roll back only to the nearest savepoint instead,
        # so application code calling db.session.rollback() on error doesn't
        # tear down the test isolation transactions. Immediately reopen a
        # savepoint afterwards, so the isolation boundary above stays alive
        # no matter how many times application code calls rollback().
        if self.in_nested_transaction():
            self.get_nested_transaction().rollback()
            self.expire_all()
            self.begin_nested()
        else:
            super().rollback()


class JSONClient(testing.FlaskClient):
    def open(self, *args, **kwargs):
        headers = kwargs.pop("headers", Headers())
        if "Accept" not in headers:
            headers.extend(
                Headers(
                    {
                        "Accept": "application/json, text/plain, */*",
                    }
                )
            )
        if "content_type" not in kwargs and "Content-Type" not in headers and "data" in kwargs:
            kwargs["data"] = json.dumps(kwargs["data"])
            headers.extend(
                Headers(
                    {
                        "Content-Type": "application/json",
                    }
                )
            )
        kwargs["headers"] = headers
        return super().open(*args, **kwargs)
