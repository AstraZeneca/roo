import pathlib
import logging
import os
from typing import Union

import click
import shutil

from ..environment import Environment, available_environments, \
    UnexistentEnvironment, enabled_environment
from ..exporters.lock.base_exporter import BaseExporter
from ..exporters.lock.lock_csv_exporter import LockCSVExporter
from ..exporters.lock.lock_packrat_exporter import LockPackratExporter
from ..installer import Installer, InstallationError
from ..parsers.exceptions import ParsingError
from ..r_executor import ExecutorError
from ..resolver import CannotResolveError
from ..semver import VersionRange
from ..user_notifier import UserNotifier
from ..locker import Locker
from ..parsers.lock import Lock
from ..parsers.rproject import RProject, Source, Dependency
from ..sources.source_group import create_source_group_from_config_list

logger = logging.getLogger(__file__)


@click.group()
@click.option("-d", "--debug", is_flag=True, help="Show debug information")
@click.version_option()
def main(debug):
    if debug:
        logging.basicConfig(level=logging.INFO)


@main.command(
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


@main.group(help="Subcommands related to environment management")
def environment():
    pass


@environment.command(
    name="init",
    help=("Initialises a new environment with a given name,"
          "or the name \"default\" if not specified.")
)
@click.option("--base-dir",
              help=("The base directory for the environments. "
                    "If not specified, use the current directory."),
              type=click.Path(), default=".")
@click.option("--overwrite",
              help="Overwrites the environment if already present.",
              is_flag=True, default=False)
@click.option("--r-executable-path",
              help="The path to the R executable to use",
              type=click.Path(), default=None)
@click.argument("name", type=click.STRING, default="default")
def environment_init(base_dir, overwrite, r_executable_path, name):
    base_dir = pathlib.Path(base_dir)

    env = Environment(base_dir=base_dir, name=name)

    try:
        env.init(r_executable_path, overwrite)
    except Exception as e:
        logger.exception("Unable to initialise environment")
        raise click.ClickException(f"Unable to initialise environment: {e}")


@environment.command(
    name="list",
    help="List all available environments"
)
@click.option("--base-dir",
              help=("The base directory for the environments. "
                    "If not specified, use the current directory."),
              type=click.Path(), default=".")
def environment_list(base_dir):
    base_dir = pathlib.Path(base_dir)
    envs = available_environments(base_dir)
    notifier = UserNotifier()

    for env in envs:
        try:
            r_version = env.r_version_info["version"]
        except ExecutorError:
            r_version = "[error]broken R[/error]"

        if env.is_enabled():
            notifier.message(
                f"* [environment]{env.name}[/environment] "
                f"([version]{r_version}[/version])"
            )
        else:
            notifier.message(f"{env.name} ([version]{r_version}[/version])",
                             indent=2)


@environment.command(
    name="enable",
    help="Enable a given environment."
)
@click.option("--base-dir",
              help=("The base directory for the environments. "
                    "If not specified, use the current directory."),
              type=click.Path(), default=".")
@click.argument("name", type=click.STRING)
def environment_enable(base_dir, name):
    base_dir = pathlib.Path(base_dir)
    notifier = UserNotifier()

    env = Environment(base_dir=base_dir, name=name)
    try:
        env.enable(True)
    except UnexistentEnvironment:
        raise click.ClickException("Error: environment does not exist.")

    notifier.message(
        f"Environment [environment]{env.name}[/environment] enabled")


@environment.command(
    name="disable",
    help="Disable the currently enabled environment."
)
@click.option("--base-dir",
              help=("The base directory for the environments. "
                    "If not specified, use the current directory."),
              type=click.Path(), default=".")
def environment_disable(base_dir):
    base_dir = pathlib.Path(base_dir)
    notifier = UserNotifier()

    env = enabled_environment(base_dir)
    if env is None:
        return

    try:
        env.enable(False)
    except UnexistentEnvironment:
        raise click.ClickException("Error: environment does not exist.")

    notifier.message(
        f"Environment [environment]{env.name}[/environment] disabled")


@environment.command(name="remove",
                     help="Removes an environment by name")
@click.option("--base-dir", type=click.Path(), default=".")
@click.argument("name", type=click.STRING, default="default")
def environment_remove(base_dir, name):
    base_dir = pathlib.Path(base_dir)

    env = Environment(base_dir=base_dir, name=name)

    try:
        env.remove()
    except Exception as e:
        logger.exception("Unable to initialise environment")
        raise click.ClickException(f"Unable to remove environment: {e}")


@main.group(help="Subgroup for package management commands")
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


@main.command(help="Creates a lock file from the rproject.toml")
@click.option(
    "--quiet", is_flag=True, default=False,
    help="Produce no output")
@click.option(
    "--overwrite", is_flag=True, default=False,
    help="Force recreation of the roo.lock overwriting the current one")
@click.option(
    "--conservative", is_flag=True, default=False,
    help="Ensures that only minimal changes will be performed to the lock."
)
def lock(quiet, overwrite, conservative):
    notifier = UserNotifier(quiet)
    _ensure_lock(overwrite, notifier, conservative)


def _ensure_lock(overwrite, notifier, conservative) -> Lock:
    """Ensure that a lock file is present and sync"""
    try:
        rproject = RProject.parse(pathlib.Path(".") / "rproject.toml")
    except IOError:
        raise click.ClickException(
            "Unable to open rproject.toml in current directory"
        )
    lock_path = pathlib.Path(".") / "roo.lock"

    if overwrite:
        try:
            os.remove(lock_path)
        except FileNotFoundError:
            pass

    old_lock = Lock()
    try:
        old_lock = Lock.parse(lock_path)
    except FileNotFoundError:
        notifier.warning("Lockfile not found. Creating it.")
    except ParsingError as e:
        logger.exception("Unable to parse current lockfile")
        notifier.error(f"Existing Lockfile could not be parsed: {e}.")
        raise click.ClickException(f"Unable to parse current lock file: {e}")

    locker = Locker(notifier)
    try:
        new_lock = locker.lock(rproject, old_lock, conservative)
    except CannotResolveError as e:
        raise click.ClickException(f"Unable to sync lock files: {e}")

    new_lock.save(old_lock.path)
    return new_lock


@main.command(help="Installs the packages specified in the current lock file.")
@click.option("--env-base-dir",
              help="The environment base directory.",
              type=click.Path(), default=".")
@click.option("--env-name",
              help="The name of the environment to create",
              type=click.STRING, default="default")
@click.option("--quiet",
              help="Disables output",
              is_flag=True, default=False)
@click.option("--verbose-build",
              help=("Enables verbose building process. "
                    "Useful to debug errors in the build."),
              is_flag=True, default=False)
@click.option("--env-overwrite",
              help="Overwrite the environment if already existent",
              is_flag=True, default=False)
@click.option("--env-r-executable-path",
              help=("The path to the R executable to use if a new"
                    "environment needs to be created. Ignored if the"
                    "environment already exists."),
              type=click.Path(), default=None)
@click.option("--category",
              help=(
                  "Install the deps of the specified category. "
                  "Can be provided multiple times."),
              multiple=True,
              type=click.Choice(RProject.ALL_DEPENDENCY_CATEGORIES),
              )
@click.option("--serial",
              help=(
                  "Perform downloading and installation serially."
                  " Slower but safer."
              ),
              is_flag=True,
              default=False)
def install(env_base_dir: Union[str, pathlib.Path],
            env_name: str,
            quiet: bool,
            verbose_build: bool,
            env_overwrite: bool,
            env_r_executable_path: Union[str, pathlib.Path, None],
            category: list,
            serial: bool):

    notifier = UserNotifier(quiet)

    lock_file = _ensure_lock(False, notifier, False)

    env_base_dir = pathlib.Path(env_base_dir)

    if env_r_executable_path is not None:
        env_r_executable_path = pathlib.Path(env_r_executable_path)

    env = Environment(base_dir=env_base_dir, name=env_name)
    if not env.exists() or env_overwrite:
        try:
            env.init(r_executable_path=env_r_executable_path,
                     overwrite=env_overwrite
                     )
        except Exception as e:
            logger.exception("Unable to initialise environment")
            raise click.ClickException(
                f"Unable to initialise environment: {e}"
            )

    if len(category) == 0:
        categories = RProject.ALL_DEPENDENCY_CATEGORIES
    else:
        categories = list(set(category))

    installer = Installer(
        notifier,
        verbose_build=verbose_build,
        serial=serial)
    try:
        installer.install_lockfile(
            lock_file,
            env,
            install_dep_categories=categories
        )
    except InstallationError as e:
        notifier.error(f"Unable to perform installation: {e}")
        raise click.ClickException(str(e))


@main.group(help="Commands to interact with the cache")
def cache():
    pass


@cache.command(name="clear", help="Clear the cache completely")
def cache_clear():
    cache_root_dir = pathlib.Path("~/.roo/cache").expanduser()
    notifier = UserNotifier()
    notifier.message("Clearing cache")
    try:
        shutil.rmtree(cache_root_dir)
        cache_root_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise click.ClickException(f"Unable to clear cache: {e}")


@main.group(help="Commands to export data and information to different tools")
def export():
    pass


@export.command(name="lock", help="Exports lock to different formats")
@click.argument("format", type=click.Choice(["csv", "packrat"]))
@click.argument("output", type=click.Path(writable=True))
def export_lock(format, output):
    notifier = UserNotifier()
    lock_file = _ensure_lock(False, notifier, False)

    exporter: BaseExporter
    if format == "csv":
        exporter = LockCSVExporter()
    elif format == "packrat":
        exporter = LockPackratExporter()
    else:
        raise RuntimeError(f"Programming error. Not matched format {format}")

    exporter.export(lock_file, output)


@main.command(
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
