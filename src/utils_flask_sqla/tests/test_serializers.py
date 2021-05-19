from datetime import datetime
from uuid import uuid4

import pytest
from unittest import TestCase
import json
from jsonschema import validate

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, HSTORE, ARRAY, JSON, JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from utils_flask_sqla.serializers import serializable


db = SQLAlchemy()


@serializable
class Parent(db.Model):
    pk = db.Column(db.Integer, primary_key=True)

@serializable
class Child(db.Model):
    pk = db.Column(db.Integer, primary_key=True)
    parent_pk = db.Column(db.Integer, db.ForeignKey(Parent.pk))
    parent = relationship('Parent', backref='childs')

@serializable
class A(db.Model):
    pk = db.Column(db.Integer, primary_key=True)

@serializable
class B(db.Model):
    pk = db.Column(db.Integer, primary_key=True)
    a_pk = db.Column(db.Integer, db.ForeignKey(A.pk))
    a = relationship('A', backref='b_set')

@serializable
class C(db.Model):
    pk = db.Column(db.Integer, primary_key=True)
    b_pk = db.Column(db.Integer, db.ForeignKey(B.pk))
    b = relationship('B', backref='c_set')


class TestSerializers:
    def test_types(self):
        @serializable
        class TestModel(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            string = db.Column(db.String)
            unicode = db.Column(db.Unicode)
            datetime = db.Column(db.DateTime)
            boolean = db.Column(db.Boolean)
            uuid = db.Column(UUID(as_uuid=True))
            hstore = db.Column(HSTORE)
            array = db.Column(ARRAY(db.Integer))
            json = db.Column(JSON)
            jsonb = db.Column(JSONB)
            geom = db.Column(Geometry("GEOMETRY", 4326))

        o = TestModel(pk=1, string='string', unicode='unicode',
                         datetime=datetime.now(), boolean=True,
                         uuid=uuid4(), hstore={'a': ['b', 'c']},
                         json={'a': [1, 2]},
                         jsonb={'a': [1, 2]},
                         array=[1, 2], geom='POINT(6 10)')
        d = o.as_dict()
        json.dumps(d)  # check dict is JSON-serializable
        validate(d, {
            'type': 'object',
            'properties': {
                'pk': { 'type': 'integer', },
                'string': { 'type': 'string', },
                'unicode': { 'type': 'string', },
                'datetime': { 'type': 'string', },
                'boolean': { 'type': 'boolean', },
                'uuid': { 'type': 'string', },
                'array': { 'type': 'array', },
                'json': { 'type': 'object', },
                'jsonb': { 'type': 'object', },
                'hstore': {
                    'type': 'object',
                    'properties': {
                        'a': {
                            'type': 'array',
                            'items': { 'type': 'string', },
                        },
                    },
                },
                'geom': { 'type': 'string', },
            },
            'minProperties': 8,
            'additionalProperties': False,
        })

    def test_many_to_one(self):
        parent = Parent(pk=1)
        child = Child(pk=1, parent_pk=parent.pk, parent=parent)

        d = parent.as_dict()
        TestCase().assertDictEqual({'pk': 1}, d)

        d = child.as_dict()
        TestCase().assertDictEqual({'pk': 1, 'parent_pk': 1}, d)

        with pytest.deprecated_call():
            d =  parent.as_dict(recursif=True)  # no recursion limit
        TestCase().assertDictEqual({
            'pk': 1,
            'childs': [{
                'pk': 1,
                'parent_pk': 1,
            }],
        }, d)

        with pytest.deprecated_call():
            d =  child.as_dict(recursif=True)  # no recursion limit
        TestCase().assertDictEqual({
            'pk': 1,
            'parent_pk': 1,
            'parent': {
                'pk': 1,
            },
        }, d)

        with pytest.deprecated_call():
            d =  parent.as_dict(recursif=True, depth=1)
        TestCase().assertDictEqual({
            'pk': 1,
            'childs': [{
                'pk': 1,
                'parent_pk': 1,
            }],
        }, d)

        with pytest.deprecated_call():
            d =  child.as_dict(recursif=True, depth=1)
        TestCase().assertDictEqual({
            'pk': 1,
            'parent_pk': 1,
            'parent': {
                'pk': 1,
            },
        }, d)

        with pytest.deprecated_call():
            d = parent.as_dict(recursif=True, depth=2)
        # depth=2 must not go further than depth=1 because of loop-avoidance
        TestCase().assertDictEqual({
            'pk': 1,
            'childs': [{
                'pk': 1,
                'parent_pk': 1,
            }],
        }, d)

        d = parent.as_dict(fields=['childs'])
        TestCase().assertDictEqual({
            'pk': 1,
            'childs': [{
                'pk': 1,
                'parent_pk': 1,
            }]
        }, d)

    def test_depth(self):
        a = A(pk=1)
        b = B(pk=10, a_pk=a.pk, a=a)
        c = C(pk=100, b_pk=b.pk, b=b)

        with pytest.deprecated_call():
            d = a.as_dict(recursif=True, depth=0)
        TestCase().assertDictEqual({
            'pk': 1,
        }, d)

        with pytest.deprecated_call():
            d = a.as_dict(recursif=True, depth=1)
        TestCase().assertDictEqual({
            'pk': 1,
            'b_set': [{
                'pk': 10,
                'a_pk': 1,
            }],
        }, d)

        with pytest.deprecated_call():
            d = a.as_dict(recursif=True, depth=2)
        TestCase().assertDictEqual({
            'pk': 1,
            'b_set': [{
                'pk': 10,
                'a_pk': 1,
                'c_set': [{
                    'pk': 100,
                    'b_pk': 10,
                }],
            }],
        }, d)

        with pytest.deprecated_call():
            d = a.as_dict(recursif=True, depth=3)
        TestCase().assertDictEqual({
            'pk': 1,
            'b_set': [{
                'pk': 10,
                'a_pk': 1,
                'c_set': [{
                    'pk': 100,
                    'b_pk': 10,
                }],
            }],
        }, d)

    def test_relationships(self):
        a = A(pk=1)
        b = B(pk=10, a_pk=a.pk, a=a)
        c = C(pk=100, b_pk=b.pk, b=b)

        # as 'pk' is specified, 'b_pk' is not taken
        d = c.as_dict(fields=['pk', 'b'])
        TestCase().assertDictEqual({
            'pk': 100,
            'b': {
                'pk': 10,
                'a_pk': 1,
            },
        }, d)

        d = c.as_dict(fields=['pk', 'b.pk'])
        TestCase().assertDictEqual({
            'pk': 100,
            'b': {
                'pk': 10,
            },
        }, d)

        d = c.as_dict(fields=['pk', 'b.a'])
        TestCase().assertDictEqual({
            'pk': 100,
            'b': {
                'pk': 10,
                'a_pk': 1,
                'a': {
                    'pk': 1,
                },
            },
        }, d)

        d = c.as_dict(fields=['pk', 'b.pk', 'b.a'])
        TestCase().assertDictEqual({
            'pk': 100,
            'b': {
                'pk': 10,
                'a': {
                    'pk': 1,
                },
            },
        }, d)

        d = c.as_dict(fields=['b.c_set.b', 'b.c_set.pk'])
        TestCase().assertDictEqual({
            'pk': 100,
            'b_pk': 10,
            'b': {
                'pk': 10,
                'a_pk': 1,
                'c_set': [{
                    'pk': 100,
                    'b': {
                        'pk': 10,
                        'a_pk': 1,
                    },
                }],
            },
        }, d)

        d = c.as_dict(fields=['b', 'b.c_set'], exclude=['b_pk', 'b.a_pk', 'b.c_set.pk'])
        TestCase().assertDictEqual({
            'pk': 100,
            'b': {
                'pk': 10,
                'c_set': [{
                    'b_pk': 10,
                }],
            },
        }, d)

    def test_unexisting_field(self):
        @serializable
        class Model(db.Model):
            pk = db.Column(db.Integer, primary_key=True)

        obj = Model(pk=1)
        d = obj.as_dict(fields=['pk'])
        TestCase().assertDictEqual({'pk': 1}, d)
        with pytest.raises(Exception) as excinfo:
            obj.as_dict(fields=['unexisting'])
        assert('does not exist on' in str(excinfo.value))
        with pytest.raises(Exception) as excinfo:
            obj.as_dict(fields=['pk.unexisting'])
        assert('does not exist on' in str(excinfo.value))

    def test_backward_compatibility(self):
        parent = Parent(pk=1)
        child = Child(pk=1, parent_pk=parent.pk, parent=parent)

        with pytest.deprecated_call():
            d = child.as_dict(columns=['parent_pk'])
        TestCase().assertDictEqual({'parent_pk': 1}, d)

        with pytest.deprecated_call():
            d = parent.as_dict(relationships=['childs'])
        TestCase().assertDictEqual({
            'pk': 1,
            'childs': [{
                'pk': 1,
                'parent_pk': 1,
            }],
        }, d)

        with pytest.deprecated_call():
            d = child.as_dict(columns=['pk'], relationships=['parent'])
        TestCase().assertDictEqual({
            'pk': 1,
            'parent': {
                'pk': 1,
            },
        }, d)

    def test_serializable_parameters(self):
        @serializable(fields=['v_set'])
        class U(db.Model):
            pk = db.Column(db.Integer, primary_key=True)

        @serializable(exclude=['u_pk'])
        class V(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            u_pk = db.Column(db.Integer, db.ForeignKey(U.pk))
            u = relationship('U', backref='v_set')

        u = U(pk=1)
        v = V(pk=1, u_pk=u.pk, u=u)

        d = u.as_dict()
        TestCase().assertDictEqual({
            'pk': 1,
            'v_set': [{
                'pk': 1,
            }],
        }, d)

        d = v.as_dict()
        TestCase().assertDictEqual({
            'pk': 1,
        }, d)

        d = u.as_dict(fields=None, exclude=None)
        TestCase().assertDictEqual({
            'pk': 1,
            'v_set': [{
                'pk': 1,
            }],
        }, d)

        d = v.as_dict(fields=None, exclude=None)
        TestCase().assertDictEqual({
            'pk': 1,
        }, d)

        d = u.as_dict(fields=[])
        TestCase().assertDictEqual({
            'pk': 1,
        }, d)

        d = v.as_dict(exclude=[])
        TestCase().assertDictEqual({
            'pk': 1,
            'u_pk': 1,
        }, d)

        d = v.as_dict(fields=['u.pk'])
        TestCase().assertDictEqual({
            'pk': 1,
            'u': {
                'pk': 1,
            },
        }, d)

        d = v.as_dict(fields=['u'])  # use default U serialization parameters
        TestCase().assertDictEqual({
            'pk': 1,
            'u': {
                'pk': 1,
                'v_set': [{
                    'pk': 1,
                }],
            },
        }, d)

    def test_as_dict_override(self):
        @serializable
        class O(db.Model):
            pk = db.Column(db.Integer, primary_key=True)

            def as_dict(self, data):
                data['o'] = True
                return data

        @serializable
        class P(O):
            pass

        @serializable
        class Q(O):
            def as_dict(self, data):
                data = super().as_dict()
                data['q'] = True
                return data

        @serializable
        class R(P):
            def as_dict(self, data):
                data['r'] = True
                return data

        @serializable
        class S(P):
            def as_dict(self):
                data = super().as_dict()
                data['s'] = True
                return data

        @serializable
        class T(O):
            def as_dict(self, *args, **kwargs):
                data = super().as_dict(*args, **kwargs)
                data['t'] = True
                return data

        o = O(pk=1)
        d = o.as_dict()
        TestCase().assertDictEqual({
            'pk': 1,
            'o': True,
        }, d)

        p = P(pk=2)
        d = p.as_dict()
        TestCase().assertDictEqual({
            'pk': 2,
        }, d)

        q = Q(pk=3)
        d = q.as_dict()
        TestCase().assertDictEqual({
            'pk': 3,
            'o': True,
            'q': True,
        }, d)

        r = R(pk=4)
        d = r.as_dict()
        TestCase().assertDictEqual({
            'pk': 4,
            'r': True,
        }, d)

        s = S(pk=5)
        d = s.as_dict()
        TestCase().assertDictEqual({
            'pk': 5,
            's': True,
        }, d)

        t = T(pk=6)
        d = t.as_dict(fields=['pk'])
        TestCase().assertDictEqual({
            'pk': 6,
            'o': True,
            't': True,
        }, d)

    def test_renamed_field(self):
        @serializable
        class TestModel2(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            field = db.Column('column', db.String)

        o = TestModel2(pk=1, field='test')
        d = o.as_dict()
        TestCase().assertDictEqual({
            'pk': 1,
            'field': 'test',
        }, d)

    def test_null_relationship(self):
        parent = Parent(pk=1)
        child = Child(pk=1, parent_pk=None, parent=None)

        d = parent.as_dict(fields=['childs'])
        TestCase().assertDictEqual({
            'pk': 1,
            'childs': [],
        }, d)

        d = child.as_dict(fields=['parent'])
        TestCase().assertDictEqual({
            'pk': 1,
            'parent_pk': None,
            'parent': None,
        }, d)
