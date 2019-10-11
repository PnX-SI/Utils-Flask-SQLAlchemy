import json
import csv
import io
from functools import wraps

from flask import Response
from werkzeug.datastructures import Headers


def json_resp(fn):
    """
    Décorateur transformant le résultat renvoyé par une vue
    en objet JSON
    """

    @wraps(fn)
    def _json_resp(*args, **kwargs):
        res = fn(*args, **kwargs)
        if isinstance(res, tuple):
            return to_json_resp(*res)
        else:
            return to_json_resp(res)

    return _json_resp


def to_json_resp(
    res, status=200, filename=None, as_file=False, indent=None, extension="json"
):
    if not res:
        status = 404
        res = {"message": "not found"}

    headers = None
    if as_file:
        headers = Headers()
        headers.add("Content-Type", "application/json")
        headers.add(
            "Content-Disposition",
            "attachment",
            filename="export_{}.{}".format(filename, extension),
        )
    return Response(
        json.dumps(res, ensure_ascii=False, indent=indent),
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
