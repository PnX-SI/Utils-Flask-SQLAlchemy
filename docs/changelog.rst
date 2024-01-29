=========
CHANGELOG
=========

0.4.1 (2024-01-29)
------------------

**🐛 Corrections**

- Mise à jour de Flask version 2 à 3 (#46)
- Mise à jour de SQLAlchemy version 1.3 à 1.4 (#46)
- Abandon du support de Debian 10 (#46)
- Abandon du support de Python 3.7 (#46)
- Refactorisation du SmartRelationshipsMixin par défaut (via ``only``) des fields de type ``RelatedList`` et ``Related`` utilisé par ``marshmallow_sqlalchemy`` lorsqu'on utilise la propriété ``include_relationships=True`` ou qu'on charge le champs via ``auto_field`` (#47)


0.3.6 (2023-09-14)
------------------

**🐛 Corrections**

* Correction du ``total_filtered`` (#40 by @lpofrec)

0.3.5 (2023-08-08)
------------------

**🐛 Corrections**

* Correction de la limite non mise sur les GenericQuery

0.3.4 (2023-06-06)
------------------
**🚀 Nouveautés**

* GenericQuery : Ajout de filtres supérieur ou inférieur pour les entiers (``filter_d_up_nomchamp``, ``filter_d_lo_nomchamp``).

**🐛 Corrections**

* Correction d'une erreur lorsque le paramètre ``orderby`` est vide (#34).
* Dé-sérialiseurs ``from_dict`` : ajout d'un test sur l’existence d'une valeur de clé primaire nulle dans les données avant de la supprimer.


0.3.3 (2023-04-11)
------------------

**🚀 Nouveautés**

* Ajout de SQLAlchemy 1.4 aux tests unitaires
* ``SmartRelationshipsMixin``: exclusion par défaut des champs ``deferred``


0.3.2 (2023-03-03)
------------------

**🚀 Nouveautés**

* ``SmartRelationshipsMixin`` : possibilité d’exclure par défaut certains champs avec ``metadata={"exclude": True}``


0.3.1 (2022-12-12)
------------------

**🚀 Nouveautés**

* Ajout du context manager générique ``remote_file``, sur lequel vient s’appuyer le context manager ``open_remote_file`` qui ajoute l’ouverture du fichier récupéré.

**🐛 Corrections**

* Utilisation le l’encodeur JSON de Flask, supportant l’encodage des réponses SQLAlchemy


0.3.0 (2022-08-30)
------------------

**🚀 Nouveautés**

* Publication automatique des nouvelles releases sur `pypi <https://pypi.org/project/utils-flask-sqlalchemy/>`_.
* Ajout de sous-commandes au group de commande ``db`` permettant de gérer la base de données avec Alembic (`Flask-Migrate <https://flask-migrate.readthedocs.io/en/latest/>`_)

  * ``status`` : Affiche l’ensemble des révisions triées par branches avec leur status (appliquées ou non) et optionnellement leur dépendances.
  * ``autoupgrade`` : Applique automatiquement toutes les révisions des branches en retard
  * ``exec`` : permet d’exécuter des commandes SQL et de renvoyer leurs résultats en JSON

* Amélioration du décorateur ``@serializable`` :

  * Les champs marqués ``deferred`` sont par défaut exclus
  * Support des modèles possédant des `properties` (``@property``).

* Le code est désormais formaté avec `Black <https://black.readthedocs.io/en/stable/>`_ et ceci est vérifié par une Github Action.
* Création du collation ``fr_numeric`` (branche Alembic ``sql_utils``).
* Compatibilité Flask 2.
* L’utilitaire ``open_remote_file`` peut chercher des fichiers dans le dossier spécifié par la variable d’environnement ``DATA_DIRECTORY`` pour un usage hors Alembic (pour ce dernier, il reste possible d’utiliser ``-x data-directory=…``).

**🐛 Corrections**

* Correction des requêtes génériques :

  * Correction d’un bug lorsque les données sont ordonnées et amélioration des performances de comptage
  * Changement du format du paramètre ``orderby``


0.2.6 (2022-01-04)
------------------

**🚀 Nouveautés**

* Ajout de la fixture pytest ``temporary_transaction``. Utilisation :

  ::

    @pytest.mark.usefixtures("temporary_transaction")
    class TestClass:
        …

* Ajout de l’utilitaire ``JSONClient``. Utilisation :

  ::

    from utils_flask_sqla.tests.utils import JSONClient
    app.test_client_class = JSONClient

* Intégration continue du module pour exécuter automatiquement les tests et la couverture de code avec GitHub Actions, à chaque commit ou pull request dans les branches ``develop`` ou ``master``

0.2.5 (2022-01-03)
------------------

**🚀 Nouveautés**

* ``as_dict()`` : ajout de l’option ``unloaded``, acceptant les valeurs ``raise`` et ``warn``
* ``@json_resp`` : les réponses vides ne déclenchent plus l’émission d’une 404
* Ajout de ``SmartRelationshipsMixin`` permettant d’exclure par défaut les schémas ``Nested`` lors de la sérialisation avec Marshmallow

0.2.4 (2021-09-30)
------------------

**🚀 Nouveautés**

* Ajout d’une fonction utilitaire ``open_remote_file`` utile pour les migrations Alembic
* Ajout d’une branche Alembic ``sql_utils`` offrant la fonction SQL ``public.fct_trg_meta_dates_change``
* Compatibilité avec Python 3.9

**🐛 Corrections**

* Ajout d’une dépendance manquante

0.2.3 (2021-06-30)
------------------

**🚀 Nouveautés**

* Ajout du paramètre ``stringify`` (default ``True``) qui contrôle la transformation des types non JSON sérialisable en ``str``

**🐛 Corrections**

* Correction des régressions de performance sur la sérialisation

0.2.2 (2021-06-22)
------------------

**🐛 Corrections**

* Support des propriétés hybrides des modèles
* Ajout de tests sur les modèles polymorphiques

0.2.1 (2021-06-03)
------------------

**🐛 Corrections**

* Gestion du cas suivant :

::

    @serializable
    @geoserializable
    def MyModel(db.Model):
        pass


0.2.0 (2021-05-27)
------------------

**🚀 Nouveautés**

* Il est possible de surcoucher la méthode ``as_dict`` avec la signature suivante :

::

    def MyModel(db.Model):
        def as_dict(self, data):
            return data

Celle-ci reçoit alors les données sérialisées dans l'argument ``data`` et peut les modifier avant de les renvoyer.

* Ajout de tests unitaires
* Ajout d’un encodeur JSON supportant les objets de type ``time``
* Ajout des paramètres ``fields`` et ``exclude``, supportant indifféremment les colonnes et relationships. Ces paramètres peuvent être utilisés en argument de la méthode ``as_dict``, ou en argument du décorateur ``@serializable`` directement afin de définir des paramètres par défaut pour le modèle
* Dépréciation des paramètres ``columns``, ``relationships``, ``recursif`` et ``depth``

**🐛 Corrections**

* Le décorateur ``@serializable`` peut être utilisé lorsque le modèle n’est pas encore prêt (e.g. utilisation de ``backref``)
* Corrige un bug de récursion infinie lorsque 2 modèles se référencent


0.1.4 (2021-02-03)
------------------

**🚀 Nouveautés**

* Le décorateur ``@json_resp`` accepte les réponses vides si le code passé est 204


0.1.3 (2021-01-27)
------------------

**🚀 Nouveautés**

* Ajout du paramètre ``exclude`` (list) sur le décorateur ``serializable`` pour exclure une colonne de la sérialisation

**🐛 Corrections**

* Les dépendances du fichier ``requirements.txt`` ne sont plus fixées à une version

0.1.2 (2020-10-17)
------------------

**🚀 Nouveautés**

* Amélioration de la fonction ``from_dict`` (possibilité de passer des ID aux relationships)
* Mise à jour des dépendances (SQLAlchemy 1.3.19)

0.1.1 (2020-06-17)
------------------

**🚀 Nouveautés**

* ``to_json`` sérialise désormais les ``datetime`` et ``UUID`` (par @jbdesbas)
* Méthode ``from_dict`` récursive pour renseigner les relations

0.1.0 (2019-12-18)
------------------

**🚀 Nouveautés**

* Ajout de ``json_resp_accept`` pour définir les réponses qui ne renvoient pas un code erreur, ne modifie pas ``json_resp``
* Ajout des ``GenericTable`` et ``GenericQuery`` (en version simplifiée sans la gestion des géométries)
* Ajout de l'instance ``sqlalchemy (DB)`` en paramètre de ``GenericQuery``
* Ajout des exceptions ``UtilsSqlaError``
* Modification de ``as_dict`` : ajout d'un paramètre ``depth`` pour définir le niveau de récursivité
* Prise en compte des colonnes redéfinies dans le cas d'un héritage

0.0.1 (2019-10-17)
------------------

Première version fonctionnelle de la librairie

* Décorateur de classe permettant de serialiser des modèles SQLAlchemy via la méthode ``as_dict`` (recursivité, choix de colonnes, choix de relationships)
* Fonctions utilitaires pour retourner des réponses HTTP JSON ou CSV.
