import pathlib
import shutil

import click
from roo.console import console


@click.group(help="Commands to interact with the cache")
def cache():
    pass


@cache.command(name="clear", help="Clear the cache completely")
def cache_clear():
    cache_root_dir = pathlib.Path("~/.roo/cache").expanduser()
    console().print("Clearing cache")
    try:
        shutil.rmtree(cache_root_dir)
        cache_root_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise click.ClickException(f"Unable to clear cache: {e}")
