## Librairie "outil" pour SQLAlchemy et Flask

La librairie fournir des décorateurs pour faciliter le développement avec Flask et SQLAlchemy.
Elle est composée de deux outils principaux:

- **Les serialisers**

  Le décorateur de classe `@serializable` permet la seralisation JSON d'objet Python issu des classes SQLAlchemy. Il rajoute dynamiquement une méthode `as_dict()` aux classes qu'il décore. Cette méthode transforme l'objet de la classe en dictionnaire en transformant les types Python non compatible avec le format JSON. Pour cela, elle se base sur les types des colonnes décrit dans le modèle SQLAlchemy.
  La méthode contient les paramètre suivant:

  - `recursif` (boolean, default = False): contrôle si la serialisation doit sérialiser les modèles enfant (relationships) de la manière recursive
  - `columns` (iterable, default=()). Spécifie les colonnes qui doivent être présent dans le dictionnaire en sortie. Par défaut toutes les colonnes sont prises.
  - `columns` (iterable, default=()). Spécifie les relationnships qui doivent être présentes dans le dictionnaire en sortie. Par défaut toutes les relationships sont prises si `recursif=True`.

* **Les réponses**

Le fichier contient des décorateur de route Flask

- Le décorateur `@json_resp` transforme l'objet retourné par la fonction en JSON.
- Le décorateur `@csv_resp` tranforme l'objet retourné par la fonction en fichier CSV. La fonction doit retourner un tuple de ce format `(file_name, data, columns, separator)`
