import os
import os.path
import logging
from contextlib import ExitStack
from tempfile import TemporaryDirectory
from shutil import copyfileobj
from urllib.request import urlopen
from contextlib import suppress
from sqlalchemy.sql import visitors


class remote_file(ExitStack):
    """
    Ce contextmanager renvoit le chemin d’accès d’un fichier après l’avoir préalablement téléchargé.
    """

    def __init__(self, url, filename, data_dir=None, logger=None):
        super().__init__()
        self.url = url
        self.filename = filename
        self.data_dir = data_dir or os.environ.get("DATA_DIRECTORY")
        self.logger = logger or logging.getLogger(__name__)

    def __enter__(self):
        super().__enter__()
        if not self.data_dir:
            self.data_dir = self.enter_context(TemporaryDirectory())
            self.logger.info("Created temporary directory '{}'".format(self.data_dir))
        if not os.path.exists(self.data_dir):
            os.mkdir(self.data_dir)
        remote_file_path = os.path.join(self.data_dir, self.filename)
        if not os.path.isfile(remote_file_path):
            self.logger.info("Downloading '{}'…".format(self.filename))
            with urlopen(self.url) as response, open(remote_file_path, "wb") as remote_file:
                copyfileobj(response, remote_file)
        return remote_file_path


def is_already_joined(my_class, query):
    """
    Check if the given class is already present is the current query
    _class: SQLAlchemy class
    query: SQLAlchemy query
    return boolean
    """
    for visitor in visitors.iterate(query):
        # Checking for `.join(Parent.child)` clauses
        if visitor.__visit_name__ == "binary":
            for vis in visitors.iterate(visitor):
                # Visitor might not have table attribute
                with suppress(AttributeError):
                    # Verify if already present based on table name
                    if my_class.__table__.fullname == vis.table.fullname:
                        return True
        # Checking for `.join(Child)` clauses
        if visitor.__visit_name__ == "table":
            # Visitor might be of ColumnCollection or so,
            # which cannot be compared to model
            with suppress(TypeError):
                if my_class == visitor.entity_namespace:
                    return True
        # Checking for `Model.column` clauses
        if visitor.__visit_name__ == "column":
            with suppress(AttributeError):
                if my_class.__table__.fullname == visitor.table.fullname:
                    return True
    return False
