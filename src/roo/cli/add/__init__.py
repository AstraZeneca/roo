import pathlib

import click
from roo.parsers.rproject import RProject, Dependency
from roo.semver import VersionRange


@click.command(
    name="add", help="Add the most recent package to the rproject.toml")
@click.option("--category",
              help=(
                  "Install the deps of the specified category. "
                  "Can be provided multiple times."),
              type=click.Choice(RProject.ALL_DEPENDENCY_CATEGORIES),
              default="main"
              )
@click.argument("package", type=click.STRING)
def add(category: str, package: str):
    try:
        rproject = RProject.parse(pathlib.Path(".") / "rproject.toml")
    except IOError:
        raise click.ClickException(
            "Unable to open rproject.toml in current directory"
        )

    rproject.dependencies.append(
        Dependency(
            name=package,
            constraint=VersionRange(),
            category=category,
            vcs_spec=None
        )
    )
    rproject.save()
