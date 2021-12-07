from uuid import uuid4
import datetime

import pytest
from unittest import TestCase
import json
from shapely import wkt

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import UUID, HSTORE, ARRAY, JSON, JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from utils_flask_sqla.serializers import serializable


db = SQLAlchemy()


@serializable(stringify=False)
class Parent(db.Model):
    pk = db.Column(db.Integer, primary_key=True)

@serializable(stringify=False)
class Child(db.Model):
    pk = db.Column(db.Integer, primary_key=True)
    parent_pk = db.Column(db.Integer, db.ForeignKey(Parent.pk))
    parent = relationship('Parent', backref='childs')

@serializable(stringify=False)
class A(db.Model):
    pk = db.Column(db.Integer, primary_key=True)

@serializable(stringify=False)
class B(db.Model):
    pk = db.Column(db.Integer, primary_key=True)
    a_pk = db.Column(db.Integer, db.ForeignKey(A.pk))
    a = relationship('A', backref='b_set')

@serializable(stringify=False)
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
            date = db.Column(db.Date)
            time = db.Column(db.Time)
            datetime = db.Column(db.DateTime)
            boolean = db.Column(db.Boolean)
            uuid = db.Column(UUID(as_uuid=True))
            hstore = db.Column(HSTORE)
            array = db.Column(ARRAY(db.Integer))
            json = db.Column(JSON)
            jsonb = db.Column(JSONB)
            geom = db.Column(Geometry("GEOMETRY", 4326))

        now = datetime.datetime.now()
        uuid = uuid4()
        json_data = {'a': ['b', 'c']}
        geom = wkt.loads('POINT(6 10)')
        kwargs = dict(pk=1,
                      string='string',
                      unicode='unicode',
                      date=now.date(),
                      time=now.time(),
                      datetime=now,
                      boolean=True,
                      uuid=uuid,
                      hstore={'a': ['b', 'c']},
                      json={'e': [1, 2]},
                      jsonb=[3, {'f': 'g'}],
                      array=[1, 2],
                      geom=geom)
        o = TestModel(**kwargs)
        d = o.as_dict(stringify=False)
        TestCase().assertDictEqual(kwargs, d)

        d = o.as_dict(exclude=['geom'])
        json.dumps(d)  # check dict is JSON-serializable

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
        @serializable(stringify=False)
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
        @serializable(fields=['v_set'], stringify=False)
        class U(db.Model):
            pk = db.Column(db.Integer, primary_key=True)

        @serializable(exclude=['u_pk'], stringify=False)
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
        @serializable(stringify=False)
        class O(db.Model):
            pk = db.Column(db.Integer, primary_key=True)

            def as_dict(self, data):
                data['o'] = True
                return data

        @serializable(stringify=False)
        class P(O):
            pass

        @serializable(stringify=False)
        class Q(O):
            def as_dict(self, data):
                data = super().as_dict()
                data['q'] = True
                return data

        @serializable(stringify=False)
        class R(P):
            def as_dict(self, data):
                data['r'] = True
                return data

        @serializable(stringify=False)
        class S(P):
            def as_dict(self):
                data = super().as_dict()
                data['s'] = True
                return data

        @serializable(stringify=False)
        class T(O):
            def as_dict(self, *args, **kwargs):
                data = super().as_dict(*args, **kwargs)
                data['t'] = True
                return data

        @serializable(exclude=['pk'], stringify=False)
        @serializable
        class W(O):
            pass

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

        w = W(pk=7)
        d = w.as_dict()
        TestCase().assertDictEqual({}, d)

    def test_renamed_field(self):
        @serializable(stringify=False)
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

    def test_polymorphic_model(self):
        @serializable(stringify=False)
        class PolyModel(db.Model):
            __mapper_args__ = {
                'polymorphic_identity': 'IdentityBase',
                'polymorphic_on': 'kind',
            }
            pk = db.Column(db.Integer, primary_key=True)
            kind = db.Column(db.String)
            base = db.Column(db.String)

        @serializable(stringify=False)
        class PolyModelA(PolyModel):
            __mapper_args__ = {
                'polymorphic_identity': 'A',
            }
            pk = db.Column(db.Integer, db.ForeignKey(PolyModel.pk), primary_key=True)
            a = db.Column(db.String)

        @serializable(stringify=False)
        class PolyModelB(PolyModel):
            __mapper_args__ = {
                'polymorphic_identity': 'B',
            }
            pk = db.Column(db.Integer, db.ForeignKey(PolyModel.pk), primary_key=True)
            b = db.Column(db.String)

        a = PolyModelA(pk=1, base='BA', a='A')
        d = a.as_dict()
        TestCase().assertDictEqual({
            'pk': 1,
            'kind': 'A',
            'base': 'BA',
            'a': 'A',
        }, d)

        b = PolyModelB(pk=2, base='BB', b='B')
        d = b.as_dict()
        TestCase().assertDictEqual({
            'pk': 2,
            'kind': 'B',
            'base': 'BB',
            'b': 'B',
        }, d)

        d = {
            'pk': 2,
            'kind': 'B',
            'base': 'BB',
            'b': 'B',
        }
        TestCase().assertDictEqual(d, PolyModelB().from_dict(d).as_dict())

    def test_hybrid_property(self):
        @serializable(stringify=False)
        class HybridModel(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            part1 = db.Column(db.String)
            part2 = db.Column(db.String)

            @hybrid_property
            def concat(self):
                return '{0} {1}'.format(self.part1, self.part2)

            @concat.expression
            def concat(cls):
                return db.func.concat(cls.part1, ' ', cls.part2)

        h = HybridModel(pk=1, part1='a', part2='b')
        d = h.as_dict()
        TestCase().assertDictEqual({
            'pk': 1,
            'part1': 'a',
            'part2': 'b',
            'concat': 'a b',
        }, d)

    def test_additional_fields(self):
        @serializable(fields=['v_set'], exclude=['field2'])
        class U2(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            field1 = db.Column(db.String)
            field2 = db.Column(db.String)

        @serializable(fields=['pk'])
        class V2(db.Model):
            pk = db.Column(db.Integer, primary_key=True)
            u_pk = db.Column(db.Integer, db.ForeignKey(U2.pk))
            u = relationship('U2', backref='v_set')

        u = U2(pk=1, field1='test', field2='test')
        v = V2(pk=1, u_pk=u.pk, u=u)

        d = u.as_dict()
        TestCase().assertDictEqual({
            'pk': 1,
            'field1': 'test',
            'v_set': [{'pk': 1}],
        }, d)

        d = u.as_dict(exclude=[])
        TestCase().assertDictEqual({
            'pk': 1,
            'field1': 'test',
            'field2': 'test',
            'v_set': [{'pk': 1}],
        }, d)

        d = u.as_dict(fields=['field1'])
        TestCase().assertDictEqual({
            'field1': 'test',
        }, d)

        # Verify that field2 is removed from default_exclude
        d = u.as_dict(fields=['field1', 'field2'])
        TestCase().assertDictEqual({
            'field1': 'test',
            'field2': 'test',
        }, d)

        # Verify that field2 is removed from default_exclude
        d = u.as_dict(fields=['field1', '+field2'])
        TestCase().assertDictEqual({
            'field1': 'test',
            'field2': 'test',
        }, d)

        # Verify that field2 is removed from default_exclude
        d = u.as_dict(fields=['field2'])
        TestCase().assertDictEqual({
            'field2': 'test',
        }, d)

        # Verify that field2 is removed from default_exclude, will keeping default_fields
        d = u.as_dict(fields=['+field2', 'v_set'])
        TestCase().assertDictEqual({
            'pk': 1,
            'field1': 'test',
            'field2': 'test',
            'v_set': [{'pk': 1}],
        }, d)

        d = u.as_dict(fields=['v_set.u_pk'])
        TestCase().assertDictEqual({
            'pk': 1,
            'field1': 'test',
            'v_set': [{'u_pk': 1}],
        }, d)

        d = u.as_dict(fields=['v_set.+u_pk'])
        TestCase().assertDictEqual({
            'pk': 1,
            'field1': 'test',
            'v_set': [{'pk': 1, 'u_pk': 1}],
        }, d)
