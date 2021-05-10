'''
  config
'''

from flask import current_app
from.definitions import GenericRouteDefinitions
from sqlalchemy import func, cast, orm, and_
import unidecode


from sqlalchemy.sql.functions import ReturnTypeFromArgs

class unaccent(ReturnTypeFromArgs):
    pass


config = current_app.config
DB = config['DB']


definitions = GenericRouteDefinitions()



def serialize(model, module_name, object_type):
    relationships = definitions.get_object_type(module_name, object_type).get('relationships', [])
    return model.as_dict(True, relationships=relationships)
# def count_objects_type(module_name, object_type, args={}):
#     '''
#         get count
#     '''
#     Model, _ = definitions.get_model(module_name, object_type)
#     obj = definitions.get_object_type(module_name, object_type)
#     query = DB.session.query(Model)

#     # prefiltres 
#     pre_filters = obj.get('pre_filters', {})
#     for key in pre_filters:
#         if not hasattr(Model, key):
#             pass
#         query = query.filter(getattr(Model, key).in_(pre_filters[key]))

#     return query.count()


def getlist(args, key): 
    '''
        patch getlist pour tenir compte des cas ?val='val1,val2'
    '''

    val = args.get(key)

    if not val:
        return []

    if ',' in val:
        return val.split(',')       

    return args.getlist(key)



def custom_getattr(Model, attr_name, query):
    '''
        Recupere 
            - l'attribut d'un modele Model.attr si attr_name = 'attr'
            - ou l'attribut d'une relation Model si attr_name = 'rel.attr'

        Pour une relation directement, a voir si on peut le faire sur plusieurs niveaux
    '''

    if '.' in attr_name:
            
        # cas a.b on verra ensuite
        rel = attr_name.split('.')[0]
        col = attr_name.split('.')[1]

        if not hasattr(Model, rel):
            return None, query

        if not hasattr(getattr(Model, rel).mapper.columns, col):
            return None, query

        relationship = getattr(Model, rel)
        alias = orm.aliased(relationship.mapper.entity) # Model ?????

        query = query.join(alias, relationship)

        model_attribute = getattr(alias, col)

        return  model_attribute, query
        
    else:

        if not hasattr(Model, attr_name):
            return None, query
        
        return  getattr(Model, attr_name), query


def get_objects_type(module_name, object_type, args={}):
    '''
        get all
    '''

    joins = []

    Model, _ = definitions.get_model(module_name, object_type)
    obj = definitions.get_object_type(module_name, object_type)

    query = DB.session.query(Model)
    query.enable_assertions = True # prttt ???


    # prefiltres 
    pre_filters = obj.get('pre_filters', {})
    for key in pre_filters:
        if not hasattr(Model, key):
            continue
        query = query.filter(getattr(Model, key).in_(pre_filters[key]))

    count = query.count()

    # enlever prefiltres et mettre custom filter a la place
    custom_filter = obj.get('custom_filters')
    if custom_filter:
        # TODO action ????
        query = custom_filter(query, Model, module_name, object_type, 'R')


    # filtres
    #
    # si ?<key>=<value_filter> -> filtre =
    # si ?<key>__ilike=<value_filter> -> filtre ilike (ajouter sans accents ??)
    #
    # ajouter filtre par relationship (join ???)
    # si . in key 
    # ?a.b=<value_filter>
    # a : relationship et b attribut de a
    #
    for key in args:
        
        # test search- ?

        params_filter = key.split('__')

        key_filter = params_filter[0]
        
        type_filter=None
        if len(params_filter) > 1:
            type_filter = params_filter[1]

        #  test si clé null à ajouter ???
        value_filter = args[key]

        if not value_filter:
            continue

        # value

        # # si la cle n'est pas présente dans le modèle on passe

        # pour les cas ou key_filter = relationship.attribute 
        # (ou plus profond ?? r1.r2.attribute)
        model_attribute, query = custom_getattr(Model, key_filter, query)

        if model_attribute is None:
            continue

        if type_filter == 'ilike' and value_filter and value_filter[0] != '=':  

            # filre ILIKE            
            value_filter_unaccent = unidecode.unidecode(value_filter)
            value_filters=value_filter.split(' ')
            filters = []
            for v in value_filters:
                filters.append(
                    unaccent(cast(model_attribute, DB.String))
                    .ilike(func.concat('%', unaccent(v), '%'))
                )

            query = query.filter(and_(*(tuple(filters))))

        else:
            
            value_filter_effectif = value_filter
            if value_filter and value_filter[0] == '=':
                value_filter_effectif = value_filter[1:] 
            # filtre =
            query = query.filter(
                cast(model_attribute, DB.String ) == value_filter_effectif
            )

    # print sort by
    sort_by = getlist(args, 'sortBy')
    sort_desc = getlist(args, 'sortDesc')

    # sort
    order_bys = []
    for index, key in enumerate(sort_by):
        model_attribute, query = custom_getattr(Model, key, query)
        if model_attribute is None:
            continue

        desc = sort_desc[index]
        if(desc == 'true'):
            model_attribute = model_attribute.desc()
        else: 
            model_attribute.asc()

        order_bys.append(model_attribute)


    if order_bys:
        query = query.order_by(*(tuple(order_bys)))

    count_filtered = query.count()

    page = args.get('page')
    itemsPerPage = args.get('itemsPerPage')
    if itemsPerPage and int(itemsPerPage) > 0:
        query = query.limit(itemsPerPage)

        if page:
            query = query.offset((int(page)-1))

    return query, count, count_filtered


def get_object_type(module_name, object_type, value, field_name=None):
    '''
        get one
        value = model.<field_name>
        default field_name = id_field_name
    '''
    (Model, id_field_name) = definitions.get_model(module_name, object_type)

    if not field_name:
        field_name = id_field_name

    return (
        DB.session.query(Model).
        filter(getattr(Model, field_name) == value)
        .one()
    )


def create_or_update_object_type(module_name, object_type, id_value, post_data):
    '''
        toujours par id_value
    '''
    (Model, _) = definitions.get_model(module_name, object_type)

    res = None

    if not id_value:
        res = Model()
        DB.session.add(res)
    else:
        res = get_object_type(module_name, object_type, id_value)

    res.from_dict(post_data, True)

    DB.session.commit()

    return res

def delete_object_type(module_name, object_type, id_value):
    '''
        toujours par id_value
    '''

    (Model, id_field_name) = definitions.get_model(module_name, object_type)

    res = get_object_type(module_name, object_type, id_value)

    if not res:
        return None

    out = res.as_dict(True)

    (
        DB.session.query(Model)
        .filter(getattr(Model, id_field_name) == id_value)
        .delete()
    )



    DB.session.commit()

    return out
