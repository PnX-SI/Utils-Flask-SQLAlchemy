"""move fr_numeric collation to public schema

La collation `fr_numeric` est référencée sans nom de schéma (`COLLATE "fr_numeric"`). Créée sans schéma
explicite par la migration ba207b468e31, elle peut se retrouver dans un schéma absent du `search_path`
(ex. gn_permissions) : la requête échoue avec « collation "fr_numeric" ... does not exist ».
Cette révision déplace la collation dans le schéma public pour les installations existantes.

Revision ID: 4c1e7a9d2b60
Revises: 1d09a9b67970
Create Date: 2026-11-25

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4c1e7a9d2b60"
down_revision = "1d09a9b67970"
branch_labels = None
depends_on = None


def upgrade():
    # Collation présente dans un autre schéma que public, et pas encore dans public : on la déplace.
    op.execute("""
        DO $$
        DECLARE
            current_schema_name text;
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_collation c
                JOIN pg_namespace n ON n.oid = c.collnamespace
                WHERE c.collname = 'fr_numeric' AND n.nspname = 'public'
            ) THEN
                RETURN;
            END IF;
            SELECT n.nspname INTO current_schema_name
            FROM pg_collation c
            JOIN pg_namespace n ON n.oid = c.collnamespace
            WHERE c.collname = 'fr_numeric'
            LIMIT 1;
            IF current_schema_name IS NOT NULL THEN
                EXECUTE format('ALTER COLLATION %I.fr_numeric SET SCHEMA public', current_schema_name);
            ELSE
                CREATE COLLATION public.fr_numeric (provider = icu, locale = 'fr_FR.UTF-8@colNumeric=yes');
            END IF;
        END
        $$;
        """)


def downgrade():
    # Pas de retour arrière : la collation reste dans public (la migration ba207b468e31 la crée là maintenant),
    # et de toute manière, le schéma précédent est inconnu et plus ou moins aléatoire.
    pass
