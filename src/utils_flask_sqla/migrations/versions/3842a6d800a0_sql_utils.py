"""Add public shared functions

Revision ID: 3842a6d800a0
Revises:
Create Date: 2021-09-17 08:00:57.784074

"""
import importlib.resources

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3842a6d800a0'
down_revision = None
branch_labels = ('sql_utils',)
depends_on = None


def upgrade():
    op.execute('''
CREATE OR REPLACE FUNCTION public.fct_trg_meta_dates_change()
    RETURNS trigger AS
    $BODY$
        BEGIN
            IF(TG_OP = 'INSERT') THEN
                    NEW.meta_create_date = NOW();
            ELSIF(TG_OP = 'UPDATE') THEN
                    NEW.meta_update_date = NOW();
                    IF(NEW.meta_create_date IS NULL) THEN
                            NEW.meta_create_date = NOW();
                    END IF;
            END IF;
            RETURN NEW;
        END;
    $BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
''')


def downgrade():
    op.execute('''
DROP FUNCTION public.fct_trg_meta_dates_change();
    ''')
