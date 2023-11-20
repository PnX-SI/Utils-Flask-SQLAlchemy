import os
import os.path
import logging
from contextlib import ExitStack
from tempfile import TemporaryDirectory
from shutil import copyfileobj
from urllib.request import urlopen
import uuid
import collections


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


def dict_merge(dct, merge_dct):
    """Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None
    """
    for k, v in merge_dct.items():
        if (
            k in dct
            and isinstance(dct[k], dict)
            and isinstance(merge_dct[k], collections.abc.Mapping)
        ):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


def is_uuid(uuid_string):
    try:
        # Si uuid_string est un code hex valide mais pas un uuid valid,
        # UUID() va quand même le convertir en uuid valide. Pour se prémunir
        # de ce problème, on check la version original (sans les tirets) avec
        # le code hex généré qui doivent être les mêmes.
        uid = uuid.UUID(uuid_string)
        return uid.hex == uuid_string.replace("-", "")
    except ValueError:
        return False
