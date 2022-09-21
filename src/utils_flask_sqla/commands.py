from collections import deque, defaultdict
from itertools import chain
from io import StringIO
import json

import click
import flask_migrate
from flask import current_app
from alembic.migration import MigrationContext
from alembic.context import EnvironmentContext
from alembic.script import ScriptDirectory
from flask_migrate.cli import db as db_cli
from flask.cli import with_appcontext


def box_drowing(up, down, left, right, bold=True):
    if not up and not down and not left and not right:
        return "─"
    elif up and not down and not left and not right:
        return "┸"
    elif not up and down and not left and not right:
        return "┰"
    elif up and down and not left and not right:
        return "┃"
    elif up and not down and left and not right:
        return "┛"
    elif up and not down and not left and right:
        return "┗" if bold else "└"
    elif not up and not down and left and right:
        return "━"
    elif not up and down and left and not right:
        return "┓"
    elif not up and down and not left and right:
        return "┏"
    elif up and down and not left and right:
        return "┣" if bold else "├"
    elif up and down and left and not right:
        return "┫"
    elif up and not down and left and right:
        return "┻"
    elif not up and down and left and right:
        return "┳"
    elif up and down and left and right:
        return "╋"
    else:
        raise Exception("Unexpected box drowing symbol")


@db_cli.command()
@click.argument("command", nargs=-1, required=True)
@click.option("--commit/--no-commit", default=True, help="Commit transaction.")
@click.option("--json", "json_output", is_flag=True, help="Output commands results as JSON.")
@with_appcontext
def exec(command, commit, json_output):
    db = current_app.extensions["sqlalchemy"].db
    results = []
    for cmd in command:
        results.append(db.session.execute(cmd))
    if commit:
        db.session.commit()
    if json_output:
        results = [
            [dict(row) for row in result] if result.returns_rows else [] for result in results
        ]
        if len(results) == 1:
            (results,) = results
        click.echo(current_app.json.dumps(results))


@db_cli.command()
@click.option(
    "-d",
    "--directory",
    default=None,
    help=('Migration script directory (default is "migrations")'),
)
@click.option(
    "--sql", is_flag=True, help=("Don't emit SQL to database - dump to standard output " "instead")
)
@click.option(
    "--tag", default=None, help=('Arbitrary "tag" name - can be used by custom env.py ' "scripts")
)
@click.option(
    "-x", "--x-arg", multiple=True, help="Additional arguments consumed by custom env.py scripts"
)
@with_appcontext
def autoupgrade(directory, sql, tag, x_arg):
    """Upgrade all branches to head."""
    db = current_app.extensions["sqlalchemy"].db
    migrate = current_app.extensions["migrate"].migrate
    config = migrate.get_config(directory, x_arg)
    script = ScriptDirectory.from_config(config)
    heads = set(script.get_heads())
    migration_context = MigrationContext.configure(db.session.connection())
    current_heads = migration_context.get_current_heads()
    # get_current_heads does not return implicit revision through dependecies, get_all_current does
    current_heads = set(map(lambda rev: rev.revision, script.get_all_current(current_heads)))
    for head in current_heads - heads:
        revision = head + "@head"
        flask_migrate.upgrade(directory, revision, sql, tag, x_arg)


