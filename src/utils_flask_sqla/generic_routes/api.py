'''
    routes generiques
'''

from utils_flask_sqla.response import json_resp, json_resp_accept_empty_list
from flask import Blueprint, request
from .decorator import check_object_type

from .repository import (
    get_objects_type,
    get_object_type,
    create_or_update_object_type,
    delete_object_type,
    serialize
)

from .definitions import GenericRouteDefinitions

grd = GenericRouteDefinitions()

bp = Blueprint('generic_api', __name__)


@bp.route('<string:module_name>/<string:object_types>/', methods=['GET'])
@check_object_type('R')
@json_resp_accept_empty_list
def get_all_generic(module_name, object_types):
    '''
        get_all_generic
    '''

    # on enleve le s à la fin
    object_type = object_types[:-1]
    
    args = request.args

    res, count, count_filtered = get_objects_type(module_name, object_type, args)

    if 'count' in args:
        return count

    items = [serialize(r, module_name, object_type) for r in res.all()]

    return {
        'total' : count,
        'total_filtered' : count_filtered,
        'items' : items
    }

@bp.route('<string:module_name>/<string:object_type>/<value>', methods=['GET'])
@check_object_type('R')
@json_resp
def get_generic(module_name, object_type, value):
    '''
    field_name (id_field_name par defaut)
    '''

    field_name = request.args.get('field_name')

    res = get_object_type(module_name, object_type, value, field_name)

    if not res:
        return None

    return res.as_dict(True)


@bp.route('<string:module_name>/<string:object_type>/<int:id_value>', methods=['PATCH'])
@check_object_type('U')
@json_resp
def patch_generic(module_name, object_type, id_value):
    '''
        patch generic
    '''
    post_data = request.get_json()

    res = create_or_update_object_type(module_name, object_type, id_value, post_data)

    return res.as_dict(True)


@bp.route('<string:module_name>/<string:object_type>/', methods=['POST'])
@check_object_type('C')
@json_resp
def post_generic(module_name, object_type):
    '''
        post generic
    '''

    post_data = request.get_json()

    res = create_or_update_object_type(module_name, object_type, None, post_data)

    return res.as_dict(True)


@bp.route('<string:module_name>/<string:object_type>/<int:id_value>', methods=['DELETE'])
@check_object_type('D')
@json_resp
def delete_generic(module_name, object_type, id_value):
    '''
    delete generic
    '''

    return  delete_object_type(module_name, object_type, id_value)
