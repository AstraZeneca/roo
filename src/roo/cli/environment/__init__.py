import pathlib
import logging
import click
from roo.console import console
from roo.r_executor import ExecutorError

from roo.environment import Environment, available_environments, \
    UnexistentEnvironment, enabled_environment, find_all_installed_r_homes

logger = logging.getLogger(__file__)


@click.group(help="Subcommands related to environment management")
def environment():
    pass


@environment.command(
    name="init",
    help=("Initialises a new environment with a given name, "
          "or the name \"default\" if not specified.")
)
@click.option("--base-dir",
              help=("The base directory for the environments. "
                    "If not specified, use the current directory."),
              type=click.Path(), default=".")
@click.option("--overwrite",
              help="Overwrites the environment if already present.",
              is_flag=True, default=False)
@click.option("--r-version",
              help="The version of R to use among the available ones. "
                   "If not specified, uses the highest.",
              type=click.STRING, default=None)
@click.option("--r-executable-path",
              help="The path to the R executable to use.",
              type=click.Path(), default=None)
@click.argument("name", type=click.STRING, default="default")
def environment_init(base_dir, overwrite, r_version, r_executable_path, name):
    base_dir = pathlib.Path(base_dir)

    try:
        env = Environment(base_dir=base_dir, name=name)
        env.init(r_version, r_executable_path, overwrite)
    except Exception as e:
        logger.exception("Unable to initialise environment")
        raise click.ClickException(f"Unable to initialise environment: {e}")

    console().print(f"Initialised and enabled environment "
                    f"[environment]{name}[/environment]")


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

    for env in envs:
        try:
            r_version = env.r_version_info["version"]
        except ExecutorError:
            r_version = "[error]broken R[/error]"

        if env.is_enabled():
            console().print(
                f"* [environment]{env.name}[/environment] "
                f"([version]{r_version}[/version])"
            )
        else:
            console().print(f"{env.name} ([version]{r_version}[/version])")


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

    env = Environment(base_dir=base_dir, name=name)
    try:
        env.enable(True)
    except UnexistentEnvironment:
        raise click.ClickException("Error: environment does not exist.")

    console().print(
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

    env = enabled_environment(base_dir)
    if env is None:
        return

    try:
        env.enable(False)
    except UnexistentEnvironment:
        raise click.ClickException("Error: environment does not exist.")

    console().print(
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


@environment.command(name="options",
                     help=(
                         "Show all found R executables that can be assigned "
                         "to an environment."
                     ))
def environment_options():
    all_r_homes = find_all_installed_r_homes()
    for entry in all_r_homes:
        console().print(
            ("* " if entry["active"] else "  ") +
            f"[version]{entry['version']}[/version] {entry['home_path']}"
        )
