"""
  Serialize function for SQLAlchemy models
"""
from sqlalchemy.orm import ColumnProperty
from sqlalchemy import inspect

"""
    List of data type who need a particular serialization
    @TODO MISSING FLOAT
"""
SERIALIZERS = {
    "date": lambda x: str(x) if x else None,
    "datetime": lambda x: str(x) if x else None,
    "time": lambda x: str(x) if x else None,
    "timestamp": lambda x: str(x) if x else None,
    "uuid": lambda x: str(x) if x else None,
    "numeric": lambda x: str(x) if x else None,
}


def get_serializable_decorator(exclude=[]):
    def _serializable(cls):
        """
            Décorateur de classe pour les DB.Models
            Permet de rajouter la fonction as_dict
            qui est basée sur le mapping SQLAlchemy
        """

        """
            Liste des propriétés sérialisables de la classe
            associées à leur sérializer en fonction de leur type
        """
        cls_db_columns = []
        for prop in cls.__mapper__.column_attrs:
            if isinstance(prop, ColumnProperty):  # and len(prop.columns) == 1:
                # -1 : si on est dans le cas d'un heritage on recupere le dernier element de prop
                # qui correspond à la derniere redefinition de cette colonne
                db_col = prop.columns[-1]
                # HACK
                #  -> Récupération du nom de l'attribut sans la classe
                name = str(prop).split('.', 1)[1]
                if db_col.type.__class__.__name__ == 'Geometry':
                    continue
                if name in exclude:
                    continue
                cls_db_columns.append((
                    name,
                    SERIALIZERS.get(
                        db_col.type.__class__.__name__.lower(),
                        lambda x: x
                    )
                ))
        """
            Liste des propriétés synonymes
            sérialisables de la classe
            associées à leur sérializer en fonction de leur type
        """
        for syn in cls.__mapper__.synonyms:
            col = cls.__mapper__.c[syn.name]
            # if column type is geometry pass
            if col.type.__class__.__name__ == 'Geometry':
                pass

            # else add synonyms in columns properties
            cls_db_columns.append((
                syn.key,
                SERIALIZERS.get(
                    col.type.__class__.__name__.lower(),
                    lambda x: x
                )
            ))
        """
            Liste des propriétés de type relationship
            uselist permet de savoir si c'est une collection de sous objet
            sa valeur est déduite du type de relation
            (OneToMany, ManyToOne ou ManyToMany)
        """
        cls_db_relationships = [
            (
                db_rel.key,
                db_rel.uselist,
                getattr(cls, db_rel.key).mapper.class_
            ) for db_rel in cls.__mapper__.relationships
        ]

        def serializefn(self, recursif=False, columns=(), relationships=(), depth=None):
            """
            Méthode qui renvoie les données de l'objet sous la forme d'un dict

            Parameters
            ----------
                recursif: boolean
                        Spécifie si on veut que les sous-objets (relationship)
                depth: entier
                    spécifie le niveau de niveau de récursion:
                        0 juste l'objet
                        1 l'objet et ses sous-objets
                        2 ...
                    si depth est spécifié :
                        recursif prend la valeur True
                    si depth n'est pas spécifié et recursif est à True :
                        il n'y a pas de limite à la récursivité
                columns: liste
                    liste des colonnes qui doivent être prises en compte
                relationships: liste
                    liste des relationships qui doivent être prise en compte
            """

            if isinstance(depth, int) and depth >= 0:
                recursif = True
                depth -= 1

            if columns:
                fprops = list(filter(lambda d: d[0] in columns, cls_db_columns))
            else:
                fprops = cls_db_columns
            if relationships:
                selected_relationship = list(
                    filter(lambda d: d[0] in relationships, cls_db_relationships)
                )
            else:
                selected_relationship = cls_db_relationships
            out = {item: _serializer(getattr(self, item))
                   for item, _serializer in fprops}

            if (depth and depth < 0) or not recursif:
                return out

            for (rel, uselist, _) in selected_relationship:
                if getattr(self, rel):
                    if uselist is True:
                        out[rel] = [
                            x.as_dict(recursif=recursif, depth=depth, relationships=relationships)
                            for x in getattr(self, rel)
                        ]
                    else:
                        out[rel] = getattr(self, rel).as_dict(
                            recursif=recursif, depth=depth, relationships=relationships)

            return out

        def populatefn(self, dict_in, recursif=False):
            '''
            Méthode qui initie les valeurs de l'objet à partir d'un dictionnaire

            Parameters
            ----------
                dict_in : dictionnaire contenant les valeurs à passer à l'objet
                recursif: si on renseigne les relationships

            '''

            cls_db_columns_key = list(map(lambda x: x[0], cls_db_columns))

            # populate cls_db_columns
            for key in dict_in:
                if key in cls_db_columns_key:
                    setattr(self, key, dict_in[key])

            # si non recursif, on ne traite pas les relationship
            if not recursif:
                return self

            # gestion des relationships
            frel = cls_db_relationships

            for (rel, uselist, Model) in frel:

                if rel not in dict_in:
                    continue

                values = dict_in.get(rel)
                if not values:
                    # check if None or {}
                    setattr(self, rel, [] if uselist else None)
                    continue

                # pour pouvoir traiter les cas uselist et not uselist de la même manière
                if not uselist:
                    values = [values]

                # get id_field_name
                id_field_name = inspect(Model).primary_key[0].name
                # si on a pas une liste de dictionaires
                # -> on suppose qu'on a une liste d'id
                # test sur le premier element de la liste
                # on cree une liste [ ... { <id_field_name>: id_value } ... ]
                if not isinstance(values[0], dict):
                    values_inter = []
                    for id_value in values:
                        data = {}
                        data[id_field_name] = id_value
                        values_inter.append(data)
                    values = values_inter



                # preload with id
                # pour faire une seule requête
                ids = filter(
                    lambda x: x,
                    map(
                        lambda x: x.get(id_field_name),
                        values
                    )
                )
                preload_res_with_ids = (
                    Model.query
                    .filter(getattr(Model, id_field_name).in_(ids))
                    .all()
                )

                # resul
                v_obj = []

                for data in values:

                    id_value = data.get(id_field_name)

                    # si id_value est null
                    # creation -> on supprime id_value
                    if not id_value:
                        data.pop(id_field_name)

                    res = (
                        # si on a une id -> on recupère dans la liste preload_res_with_ids
                        # TODO trouver un find plus propre ?
                        list(
                            filter(
                                lambda x: getattr(x, id_field_name) == id_value,
                                preload_res_with_ids
                            )
                        )[0]
                        if id_value and len(preload_res_with_ids)
                        # sinon on cree une nouvelle instance
                        else Model()
                    )
                    if hasattr(res, 'from_dict'):
                        res.from_dict(data, recursif)

                    v_obj.append(res)

                # attribution de la relation
                # si uselist est à false -> on prend le premier de la liste
                setattr(
                    self,
                    rel,
                    v_obj if uselist else v_obj[0]
                )

            return self

        cls.as_dict = serializefn
        cls.from_dict = populatefn

        return cls
    return _serializable


def serializable(*args, **kwargs):
    if not kwargs and len(args) == 1 and isinstance(args[0], type): # e.g. @serializable
        return get_serializable_decorator()(args[0])
    else:
        return get_serializable_decorator(*args, **kwargs) # e.g. @serializable(exclude=['field'])
