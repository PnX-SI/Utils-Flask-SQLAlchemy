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


cor_hobby_child = db.Table(
    "cor_hobby_child",
    db.Column("id_child", db.Integer, ForeignKey("child.pk")),
    db.Column("id_hobby", db.Integer, ForeignKey("hobby.pk")),
)


class Hobby(db.Model):
    __tablename__ = "hobby"
    pk = Column(Integer, primary_key=True)
    name = Column(Integer)


class Address(db.Model):
    __tablename__ = "address"
    pk = Column(Integer, primary_key=True)
    street = Column(Integer)
    city = Column(Integer)


class Child(db.Model):
    __tablename__ = "child"
    pk = Column(Integer, primary_key=True)
    col = Column(String)
    parent_pk = Column(Integer, ForeignKey(Parent.pk))
    address_pk = Column(Integer, ForeignKey(Address.pk))
    parent = relationship("Parent", backref="childs")
    hobbies = relationship(Hobby, secondary=cor_hobby_child)
    address = relationship(Address)


class ParentSchema(SmartRelationshipsMixin, SQLAlchemyAutoSchema):
    class Meta:
        model = Parent
        include_fk = True

    childs = Nested("ChildSchema", many=True)


class HobbySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Hobby


class AdressSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Address


class ChildSchema(SmartRelationshipsMixin, SQLAlchemyAutoSchema):
    class Meta:
        model = Child
        include_fk = True

    parent = Nested(ParentSchema)
    hobbies = (
        auto_field()
    )  # For a n-n relationship a RelatedList field is created by marshmallow_sqalchemy
    address = auto_field()


class TestSmartRelationshipsMixin:
    def test_only(self):
        parent = Parent(pk=1, col="p")
        child = Child(pk=1, col="c", parent_pk=1, address_pk=1, parent=parent)
        child.hobbies = [Hobby(pk=1, name="Tennis"), Hobby(pk=2, name="petanque")]
        child.address = Address(pk=1, street="5th avenue", city="New-York")
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
            {"pk": 1, "col": "c", "parent_pk": 1, "address_pk": 1},
        )

        TestCase().assertDictEqual(
            ParentSchema(only=["childs", "childs.hobbies"]).dump(parent),
            {
                "pk": 1,
                "col": "p",
                "childs": [
                    {"pk": 1, "col": "c", "parent_pk": 1, "address_pk": 1, "hobbies": [1, 2]},
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
                        "address_pk": 1,
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
            {"pk": 1, "col": None, "parent_pk": None, "parent": None, "address_pk": None},
        )

    def test_no_firstlevel_fields(self):
        child = Child(pk=1)
        parent = Parent(pk=1, childs=[child])

        TestCase().assertDictEqual(
            ParentSchema(only=("-", "childs.pk")).dump(parent),
            {
                "childs": [{"pk": 1}],
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
