import csv
import io
import json
from functools import wraps

from flask import Response
from flask.json import JSONEncoder
from werkzeug.datastructures import Headers

def json_resp_accept(accepted_list=[]):
    def json_resp(fn):
        """
        Décorateur transformant le résultat renvoyé par une vue
        en objet JSON
        """

        @wraps(fn)
        def _json_resp(*args, **kwargs):
            res = fn(*args, **kwargs)
            if isinstance(res, tuple):
                return to_json_resp(*res, accepted_list=accepted_list)
            else:
                return to_json_resp(res, accepted_list=accepted_list)

        return _json_resp

    return json_resp


json_resp = json_resp_accept()
json_resp_accept_empty_list = json_resp_accept([[]])




def to_json_resp(
    res,
    status=200,
    filename=None,
    as_file=False,
    indent=None,
    extension="json",
    accepted_list=[],
):
    if res is None:
        return ('', 204)

    headers = None
    if as_file:
        headers = Headers()
        headers.add("Content-Type", "application/json")
        headers.add(
            "Content-Disposition",
            "attachment",
            filename="export_{}.{}".format(filename, extension),
        )
    # use Flask JSONEncoder for raw sql query
    return Response(
        json.dumps(
            res, ensure_ascii=False, indent=indent, cls=JSONEncoder
        ),
        status=status,
        mimetype="application/json",
        headers=headers,
    )


def csv_resp(fn):
    """
    Décorateur transformant le résultat renvoyé en un fichier csv
    """

    @wraps(fn)
    def _csv_resp(*args, **kwargs):
        res = fn(*args, **kwargs)
        filename, data, columns, separator = res
        return to_csv_resp(filename, data, columns, separator)

    return _csv_resp


def to_csv_resp(filename, data, columns, separator=";"):

    headers = Headers()
    headers.add("Content-Type", "text/plain")
    headers.add(
        "Content-Disposition", "attachment", filename="export_%s.csv" % filename
    )
    out = generate_csv_content(columns, data, separator)
    return Response(out, headers=headers)


def generate_csv_content(columns, data, separator):
    fp = io.StringIO()
    writer = csv.DictWriter(
        fp, columns, delimiter=separator, quoting=csv.QUOTE_ALL, extrasaction="ignore"
    )
    writer.writeheader()  # ligne d'entête

    for line in data:
        writer.writerow(line)
    fp.seek(0)  # Rembobinage du "fichier"
    return fp.read()  # Retourne une chaine
