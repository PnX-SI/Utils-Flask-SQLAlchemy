import json

from flask import testing
from werkzeug.datastructures import Headers


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
        if "Content-Type" not in headers and "data" in kwargs:
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
