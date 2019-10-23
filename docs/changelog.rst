0.0.2 (2019-22-17)
-------------------------

**Nouveautés**

* Ajout des ``GenericTable`` et ``GenericQuery`` (en version simplifiée sans la gestion des géométries)
* Ajout des exceptions GeonatureApiError
* Ajout d'une methode from_dict
0.0.1 (2019-10-17)
------------------

Première version fonctionnelle de la librairie

* Décorateur de classe permettant de serialiser des modèles SQLAlchemy via la méthode ``as_dict`` (recursivité, choix de colonnes, choix de relationships)
* Fonctions utilitaires pour retourner des réponses HTTP JSON ou CSV.
