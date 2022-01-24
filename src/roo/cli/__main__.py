import logging

import click

from roo.cli.add import add
from roo.cli.cache import cache
from roo.cli.environment import environment
from roo.cli.export import export
from roo.cli.init import init
from roo.cli.install import install
from roo.cli.lock import lock
from roo.cli.package import package
from roo.console import init_console

logger = logging.getLogger(__file__)


@click.group()
@click.option("-q", "--quiet", is_flag=True, help="Suppress any output")
@click.option("-d", "--debug", is_flag=True, help="Show debug information")
@click.version_option()
def main(quiet, debug):
    level = logging.INFO if debug else logging.CRITICAL
    logging.basicConfig(level=level)
    init_console(quiet)


main.add_command(init)
main.add_command(environment)
main.add_command(package)
main.add_command(lock)
main.add_command(install)
main.add_command(cache)
main.add_command(export)
main.add_command(add)
