import sys

if sys.version_info < (3, 10):

    def pairwise(iterable):
        # pairwise('ABCDEFG') → AB BC CD DE EF FG

        iterator = iter(iterable)
        a = next(iterator, None)

        for b in iterator:
            yield a, b
            a = b

else:
    from itertools import pairwise


import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
from werkzeug.exceptions import BadRequest

from utils_flask_sqla.db import ordered


db = SQLAlchemy()


class Parent(db.Model):
    pk = db.Column(db.Integer, primary_key=True)


class Child(db.Model):
    pk = db.Column(db.Integer, primary_key=True)
    parent_pk = db.Column(db.Integer, db.ForeignKey(Parent.pk))
    parent = db.relationship("Parent", backref="childs")


@pytest.fixture(scope="session")
def app():
    app = Flask("utils-flask-sqla")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///"
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture(scope="class")
def data(app):
    p1 = Parent(pk=1)
    p2 = Parent(pk=2)
    c1 = Child(pk=1, parent_pk=1)
    c2 = Child(pk=2, parent_pk=2)
    c3 = Child(pk=3, parent_pk=1)
    c4 = Child(pk=4, parent_pk=2)
    with db.session.begin_nested():
        db.session.add_all([p1, p2, c1, c2, c3, c4])


@pytest.mark.usefixtures("data")
class TestOrdered:
    def test_no_ordering(self, app):
        query = sa.select(Parent)

        with app.test_request_context():
            stmt = ordered(query, Parent)
            results = db.session.execute(stmt).scalars()

    def test_ordered_default(self, app):
        query = sa.select(Parent)

        with app.test_request_context():
            stmt = ordered(query, Parent, order_by="pk")
            results = db.session.execute(stmt).scalars()
            for o1, o2 in pairwise(results):
                assert o1.pk < o2.pk

            stmt = ordered(query, Parent, order_by=Parent.pk.desc())
            results = db.session.execute(stmt).scalars()
            for o1, o2 in pairwise(results):
                assert o1.pk > o2.pk

            stmt = ordered(query, Parent, order_by=[Parent.pk.asc()])
            results = db.session.execute(stmt).scalars()
            for o1, o2 in pairwise(results):
                assert o1.pk < o2.pk

    def test_ordered_column(self, app):
        query = sa.select(Parent)

        with app.test_request_context("?sort=pk"):
            stmt = ordered(query, Parent)
            results = db.session.execute(stmt).scalars()
            for o1, o2 in pairwise(results):
                assert o1.pk < o2.pk

        with app.test_request_context("?sort=-pk"):
            stmt = ordered(query, Parent)
            results = db.session.execute(stmt).scalars()
            for o1, o2 in pairwise(results):
                assert o1.pk > o2.pk

    def test_ordered_relationship_not_joined(self, app):
        query = sa.select(Child)

        with app.test_request_context("?sort=parent.pk"):
            with pytest.raises(BadRequest, match=".*not part of from clauses.*"):
                stmt = ordered(query, Child)

    def test_ordered_relationship_manually_joined(self, app):
        query = sa.select(Child).join(Parent)

        with app.test_request_context("?sort=parent.pk"):
            stmt = ordered(query, Child)
            results = db.session.execute(stmt).scalars()
            for o1, o2 in pairwise(results):
                assert o1.parent.pk <= o2.parent.pk

        with app.test_request_context("?sort=-parent.pk"):
            stmt = ordered(query, Child)
            results = db.session.execute(stmt).scalars()
            for o1, o2 in pairwise(results):
                assert o1.parent.pk >= o2.parent.pk

    def test_ordered_relationship_auto_joined(self, app):
        query = sa.select(Child)

        with app.test_request_context("?sort=parent.pk"):
            stmt = ordered(query, Child, join=True)
            results = db.session.execute(stmt).scalars()
            for o1, o2 in pairwise(results):
                assert o1.parent.pk <= o2.parent.pk

        with app.test_request_context("?sort=-parent.pk"):
            stmt = ordered(query, Child, join=True)
            results = db.session.execute(stmt).scalars()
            for o1, o2 in pairwise(results):
                assert o1.parent.pk >= o2.parent.pk

    def test_ordered_multiple_criterias(self, app):
        query = sa.select(Child)

        with app.test_request_context("?sort=parent.pk,pk"):
            stmt = ordered(query, Child, join=True)
            results = db.session.execute(stmt).scalars()
            for o1, o2 in pairwise(results):
                assert o1.parent.pk <= o2.parent.pk
                if o1.parent.pk == o2.parent.pk:
                    assert o1.pk < o2.pk

        with app.test_request_context("?sort=parent.pk,-pk"):
            stmt = ordered(query, Child, join=True)
            results = db.session.execute(stmt).scalars()
            for o1, o2 in pairwise(results):
                assert o1.parent.pk <= o2.parent.pk
                if o1.parent.pk == o2.parent.pk:
                    assert o1.pk > o2.pk

    def test_ordered_unexisting_criterias(self, app):
        query = sa.select(Child)

        with app.test_request_context("?sort=unexisting"):
            with pytest.raises(BadRequest, match=".*does not have.*"):
                stmt = ordered(query, Child, join=True)

        with app.test_request_context("?sort=unexisting.pk"):
            with pytest.raises(BadRequest, match=".*does not have.*"):
                stmt = ordered(query, Child, join=True)

        with app.test_request_context("?sort=parent.unexisting"):
            with pytest.raises(BadRequest, match=".*does not have.*"):
                stmt = ordered(query, Child, join=True)
