## Librairie "outil" pour SQLAlchemy et Flask

[![pytest](https://github.com/PnX-SI/Utils-Flask-SQLAlchemy/actions/workflows/pytest.yml/badge.svg)](https://github.com/PnX-SI/Utils-Flask-SQLAlchemy/actions/workflows/pytest.yml)
[![codecov](https://codecov.io/gh/PnX-SI/Utils-Flask-SQLAlchemy/branch/master/graph/badge.svg?token=R81RR3V5RI)](https://codecov.io/gh/PnX-SI/Utils-Flask-SQLAlchemy)

Cette librairie fournit des décorateurs pour faciliter le développement avec Flask et SQLAlchemy. 

Paquet Python : https://pypi.org/project/utils-flask-sqlalchemy/.

Elle est composée de trois outils principaux :

### Les serialisers

Le décorateur de classe ``@serializable`` permet la sérialisation JSON d'objets Python issus des classes SQLAlchemy. Il rajoute dynamiquement une méthode ``as_dict()`` aux classes qu'il décore. Cette méthode transforme l'objet de la classe en dictionnaire en transformant les types Python non compatibles avec le format JSON. Pour cela, elle se base sur les types des colonnes décrits dans le modèle SQLAlchemy.

Le décorateur ``@serializable`` peut être utilisé tel quel, ou être appelé avec les arguments suivants :

- ``exclude`` (iterable, default=()). Spécifie les colonnes qui doivent être exclues lors de la sérialisation. Par défaut, toutes les colonnes sont sérialisées.
  
La méthode ``as_dict()`` contient les paramètre suivants :

- ``recursif`` (boolean, default = False) : contrôle si la serialisation doit sérialiser les modèles enfants (relationships) de manière recursive
- ``columns`` (iterable, default=()). Spécifie les colonnes qui doivent être présentes dans le dictionnaire en sortie. Si non spécifié, le comportement par défaut du décorateur est adopté.
- ``relationships`` (iterable, default=()). Spécifie les relationnships qui doivent être présentes dans le dictionnaire en sortie. Par défaut toutes les relationships sont prises si ``recursif=True``.

### Les réponses

Le fichier contient des décorateurs de route Flask :

- Le décorateur ``@json_resp`` transforme l'objet retourné par la fonction en JSON. Renvoie une 404 si la valeur retournée par la fonction est None ou un tableau vide
- Le décorateur ``@json_resp_accept_empty_list`` transforme l'objet retourné par la fonction en JSON. Renvoie  une 404 si la valeur retournée par la fonction est None et 200 si c'est un tableau vide
- Le décorateur ``@csv_resp`` tranforme l'objet retourné par la fonction en fichier CSV. La fonction doit retourner un tuple de ce format ``(file_name, data, columns, separator)``

### Le mapping à la volée

Le fichier ``generic`` contient les classes ``GenericTable`` et ``GenericQuery`` permettant de faire des requêtes sans définir de modèle au préalable.
