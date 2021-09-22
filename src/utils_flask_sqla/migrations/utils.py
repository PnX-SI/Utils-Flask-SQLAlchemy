from alembic import context
import logging
from contextlib import ExitStack
from tempfile import TemporaryDirectory
from shutil import copyfileobj
from urllib.request import urlopen
import lzma
import os, os.path

logger = logging.getLogger('alembic.runtime.migration')

"""
Ce contextmanager permet d’ouvrir un fichier après l’avoir préalablement téléchargé.
Le fichier peut être compréssé et gérer en tant que tel pour les types suivants:
  - xz
dans les autres cas le fichier est ouvert comme un fichier normal
Le fichier téléchargé est enregistré dans le dossier spécifié par -x data-directory=…
Si aucun dossier n’est spécifié, un dossier temporaire, supprimé à la fin de la migration, est utilisé.
"""
class open_remote_file(ExitStack):
    def __init__(self, base_url, filename, open_fct=lzma.open):
        super().__init__()
        self.base_url = base_url
        self.filename = filename
        self.open_fct = open_fct
        self.data_dir = context.get_x_argument(as_dictionary=True).get('data-directory')

    def __enter__(self):
        stack = super().__enter__()
        if not self.data_dir:
            self.data_dir = stack.enter_context(TemporaryDirectory())
            logger.info("Created temporary directory '{}'".format(self.data_dir))
        if not os.path.exists(self.data_dir):
            os.mkdir(self.data_dir)
        remote_file_path = os.path.join(self.data_dir, self.filename)
        if not os.path.isfile(remote_file_path):
            logger.info("Downloading '{}'…".format(self.filename))
            with urlopen('{}{}'.format(self.base_url, self.filename)) as response, \
                                              open(remote_file_path, 'wb') as remote_file:
                copyfileobj(response, remote_file)
        return stack.enter_context(self.open_fct(remote_file_path))
