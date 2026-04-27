import json
from flask import testing
from werkzeug.datastructures import Headers
from flask_sqlalchemy.session import Session


class TestSession(Session):
    join_transaction_mode = "create_savepoint"
    expire_on_commit = False

    def commit(self):
        if self.in_nested_transaction():
            self.flush()
        else:
            super().commit()


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
