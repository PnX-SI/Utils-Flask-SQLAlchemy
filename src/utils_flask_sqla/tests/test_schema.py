from unittest import TestCase

import marshmallow as ma
from marshmallow.fields import Nested
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, deferred
from sqlalchemy.ext.hybrid import hybrid_property
from flask_sqlalchemy import SQLAlchemy

from utils_flask_sqla.schema import SmartRelationshipsMixin


db = SQLAlchemy()


class Parent(db.Model):
    pk = Column(Integer, primary_key=True)
    col = Column(String)


class Child(db.Model):
    pk = Column(Integer, primary_key=True)
    col = Column(String)
    parent_pk = Column(Integer, ForeignKey(Parent.pk))
    parent = relationship("Parent", backref="childs")


class ParentSchema(SmartRelationshipsMixin, SQLAlchemyAutoSchema):
    class Meta:
        model = Parent
        include_fk = True

    childs = Nested("ChildSchema", many=True)


class ChildSchema(SmartRelationshipsMixin, SQLAlchemyAutoSchema):
    class Meta:
        model = Child
        include_fk = True

    parent = Nested(ParentSchema)


class TestSmartRelationshipsMixin:
    def test_only(self):
        parent = Parent(pk=1, col="p")
        child = Child(pk=1, col="c", parent_pk=1, parent=parent)
        parent.childs = [child]

        TestCase().assertDictEqual(
            ParentSchema().dump(parent),
            {
                "pk": 1,
                "col": "p",
            },
        )

        TestCase().assertDictEqual(
            ChildSchema().dump(child),
            {
                "pk": 1,
                "col": "c",
                "parent_pk": 1,
            },
        )

        TestCase().assertDictEqual(
            ParentSchema(only=["childs"]).dump(parent),
            {
                "pk": 1,
                "col": "p",
                "childs": [
                    {"pk": 1, "col": "c", "parent_pk": 1},
                ],
            },
        )

        TestCase().assertDictEqual(
            ParentSchema(only=["childs.pk"]).dump(parent),
            {
                "pk": 1,
                "col": "p",
                "childs": [
                    {"pk": 1},
                ],
            },
        )

        TestCase().assertDictEqual(
            ParentSchema(only=["childs.parent"]).dump(parent),
            {
                "pk": 1,
                "col": "p",
                "childs": [
                    {
                        "pk": 1,
                        "col": "c",
                        "parent_pk": 1,
                        "parent": {
                            "pk": 1,
                            "col": "p",
                        },
                    }
                ],
            },
        )

        TestCase().assertDictEqual(
            ParentSchema(only=["childs.pk", "childs.parent"]).dump(parent),
            {
                "pk": 1,
                "col": "p",
                "childs": [
                    {
                        "pk": 1,
                        "parent": {
                            "pk": 1,
                            "col": "p",
                        },
                    }
                ],
            },
        )

        TestCase().assertDictEqual(
            ParentSchema(only=["childs.pk", "childs.parent.col"]).dump(parent),
            {
                "pk": 1,
                "col": "p",
                "childs": [
                    {
                        "pk": 1,
                        "parent": {
                            "col": "p",
                        },
                    }
                ],
            },
        )

        TestCase().assertDictEqual(
            ParentSchema(only=["childs.pk", "childs.parent.childs.col"]).dump(parent),
            {
                "pk": 1,
                "col": "p",
                "childs": [
                    {
                        "pk": 1,
                        "parent": {
                            "pk": 1,
                            "col": "p",
                            "childs": [
                                {
                                    "col": "c",
                                },
                            ],
                        },
                    }
                ],
            },
        )

    def test_null_relationship(self):
        parent = Parent(pk=1)
        child = Child(pk=1)

        TestCase().assertDictEqual(
            ParentSchema(only=("childs",)).dump(parent),
            {
                "pk": 1,
                "col": None,
                "childs": [],
            },
        )

        TestCase().assertDictEqual(
            ChildSchema(only=("parent",)).dump(child),
            {
                "pk": 1,
                "col": None,
                "parent_pk": None,
                "parent": None,
            },
        )

    def test_polymorphic_model(self):
        class PolyModel(db.Model):
            __mapper_args__ = {
                "polymorphic_identity": "IdentityBase",
                "polymorphic_on": "kind",
            }
            pk = db.Column(db.Integer, primary_key=True)
            kind = db.Column(db.String)
            base = db.Column(db.String)

        class PolyModelSchema(SmartRelationshipsMixin, SQLAlchemyAutoSchema):
            class Meta:
                model = PolyModel

        class PolyModelA(PolyModel):
            __mapper_args__ = {
                "polymorphic_identity": "A",
            }
            pk = db.Column(db.Integer, db.ForeignKey(PolyModel.pk), primary_key=True)
            a = db.Column(db.String)

        class PolyModelASchema(SmartRelationshipsMixin, SQLAlchemyAutoSchema):
            class Meta:
                model = PolyModelA

        class PolyModelB(PolyModel):
            __mapper_args__ = {
                "polymorphic_identity": "B",
            }
            pk = db.Column(db.Integer, db.ForeignKey(PolyModel.pk), primary_key=True)
            b = db.Column(db.String)

        class PolyModelBSchema(SmartRelationshipsMixin, SQLAlchemyAutoSchema):
            class Meta:
                model = PolyModelB

        a = PolyModelA(pk=1, base="BA", a="A")
        TestCase().assertDictEqual(
            PolyModelASchema().dump(a),
            {
                "pk": 1,
                "kind": "A",
                "base": "BA",
                "a": "A",
            },
        )

        b = PolyModelB(pk=2, base="BB", b="B")
        TestCase().assertDictEqual(
            PolyModelBSchema().dump(b),
            {
                "pk": 2,
                "kind": "B",
                "base": "BB",
                "b": "B",
            },
        )

    def test_hybrid_property(self):
        class HybridModel(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            part1 = db.Column(db.String)
            part2 = db.Column(db.String)

            @hybrid_property
            def concat(self):
                return "{0} {1}".format(self.part1, self.part2)

            @concat.expression
            def concat(cls):
                return db.func.concat(cls.part1, " ", cls.part2)

        class HybridModelSchema(SmartRelationshipsMixin, SQLAlchemyAutoSchema):
            class Meta:
                model = HybridModel

            concat = ma.fields.String(dump_only=True)

        h = HybridModel(pk=1, part1="a", part2="b")
        TestCase().assertDictEqual(
            HybridModelSchema().dump(h),
            {
                "pk": 1,
                "part1": "a",
                "part2": "b",
                "concat": "a b",
            },
        )

    def test_excluded_field(self):
        class ExcludeSchema(SmartRelationshipsMixin, ma.Schema):
            class Meta:
                exclude = ("d",)

            a = ma.fields.String(metadata={"exclude": False})
            b = ma.fields.String(metadata={"exclude": True})
            c = ma.fields.String()
            d = ma.fields.String()

        s = {"a": "A", "b": "B", "c": "C", "d": "D"}

        TestCase().assertDictEqual(
            ExcludeSchema().dump(s),
            {
                "a": "A",
                "c": "C",
            },
        )
        TestCase().assertDictEqual(
            ExcludeSchema(only=["a"]).dump(s),
            {
                "a": "A",
            },
        )
        TestCase().assertDictEqual(
            ExcludeSchema(only=["b"]).dump(s),
            {
                "b": "B",
            },
        )
        TestCase().assertDictEqual(
            ExcludeSchema(only=["+b"]).dump(s),
            {
                "a": "A",
                "b": "B",
                "c": "C",
            },
        )
        TestCase().assertDictEqual(
            ExcludeSchema(only=["+c"]).dump(s),
            {
                "a": "A",
                "c": "C",
            },
        )
        TestCase().assertDictEqual(ExcludeSchema(only=["c"], exclude=["c"]).dump(s), {})
        TestCase().assertDictEqual(
            ExcludeSchema(only=["+c"], exclude=["c"]).dump(s),
            {
                "a": "A",
            },
        )
        TestCase().assertDictEqual(
            ExcludeSchema(only=["a", "+b"]).dump(s),
            {
                "a": "A",
                "b": "B",
            },
        )

    def test_nested_excluded_field(self):
        class ParentExcludeSchema(SmartRelationshipsMixin, ma.Schema):
            child = ma.fields.Nested("ChildExcludeSchema")

        class ChildExcludeSchema(SmartRelationshipsMixin, ma.Schema):
            a = ma.fields.String(metadata={"exclude": False})
            b = ma.fields.String(metadata={"exclude": True})

            parent = ma.fields.Nested("ParentExcludeSchema")

        p = {"child": {"a": "A", "b": "B"}}
        TestCase().assertDictEqual(ParentExcludeSchema().dump(p), {})
        TestCase().assertDictEqual(
            ParentExcludeSchema(only=["child"]).dump(p),
            {
                "child": {
                    "a": "A",
                },
            },
        )
        TestCase().assertDictEqual(
            ParentExcludeSchema(only=["child.a"]).dump(p),
            {
                "child": {
                    "a": "A",
                },
            },
        )
        TestCase().assertDictEqual(
            ParentExcludeSchema(only=["child.b"]).dump(p),
            {
                "child": {
                    "b": "B",
                },
            },
        )
        TestCase().assertDictEqual(
            ParentExcludeSchema(only=["child.+b"]).dump(p),
            {
                "child": {
                    "a": "A",
                    "b": "B",
                },
            },
        )
        TestCase().assertDictEqual(
            ParentExcludeSchema(only=["child.a", "child.+b"]).dump(p),
            {
                "child": {
                    "a": "A",
                    "b": "B",
                },
            },
        )

    def test_deferred_field(self):
        class DeferredModel(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            a = db.Column(db.String)
            b = deferred(db.Column(db.String))

        class DeferredSchema(SmartRelationshipsMixin, SQLAlchemyAutoSchema):
            class Meta:
                model = DeferredModel

        d = DeferredModel(pk=1, a="A", b="B")

        TestCase().assertDictEqual(DeferredSchema().dump(d), {"pk": 1, "a": "A"})
        TestCase().assertDictEqual(
            DeferredSchema(only=["+b"]).dump(d), {"pk": 1, "a": "A", "b": "B"}
        )
        TestCase().assertDictEqual(DeferredSchema(only=["b"]).dump(d), {"b": "B"})
