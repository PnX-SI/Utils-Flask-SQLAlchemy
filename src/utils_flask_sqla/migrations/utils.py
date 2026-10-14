from alembic import context
import logging

from .. import utils

logger = logging.getLogger("alembic.runtime.migration")

"""
Ce contextmanager permet d’ouvrir un fichier après l’avoir préalablement téléchargé.
Le fichier peut être compréssé et gérer en tant que tel pour les types suivants:
  - xz
dans les autres cas le fichier est ouvert comme un fichier normal
Le fichier téléchargé est enregistré dans le dossier spécifié par -x data-directory=…
Si aucun dossier n’est spécifié, un dossier temporaire, supprimé à la fin de la migration, est utilisé.
"""


def open_remote_file(*args, data_dir=None, **kwargs):
    if data_dir is None:
        try:
            data_dir = context.get_x_argument(as_dictionary=True).get("data-directory")
        except NameError:  # not used in alembic migration
            pass
    return utils.open_remote_file(*args, data_dir=data_dir, **kwargs)
