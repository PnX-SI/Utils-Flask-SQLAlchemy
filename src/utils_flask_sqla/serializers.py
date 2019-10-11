"""
  Serialize function for SQLAlchemy models
"""
from sqlalchemy.orm import ColumnProperty
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


def serializable(cls):
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
        if isinstance(prop, ColumnProperty) and len(prop.columns) == 1:
            db_col = prop.columns[0]
            # HACK
            #  -> Récupération du nom de l'attribut sans la classe
            name = str(prop).split('.', 1)[1]
            if not db_col.type.__class__.__name__ == 'Geometry':
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
        (db_rel.key, db_rel.uselist) for db_rel in cls.__mapper__.relationships
    ]

    def serializefn(self, recursif=False, columns=(), relationships=()):
        """
        Méthode qui renvoie les données de l'objet sous la forme d'un dict

        Parameters
        ----------
            recursif: boolean
                Spécifie si on veut que les sous objet (relationship)
                soit également sérialisé
            columns: liste
                liste des colonnes qui doivent être prises en compte
            relationships: liste
                liste des relationships qui doivent être prise en compte
        """
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
        if recursif is False:
            return out

        for (rel, uselist) in selected_relationship:
            if getattr(self, rel):
                if uselist is True:
                    out[rel] = [
                        x.as_dict(recursif, relationships=relationships)
                        for x in getattr(self, rel)
                    ]
                else:
                    out[rel] = getattr(self, rel).as_dict(recursif)

        return out

    cls.as_dict = serializefn
    return cls
