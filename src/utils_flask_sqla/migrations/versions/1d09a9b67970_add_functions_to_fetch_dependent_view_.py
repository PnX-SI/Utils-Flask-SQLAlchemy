"""add functions to fetch dependent view and recreate them

Revision ID: 1d09a9b67970
Revises: ba207b468e31
Create Date: 2026-08-12 11:12:11.614522

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1d09a9b67970"
down_revision = "ba207b468e31"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
    
    -- 1. Recursively find all views/matviews that (transitively) depend on
    --    a given table or view, ordered deepest-dependent first.
    
    CREATE OR REPLACE FUNCTION public.pg_view_dependency_tree(p_schema text, p_relname text)
    RETURNS TABLE(view_schema text, view_name text, view_kind text, depth int)
    LANGUAGE sql
    AS $$
        WITH RECURSIVE deps AS (
            SELECT
                dependent_ns.nspname::text AS view_schema,
                dependent_view.relname::text AS view_name,
                dependent_view.relkind::text AS view_kind,
                1 AS depth
            FROM pg_depend
            JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid
            JOIN pg_class dependent_view ON pg_rewrite.ev_class = dependent_view.oid
            JOIN pg_class source_table ON pg_depend.refobjid = source_table.oid
            JOIN pg_namespace dependent_ns ON dependent_view.relnamespace = dependent_ns.oid
            JOIN pg_namespace source_ns ON source_table.relnamespace = source_ns.oid
            WHERE source_table.relname = p_relname
              AND source_ns.nspname = p_schema
              AND dependent_view.relkind IN ('v', 'm')
              AND dependent_view.oid <> source_table.oid
    
            UNION
    
            SELECT
                dependent_ns.nspname::text,
                dependent_view.relname::text,
                dependent_view.relkind::text,
                deps.depth + 1
            FROM deps
            JOIN pg_namespace source_ns ON source_ns.nspname = deps.view_schema
            JOIN pg_class source_table
                ON source_table.relname = deps.view_name
               AND source_table.relnamespace = source_ns.oid
            JOIN pg_depend ON pg_depend.refobjid = source_table.oid
            JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid
            JOIN pg_class dependent_view ON pg_rewrite.ev_class = dependent_view.oid
            JOIN pg_namespace dependent_ns ON dependent_view.relnamespace = dependent_ns.oid
            WHERE dependent_view.relkind IN ('v', 'm')
              AND dependent_view.oid <> source_table.oid
        )
        SELECT view_schema, view_name, view_kind, MAX(depth) AS depth
        FROM deps
        GROUP BY view_schema, view_name, view_kind
        ORDER BY depth DESC;  -- most-dependent first (correct drop order)
    $$;
    
    
    -- 2. Capture full definitions (+ owner, + indexes for matviews) as jsonb,
    --    in drop order.
    CREATE OR REPLACE FUNCTION public.pg_capture_dependent_views(p_schema text, p_relname text)
    RETURNS jsonb
    LANGUAGE plpgsql
    AS $$
    DECLARE
        result jsonb := '[]'::jsonb;
        rec record;
        v_def text;
        v_owner text;
        v_indexes jsonb;
    BEGIN
        FOR rec IN
            SELECT * FROM public.pg_view_dependency_tree(p_schema, p_relname)
        LOOP
            SELECT pg_get_viewdef(format('%I.%I', rec.view_schema, rec.view_name)::regclass, true)
            INTO v_def;
    
            SELECT pg_get_userbyid(c.relowner) INTO v_owner
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = rec.view_name AND n.nspname = rec.view_schema;
    
            v_indexes := '[]'::jsonb;
            IF rec.view_kind = 'm' THEN
                SELECT coalesce(jsonb_agg(indexdef), '[]'::jsonb) INTO v_indexes
                FROM pg_indexes
                WHERE schemaname = rec.view_schema AND tablename = rec.view_name;
            END IF;
    
            result := result || jsonb_build_object(
                'schema', rec.view_schema,
                'name', rec.view_name,
                'kind', rec.view_kind,
                'definition', v_def,
                'owner', v_owner,
                'indexes', v_indexes
            );
        END LOOP;
        RETURN result;
    END;
    $$;
    
    
    -- 3. Drop the captured views (dependents first, order already correct
    --    in the jsonb array). CASCADE is a safety net, not the primary
    --    mechanism, since we already dropped dependents-first.
    CREATE OR REPLACE FUNCTION public.pg_drop_dependent_views(p_views jsonb)
    RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE
        rec jsonb;
        obj_type text;
    BEGIN
        FOR rec IN SELECT * FROM jsonb_array_elements(p_views)
        LOOP
            obj_type := CASE WHEN rec->>'kind' = 'm' THEN 'MATERIALIZED VIEW' ELSE 'VIEW' END;
            EXECUTE format('DROP %s IF EXISTS %I.%I CASCADE', obj_type, rec->>'schema', rec->>'name');
        END LOOP;
    END;
    $$;
    
    
    -- 4. Recreate the captured views in reverse order (dependencies before
    --    dependents), reapply owner, indexes, and refresh matviews.
    CREATE OR REPLACE FUNCTION public.pg_recreate_dependent_views(p_views jsonb)
    RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE
        rec jsonb;
        obj_type text;
        idx text;
        n int;
        i int;
    BEGIN
        n := jsonb_array_length(p_views);
        FOR i IN REVERSE (n - 1)..0 LOOP
            rec := p_views -> i;
            obj_type := CASE WHEN rec->>'kind' = 'm' THEN 'MATERIALIZED VIEW' ELSE 'VIEW' END;
    
            EXECUTE format('CREATE %s %I.%I AS %s',
                            obj_type, rec->>'schema', rec->>'name', rec->>'definition');
    
            IF rec->>'owner' IS NOT NULL THEN
                EXECUTE format('ALTER %s %I.%I OWNER TO %I',
                                obj_type, rec->>'schema', rec->>'name', rec->>'owner');
            END IF;
    
            IF jsonb_array_length(rec->'indexes') > 0 THEN
                FOR idx IN SELECT jsonb_array_elements_text(rec->'indexes')
                LOOP
                    EXECUTE idx;
                END LOOP;
            END IF;
    
            IF rec->>'kind' = 'm' THEN
                EXECUTE format('REFRESH MATERIALIZED VIEW %I.%I', rec->>'schema', rec->>'name');
            END IF;
        END LOOP;
    END;
    $$;
        """))


def downgrade():
    op.execute(sa.text("""
    DROP FUNCTION IF EXISTS public.pg_recreate_dependent_views(jsonb);
    DROP FUNCTION IF EXISTS public.pg_drop_dependent_views(jsonb);
    DROP FUNCTION IF EXISTS public.pg_capture_dependent_views(text, text);
    DROP FUNCTION IF EXISTS public.pg_view_dependency_tree(text, text);
        """))