@db_cli.command()
@click.option(
    "-d",
    "--directory",
    default=None,
    help=('Migration script directory (default is "migrations")'),
)
@click.option(
    "-x", "--x-arg", multiple=True, help="Additional arguments consumed by custom env.py scripts"
)
@click.option(
    "--deps", "--dependencies", "show_dependencies", is_flag=True, help="Show dependencies"
)
@click.argument("branches", nargs=-1)
@with_appcontext
def status(directory, x_arg, show_dependencies, branches):
    """Show all revisions sorted by branches."""
    db = current_app.extensions["sqlalchemy"].db
    migrate = current_app.extensions["migrate"].migrate

    config = migrate.get_config(directory, x_arg)
    script = ScriptDirectory.from_config(config)
    migration_context = MigrationContext.configure(db.session.connection())

    current_heads = migration_context.get_current_heads()
    applied_rev = set(script.iterate_revisions(current_heads, "base"))

    bases = [script.get_revision(base) for base in script.get_bases()]
    bases = {
        next(iter(base.branch_labels)): base
        for base in sorted(bases, key=lambda rev: next(iter(rev.branch_labels)))
    }
    heads = [script.get_revision(head) for head in script.get_heads()]

    def print_revision(
        prefix, revision, *, file=None, show_branch_label=False, show_dependencies=False
    ):
        (branch_label,) = revision.branch_labels
        branch_base = bases[branch_label]
        if branch_base in applied_rev:
            fg = "white" if revision in applied_rev else "red"
        else:
            fg = None
        branch_display = f"({branch_label}) " if show_branch_label else ""
        print(
            click.style(f"{prefix}{branch_display}{revision.revision} {revision.doc}", fg=fg),
            file=file,
        )
        if show_dependencies and revision.dependencies:
            deps = (
                (revision.dependencies,)
                if type(revision.dependencies) == str
                else revision.dependencies
            )
            for i, dep in enumerate(deps):
                dep = script.get_revision(dep)
                symbol = box_drowing(
                    up=True, down=i < len(deps) - 1, left=False, right=True, bold=False
                )
                print_revision(
                    " " * len(prefix) + symbol + " ",
                    dep,
                    file=output,
                    show_branch_label=True,
                    show_dependencies=show_dependencies,
                )

    outdated = False
    for branch_label, branch_base in bases.items():
        output = StringIO()
        if branches and branch_label not in branches:
            continue
        levels = defaultdict(set)
        branch_outdated = False
        seen = set()
        todo = deque()
        todo.append(branch_base)
        while todo:
            rev = todo.pop()

            down_levels = levels[rev]
            if rev.is_merge_point:
                down_revisions = rev.down_revision
            elif rev.down_revision:
                down_revisions = [rev.down_revision]
            else:
                down_revisions = []
            down_revisions = [script.get_revision(r) for r in down_revisions]

            next_revisions = [script.get_revision(r) for r in rev.nextrev]

            if rev.is_merge_point and (not seen.issuperset(down_revisions) or rev in todo):
                continue
            seen.add(rev)

            next_levels = set()
            for j, nextrev in enumerate(next_revisions):
                if j == 0:
                    next_level = min(down_levels) if down_levels else 0
                else:
                    next_level = max(chain(*[levels[rev] for rev in todo])) + 1
                levels[nextrev].add(next_level)
                next_levels.add(next_level)
                todo.append(nextrev)

            all_levels = list(chain(down_levels, next_levels))
            min_level = min(all_levels, default=0)
            max_level = max(all_levels, default=0)
            symbol = ""
            for i in range(max_level + 1):
                if i < min_level:
                    symbol += " "
                else:
                    symbol += box_drowing(
                        up=i in down_levels,
                        down=i in next_levels,
                        left=i > min_level,
                        right=i < max_level,
                    )

            check = "x" if rev in applied_rev else " "
            if branch_base in applied_rev and rev not in applied_rev:
                outdated = True
                branch_outdated = True
            print_revision(
                f"  [{check}] {symbol} ",
                rev,
                file=output,
                show_dependencies=show_dependencies,
            )

        if branch_base in applied_rev:
            fg = "white"
            mark = " "
            mark += click.style("×", fg="red") if branch_outdated else click.style("✓", fg="green")
        else:
            fg = None
            mark = ""
        click.echo(
            click.style(f"[{branch_label}", bold=True, fg=fg)
            + mark
            + click.style("]", bold=True, fg=fg)
        )
        click.echo(output.getvalue(), nl=False)

    if outdated:
        click.secho(
            "Some branches are outdated, you can upgrade with 'autoupgrade' sub-command.", fg="red"
        )
