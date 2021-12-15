import pathlib

import click
from roo.parsers.rproject import RProject, Source


@click.command(
    name="init",
    help="Create a basic rproject.toml"
)
def init():
    path = pathlib.Path("rproject.toml")
    if path.exists():
        raise click.ClickException("File rproject.toml already present.")

    rproject = RProject()
    rproject.path = "rproject.toml"
    rproject.metadata.name = "myproject"
    rproject.metadata.version = "0.1.0"
    rproject.sources.append(
        Source(name="CRAN", url="https://cloud.r-project.org/")
    )

    rproject.save()
