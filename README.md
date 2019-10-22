## Librairie "outil" pour SQLAlchemy et Flask

Cette librairie fournit des décorateurs pour faciliter le développement avec Flask et SQLAlchemy.

Elle est composée de trois outils principaux :

- **Les serialisers**

  Le décorateur de classe `@serializable` permet la sérialisation JSON d'objets Python issus des classes SQLAlchemy. Il rajoute dynamiquement une méthode `as_dict()` aux classes qu'il décore. Cette méthode transforme l'objet de la classe en dictionnaire en transformant les types Python non compatibles avec le format JSON. Pour cela, elle se base sur les types des colonnes décrits dans le modèle SQLAlchemy.
  
  La méthode contient les paramètre suivants :

  - `recursif` (boolean, default = False) : contrôle si la serialisation doit sérialiser les modèles enfants (relationships) de manière recursive
  - `columns` (iterable, default=()). Spécifie les colonnes qui doivent être présentes dans le dictionnaire en sortie. Par défaut toutes les colonnes sont prises.
  - `columns` (iterable, default=()). Spécifie les relationnships qui doivent être présentes dans le dictionnaire en sortie. Par défaut toutes les relationships sont prises si `recursif=True`.

* **Les réponses**

Le fichier contient des décorateurs de route Flask :

- Le décorateur `@json_resp` transforme l'objet retourné par la fonction en JSON.
- Le décorateur `@csv_resp` tranforme l'objet retourné par la fonction en fichier CSV. La fonction doit retourner un tuple de ce format `(file_name, data, columns, separator)`

* **Le mapping à la volée**

Le fichier `generic` contient les classes `GenericTable` et `GenericQuery` permettant de faire des requêtes sans définir de modèle au préalable.
