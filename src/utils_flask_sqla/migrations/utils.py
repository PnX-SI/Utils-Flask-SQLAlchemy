from alembic import context
import logging
from contextlib import ExitStack
from tempfile import TemporaryDirectory
from shutil import copyfileobj
from urllib.request import urlopen
import lzma
import os, os.path

from ..utils import remote_file


logger = logging.getLogger("alembic.runtime.migration")

"""
Ce contextmanager permet d’ouvrir un fichier après l’avoir préalablement téléchargé.
Le fichier peut être compréssé et gérer en tant que tel pour les types suivants:
  - xz
dans les autres cas le fichier est ouvert comme un fichier normal
Le fichier téléchargé est enregistré dans le dossier spécifié par -x data-directory=…
Si aucun dossier n’est spécifié, un dossier temporaire, supprimé à la fin de la migration, est utilisé.
"""


class open_remote_file(remote_file):
    def __init__(self, base_url, filename, open_fct=lzma.open, data_dir=None):
        if data_dir is None:
            try:
                data_dir = context.get_x_argument(as_dictionary=True).get("data-directory")
            except NameError:  # not used in alembic migration
                pass
        url = "{}{}".format(base_url, filename)
        super().__init__(url=url, filename=filename, data_dir=data_dir, logger=logger)
        self.open_fct = open_fct

    def __enter__(self):
        remote_file_path = super().__enter__()
        return self.enter_context(self.open_fct(remote_file_path))
