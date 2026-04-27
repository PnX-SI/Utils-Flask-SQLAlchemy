from flask_sqlalchemy.session import Session


class TestSession(Session):
    join_transaction_mode = "create_savepoint"
    expire_on_commit = False

    def commit(self):
        if self.in_nested_transaction():
            self.flush()
        else:
            super().commit()
