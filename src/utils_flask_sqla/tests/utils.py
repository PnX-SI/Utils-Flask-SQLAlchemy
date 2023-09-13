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
        if "content_type" not in kwargs and "Content-Type" not in headers and "data" in kwargs:
            kwargs["data"] = json.dumps(kwargs["data"])
            headers.extend(
                Headers(
                    {
                        "Content-Type": "application/json",
                    }
                )
            )
        # the set_logged_user_jwt add a jwt attribute to client with the current logged user
        jwt = getattr(self, "jwt", None)
        if jwt:
            jwt_headers = Headers({"Authorization": f"Bearer {jwt}"})
            headers.extend(jwt_headers)

        kwargs["headers"] = headers
        return super().open(*args, **kwargs)
