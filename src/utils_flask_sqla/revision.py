from contextlib import contextmanager
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import bindparam


@contextmanager
def alter_table_with_dependent_views(conn, schema, table_name):
    """
    Python wrapper that allows to modify a table/view with dependent views (and their dependant views).

    **Example**

    >>> with alter_table_with_dependent_views(conn,"gn_synthese","synthese"):
    >>>     op.execute("ALTER gn_synthese.synthese DROP COLUMN id_individual")

    Parameters
    ----------
    conn: any
        SQLAlchemy connection to your database
    schema: str
        name of the schema of the table
    table_name: str
        name of the table in your schema

    Notes
    -----
    This function relies on the existence of sql functions (`public.pg_capture_dependent_views`,
    `public.pg_drop_dependent_views`, `public.pg_recreate_dependent_views`) in your database !
    Make sure the revision 1d09a9b67970 is applied on your database !
    In an Alembic revision, you can enforce this by adding `depends_on = ("1d09a9b67970",)`
    """
    captured = conn.execute(
        text("SELECT public.pg_capture_dependent_views(:s, :t)"),
        {"s": schema, "t": table_name},
    ).scalar()

    conn.execute(
        text("SELECT public.pg_drop_dependent_views(:v)").bindparams(bindparam("v", type_=JSONB)),
        {"v": captured},
    )

    try:
        yield
    finally:
        conn.execute(
            text("SELECT public.pg_recreate_dependent_views(:v)").bindparams(
                bindparam("v", type_=JSONB)
            ),
            {"v": captured},
        )
