from marshmallow.fields import Nested


class SmartRelationshipsMixin:
    def __init__(self, *args, **kwargs):
        natural_fields = set()
        nested_fields = set()
        for name, field in self._declared_fields.items():
            if isinstance(field, Nested):
                nested_fields.add(name)
            else:
                natural_fields.add(name)

        only = kwargs.pop('only', None)
        only = set(only) if only is not None else set()
        firstlevel_only = { field.split('.', 1)[0] for field in only }
        exclude = kwargs.pop('exclude', None)
        exclude = set(exclude) if exclude is not None else set()
        exclude |= (nested_fields - firstlevel_only)
        if not firstlevel_only - nested_fields:
            only |= natural_fields
        if only:
            kwargs['only'] = only
        if exclude:
            kwargs['exclude'] = exclude
        super().__init__(*args, **kwargs)
