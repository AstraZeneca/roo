import pathlib
import logging

import click
from roo.console import console
from roo.environment import enabled_environment

logger = logging.getLogger(__file__)


@click.command(
    help=(
        "Runs R or an R script in the currently active "
        "environment, using the correct R version.\n\n"
        "Note only for macOS: as a side effect, this command will switch the "
        "currently enabled R executable to the R version of the environment, "
        "if such switching is needed. As a result, it will affect other, "
        "currently running programs, as well as users of the same platform."
    ),
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.option("--env-base-dir",
              help=("The base directory for the environments. "
                    "If not specified, use the current directory."),
              type=click.Path(), default=".")
@click.pass_context
def run(context, env_base_dir):
    env_base_dir = pathlib.Path(env_base_dir)

    enabled_env = enabled_environment(env_base_dir)
    if enabled_env is None:
        console().print("[error]No environment currently enabled[/error]")
        raise click.ClickException("No environment currently enabled")

    executor = enabled_env.executor()
    executor.run(context.args)
