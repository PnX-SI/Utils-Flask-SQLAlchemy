=========
CHANGELOG
=========

0.1.2 (unreleased)
------------------

**🚀 Nouveautés**

*

**🐛 Corrections**

* 

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
