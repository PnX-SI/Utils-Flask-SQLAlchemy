'''
    decorator
'''

from functools import wraps
from flask import session
from .definitions import GenericRouteDefinitions

definitions = GenericRouteDefinitions()


def check_object_type(droit_type):
    '''
        decorateur qui verifie les droits et les définitions
    '''
    def check_object_type_(fn):
        @wraps(fn)
        def check_object_type__(*args, **kwargs):

            module_name = kwargs.get('module_name')
            object_type = kwargs.get('object_type') or kwargs.get('object_types')[:-1]
            current_user = session.get('current_user', {})

            module = definitions.get_module(module_name)
            if not module:
                return (
                    "pas de module défini pour {}".format(module_name),
                    403
                )

            object_definition = definitions.get_object_type(module_name, object_type)

            if not object_definition:
                return (
                    "pas d'object défini pour {} {}".format(module_name, object_type),
                    403
                )

            (test, error_msg) = definitions.check_rights(module_name, object_type, droit_type)

            if not test:
                msg = (
                    error_msg 
                    or 
                    "droits insuffisants en {} pour la route {} {} : route fermée"
                        .format(droit_type, module_name, object_type)
                )
                return (msg, 403)

            return fn(*args, **kwargs)
        return check_object_type__
    return check_object_type_
