0.1.0 (2019-12-18)
------------------

**Nouveautés**

* Ajout de ``json_resp_accept`` pour définir les réponses qui ne renvoient pas un code erreur, ne modifie pas ``json_resp``
* Ajout des ``GenericTable`` et ``GenericQuery`` (en version simplifiée sans la gestion des géométries)
* Ajout de l'instance sqlalchemy (DB) en paramètre de GenericQuery
* Ajout des exceptions UtilsSqlaError
* Ajout d'une methode from_dict
* Modification de as_dict : ajout d'un parametre depth pour definir le niveau de récursivité
* Prise en compte des colonnes redefinies dans le cas d'un heritage

0.0.1 (2019-10-17)
------------------

Première version fonctionnelle de la librairie

* Décorateur de classe permettant de serialiser des modèles SQLAlchemy via la méthode ``as_dict`` (recursivité, choix de colonnes, choix de relationships)
* Fonctions utilitaires pour retourner des réponses HTTP JSON ou CSV.
