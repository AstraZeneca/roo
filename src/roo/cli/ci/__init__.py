import pathlib
from typing import Union
import logging

import click
from roo.console import console
from roo.environment import enabled_environment, Environment
from roo.installer import Installer, InstallationError
from roo.locker import Locker
from roo.parsers.exceptions import ParsingError
from roo.parsers.lock import Lock
from roo.parsers.rproject import RProject

logger = logging.getLogger(__file__)


@click.command(
    help="CI friendly version of install. Does not recreate the lock."
)
@click.option(
    "--env-base-dir",
    help="The environment base directory.",
    type=click.Path(), default=".")
@click.option(
    "--env-name",
    help="The name of the environment to create",
    type=click.STRING, default=None)
@click.option(
    "--quiet",
    help="Disables output",
    is_flag=True, default=False)
@click.option(
    "--verbose-build",
    help=(
        "Enables verbose building process. "
        "Useful to debug errors in the build."),
    is_flag=True, default=False
)
@click.option(
    "--env-overwrite",
    help="Overwrite the environment if already existent",
    is_flag=True, default=False)
@click.option(
    "--env-r-executable-path",
    help=(
        "The path to the R executable to use if a new"
        " environment needs to be created. Ignored if the"
        " environment already exists."
    ),
    type=click.Path(), default=None)
@click.option(
    "--category",
    help=(
        "Install the deps of the specified category. "
        "Can be provided multiple times."),
    multiple=True,
    type=click.Choice(RProject.ALL_DEPENDENCY_CATEGORIES),
)
@click.option(
    "--serial",
    help=(
        "Perform downloading and installation serially."
        " Slower but safer."
    ),
    is_flag=True,
    default=False
)
@click.option(
    "--use-vanilla",
    help=(
        "If specified, do not run any Renviron or Rprofile files."
    ),
    is_flag=True,
    default=False
)
def ci(env_base_dir: Union[str, pathlib.Path],
       env_name: str,
       quiet: bool,
       verbose_build: bool,
       env_overwrite: bool,
       env_r_executable_path: Union[str, pathlib.Path, None],
       category: list,
       serial: bool,
       use_vanilla: bool):

    try:
        rproject = RProject.parse(pathlib.Path(".") / "rproject.toml")
    except IOError:
        raise click.ClickException(
            "Unable to open rproject.toml in current directory"
        )
    lock_path = pathlib.Path(".") / "roo.lock"

    try:
        lock_file = Lock.parse(lock_path)
    except FileNotFoundError:
        console().print("[error]Lockfile not found.[/error]")
        raise click.ClickException(f"Lockfile not found")
    except ParsingError as e:
        logger.exception("Unable to parse current lockfile")
        console().print(
            f"[error]Existing Lockfile could not be parsed: {e}.[/error]")
        raise click.ClickException(f"Unable to parse current lock file: {e}")

    locker = Locker()

    if not locker.is_lock_file_sync(
            rproject, lock_file, lock_file.metadata.conservative):
        console().print(
            "[error]Lockfile is not synchronized with rproject. "
            "Cannot run roo ci.[/error]"
        )
        console().print("[error]Recreate the lock file with roo lock.[/error]")
        raise click.ClickException("Lock file is not synchronized")

    env_base_dir = pathlib.Path(env_base_dir)

    enabled_env = enabled_environment(env_base_dir)
    if enabled_env is not None:
        if env_name is None:
            # If we already have an environment enabled and no further
            # specification of parameters, we keep using that env.
            env = enabled_env
        else:
            # However, if the user specified a --env-name, we'll honor that
            env = Environment(base_dir=env_base_dir, name=env_name)
    else:
        # Otherwise, we use the env as specified, using the defaults in case.
        if env_name is None:
            env_name = "default"
        env = Environment(base_dir=env_base_dir, name=env_name)

    if env_r_executable_path is not None:
        env_r_executable_path = pathlib.Path(env_r_executable_path)

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
        verbose_build=verbose_build,
        serial=serial,
        use_vanilla=use_vanilla)

    try:
        installer.install_lockfile(
            lock_file,
            env,
            install_dep_categories=categories
        )
    except InstallationError as e:
        raise click.ClickException(str(e))
