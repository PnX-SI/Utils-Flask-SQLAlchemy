0.0.2 (2019-22-17)
-------------------------

**Nouveautés**

* Ajout de json_reps_accept pour definir les reponse qui ne renvoient pas un code erreur, ne modifie pas json_resp
* Ajout des ``GenericTable`` et ``GenericQuery`` (en version simplifiée sans la gestion des géométries)
* Ajout de l'instance sqlalchemy (DB) en paramètre de GenericQuery
* Ajout des exceptions GeonatureApiError
* Ajout d'une methode from_dict
* gestion des uuid qui arrivent comme des integer dans les fonctions de sérialisation

0.0.1 (2019-10-17)
------------------

Première version fonctionnelle de la librairie

* Décorateur de classe permettant de serialiser des modèles SQLAlchemy via la méthode ``as_dict`` (recursivité, choix de colonnes, choix de relationships)
* Fonctions utilitaires pour retourner des réponses HTTP JSON ou CSV.
