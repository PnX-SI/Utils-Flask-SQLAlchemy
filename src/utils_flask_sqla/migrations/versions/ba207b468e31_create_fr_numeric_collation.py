"""create fr_numeric collation

Revision ID: ba207b468e31
Revises: 3842a6d800a0
Create Date: 2022-05-02 14:00:09.987246

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ba207b468e31"
down_revision = "3842a6d800a0"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE COLLATION fr_numeric (provider = icu, locale = 'fr_FR.UTF-8@colNumeric=yes')
        """
    )


def downgrade():
    op.execute(
        """
        DROP COLLATION fr_numeric
        """
    )
