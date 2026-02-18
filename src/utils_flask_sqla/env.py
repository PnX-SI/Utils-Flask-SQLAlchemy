from os import environ
from importlib import import_module

db_path = environ.get("FLASK_SQLALCHEMY_DB")
if not db_path:
    raise Exception("FLASK_SQLALCHEMY_DB env var is missing")
db_module_name, db_object_name = db_path.rsplit(".", 1)
db_module = import_module(db_module_name)
db = getattr(db_module, db_object_name)
