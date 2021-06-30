=========
CHANGELOG
=========

0.2.3 (2021-06-30)
------------------

**🚀 Nouveautés**

* Ajout du paramètre `stringify` (default `True`) qui contrôle la transformation des types non JSON sérialisable en `str`

**🐛 Corrections**

* Support des propriétés hybrides des modèles 
* Correction des regressions de performance sur la serialisation 
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
