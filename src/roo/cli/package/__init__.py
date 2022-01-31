import pathlib

import click
from roo.console import console
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
        console().print(
            f":earth_africa: [source]{source.name}[/source] "
            f"({source.location})")
        with console().status("Searching ... "):
            for package in source.find_package_versions(name):
                icon = ":glowing_star:" if package.active else ":package:"
                console().print(
                    f"  {icon} [package]{package.name}[/package]"
                    f" [version]{package.version}" +

                    (" ([active]Active[/active]) " if package.active else ""))
        console().print("")


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
