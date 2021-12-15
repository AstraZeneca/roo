import pathlib

import click
from roo.parsers.rproject import RProject
from roo.sources.source_group import create_source_group_from_config_list


@click.group(help="Subgroup for package management commands")
def package():
    pass


@package.command(name="search",
                 help="Searches a given package in the sources specified"
                      " by the current rproject.toml")
@click.argument("name", type=click.STRING)
def package_search(name):
    try:
        rproject = RProject.parse(pathlib.Path(".") / "rproject.toml")
    except IOError:
        raise click.ClickException(
            "Unable to open rproject.toml in current directory"
        )

    source_group = create_source_group_from_config_list(rproject.sources)
    for source in source_group.all_sources:
        click.echo(f"Source: {source.name}")
        for package in source.find_package_versions(name):
            click.echo("    " + package.versioned_name +
                       (" (Active) " if package.active else ""))
        click.echo("")


@package.command(name="dependencies",
                 help="Shows the dependencies of a given package, given its "
                      "name and version.")
@click.argument("name", type=click.STRING)
@click.argument("version", type=click.STRING)
def package_dependencies(name, version):
    try:
        rproject = RProject.parse(pathlib.Path(".") / "rproject.toml")
    except IOError:
        raise click.ClickException(
            "Unable to open rproject.toml in current directory"
        )

    source_group = create_source_group_from_config_list(rproject.sources)
    for source in source_group.all_sources:
        package = source.find_package(name, version)
        if package is not None:
            for dep in package.dependencies:
                click.echo(dep.name)
            break
    else:
        click.echo(f"Unable to find package {name} {version}")
