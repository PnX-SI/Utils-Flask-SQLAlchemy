from marshmallow.fields import Nested


class SmartRelationshipsMixin:
    """
    This mixin automatically exclude from serialization:
    - Nested fields
    - all fields with exclude=True in their metadata (e.g. fields.String(metadata={'exclude': True}))
    Adding Nested fields to only will serialize defaults fields and specified Nested fields.
    Adding exclude=True fields to only will serialize only specified fields (default marshmallow behaviour).
    You can use '+field_name' syntax to serialize excluded fields without excluding defaults fields.
    """

    def __init__(self, *args, **kwargs):
        included_fields = set()
        excluded_fields = set()
        nested_fields = set()
        for name, field in self._declared_fields.items():
            # excluded fields at meta level are not even generated by auto-schema
            if field is None:
                continue
            if isinstance(field, Nested):
                nested_fields.add(name)
            elif field.metadata.get("exclude", False):
                excluded_fields.add(name)
            elif (
                hasattr(self.opts, "model")
                and hasattr(self.opts.model.__mapper__.column_attrs, name)
                and getattr(self.opts.model.__mapper__.column_attrs, name).deferred
            ):
                excluded_fields.add(name)
            else:
                included_fields.add(name)

        only = kwargs.pop("only", None)
        only = set(only) if only is not None else set()
        additional_fields = {field[1:] for field in only if field.startswith("+")}
        only = {field[1:] if field.startswith("+") else field for field in only}
        firstlevel_only = {field.split(".", 1)[0] for field in only}
        exclude = kwargs.pop("exclude", None)
        exclude = set(exclude) if exclude is not None else set()
        exclude |= (excluded_fields | nested_fields) - firstlevel_only
        # If only contains only nested & additional fields, we need to add included_fields to serialize nested, additional & included fields.
        # If only does not contains nested or additional fields, we do nothing and marshmallow will serialize only specified fields.
        if only and not firstlevel_only - nested_fields - additional_fields:
            only |= included_fields
        if only:
            kwargs["only"] = only
        if exclude:
            kwargs["exclude"] = exclude
        super().__init__(*args, **kwargs)
